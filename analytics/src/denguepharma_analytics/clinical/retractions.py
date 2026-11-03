"""Módulo de Monitoramento e Tratamento de Retratações Científicas (REQ-ANA-010).

Quando um estudo publicado é retratado pela revista científica (por erro, fraude,
duplicação ou má conduta), o sistema deve removê-lo da síntese vigente,
registrando data da retratação, motivo e fonte do aviso (ex.: Retraction Watch / Crossref).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RetractionNotice:
    study_id: str
    doi: str | None
    pmid: str | None
    retraction_date: str
    reason: str
    source: str
    notice_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Registro de retratações conhecidas no ecossistema de dengue / flavivírus
KNOWN_RETRACTIONS: list[RetractionNotice] = [
    RetractionNotice(
        study_id="s_retracted_sample",
        doi="10.1016/j.antiviral.2020.104999",
        pmid="32000000",
        retraction_date="2021-04-15",
        reason="Inconsistência irreconciliável em dados primários de viabilidade celular e contagens virais in vitro.",
        source="RETRACTION_WATCH",
        notice_url="https://doi.org/10.1016/j.antiviral.2021.105100",
    ),
    RetractionNotice(
        study_id="s_ivermectin_fabricated",
        doi="10.1002/rmv.2199",
        pmid="33555555",
        retraction_date="2022-02-10",
        reason="Preocupações éticas graves e discrepâncias estatísticas não resolvidas pelos autores primários.",
        source="RETRACTION_WATCH",
        notice_url="https://doi.org/10.1002/rmv.2280",
    ),
]


def check_document_retraction(
    study_id: str,
    metadata: Mapping[str, Any] | None = None,
    extra_registry: list[RetractionNotice] | None = None,
) -> RetractionNotice | None:
    """Verifica se um estudo ou seus identificadores correspondem a um registro de retratação."""
    all_notices = (extra_registry or []) + KNOWN_RETRACTIONS
    meta = metadata or {}
    pmid = str(meta.get("pmid", "")).strip() or None
    doi = str(meta.get("doi", "")).strip().lower() or None

    for notice in all_notices:
        if notice.study_id and notice.study_id == study_id:
            return notice
        if pmid and notice.pmid and notice.pmid == pmid:
            return notice
        if doi and notice.doi and notice.doi.lower() == doi:
            return notice

    # Sinalização explícita nos metadados do documento
    if meta.get("is_retracted") is True or meta.get("retraction_date"):
        return RetractionNotice(
            study_id=study_id,
            doi=doi,
            pmid=pmid,
            retraction_date=str(meta.get("retraction_date", "DATA_NAO_INFORMADA")),
            reason=str(meta.get("retraction_reason", "Retratação informada pelo periódico de publicação")),
            source=str(meta.get("retraction_source", "EDITORIAL_NOTICE")),
            notice_url=meta.get("retraction_notice_url"),
        )

    return None


def filter_synthesis_retractions(
    studies: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    extra_registry: list[RetractionNotice] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Filtra estudos e resultados retratados, retirando-os da síntese ativa.
    
    Retorna:
    - active_studies: estudos vigentes
    - active_groups: grupos de síntese sem contribuições de estudos retratados
    - excluded_retractions: lista descritiva de estudos retirados por retratação
    """
    excluded_retractions: list[dict[str, Any]] = []
    retracted_study_ids: set[str] = set()

    active_studies: list[dict[str, Any]] = []
    for study in studies:
        sid = study["study_id"]
        notice = check_document_retraction(sid, study.get("metadata"), extra_registry)
        if notice:
            retracted_study_ids.add(sid)
            excluded_retractions.append({
                "study_id": sid,
                "title": study.get("title", sid),
                "status": "RETRATADO",
                "retraction_date": notice.retraction_date,
                "reason": notice.reason,
                "source": notice.source,
                "notice_url": notice.notice_url,
                "exclusion_policy": "EXCLUIDO_DA_SINTESE_VIGENTE",
            })
        else:
            active_studies.append(study)

    # Remove os resultados de estudos retratados de todos os grupos de síntese
    active_groups: list[dict[str, Any]] = []
    for group in groups:
        clean_results = [
            r for r in group.get("results", [])
            if r.get("study_id") not in retracted_study_ids
        ]
        if clean_results:
            active_groups.append({**group, "results": clean_results})

    return active_studies, active_groups, excluded_retractions
