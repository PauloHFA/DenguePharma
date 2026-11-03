"""Testes para auditoria de discrepâncias (REQ-ANA-005) e versionamento por hash (REQ-ING-006)."""
from __future__ import annotations

import pytest

from denguepharma_analytics.analyses.discrepancies import (
    PublicationRecord,
    RegistryRecord,
    compare_registry_and_publication,
    detect_registry_version_change,
)


@pytest.mark.requirement("REQ-ANA-005")
def test_outcome_switching_and_discrepancy_detection():
    """Valida que desfecho primário diferente entre registro e publicação

    gera discrepância crítica de OUTCOME_SWITCHING roteada para revisão humana (ACC-ANA-005).
    """
    registry = RegistryRecord(
        study_id="NCT01234567",
        primary_outcome="Tempo até a redução da viremia em 48 horas",
        sample_size=100,
        completion_date="2022-12-31",
        status="COMPLETED",
    )

    # Publicação alterou o desfecho primário para duração da febre e reduziu N analisado
    publication = PublicationRecord(
        study_id="NCT01234567",
        pmid="34567890",
        primary_outcome="Duração total do pico febril (dias)",
        sample_size=82,
        publication_date="2023-06-15",
    )

    report = compare_registry_and_publication(registry, publication)

    assert report.has_discrepancies is True
    assert report.discrepancies_count == 2
    assert report.critical_count == 1

    # Verificação de Outcome Switching
    switch_item = next(i for i in report.items if i.field_name == "primary_outcome")
    assert switch_item.discrepancy_type == "OUTCOME_SWITCHING"
    assert switch_item.severity == "CRITICA"
    assert switch_item.routing_status == "AGUARDA_REVISAO_HUMANA"
    assert switch_item.registry_value == "Tempo até a redução da viremia em 48 horas"
    assert switch_item.publication_value == "Duração total do pico febril (dias)"

    # Verificação de Sample Size Mismatch
    sample_item = next(i for i in report.items if i.field_name == "sample_size")
    assert sample_item.discrepancy_type == "SAMPLE_SIZE_MISMATCH"
    assert sample_item.severity == "MODERADA"
    assert sample_item.registry_value == 100
    assert sample_item.publication_value == 82


@pytest.mark.requirement("REQ-ING-006")
def test_registry_hash_change_generates_new_version_and_diff():
    """Quando o status ou dados de um registro mudam, gera nova DocumentVersion,

    calcula a diferença de campos e abre fila de reavaliação preservando a decisão anterior (ACC-ING-006 / T2).
    """
    initial_registry = RegistryRecord(
        study_id="NCT00987654",
        primary_outcome="Incidência de Dengue Grave",
        sample_size=300,
        completion_date="2023-01-01",
        status="RECRUITING",
    )

    updated_registry = RegistryRecord(
        study_id="NCT00987654",
        primary_outcome="Incidência de Dengue Grave",
        sample_size=320,  # Amostra expandida
        completion_date="2023-06-30",  # Término postergado
        status="COMPLETED",  # Status alterado
    )

    diff_report = detect_registry_version_change(initial_registry, updated_registry, previous_version_number=1)

    assert diff_report.version_incremented is True
    assert diff_report.new_version_id == "dv-nct00987654-v2"
    assert diff_report.previous_hash != diff_report.current_hash
    assert diff_report.reassessment_task_opened is True
    assert diff_report.preserves_prior_decision is True

    # Verifica os campos identificados no diff
    assert "status" in diff_report.changed_fields
    assert "sample_size" in diff_report.changed_fields
    assert "completion_date" in diff_report.changed_fields
    assert "primary_outcome" not in diff_report.changed_fields

    assert diff_report.diff["status"]["before"] == "RECRUITING"
    assert diff_report.diff["status"]["after"] == "COMPLETED"
    assert diff_report.diff["sample_size"]["before"] == 300
    assert diff_report.diff["sample_size"]["after"] == 320

