"""Testes de monitoramento e exclusão de estudos retratados na síntese (REQ-ANA-010)."""
import copy
import pytest

from test_clinical import workspace, R1, R2, ADJ, screen, CLASSIFICATION
from denguepharma_analytics.clinical.retractions import (
    RetractionNotice,
    check_document_retraction,
    filter_synthesis_retractions,
)
from denguepharma_analytics.clinical.synthesis import view


@pytest.mark.requirement("REQ-ANA-010")
def test_retraction_detection_by_identifiers():
    notice = check_document_retraction("s_retracted_sample")
    assert notice is not None
    assert notice.retraction_date == "2021-04-15"
    assert "Inconsistência" in notice.reason
    assert notice.source == "RETRACTION_WATCH"

    # Verificação por DOI
    notice_doi = check_document_retraction("any_id", metadata={"doi": "10.1016/j.antiviral.2020.104999"})
    assert notice_doi is not None
    assert notice_doi.pmid == "32000000"

    # Verificação por PMID
    notice_pmid = check_document_retraction("any_id", metadata={"pmid": "33555555"})
    assert notice_pmid is not None
    assert notice_pmid.study_id == "s_ivermectin_fabricated"

    # Estudo idôneo não retratado
    clean = check_document_retraction("study_clean", metadata={"pmid": "99999999", "doi": "10.1000/clean"})
    assert clean is None


@pytest.mark.requirement("REQ-ANA-010")
def test_filter_synthesis_retractions_excludes_retracted_and_records_reason():
    studies = [
        {"study_id": "s_clean_1", "title": "Estudo Válido Balapiravir", "metadata": {"pmid": "111"}},
        {"study_id": "s_retracted_sample", "title": "Estudo Problemático Retratado", "metadata": {"pmid": "32000000"}},
    ]
    groups = [
        {
            "scope": {"substance": "TEST-DRUG"},
            "results": [
                {"study_id": "s_clean_1", "effect": 0.85},
                {"study_id": "s_retracted_sample", "effect": 0.20},
            ],
        }
    ]

    active_studies, active_groups, retracted_studies = filter_synthesis_retractions(studies, groups)

    # 1. Estudo retratado é removido dos estudos ativos da síntese
    assert len(active_studies) == 1
    assert active_studies[0]["study_id"] == "s_clean_1"

    # 2. Resultado do estudo retratado é expurgado dos grupos de síntese
    assert len(active_groups) == 1
    assert len(active_groups[0]["results"]) == 1
    assert active_groups[0]["results"][0]["study_id"] == "s_clean_1"

    # 3. Registro auditável em retracted_studies com motivo e data
    assert len(retracted_studies) == 1
    retracted = retracted_studies[0]
    assert retracted["study_id"] == "s_retracted_sample"
    assert retracted["status"] == "RETRATADO"
    assert retracted["retraction_date"] == "2021-04-15"
    assert "Inconsistência" in retracted["reason"]
    assert retracted["exclusion_policy"] == "EXCLUIDO_DA_SINTESE_VIGENTE"


@pytest.mark.requirement("REQ-ANA-010")
def test_workspace_synthesis_view_integrates_retraction_filtering(workspace):
    synth_view = view(workspace, ADJ)
    assert "retracted_studies" in synth_view
    assert isinstance(synth_view["retracted_studies"], list)
