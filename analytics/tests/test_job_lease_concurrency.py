"""Testes para concorrência, isolamento transacional de chamadas de IA e proteção por leases.

Cobre formalmente:
- REQ-OPS-003 (ACC-OPS-003 / RNF): Não manter transação SQL aberta durante chamada de IA;
  persistir resultados intermediários e tentativas sem locking prolongado.
- REQ-OPS-004 (ACC-OPS-004 / P10): Tarefas reservadas por lease; aceitação estrita somente
  com token vigente; resultados atrasados (stale worker) são descartados e registrados em auditoria.
"""

from __future__ import annotations

import sqlite3
import time
import pytest
from denguepharma_analytics.ops.job_lease_concurrency import (
    JobLease,
    JobLeaseManager,
    LeaseExpiredError,
    StaleWorkerRejectedError,
)


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.mark.requirement("REQ-OPS-003")
def test_no_sql_transaction_open_during_ai_call(db_conn):
    """Cobre ACC-OPS-003: Dado uma chamada de IA lenta, quando em curso, então não há

    transação aberta no banco.
    """
    manager = JobLeaseManager(db_conn)
    job_id = manager.create_job(job_type="EXTRACT_DOCUMENT", ref_id="doc-uuid-123")

    lease = manager.claim_lease(job_id, lease_duration_sec=10.0)
    assert lease is not None
    assert lease.attempts == 1

    # Verifica formalmente que após o claim_lease a transação foi encerrada
    assert not db_conn.in_transaction

    # Simula chamada de IA lenta verificando estado da transação relacional
    def slow_ai_model_call(current_lease: JobLease) -> dict:
        # Durante a execução da IA, o banco DEVE estar com transação inativa
        assert not db_conn.in_transaction, "Violação REQ-OPS-003: Transação SQL ativa durante inferência de IA"
        # Simula latência do modelo LLM
        time.sleep(0.05)
        return {"extracted_field": "sample_size", "value": "120"}

    result = manager.execute_with_isolated_transaction(lease, slow_ai_model_call)
    assert result["status"] == "COMPLETED"
    assert result["committed"] is True
    assert result["result"]["value"] == "120"


@pytest.mark.requirement("REQ-OPS-003")
def test_fails_if_attempted_with_open_transaction(db_conn):
    """Garante que a salvaguarda REQ-OPS-003 bloqueia ativamente qualquer tentativa de

    invocar o modelo de IA com transação aberta.
    """
    manager = JobLeaseManager(db_conn)
    job_id = manager.create_job(job_type="EXTRACT_DOCUMENT", ref_id="doc-uuid-456")
    lease = manager.claim_lease(job_id, lease_duration_sec=10.0)

    # Força uma transação aberta
    db_conn.execute("BEGIN TRANSACTION")
    assert db_conn.in_transaction

    def mock_ai(current_lease: JobLease) -> dict:
        return {}

    with pytest.raises(RuntimeError) as exc_info:
        manager.execute_with_isolated_transaction(lease, mock_ai)

    assert "Transacao SQL ativa detectada" in str(exc_info.value)
    db_conn.rollback()


@pytest.mark.requirement("REQ-OPS-004")
def test_stale_worker_result_is_discarded_and_recorded(db_conn):
    """Cobre ACC-OPS-004: Dado um lease expirado, quando o resultado chegar, então é

    descartado e registrado na auditoria sem sobrescrever o job.
    """
    manager = JobLeaseManager(db_conn)
    job_id = manager.create_job(job_type="EXTRACT_DOCUMENT", ref_id="doc-uuid-789")

    # 1. Primeiro worker obtém lease com duração muito curta
    stale_lease = manager.claim_lease(job_id, lease_duration_sec=0.05)
    stale_token = stale_lease.lease_token

    # 2. Worker demora mais que a vigência do lease
    time.sleep(0.08)

    # 3. Novo worker assume a tarefa expirada
    fresh_lease = manager.claim_lease(job_id, lease_duration_sec=10.0)
    assert fresh_lease is not None
    assert fresh_lease.lease_token != stale_token
    assert fresh_lease.attempts == 2

    # 4. Worker atrasado tenta entregar seu resultado
    stale_payload = {"source": "old_worker", "data": "outdated_extracted_value"}
    with pytest.raises(StaleWorkerRejectedError):
        manager.complete_job(job_id, stale_token, stale_payload)

    # 5. Verifica que o resultado atrasado foi descartado e gravado em discarded_stale_results
    cur = db_conn.execute(
        "SELECT stale_token, reason, discarded_payload FROM discarded_stale_results WHERE job_id = ?",
        (job_id,),
    )
    discarded = cur.fetchall()
    assert len(discarded) == 1
    assert discarded[0][0] == stale_token
    assert discarded[0][1] == "LEASE_EXPIRED_OR_SUPERSEDED"
    assert "outdated_extracted_value" in discarded[0][2]

    # 6. O job ainda está com o lease do novo worker vigente e não foi corrompido
    cur_job = db_conn.execute("SELECT status, lease_token FROM job WHERE id = ?", (job_id,)).fetchone()
    assert cur_job[0] == "LEASED"
    assert cur_job[1] == fresh_lease.lease_token

    # 7. O novo worker entrega com sucesso
    fresh_result = manager.complete_job(job_id, fresh_lease.lease_token, {"source": "fresh_worker", "data": "valid"})
    assert fresh_result["status"] == "COMPLETED"


@pytest.mark.requirement("REQ-OPS-004")
def test_lease_renewal_and_quarantine(db_conn):
    """Testa renovação atômica de lease ativo e transição para quarentena ao exceder tentativas."""
    manager = JobLeaseManager(db_conn)
    job_id = manager.create_job(job_type="EXTRACT_DOCUMENT", ref_id="doc-uuid-999", max_attempts=2)

    # Claim 1
    l1 = manager.claim_lease(job_id, lease_duration_sec=5.0)
    # Renova antes de expirar
    new_until = manager.renew_lease(job_id, l1.lease_token, extension_sec=10.0)
    assert new_until > l1.lease_until

    # Falha 1 -> status volta a PENDING
    status1 = manager.fail_job(job_id, l1.lease_token, "TIMEOUT")
    assert status1 == "PENDING"

    # Claim 2 (attempts = 2)
    l2 = manager.claim_lease(job_id, lease_duration_sec=5.0)
    assert l2.attempts == 2

    # Falha 2 -> atinge max_attempts (2) -> vai para QUARANTINED (DLQ)
    status2 = manager.fail_job(job_id, l2.lease_token, "REPEATED_TIMEOUT")
    assert status2 == "QUARANTINED"

    # Job em quarentena não aceita mais claim
    l3 = manager.claim_lease(job_id)
    assert l3 is None
