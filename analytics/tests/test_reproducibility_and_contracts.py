"""Testes para regenerabilidade da camada ouro e testes de contrato de esquemas versionados.

Cobre formalmente:
- REQ-OPS-009 (ACC-OPS-009 / P6): Pipeline regenerável: dado o manifesto de dados e o commit,
  reproduz tabelas ouro com hashes idênticos (bit-a-bit).
- REQ-OPS-010 (ACC-OPS-010 / RNF): Testes de contrato de dados e eventos entre produtor e
  consumidor, com esquemas versionados e falha sob incompatibilidade.
"""

from __future__ import annotations

import pytest
from denguepharma_analytics.ops.reproducibility_and_contracts import (
    EventContractValidator,
    GoldLayerPipelineRegenerator,
    IncompatibleSchemaContractError,
)


@pytest.mark.requirement("REQ-OPS-009")
def test_gold_layer_pipeline_reproducibility_bit_a_bit():
    """Cobre ACC-OPS-009: Dado o mesmo manifesto e código, quando reexecutado,

    então os hashes das tabelas ouro coincidem perfeitamente (bit-a-bit).
    """
    manifest = {
        "dataset_version": "v1.0",
        "manifest_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sources": ["pubmed", "clinicaltrials.gov"],
    }
    raw_evidence_records = [
        {"study_id": "ST-002", "field_name": "efficacy", "value": "0.78", "grade": "MODERATE"},
        {"study_id": "ST-001", "field_name": "sample_size", "value": "120", "grade": "HIGH"},
        {"study_id": "ST-001", "field_name": "adverse_events", "value": "12/120", "grade": "HIGH"},
    ]
    code_commit = "355a7b1b0c950285a86d525fa6c2780bbca6f731"

    # Duas execuções separadas da pipeline de regeneração
    verification = GoldLayerPipelineRegenerator.verify_reproducibility(
        manifest=manifest,
        raw_records=raw_evidence_records,
        code_commit=code_commit,
    )

    assert verification["reproducible"] is True
    assert verification["hash_run_1"] == verification["hash_run_2"]
    assert len(verification["hash_run_1"]) == 64

    # Alteração em registro bruto resulta em hash estritamente diferente
    altered_records = list(raw_evidence_records)
    altered_records[0] = {"study_id": "ST-002", "field_name": "efficacy", "value": "0.80", "grade": "MODERATE"}

    _, altered_hash = GoldLayerPipelineRegenerator.generate_gold_mart(manifest, altered_records, code_commit)
    assert altered_hash != verification["hash_run_1"]


@pytest.mark.requirement("REQ-OPS-010")
def test_event_contract_accepts_valid_version_1_schema():
    """Testa conformidade de evento válido com o contrato versionado V1."""
    validator = EventContractValidator()

    valid_event = {
        "event_id": "evt-uuid-100",
        "event_type": "DocumentoImportado",
        "aggregate_type": "DocumentVersion",
        "aggregate_id": "doc-uuid-200",
        "schema_version": 1,
        "payload": {
            "document_version_id": "doc-uuid-200",
            "content_hash": "a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef",
        },
    }

    # Validação deve passar sem exceções
    validator.validate_event(valid_event)


@pytest.mark.requirement("REQ-OPS-010")
def test_event_contract_fails_build_on_incompatible_schema_change():
    """Cobre ACC-OPS-010: Dado uma mudança incompatível de esquema, quando o teste de

    contrato rodar, então o build falha (IncompatibleSchemaContractError).
    """
    validator = EventContractValidator()

    # 1. Mudança incompatível de versão de esquema (ex: produtor publicando v2 sem suporte do consumidor)
    incompatible_version_event = {
        "event_id": "evt-uuid-101",
        "event_type": "DocumentoImportado",
        "aggregate_type": "DocumentVersion",
        "aggregate_id": "doc-uuid-200",
        "schema_version": 2,  # Quebra incompatível
        "payload": {"document_version_id": "doc-uuid-200", "content_hash": "hash123"},
    }
    with pytest.raises(IncompatibleSchemaContractError) as exc_info:
        validator.validate_event(incompatible_version_event)
    assert "Quebra de contrato de versao" in str(exc_info.value)

    # 2. Remoção de campo obrigatório do envelope (ex: ausência de aggregate_type)
    missing_field_event = {
        "event_id": "evt-uuid-102",
        "event_type": "DocumentoImportado",
        "aggregate_id": "doc-uuid-200",
        "schema_version": 1,
        "payload": {"document_version_id": "doc-uuid-200", "content_hash": "hash123"},
    }
    with pytest.raises(IncompatibleSchemaContractError) as exc_info:
        validator.validate_event(missing_field_event)
    assert "campos obrigatorios ausentes no envelope" in str(exc_info.value)

    # 3. Remoção de campo obrigatório dentro do payload (ex: ausência de content_hash)
    missing_payload_field_event = {
        "event_id": "evt-uuid-103",
        "event_type": "DocumentoImportado",
        "aggregate_type": "DocumentVersion",
        "aggregate_id": "doc-uuid-200",
        "schema_version": 1,
        "payload": {"document_version_id": "doc-uuid-200"},  # Falta content_hash
    }
    with pytest.raises(IncompatibleSchemaContractError) as exc_info:
        validator.validate_event(missing_payload_field_event)
    assert "Quebra de contrato no payload" in str(exc_info.value)

