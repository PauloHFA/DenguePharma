"""Testes para telemetria de estudo de tempo e pseudonimização ética de revisores.

Cobre formalmente:
- REQ-REV-005 (ACC-REV-005 / RQ5, H1): Registro de tempo ativo por documento e por campo,
  com dedução estrita de pausas para estudo de esforço cognitivo.
- REQ-GOV-002 (ACC-GOV-002 / Ética): Pseudonimização compulsória de revisores em dados
  exportados e conformidade ética prévia.
"""

from __future__ import annotations

import pytest
from denguepharma_analytics.clinical.review_telemetry import (
    EthicalGovernanceError,
    ReviewSessionTelemetry,
    ReviewerPseudonymizer,
    TimeStudyDatasetExporter,
)


@pytest.mark.requirement("REQ-REV-005")
def test_review_session_active_time_excludes_pauses():
    """Cobre ACC-REV-005: Dado uma sessão de revisão com pausa, quando concluída,

    então o tempo ativo exclui a pausa.
    """
    start_t = 1000.0
    session = ReviewSessionTelemetry(
        document_id="doc-dengue-trial-001",
        reviewer_id="user-dra-ana-1234",
        start_time=start_t,
    )

    # 1. Revisor trabalha por 30 segundos no campo 'sample_size'
    session.record_field_time("sample_size", 30.0)

    # 2. Revisor inicia primeira pausa (ex: atendeu telefone / café) de 15 segundos
    session.pause(pause_time=1030.0, reason="TELEPHONE_CALL")
    session.resume(resume_time=1045.0)

    # 3. Revisor trabalha mais 40 segundos no campo 'primary_outcome'
    session.record_field_time("primary_outcome", 40.0)

    # 4. Revisor entra em segunda pausa (inatividade/fadiga) de 25 segundos
    session.pause(pause_time=1085.0, reason="IDLE_TIMEOUT")
    session.resume(resume_time=1110.0)

    # 5. Revisor trabalha mais 20 segundos no campo 'adverse_events'
    session.record_field_time("adverse_events", 20.0)

    # 6. Sessão é finalizada aos 1130.0 segundos (tempo total corrido: 130 segundos)
    result = session.complete_session(end_time=1130.0)

    assert result["total_elapsed_sec"] == 130.0
    # Total de pausas: 15s + 25s = 40.0s
    assert result["total_pause_sec"] == 40.0
    # Tempo ativo real: 130s - 40s = 90.0s (exclusão estrita de pausas)
    assert result["active_time_sec"] == 90.0

    # Rastreamento por campo confere
    assert result["field_times"]["sample_size"] == 30.0
    assert result["field_times"]["primary_outcome"] == 40.0
    assert result["field_times"]["adverse_events"] == 20.0
    assert result["pauses_count"] == 2


@pytest.mark.requirement("REQ-GOV-002")
def test_time_study_export_pseudonymizes_reviewers_and_requires_ethics_approval():
    """Cobre ACC-GOV-002: Dado resultados do estudo de tempo, quando exportados,

    então revisores aparecem por código e exigem protocolo de aprovação ética.
    """
    # Dados de sessões com identificadores de revisores
    sessions = [
        {
            "session_id": "sess-1",
            "document_id": "doc-01",
            "reviewer_id": "dr-paulo-silva-uuid",
            "active_time_sec": 75.5,
        },
        {
            "session_id": "sess-2",
            "document_id": "doc-02",
            "reviewer_id": "dr-paulo-silva-uuid",  # mesmo revisor
            "active_time_sec": 62.0,
        },
        {
            "session_id": "sess-3",
            "document_id": "doc-01",
            "reviewer_id": "dra-maria-costa-uuid",  # revisora distinta
            "active_time_sec": 88.0,
        },
    ]

    # 1. Tentativa de exportar sem aprovação ética bloqueia o processo
    with pytest.raises(EthicalGovernanceError) as exc_info:
        TimeStudyDatasetExporter.export_dataset(sessions, ethical_approval_code=None)
    assert "req-gov-002" in str(exc_info.value).lower()

    with pytest.raises(EthicalGovernanceError):
        TimeStudyDatasetExporter.export_dataset(sessions, ethical_approval_code="INVALIDO-123")

    # 2. Exportação com aprovação ética regularizada (ex: protocolo CEP ou CAAE)
    exported = TimeStudyDatasetExporter.export_dataset(
        sessions,
        ethical_approval_code="CEP-987654/2026",
    )

    assert len(exported) == 3

    # Nenhum identificador pessoal/direto de revisor está presente no dataset exportado
    for row in exported:
        assert "reviewer_id" not in row
        assert "reviewer_code" in row
        assert row["reviewer_code"].startswith("REV-")
        assert row["ethical_approval"] == "CEP-987654/2026"

    # Consistência: o mesmo revisor tem o mesmo pseudônimo determinístico
    assert exported[0]["reviewer_code"] == exported[1]["reviewer_code"]
    # Revisores diferentes têm pseudônimos diferentes
    assert exported[0]["reviewer_code"] != exported[2]["reviewer_code"]

