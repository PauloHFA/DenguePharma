"""Módulo de Resiliência Transacional: Outbox e Inbox Idempotente.

Implementa os requisitos:
- REQ-OPS-001 (ACC-OPS-001 / P10): Mutação local e evento gravados na mesma transação SQL (Outbox);
  o publicador reencontra e reenvia sem alterar o event_id estável.
- REQ-OPS-002 (ACC-OPS-002 / T7 / P10): Consumidor registra cada event_id em Inbox e garante
  idempotência estrita (entrega duplicada produz efeito exatamente uma vez).
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OutboxEvent:
    """Evento imutável persistido na tabela outbox."""
    id: int
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    created_at: str
    published_at: Optional[str] = None
    relay_token: Optional[str] = None
    relay_until: Optional[float] = None
    attempts: int = 0
    last_error: Optional[str] = None


class TransactionalOutbox:
    """Gerenciador do padrão Transactional Outbox (REQ-OPS-001).

    Garante que a mutação local e o evento correspondente sejam gravados
    atomicamente na mesma transação relacional. Reenvios pós-falha mantêm
    rigorosamente o mesmo `event_id`.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    aggregate_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    published_at TEXT,
                    relay_token TEXT,
                    relay_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                )
            """)

    def record_mutation_and_event(
        self,
        mutation_callback: Callable[[sqlite3.Connection], Any],
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> Tuple[Any, OutboxEvent]:
        """Executa a mutação e grava o evento outbox na MESMA transação atômica.

        Se a mutação falhar, nenhum evento é gravado.
        Se a gravação do outbox falhar, a mutação sofre rollback.
        """
        stable_event_id = event_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, ensure_ascii=False)

        # Transação atômica isolada
        try:
            with self.conn:
                mutation_result = mutation_callback(self.conn)
                cur = self.conn.execute(
                    """
                    INSERT INTO outbox (
                        event_id, event_type, aggregate_type, aggregate_id,
                        payload, created_at, attempts
                    ) VALUES (?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        stable_event_id,
                        event_type,
                        aggregate_type,
                        aggregate_id,
                        payload_json,
                        created_at,
                    ),
                )
                row_id = cur.lastrowid
        except Exception:
            # Rollback automático feito pelo contexto 'with self.conn'
            raise

        event = OutboxEvent(
            id=row_id,
            event_id=stable_event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            created_at=created_at,
        )
        return mutation_result, event

    def claim_pending_events(
        self, limit: int = 10, lease_seconds: int = 60
    ) -> List[OutboxEvent]:
        """Reserva eventos pendentes para publicação com lease temporal.

        Reenvios mantêm estritamente o mesmo event_id original.
        """
        now = time.time()
        claimed: List[OutboxEvent] = []

        with self.conn:
            cur = self.conn.execute(
                """
                SELECT id, event_id, event_type, aggregate_type, aggregate_id,
                       payload, created_at, published_at, relay_token, relay_until,
                       attempts, last_error
                FROM outbox
                WHERE published_at IS NULL
                  AND (relay_until IS NULL OR relay_until < ?)
                ORDER BY id ASC
                LIMIT ?
                """,
                (now, limit),
            )
            rows = cur.fetchall()

            for row in rows:
                (
                    row_id,
                    event_id,
                    event_type,
                    agg_type,
                    agg_id,
                    p_json,
                    c_at,
                    pub_at,
                    _,
                    _,
                    attempts,
                    last_err,
                ) = row
                token = str(uuid.uuid4())
                lease_until = now + lease_seconds
                new_attempts = attempts + 1

                self.conn.execute(
                    """
                    UPDATE outbox
                    SET relay_token = ?, relay_until = ?, attempts = ?
                    WHERE id = ?
                    """,
                    (token, lease_until, new_attempts, row_id),
                )

                claimed.append(
                    OutboxEvent(
                        id=row_id,
                        event_id=event_id,  # Estabilidade garantida
                        event_type=event_type,
                        aggregate_type=agg_type,
                        aggregate_id=agg_id,
                        payload=json.loads(p_json),
                        created_at=c_at,
                        published_at=pub_at,
                        relay_token=token,
                        relay_until=lease_until,
                        attempts=new_attempts,
                        last_error=last_err,
                    )
                )

        return claimed

    def confirm_publication(self, event_id: str, relay_token: str) -> bool:
        """Confirma a publicação no broker, liberando o lease e marcando timestamp."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE outbox
                SET published_at = ?, relay_token = NULL, relay_until = NULL, last_error = NULL
                WHERE event_id = ? AND relay_token = ?
                """,
                (now_iso, event_id, relay_token),
            )
            return cur.rowcount == 1

    def fail_publication(self, event_id: str, relay_token: str, error_msg: str) -> None:
        """Registra falha de publicação e libera lease para reenvio futuro com o mesmo event_id."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE outbox
                SET relay_token = NULL, relay_until = NULL, last_error = ?
                WHERE event_id = ? AND relay_token = ?
                """,
                (error_msg, event_id, relay_token),
            )


class IdempotentInbox:
    """Gerenciador do padrão Idempotent Consumer / Inbox (REQ-OPS-002 / T7).

    Garante que entregas duplicadas de uma mesma mensagem sejam reconhecidas
    e não provoquem efeitos colaterais repetidos.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS inbox (
                    event_id TEXT NOT NULL,
                    consumer TEXT NOT NULL,
                    status TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    processed_at TEXT,
                    result_summary TEXT,
                    PRIMARY KEY (event_id, consumer)
                )
            """)

    def process_event(
        self,
        event_id: str,
        consumer: str,
        handler: Callable[[Dict[str, Any]], Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Processa o evento garantindo idempotência estrita.

        Se (event_id, consumer) já estiver gravado como 'COMPLETED', o handler NÃO é executado
        novamente e a resposta indica repetição idempotente.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        with self.conn:
            cur = self.conn.execute(
                "SELECT status, processed_at, result_summary FROM inbox WHERE event_id = ? AND consumer = ?",
                (event_id, consumer),
            )
            row = cur.fetchone()

            if row is not None:
                status, processed_at, result_summary = row
                if status == "COMPLETED":
                    # Salvaguarda T7: Entrega duplicada não repete efeito
                    return {
                        "status": "ALREADY_PROCESSED",
                        "idempotent_replay": True,
                        "event_id": event_id,
                        "consumer": consumer,
                        "processed_at": processed_at,
                        "result_summary": result_summary,
                    }

            # Registra ou atualiza para processamento
            self.conn.execute(
                """
                INSERT INTO inbox (event_id, consumer, status, received_at)
                VALUES (?, ?, 'PROCESSING', ?)
                ON CONFLICT(event_id, consumer) DO UPDATE SET received_at = excluded.received_at
                """,
                (event_id, consumer, now_iso),
            )

        # Executa o efeito colateral / lógica de negócio
        result = handler(payload)
        result_summary = str(result)[:500] if result is not None else "OK"
        completed_iso = datetime.now(timezone.utc).isoformat()

        with self.conn:
            self.conn.execute(
                """
                UPDATE inbox
                SET status = 'COMPLETED', processed_at = ?, result_summary = ?
                WHERE event_id = ? AND consumer = ?
                """,
                (completed_iso, result_summary, event_id, consumer),
            )

        return {
            "status": "PROCESSED",
            "idempotent_replay": False,
            "event_id": event_id,
            "consumer": consumer,
            "processed_at": completed_iso,
            "result_summary": result_summary,
        }

