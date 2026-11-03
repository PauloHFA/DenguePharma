"""Testes para validação determinística de extração por IA e ancoragem literal (REQ-EXT-001 a REQ-EXT-004)."""
from __future__ import annotations

import pytest

from denguepharma_analytics.clinical.extraction_validation import (
    validate_extracted_field,
    validate_extraction_batch,
)


DOC_SAMPLE = (
    "A double-blind, randomized clinical trial evaluated celgosivir (alpha-glucosidase inhibitor) "
    "versus placebo in 54 adult patients infected with DENV-1 or DENV-2. "
    "Primary endpoint: time to viral clearance. Adverse events were reported in 12/27 patients in treatment group."
)
VERSION_ID = "doc-ver-2022-001"


@pytest.mark.requirement("REQ-EXT-001")
def test_req_ext_001_preserves_version_location_and_quote():
    """Valida que para cada campo extraído são guardados document_version_id,

    localização (seção/locator) e o trecho de suporte literal (ACC-EXT-001).
    """
    res = validate_extracted_field(
        field_name="sample_size",
        original_value=54,
        document_text=DOC_SAMPLE,
        document_version_id=VERSION_ID,
        quoted_text="54 adult patients infected with DENV-1 or DENV-2",
        locator="p1-abstract-L2",
        section="Abstract",
        page=1,
    )
    assert res.is_valid is True
    assert res.absence_status == "PRESENTE"
    assert res.evidence_span is not None
    assert res.evidence_span.document_version_id == VERSION_ID
    assert res.evidence_span.section == "Abstract"
    assert res.evidence_span.page == 1
    assert res.evidence_span.locator == "p1-abstract-L2"
    assert "54 adult patients" in (res.evidence_span.quoted_text or "")


@pytest.mark.requirement("REQ-EXT-002")
def test_req_ext_002_schema_validation_and_blocks_publication():
    """Valida a saída contra o esquema e bloqueia a publicação se falhar (ACC-EXT-002)."""
    # 1. absence_status inválido
    res = validate_extracted_field(
        field_name="intervention",
        original_value="celgosivir",
        document_text=DOC_SAMPLE,
        document_version_id=VERSION_ID,
        quoted_text="evaluated celgosivir",
        locator="p1-L1",
        absence_status="STATUS_TOTALMENTE_INVALIDO",
    )
    assert res.is_valid is False
    assert res.absence_status == "INCERTO"
    assert res.published is False
    assert any("absence_status inválido" in r for r in res.rejection_reasons)

    # 2. field_name vazio
    with pytest.raises(ValueError, match="field_name é obrigatório"):
        validate_extracted_field(
            field_name="",
            original_value="celgosivir",
            document_text=DOC_SAMPLE,
            document_version_id=VERSION_ID,
            quoted_text="evaluated celgosivir",
            locator="p1-L1",
        )


@pytest.mark.requirement("REQ-EXT-003")
def test_req_ext_003_deterministic_literal_quote_and_numbers():
    """Verifica de forma determinística que o trecho citado existe no documento

    e que o número extraído aparece no trecho. Trecho inexistente rejeita o campo (ACC-EXT-003).
    """
    # Caso 1: Trecho alucinado que NÃO existe no documento
    res_fake_quote = validate_extracted_field(
        field_name="intervention",
        original_value="ivermectin",
        document_text=DOC_SAMPLE,
        document_version_id=VERSION_ID,
        quoted_text="ivermectin showed significant mortality reduction by 90%",  # alucinação
        locator="p2-results",
    )
    assert res_fake_quote.is_valid is False
    assert res_fake_quote.absence_status == "INCERTO"
    assert res_fake_quote.published is False
    assert any("inexistente no documento" in r for r in res_fake_quote.rejection_reasons)

    # Caso 2: Trecho existe no texto, mas o número extraído NÃO consta no trecho
    res_fake_num = validate_extracted_field(
        field_name="sample_size",
        original_value=120,  # alucinação de 120 quando o trecho cita 54
        document_text=DOC_SAMPLE,
        document_version_id=VERSION_ID,
        quoted_text="54 adult patients infected with DENV-1 or DENV-2",
        locator="p1-abstract",
    )
    assert res_fake_num.is_valid is False
    assert res_fake_num.absence_status == "INCERTO"
    assert res_fake_num.published is False
    assert any("Número extraído (120.0) não consta no trecho" in r for r in res_fake_num.rejection_reasons)


@pytest.mark.requirement("REQ-EXT-004")
def test_req_ext_004_abstention_and_blocks_unsupported_publication():
    """Se o modelo não produzir trecho de suporte localizável para um campo,

    registra como 'INCERTO' sem inventar número e impede a publicação (ACC-EXT-004 / T4).
    """
    # Documento sem menção a tamanho amostral de seguimento
    doc_without_n = "A prospective cohort study evaluated dengue viral kinetics without formal sample reporting."

    res_no_support = validate_extracted_field(
        field_name="n_randomized",
        original_value="200",  # IA tentou chutar 200
        document_text=doc_without_n,
        document_version_id="doc-cohort-002",
        quoted_text="",  # ausência de trecho de suporte
        locator="",  # ausência de localizador
    )
    assert res_no_support.absence_status == "INCERTO"
    assert res_no_support.normalized_value is None  # ESTRITAMENTE None; PROIBIDO INVENTAR NÚMERO
    assert res_no_support.published is False
    assert res_no_support.is_valid is False
    assert any("Sem trecho de suporte" in r for r in res_no_support.rejection_reasons)

    # Teste de lote garantindo que nenhum INCERTO é publicável
    batch = validate_extraction_batch(
        document_text=doc_without_n,
        document_version_id="doc-cohort-002",
        candidate_fields=[
            {"field_name": "n_randomized", "original_value": "200", "quoted_text": "", "locator": ""},
            {"field_name": "follow_up_days", "original_value": "30", "quoted_text": "sem suporte", "locator": "L1"},
        ],
    )
    assert batch["uncertain_abstained_count"] == 2
    assert batch["all_uncertain_unpublishable"] is True
