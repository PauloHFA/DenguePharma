"""Módulo de auditoria de discrepâncias Registro vs. Publicação e detecção de versão (Eixo B - REQ-ANA-005 e REQ-ING-006).

Regras e salvaguardas:
- REQ-ANA-005: Compara campos do registro (ClinicalTrials) e da publicação (PubMed/PMC),
  como desfecho primário, tamanho amostral (N) e datas, gerando discrepâncias
  classificadas para revisão humana (detecção de outcome switching).
- REQ-ING-006: Quando o hash de um registro mudar, cria nova DocumentVersion,
  calcula a diferença de campos e abre tarefa de reavaliação, preservando a decisão anterior intacta.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RegistryRecord:
    study_id: str
    primary_outcome: str
    sample_size: int
    completion_date: str
    status: str
    source: str = "CLINICAL_TRIALS"
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            raw = f"{self.study_id}|{self.primary_outcome}|{self.sample_size}|{self.completion_date}|{self.status}"
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            object.__setattr__(self, "content_hash", h)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PublicationRecord:
    study_id: str
    pmid: str
    primary_outcome: str
    sample_size: int
    publication_date: str
    source: str = "PUBMED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscrepancyItem:
    study_id: str
    field_name: str
    registry_value: Any
    publication_value: Any
    discrepancy_type: str  # 'OUTCOME_SWITCHING', 'SAMPLE_SIZE_MISMATCH', 'TIMELINE_SHIFT'
    severity: str  # 'CRITICA', 'MODERADA', 'INFORMATIVA'
    routing_status: str = "AGUARDA_REVISAO_HUMANA"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscrepancyReport:
    study_id: str
    has_discrepancies: bool
    discrepancies_count: int
    critical_count: int
    items: list[DiscrepancyItem]
    audit_notice: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "has_discrepancies": self.has_discrepancies,
            "discrepancies_count": self.discrepancies_count,
            "critical_count": self.critical_count,
            "items": [item.to_dict() for item in self.items],
            "audit_notice": self.audit_notice,
        }


def normalize_outcome_text(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def compare_registry_and_publication(
    registry: RegistryRecord,
    publication: PublicationRecord,
) -> DiscrepancyReport:
    """Compara campos entre pré-registro e artigo final e classifica discrepâncias (REQ-ANA-005)."""
    if registry.study_id != publication.study_id:
        raise ValueError(f"study_id incompatível: {registry.study_id} vs {publication.study_id}")

    items: list[DiscrepancyItem] = []

    # 1. Comparação de Desfecho Primário (Detecção de Outcome Switching)
    reg_out_norm = normalize_outcome_text(registry.primary_outcome)
    pub_out_norm = normalize_outcome_text(publication.primary_outcome)

    if reg_out_norm != pub_out_norm:
        # Se os termos centrais divergirem, classifica como OUTCOME_SWITCHING crítico
        items.append(
            DiscrepancyItem(
                study_id=registry.study_id,
                field_name="primary_outcome",
                registry_value=registry.primary_outcome,
                publication_value=publication.primary_outcome,
                discrepancy_type="OUTCOME_SWITCHING",
                severity="CRITICA",
                routing_status="AGUARDA_REVISAO_HUMANA",
            )
        )

    # 2. Comparação de Tamanho Amostral
    if registry.sample_size != publication.sample_size:
        items.append(
            DiscrepancyItem(
                study_id=registry.study_id,
                field_name="sample_size",
                registry_value=registry.sample_size,
                publication_value=publication.sample_size,
                discrepancy_type="SAMPLE_SIZE_MISMATCH",
                severity="MODERADA",
                routing_status="AGUARDA_REVISAO_HUMANA",
            )
        )

    # 3. Comparação Temporal (Ano de Conclusão vs Publicação)
    reg_year = registry.completion_date[:4] if len(registry.completion_date) >= 4 else ""
    pub_year = publication.publication_date[:4] if len(publication.publication_date) >= 4 else ""
    if reg_year and pub_year and int(pub_year) < int(reg_year):
        items.append(
            DiscrepancyItem(
                study_id=registry.study_id,
                field_name="dates",
                registry_value=registry.completion_date,
                publication_value=publication.publication_date,
                discrepancy_type="TIMELINE_SHIFT",
                severity="INFORMATIVA",
                routing_status="AGUARDA_REVISAO_HUMANA",
            )
        )

    critical_count = sum(1 for i in items if i.severity == "CRITICA")

    return DiscrepancyReport(
        study_id=registry.study_id,
        has_discrepancies=len(items) > 0,
        discrepancies_count=len(items),
        critical_count=critical_count,
        items=items,
        audit_notice="Discrepâncias detectadas enviadas à revisão humana; não alteram o corpus automaticamente (REQ-ANA-005).",
    )


@dataclass(frozen=True)
class VersionDiffReport:
    study_id: str
    previous_hash: str
    current_hash: str
    version_incremented: bool
    new_version_id: str
    changed_fields: list[str]
    diff: dict[str, dict[str, Any]]
    reassessment_task_opened: bool
    preserves_prior_decision: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_registry_version_change(
    previous: RegistryRecord,
    current: RegistryRecord,
    previous_version_number: int = 1,
) -> VersionDiffReport:
    """Quando o hash mudar, cria nova DocumentVersion, calcula diff e abre fila de reavaliação (REQ-ING-006)."""
    if previous.study_id != current.study_id:
        raise ValueError(f"study_id incompatível: {previous.study_id} vs {current.study_id}")

    prev_dict = previous.to_dict()
    curr_dict = current.to_dict()

    changed_fields: list[str] = []
    diff_details: dict[str, dict[str, Any]] = {}

    for k in ("primary_outcome", "sample_size", "completion_date", "status"):
        if prev_dict.get(k) != curr_dict.get(k):
            changed_fields.append(k)
            diff_details[k] = {
                "before": prev_dict.get(k),
                "after": curr_dict.get(k),
            }

    hash_changed = previous.content_hash != current.content_hash
    new_ver_num = previous_version_number + 1 if hash_changed else previous_version_number
    new_version_id = f"dv-{current.study_id.lower()}-v{new_ver_num}"

    return VersionDiffReport(
        study_id=current.study_id,
        previous_hash=previous.content_hash,
        current_hash=current.content_hash,
        version_incremented=hash_changed,
        new_version_id=new_version_id,
        changed_fields=changed_fields,
        diff=diff_details,
        reassessment_task_opened=hash_changed,
        preserves_prior_decision=True,  # Decisões anteriores nunca são sobrescritas
    )

