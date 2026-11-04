"""Testes para o subsistema de mensageria transacional e idempotência.

Cobre formalmente:
- REQ-OPS-001 (ACC-OPS-001): Mutação e Outbox atômicos e reenvio com event_id estável.
- REQ-OPS-002 (ACC-OPS-002): Consumo idempotente protegido por tabela Inbox (T7).
"""

from __future__ import annotations

import sqlite3
import uuid
import pytest
from denguepharma_analytics.ops.transactional_messaging import (
    IdempotentInbox,
    TransactionalOutbox,
)


@pytest.fixture
def db_conn():
    """Conexão isolada SQLite em memória com suporte a transações."""
    conn = sqlite3.connect(":memory:")
    # Cria uma tabela de negócio para simular mutações de dados
    with conn:
        conn.execute("""
            CREATE TABLE clinical_trial_record (
                id TEXT PRIMARY KEY,
                nct_id TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
    yield conn
    conn.close()


@pytest.mark.requirement("REQ-OPS-001")
def test_outbox_atomic_mutation_and_event_persistence(db_conn):
    """Verifica se mutação de negócio e evento outbox são persistidos na mesma transação.

    Se a mutação falhar, nenhum evento é gerado. Se suceder, ambos persistem.
    """
    outbox = TransactionalOutbox(db_conn)

    # 1. Mutação que falha (simulação de constraint violation ou erro de regra de negócio)
    def failing_mutation(conn: sqlite3.Connection):
        conn.execute("INSERT INTO clinical_trial_record VALUES ('t1', 'NCT12345', 'DRAFT')")
        raise RuntimeError("Falha proposital de banco ou validação antes do commit")

    with pytest.raises(RuntimeError):
        outbox.record_mutation_and_event(
            mutation_callback=failing_mutation,
            event_type="TrialCreated",
            aggregate_type="ClinicalTrial",
            aggregate_id="t1",
            payload={"nct_id": "NCT12345"},
        )

    # Verifica que NADA foi commitado (nem mutação, nem outbox)
    trials_count = db_conn.execute("SELECT count(*) FROM clinical_trial_record").fetchone()[0]
    outbox_count = db_conn.execute("SELECT count(*) FROM outbox").fetchone()[0]
    assert trials_count == 0
    assert outbox_count == 0

    # 2. Mutação bem-sucedida
    def successful_mutation(conn: sqlite3.Connection):
        conn.execute("INSERT INTO clinical_trial_record VALUES ('t1', 'NCT12345', 'CONFIRMED')")
        return "MUTATION_OK"

    custom_event_id = str(uuid.uuid4())
    res, event = outbox.record_mutation_and_event(
        mutation_callback=successful_mutation,
        event_type="TrialCreated",
        aggregate_type="ClinicalTrial",
        aggregate_id="t1",
        payload={"nct_id": "NCT12345"},
        event_id=custom_event_id,
    )

    assert res == "MUTATION_OK"
    assert event.event_id == custom_event_id
    assert event.aggregate_id == "t1"

    # Ambos persistidos
    assert db_conn.execute("SELECT count(*) FROM clinical_trial_record").fetchone()[0] == 1
    assert db_conn.execute("SELECT count(*) FROM outbox").fetchone()[0] == 1


@pytest.mark.requirement("REQ-OPS-001")
def test_outbox_publisher_retry_preserves_stable_event_id(db_conn):
    """Cobre ACC-OPS-001: Dado uma falha entre o commit e o envio, quando o publicador

    reiniciar, então o evento é reenviado com o mesmo event_id estável.
    """
    outbox = TransactionalOutbox(db_conn)

    original_event_id = str(uuid.uuid4())

    def mutation(conn: sqlite3.Connection):
        conn.execute("INSERT INTO clinical_trial_record VALUES ('t2', 'NCT99999', 'ACTIVE')")

    _, created_event = outbox.record_mutation_and_event(
        mutation_callback=mutation,
        event_type="TrialUpdated",
        aggregate_type="ClinicalTrial",
        aggregate_id="t2",
        payload={"nct_id": "NCT99999", "status": "ACTIVE"},
        event_id=original_event_id,
    )
    assert created_event.event_id == original_event_id

    # 1. Publicador faz o primeiro claim para envio ao broker
    claimed_1 = outbox.claim_pending_events(limit=5, lease_seconds=10)
    assert len(claimed_1) == 1
    assert claimed_1[0].event_id == original_event_id
    token_1 = claimed_1[0].relay_token
    assert token_1 is not None

    # 2. Simula falha do broker antes da confirmação (rede caiu, broker indisponível)
    outbox.fail_publication(original_event_id, token_1, "Connection refused to message broker")

    # 3. Publicador reinicia e tenta reenviar: deve obter exatamente o mesmo event_id estável
    claimed_retry = outbox.claim_pending_events(limit=5, lease_seconds=10)
    assert len(claimed_retry) == 1
    event_retry = claimed_retry[0]
    assert event_retry.event_id == original_event_id  # Estabilidade formal REQ-OPS-001
    assert event_retry.attempts == 2
    assert event_retry.relay_token != token_1  # Novo lease token

    # 4. Confirmação do envio bem-sucedido
    confirmed = outbox.confirm_publication(event_retry.event_id, event_retry.relay_token)
    assert confirmed is True

    # 5. Após confirmação, não há mais eventos pendentes
    claimed_after = outbox.claim_pending_events(limit=5)
    assert len(claimed_after) == 0


@pytest.mark.requirement("REQ-OPS-002")
def test_inbox_idempotent_consumer_strictly_executes_once(db_conn):
    """Cobre ACC-OPS-002 / T7: Dado o mesmo evento entregue duas vezes, quando

    consumido, então o efeito ocorre exatamente uma vez.
    """
    inbox = IdempotentInbox(db_conn)
    shared_event_id = str(uuid.uuid4())
    consumer_name = "analytics-worker-v1"

    side_effects = {"execution_count": 0, "processed_payloads": []}

    def business_handler(payload: dict) -> str:
        side_effects["execution_count"] += 1
        side_effects["processed_payloads"].append(payload)
        return f"SUCCESS:{payload.get('trial_id')}"

    event_payload = {"trial_id": "TRIAL-001", "phase": "III", "efficacy": 0.82}

    # 1. Primeira entrega do evento
    res1 = inbox.process_event(shared_event_id, consumer_name, business_handler, event_payload)
    assert res1["status"] == "PROCESSED"
    assert res1["idempotent_replay"] is False
    assert side_effects["execution_count"] == 1
    assert len(side_effects["processed_payloads"]) == 1

    # 2. Segunda entrega (mesmo event_id duplicado, ex: retransmissão de rede at-least-once)
    res2 = inbox.process_event(shared_event_id, consumer_name, business_handler, event_payload)
    assert res2["status"] == "ALREADY_PROCESSED"
    assert res2["idempotent_replay"] is True
    # O handler NÃO é chamado novamente; o efeito colateral permaneceu exatamente 1 vez
    assert side_effects["execution_count"] == 1
    assert len(side_effects["processed_payloads"]) == 1

    # 3. Terceira entrega
    res3 = inbox.process_event(shared_event_id, consumer_name, business_handler, event_payload)
    assert res3["status"] == "ALREADY_PROCESSED"
    assert res3["idempotent_replay"] is True
    assert side_effects["execution_count"] == 1


@pytest.mark.requirement("REQ-OPS-002")
def test_inbox_distinct_consumers_independent_processing(db_conn):
    """Verifica que múltiplos consumidores distintos processam o mesmo event_id

    cada um exatamente uma vez (deduplicação isolada por consumer).
    """
    inbox = IdempotentInbox(db_conn)
    event_id = str(uuid.uuid4())

    invocations = {"worker_a": 0, "worker_b": 0}

    def handler_a(payload):
        invocations["worker_a"] += 1
        return "OK_A"

    def handler_b(payload):
        invocations["worker_b"] += 1
        return "OK_B"

    # Worker A processa
    r_a1 = inbox.process_event(event_id, "worker_a", handler_a, {})
    assert r_a1["status"] == "PROCESSED"
    assert invocations["worker_a"] == 1

    # Worker B processa o mesmo evento
    r_b1 = inbox.process_event(event_id, "worker_b", handler_b, {})
    assert r_b1["status"] == "PROCESSED"
    assert invocations["worker_b"] == 1

    # Reentrega para Worker A é dedublicada
    r_a2 = inbox.process_event(event_id, "worker_a", handler_a, {})
    assert r_a2["status"] == "ALREADY_PROCESSED"
    assert invocations["worker_a"] == 1

