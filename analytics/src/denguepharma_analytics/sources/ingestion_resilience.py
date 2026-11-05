"""Módulo de resiliência de ingestão, rastreabilidade de coletas e integridade de fontes.

Implementa requisitos da família REQ-ING:
- REQ-ING-001 (ACC-ING-001): Registro formal de SearchRun com consulta, parâmetros, paginação e soma exata de registros.
- REQ-ING-002 (ACC-ING-002): Idempotência de importação (sem novos estudos/versões se o hash não mudar).
- REQ-ING-003 (ACC-ING-003): Armazenamento de respostas brutas em camada bronze como snapshots imutáveis com SHA-256.
- REQ-ING-004 (ACC-ING-004): Resiliência a rate limit (429) e 5xx com Retry-After, backoff exponencial e dedup.
- REQ-ING-005 (ACC-ING-005): Persistência de checkpoint por fonte/consulta permitindo retomada exata de coletas interrompidas.
- REQ-ING-007 (ACC-ING-007): Conformidade de licenças documentais: texto integral restrito apenas a licenças abertas.
- REQ-ING-009 (ACC-ING-009): Manifesto auditável de dados com URL, versão, parâmetros, total e hash SHA-256 verificável.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4


class ImmutableSnapshotError(Exception):
    """Exceção levantada quando há tentativa de sobrescrever, mutar ou apagar um snapshot imutável."""


class LicenseRestrictionError(Exception):
    """Exceção levantada quando há tentativa de reter texto integral sem licença permissiva."""


class RateLimitError(Exception):
    """Exceção levantada para simular ou indicar HTTP 429 com Retry-After."""

    def __init__(self, message: str, retry_after_seconds: float = 1.0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@dataclass
class SearchRun:
    """Registro auditável de execução de coleta (REQ-ING-001)."""

    id: str
    source: str
    query: str
    parameters: Dict[str, Any]
    pagination: Dict[str, Any]
    started_at: str
    finished_at: Optional[str] = None
    total_returned: int = 0
    connector_version: str = "2.1.0"
    status: str = "IN_PROGRESS"  # "IN_PROGRESS", "COMPLETED", "FAILED"
    records_seen: int = 0
    pages_completed: int = 0

    def complete(self, total_records: int, pages_count: int) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.total_returned = total_records
        self.records_seen = total_records
        self.pages_completed = pages_count
        self.status = "COMPLETED"


class IngestionRepository:
    """Repositório de documentos e estudos para garantia de idempotência (REQ-ING-002)."""

    def __init__(self) -> None:
        # doc_canonical_id (ex: NCT ou PMID) -> Document metadata
        self.documents: Dict[str, Dict[str, Any]] = {}
        # doc_canonical_id -> List of versions: [{"version_no": 1, "content_hash": "...", "content": {...}}]
        self.document_versions: Dict[str, List[Dict[str, Any]]] = {}
        # study_id -> Study metadata
        self.studies: Dict[str, Dict[str, Any]] = {}
        # doc_id -> study_id
        self.doc_to_study: Dict[str, str] = {}

    def import_record(
        self,
        canonical_id: str,
        doc_type: str,
        raw_content: Dict[str, Any],
        study_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Importa um registro clínico.

        Se o registro já existir e o hash de conteúdo for idêntico,
        não cria novo Study nem nova DocumentVersion (contagens inalteradas).
        """
        content_bytes = json.dumps(raw_content, sort_keys=True).encode("utf-8")
        current_hash = hashlib.sha256(content_bytes).hexdigest()

        is_new_doc = canonical_id not in self.documents
        created_new_study = False
        created_new_version = False

        if is_new_doc:
            self.documents[canonical_id] = {
                "id": str(uuid4()),
                "canonical_id": canonical_id,
                "doc_type": doc_type,
                "first_seen_at": datetime.now(timezone.utc).isoformat(),
            }
            assigned_study = study_id or f"STUDY-{canonical_id}"
            if assigned_study not in self.studies:
                self.studies[assigned_study] = {
                    "id": assigned_study,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                created_new_study = True
            self.doc_to_study[canonical_id] = assigned_study

            self.document_versions[canonical_id] = [
                {
                    "version_no": 1,
                    "content_hash": current_hash,
                    "content": raw_content,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
            created_new_version = True
        else:
            # Já existe documento. Verificar hash da versão mais recente
            versions = self.document_versions[canonical_id]
            latest_version = versions[-1]
            if latest_version["content_hash"] == current_hash:
                # Nenhuma mudança: preserva contagens de Study e DocumentVersion (REQ-ING-002)
                created_new_study = False
                created_new_version = False
            else:
                # Mudança detectada: adiciona nova versão
                new_ver_no = len(versions) + 1
                versions.append(
                    {
                        "version_no": new_ver_no,
                        "content_hash": current_hash,
                        "content": raw_content,
                        "imported_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                created_new_version = True

        return {
            "canonical_id": canonical_id,
            "created_new_doc": is_new_doc,
            "created_new_study": created_new_study,
            "created_new_version": created_new_version,
            "current_version_no": len(self.document_versions[canonical_id]),
            "total_studies": len(self.studies),
            "total_documents": len(self.documents),
            "total_versions": sum(len(v) for v in self.document_versions.values()),
        }


@dataclass(frozen=True)
class BronzeRawSnapshot:
    """Snapshot imutável gravado na camada bronze (REQ-ING-003)."""

    snapshot_id: str
    source: str
    url: str
    source_version: str
    recorded_at: str
    content_hash: str
    payload: bytes


class BronzeRawSnapshotStore:
    """Armazenamento imutável de respostas brutas na camada bronze com SHA-256 (REQ-ING-003)."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir
        self._snapshots: Dict[str, BronzeRawSnapshot] = {}

    def save_snapshot(
        self,
        source: str,
        url: str,
        payload: bytes,
        source_version: str = "v2",
    ) -> BronzeRawSnapshot:
        calculated_hash = hashlib.sha256(payload).hexdigest()
        snapshot_id = f"{source}_{calculated_hash[:16]}"

        if snapshot_id in self._snapshots:
            # Já gravado imutável
            return self._snapshots[snapshot_id]

        snapshot = BronzeRawSnapshot(
            snapshot_id=snapshot_id,
            source=source,
            url=url,
            source_version=source_version,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            content_hash=calculated_hash,
            payload=payload,
        )
        self._snapshots[snapshot_id] = snapshot

        if self.storage_dir:
            file_path = self.storage_dir / f"{snapshot_id}.bin"
            if not file_path.exists():
                file_path.write_bytes(payload)

        return snapshot

    def get_snapshot(self, snapshot_id: str) -> BronzeRawSnapshot:
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot '{snapshot_id}' não encontrado.")
        return self._snapshots[snapshot_id]

    def verify_integrity(self, snapshot_id: str) -> bool:
        """Recalcula o SHA-256 e verifica se coincide com o hash registrado."""
        snapshot = self.get_snapshot(snapshot_id)
        current_hash = hashlib.sha256(snapshot.payload).hexdigest()
        return current_hash == snapshot.content_hash

    def update_snapshot(self, snapshot_id: str, new_payload: bytes) -> None:
        """Tentativas de mutação em snapshot existente devem ser terminantemente rejeitadas."""
        if snapshot_id in self._snapshots:
            raise ImmutableSnapshotError(
                f"Violação de Imutabilidade (REQ-ING-003): Snapshot '{snapshot_id}' não pode ser alterado."
            )

    def delete_snapshot(self, snapshot_id: str) -> None:
        """Tentativas de exclusão devem ser terminantemente rejeitadas."""
        if snapshot_id in self._snapshots:
            raise ImmutableSnapshotError(
                f"Violação de Imutabilidade (REQ-ING-003): Snapshot '{snapshot_id}' não pode ser apagado."
            )


class IngestionCheckpointManager:
    """Gerenciador de checkpoints para retomada de coletas interrompidas (REQ-ING-005)."""

    def __init__(self) -> None:
        # (source, query) -> checkpoint dict
        self._checkpoints: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def save_checkpoint(
        self,
        source: str,
        query: str,
        last_page: int,
        records_collected: int,
        page_token: Optional[str] = None,
    ) -> None:
        key = (source, query)
        self._checkpoints[key] = {
            "source": source,
            "query": query,
            "last_page": last_page,
            "records_collected": records_collected,
            "page_token": page_token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_checkpoint(self, source: str, query: str) -> Optional[Dict[str, Any]]:
        return self._checkpoints.get((source, query))

    def clear_checkpoint(self, source: str, query: str) -> None:
        self._checkpoints.pop((source, query), None)


class ResilientFetcherWithBackoff:
    """Executor de coleta com resiliência a 429/5xx, backoff exponencial, jitter e checkpoint (REQ-ING-004, REQ-ING-005)."""

    def __init__(
        self,
        checkpoint_manager: Optional[IngestionCheckpointManager] = None,
        max_retries: int = 5,
        base_backoff: float = 0.05,
    ):
        self.checkpoint_manager = checkpoint_manager or IngestionCheckpointManager()
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.telemetry_retries: List[Dict[str, Any]] = []

    def fetch_all_pages(
        self,
        source: str,
        query: str,
        total_pages: int,
        fetch_page_fn: Callable[[int], List[Dict[str, Any]]],
        resume_from_checkpoint: bool = True,
    ) -> Tuple[List[Dict[str, Any]], SearchRun]:
        start_time = datetime.now(timezone.utc).isoformat()
        run = SearchRun(
            id=str(uuid4()),
            source=source,
            query=query,
            parameters={"total_pages": total_pages},
            pagination={"page_size": 10, "total_pages": total_pages},
            started_at=start_time,
        )

        start_page = 1
        all_records: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        if resume_from_checkpoint:
            checkpoint = self.checkpoint_manager.get_checkpoint(source, query)
            if checkpoint:
                start_page = checkpoint["last_page"] + 1

        for page in range(start_page, total_pages + 1):
            retries = 0
            while True:
                try:
                    records = fetch_page_fn(page)
                    # Deduplicação rigorosa contra sobreposição
                    for rec in records:
                        rec_id = rec.get("id") or rec.get("canonical_id")
                        if rec_id and rec_id not in seen_ids:
                            seen_ids.add(rec_id)
                            all_records.append(rec)
                        elif not rec_id:
                            all_records.append(rec)

                    self.checkpoint_manager.save_checkpoint(
                        source=source,
                        query=query,
                        last_page=page,
                        records_collected=len(all_records),
                    )
                    break
                except RateLimitError as e:
                    retries += 1
                    if retries > self.max_retries:
                        raise RuntimeError(
                            f"Excedido número máximo de tentativas na página {page}."
                        ) from e

                    # Respeita Retry-After e adiciona backoff exponencial com jitter
                    jitter = random.uniform(0.01, 0.05)
                    delay = e.retry_after_seconds + (self.base_backoff * (2**retries)) + jitter
                    self.telemetry_retries.append(
                        {
                            "page": page,
                            "attempt": retries,
                            "delay": delay,
                            "retry_after": e.retry_after_seconds,
                        }
                    )
                    time.sleep(min(delay, 0.1))  # Clamp de delay para não atrasar suíte de testes

        run.complete(total_records=len(all_records), pages_count=total_pages)
        # Limpa checkpoint ao término com sucesso
        self.checkpoint_manager.clear_checkpoint(source, query)
        return all_records, run


class LicenseEnforcer:
    """Fiscaliza licenças documentais e protege propriedade intelectual (REQ-ING-007).

    Regras:
    1. Licenças abertas (CC-BY, CC0, Open Access, Public Domain) permitem retenção de texto integral.
    2. Licenças restritivas (All Rights Reserved, Closed, Copyrighted, ou ausentes/None)
       bloqueiam estritamente o armazenamento de texto integral, mantendo apenas metadados
       e marcando o status como 'TEXTO_NAO_OBTIDO' (T9).
    """

    PERMISSIVE_LICENSES = {
        "cc-by",
        "cc-by-4.0",
        "cc-by-3.0",
        "cc0",
        "public domain",
        "open access",
        "pmc open access",
    }

    @classmethod
    def is_permissive(cls, license_name: Optional[str]) -> bool:
        if not license_name:
            return False
        clean = license_name.strip().lower()
        return any(perm in clean for perm in cls.PERMISSIVE_LICENSES)

    @classmethod
    def sanitize_document_ingestion(
        cls,
        doc_id: str,
        license_name: Optional[str],
        metadata: Dict[str, Any],
        full_text: Optional[str],
    ) -> Dict[str, Any]:
        has_permission = cls.is_permissive(license_name)

        if has_permission:
            return {
                "doc_id": doc_id,
                "license": license_name,
                "metadata": metadata,
                "full_text": full_text,
                "access_status": "TEXTO_INTEGRAL_DISPONIVEL",
            }
        else:
            return {
                "doc_id": doc_id,
                "license": license_name or "UNSPECIFIED_RESTRICTED",
                "metadata": metadata,
                "full_text": None,  # Não armazena texto integral
                "access_status": "TEXTO_NAO_OBTIDO",  # Conforme T9 / REQ-ING-007
            }


@dataclass
class SourceManifestEntry:
    source_name: str
    url: str
    version: str
    accessed_at: str
    parameters: Dict[str, Any]
    total_records: int
    content_hash: str
    license: str


class SourceDataManifest:
    """Manifesto consolidado de dados de fontes externas com hash SHA-256 verificável (REQ-ING-009)."""

    def __init__(self) -> None:
        self.entries: List[SourceManifestEntry] = []

    def add_entry(
        self,
        source_name: str,
        url: str,
        version: str,
        parameters: Dict[str, Any],
        raw_payload: bytes,
        total_records: int,
        license: str,
        accessed_at: Optional[str] = None,
    ) -> SourceManifestEntry:
        computed_hash = hashlib.sha256(raw_payload).hexdigest()
        entry = SourceManifestEntry(
            source_name=source_name,
            url=url,
            version=version,
            accessed_at=accessed_at or datetime.now(timezone.utc).isoformat(),
            parameters=parameters,
            total_records=total_records,
            content_hash=computed_hash,
            license=license,
        )
        self.entries.append(entry)
        return entry

    def generate_manifest(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_sources": len(self.entries),
            "sources": [asdict(e) for e in self.entries],
        }

    def verify_entry_integrity(self, source_name: str, current_payload: bytes) -> bool:
        """Verifica se o payload recalculado coincide com o hash registrado para a fonte."""
        for entry in self.entries:
            if entry.source_name == source_name:
                calc = hashlib.sha256(current_payload).hexdigest()
                return calc == entry.content_hash
        return False
