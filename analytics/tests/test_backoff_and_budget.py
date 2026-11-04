"""Testes para backoff exponencial com jitter, quarentena auditada e governança orçamentária de IA.

Cobre formalmente:
- REQ-OPS-005 (ACC-OPS-005 / RF-11): Backoff com jitter, limite de tentativas, quarentena visível
  e reprocessamento autorizado com auditoria.
- REQ-OPS-006 (ACC-OPS-006 / RNF): Controle do orçamento de IA por execução, registro de custo,
  teto orçamentário com pausa preventiva e alerta.
"""

from __future__ import annotations

import pytest
from denguepharma_analytics.ops.backoff_and_budget import (
    AIBudgetExceededError,
    AIBudgetGuard,
    BackoffPolicy,
    QuarantineManager,
)


@pytest.mark.requirement("REQ-OPS-005")
def test_backoff_computation_with_exponential_growth_and_jitter():
    """Valida cálculo de backoff exponencial com jitter e teto máximo de 300 segundos."""
    policy = BackoffPolicy(base_seconds=1.0, factor=2.0, max_seconds=300.0, max_jitter_seconds=3.0)

    # Tentativa 0: delay base 1s + jitter (0..3s) -> [1.0, 4.0]
    delay_0 = policy.compute_delay(0, seed=42)
    assert 1.0 <= delay_0 <= 4.0

    # Tentativa 1: delay base 2s + jitter (0..3s) -> [2.0, 5.0]
    delay_1 = policy.compute_delay(1, seed=42)
    assert 2.0 <= delay_1 <= 5.0

    # Tentativa 4: delay base 16s + jitter -> [16.0, 19.0]
    delay_4 = policy.compute_delay(4, seed=42)
    assert 16.0 <= delay_4 <= 19.0

    # Tentativas altas (ex: 15): limitadas a 2^8 = 256s + jitter (0..3s) conforme fórmula do backend -> [256.0, 259.0]
    delay_15 = policy.compute_delay(15, seed=42)
    assert 256.0 <= delay_15 <= 259.0


@pytest.mark.requirement("REQ-OPS-005")
def test_quarantine_transition_and_authorized_retry_audit():
    """Cobre ACC-OPS-005: Dado uma tarefa que falha N vezes, quando excedido o limite,

    então vai à quarentena visível e pode ser retomada com auditoria formal.
    """
    policy = BackoffPolicy(max_attempts=3)
    qm = QuarantineManager(policy)
    job_id = "job-retry-test-101"

    # Falha 1 (attempts = 1) -> PENDING com delay
    st1, d1 = qm.register_failure(job_id, 1, "EXTERNAL_API_503", {"doc": "NCT01"})
    assert st1 == "PENDING"
    assert d1 is not None

    # Falha 2 (attempts = 2) -> PENDING
    st2, d2 = qm.register_failure(job_id, 2, "EXTERNAL_API_503", {"doc": "NCT01"})
    assert st2 == "PENDING"

    # Falha 3 (attempts = 3 >= max_attempts) -> QUARANTINED (DLQ)
    st3, d3 = qm.register_failure(job_id, 3, "EXTERNAL_API_503", {"doc": "NCT01"})
    assert st3 == "QUARANTINED"
    assert d3 is None
    assert job_id in qm.quarantined_jobs

    # Retomada não autorizada de job inexistente falha
    with pytest.raises(ValueError):
        qm.authorize_retry("invalid-job-id", "admin-user", "Motivo qualquer")

    # Retomada formal autorizada por administrador
    retry_result = qm.authorize_retry(
        job_id=job_id,
        actor="dra-maria-adjudicadora",
        reason="Correção na conectividade do repositório PubMed",
    )

    assert retry_result["status"] == "PENDING"
    assert job_id not in qm.quarantined_jobs

    # Verifica registro formal na auditoria
    assert len(qm.audit_log) == 1
    audit = qm.audit_log[0]
    assert audit.action == "JOB_RETRY_AUTHORIZED"
    assert audit.target_id == job_id
    assert audit.actor == "dra-maria-adjudicadora"
    assert "PubMed" in audit.reason


@pytest.mark.requirement("REQ-OPS-006")
def test_ai_budget_cumulative_tracking_and_cost_calculation():
    """Cobre REQ-OPS-006: Registro de custo de IA por execução e acúmulo de gastos."""
    guard = AIBudgetGuard(ceiling_usd=1.00)

    # Execução 1: Modelo rápido gemini-1.5-flash com 10.000 tokens prompt e 2.000 completion
    # Custo: (10 * 0.000075) + (2 * 0.0003) = 0.00075 + 0.0006 = 0.00135
    run1 = guard.authorize_and_record_run("run-1", "gemini-1.5-flash", 10000, 2000)
    assert run1["cost_usd"] == pytest.approx(0.00135, rel=1e-3)
    assert guard.cumulative_spend_usd == pytest.approx(0.00135, rel=1e-3)
    assert not guard.is_suspended

    # Execução 2: Modelo avançado gpt-4o-mini com 50.000 prompt e 10.000 completion
    # Custo: (50 * 0.00015) + (10 * 0.0006) = 0.0075 + 0.006 = 0.0135
    run2 = guard.authorize_and_record_run("run-2", "gpt-4o-mini", 50000, 10000)
    assert run2["cost_usd"] == pytest.approx(0.0135, rel=1e-3)
    assert guard.cumulative_spend_usd == pytest.approx(0.00135 + 0.0135, rel=1e-3)

    status = guard.get_status()
    assert status["total_runs"] == 2
    assert status["remaining_usd"] > 0.95


@pytest.mark.requirement("REQ-OPS-006")
def test_ai_budget_suspends_and_alerts_upon_reaching_ceiling():
    """Cobre ACC-OPS-006: Dado um teto de teste, quando atingido, então novas chamadas

    são suspensas e um alerta é emitido.
    """
    test_ceiling = 0.0100  # USD $0.01 (teto de teste)
    guard = AIBudgetGuard(ceiling_usd=test_ceiling)

    # Chamada 1: Custo ~ 0.006 USD (cabe no orçamento)
    guard.authorize_and_record_run("run-allow-1", "gpt-4o-mini", 20000, 5000)
    assert not guard.is_suspended
    assert len(guard.alerts) == 0

    # Chamada 2: Custo projetado de ~0.008 USD faria o gasto total ir para ~0.014 USD (> teto de 0.010)
    # A chamada DEVE ser bloqueada preventivamente, o sistema suspenso e o alerta emitido
    with pytest.raises(AIBudgetExceededError) as exc_info:
        guard.authorize_and_record_run("run-blocked-2", "gpt-4o-mini", 30000, 5000)

    assert "Teto orcamentario" in str(exc_info.value)
    assert guard.is_suspended

    # Verifica emissão de alerta
    assert len(guard.alerts) == 1
    alert = guard.alerts[0]
    assert alert.alert_type == "BUDGET_CEILING_REACHED"
    assert alert.ceiling_usd == test_ceiling

    # Novas chamadas subsequentes continuam suspensas imediatamente
    with pytest.raises(AIBudgetExceededError):
        guard.authorize_and_record_run("run-blocked-3", "gemini-1.5-flash", 100, 50)
