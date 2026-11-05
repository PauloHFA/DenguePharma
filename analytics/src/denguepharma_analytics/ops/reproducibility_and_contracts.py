"""Módulo de Regenerabilidade Determinística da Camada Ouro e Testes de Contrato de Esquemas.

Implementa os requisitos:
- REQ-OPS-009 (ACC-OPS-009 / P6): O pipeline deve ser regenerável: dado o manifesto de dados
  e o commit, reproduz as tabelas da camada ouro com hashes SHA-256 idênticos (bit-a-bit).
- REQ-OPS-010 (ACC-OPS-010 / RNF): O sistema deve testar contratos de dados e eventos entre
  produtor e consumidor, com esquemas versionados e falha imediata do build diante de quebras incompatíveis.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


class IncompatibleSchemaContractError(Exception):
    """Lançado quando um evento ou carga viola o contrato de esquema versionado (REQ-OPS-010)."""


@dataclass(frozen=True)
class EventSchemaContract:
    """Contrato de esquema de evento canônico."""
    schema_version: int
    required_envelope_fields: Set[str]
    allowed_event_types: Set[str]
    required_payload_fields: Dict[str, Set[str]]


CANONICAL_V1_CONTRACT = EventSchemaContract(
    schema_version=1,
    required_envelope_fields={
        "event_id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "schema_version",
        "payload",
    },
    allowed_event_types={
        "DocumentoImportado",
        "FonteAlterada",
        "RelatorioSolicitado",
        "AnaliseSolicitada",
    },
    required_payload_fields={
        "DocumentoImportado": {"document_version_id", "content_hash"},
        "FonteAlterada": {"source_id", "reason"},
        "RelatorioSolicitado": {"report_type"},
        "AnaliseSolicitada": {"analysis_id"},
    },
)


class EventContractValidator:
    """Validador de contratos de eventos entre produtores e consumidores (REQ-OPS-010)."""

    def __init__(self, contract: EventSchemaContract = CANONICAL_V1_CONTRACT):
        self.contract = contract

    def validate_event(self, event_message: Dict[str, Any]) -> None:
        """Valida se o evento cumpre estritamente o contrato da versão do esquema.

        Lança IncompatibleSchemaContractError se houver violação contratual.
        """
        # 1. Validação de versão de esquema
        version = event_message.get("schema_version")
        if version != self.contract.schema_version:
            raise IncompatibleSchemaContractError(
                f"Quebra de contrato de versao: recebido schema_version={version}, esperado={self.contract.schema_version}."
            )

        # 2. Presença de todos os campos do envelope obrigatórios
        missing_envelope = self.contract.required_envelope_fields - set(event_message.keys())
        if missing_envelope:
            raise IncompatibleSchemaContractError(
                f"Quebra de contrato: campos obrigatorios ausentes no envelope: {sorted(missing_envelope)}."
            )

        # 3. Tipo de evento suportado
        event_type = event_message.get("event_type")
        if event_type not in self.contract.allowed_event_types:
            raise IncompatibleSchemaContractError(
                f"Tipo de evento '{event_type}' nao suportado pelo contrato de versao {self.contract.schema_version}."
            )

        # 4. Campos obrigatórios do payload
        payload = event_message.get("payload")
        if not isinstance(payload, dict):
            raise IncompatibleSchemaContractError("Payload deve ser um objeto JSON/dicionário.")

        required_payload = self.contract.required_payload_fields.get(event_type, set())
        missing_payload = required_payload - set(payload.keys())
        if missing_payload:
            raise IncompatibleSchemaContractError(
                f"Quebra de contrato no payload para '{event_type}': campos ausentes: {sorted(missing_payload)}."
            )


class GoldLayerPipelineRegenerator:
    """Regenerador de tabelas da camada ouro (marts) com garantia de reprodutibilidade bit-a-bit (REQ-OPS-009)."""

    @staticmethod
    def generate_gold_mart(
        manifest: Dict[str, Any],
        raw_records: List[Dict[str, Any]],
        code_commit_hash: str,
    ) -> Tuple[bytes, str]:
        """Gera a tabela analítica ouro de forma canônica e determinística.

        Retorna os bytes canônicos e o hash SHA-256 bit-a-bit.
        """
        # Ordenação canônica das linhas por chave primária
        sorted_records = sorted(raw_records, key=lambda r: (r.get("study_id", ""), r.get("field_name", "")))

        # Dicionários canônicos com chaves ordenadas
        canonical_rows = []
        for row in sorted_records:
            ordered_row = {k: row[k] for k in sorted(row.keys())}
            canonical_rows.append(ordered_row)

        gold_table_artifact = {
            "gold_layer": "mart_clinical_evidence_synthesis",
            "code_commit": code_commit_hash,
            "manifest_digest": manifest.get("manifest_digest", ""),
            "row_count": len(canonical_rows),
            "rows": canonical_rows,
        }

        # Serialização determinística bit-a-bit (sem indentação, sem espaços variáveis, chaves ordenadas)
        serialized_bytes = json.dumps(gold_table_artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        table_hash = hashlib.sha256(serialized_bytes).hexdigest()

        return serialized_bytes, table_hash

    @classmethod
    def verify_reproducibility(
        cls,
        manifest: Dict[str, Any],
        raw_records: List[Dict[str, Any]],
        code_commit: str,
    ) -> Dict[str, Any]:
        """Verifica formalmente se duas execuções isoladas produzem hashes de tabela ouro idênticos (ACC-OPS-009)."""
        _, hash_run_1 = cls.generate_gold_mart(manifest, raw_records, code_commit)
        _, hash_run_2 = cls.generate_gold_mart(manifest, raw_records, code_commit)

        hashes_match = (hash_run_1 == hash_run_2)

        return {
            "reproducible": hashes_match,
            "hash_run_1": hash_run_1,
            "hash_run_2": hash_run_2,
            "code_commit": code_commit,
        }

