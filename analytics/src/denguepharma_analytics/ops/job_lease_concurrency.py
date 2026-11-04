"""Gerenciador de Concorrência, Leases Atômicos e Quarentena (DLQ).

Implementa os requisitos:
- REQ-OPS-003 (ACC-OPS-003 / RNF): Não manter transação SQL aberta durante chamada de IA;
  persistir resultados intermediários e tentativas sem travar recursos relacionais.
- REQ-OPS-004 (ACC-OPS-004 / P10): Reservar tarefas por lease e aceitar resultado somente
  com token vigente; resultados atrasados (stale worker) são descartados e registrados em auditoria.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


class LeaseError(Exception):
    """Erro base para operações de lease de jobs."""


class LeaseExpiredError(LeaseError):
    """Lançado quando o lease expirou ou o token foi invalidado."""


class StaleWorkerRejectedError(LeaseError):
    """Lançado quando um resultado atrasado é descartado por violação de vigência (REQ-OPS-004)."""


@dataclass(frozen=True)
class JobLease:
    job_id: str
    lease_token: str
    lease_until: float
    attempts: int
    max_attempts: int
    job_type: str
    ref_id: str


class JobLeaseManager:
    """Gerenciador de jobs com proteção por lease temporal e quarentena (REQ-OPS-003 / REQ-OPS-004)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS job (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    ref_id TEXT NOT NULL,
                    source_event_id TEXT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    lease_token TEXT,
                    lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    result_payload TEXT,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS discarded_stale_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    stale_token TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    discarded_payload TEXT,
                    discarded_at TEXT NOT NULL
                )
            """)

    def create_job(
        self,
        job_type: str,
        ref_id: str,
        source_event_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> str:
        job_id = str(uuid.uuid4())
        now = time.time()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO job (id, job_type, ref_id, source_event_id, status, max_attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?)
                """,
                (job_id, job_type, ref_id, source_event_id, max_attempts, now, now),
            )
        return job_id

    def claim_lease(self, job_id: str, lease_duration_sec: float = 30.0) -> Optional[JobLease]:
        """Reserva curta atômica. A chamada de IA/processamento ocorre DEPOIS desta transação (REQ-OPS-003)."""
        now = time.time()
        new_token = str(uuid.uuid4())
        lease_until = now + lease_duration_sec

        with self.conn:
            cur = self.conn.execute(
                """
                SELECT job_type, ref_id, status, lease_token, lease_until, attempts, max_attempts
                FROM job WHERE id = ?
                """,
                (job_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            job_type, ref_id, status, old_token, old_until, attempts, max_attempts = row

            if status in ("COMPLETED", "QUARANTINED"):
                return None

            # Só pode reivindicar se PENDING ou se LEASED com lease_until expirado
            if status == "LEASED" and old_until is not None and old_until >= now:
                return None  # Lease ainda vigente com outro worker

            new_attempts = attempts + 1
            if new_attempts > max_attempts:
                self.conn.execute(
                    "UPDATE job SET status = 'QUARANTINED', last_error = 'MAX_ATTEMPTS_EXCEEDED', updated_at = ? WHERE id = ?",
                    (now, job_id),
                )
                return None

            self.conn.execute(
                """
                UPDATE job
                SET status = 'LEASED', lease_token = ?, lease_until = ?, attempts = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_token, lease_until, new_attempts, now, job_id),
            )

            return JobLease(
                job_id=job_id,
                lease_token=new_token,
                lease_until=lease_until,
                attempts=new_attempts,
                max_attempts=max_attempts,
                job_type=job_type,
                ref_id=ref_id,
            )

    def renew_lease(self, job_id: str, lease_token: str, extension_sec: float = 30.0) -> float:
        """Renova o lease vigente atomicamente se ainda não expirou."""
        now = time.time()
        new_until = now + extension_sec

        with self.conn:
            cur = self.conn.execute(
                """
                UPDATE job
                SET lease_until = ?, updated_at = ?
                WHERE id = ? AND lease_token = ? AND status = 'LEASED' AND lease_until >= ?
                """,
                (new_until, now, job_id, lease_token, now),
            )
            if cur.rowcount != 1:
                raise LeaseExpiredError(f"Lease {job_id} expirado ou substituido; renovacao rejeitada.")
            return new_until

    def execute_with_isolated_transaction(
        self,
        job_lease: JobLease,
        ai_invocation_fn: Callable[[JobLease], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Garante a salvaguarda REQ-OPS-003: Durante a chamada de IA, nenhuma transação

        fica aberta no banco de dados relacional.
        """
        # Verifica se o banco de dados NÃO está no meio de uma transação aberta
        if self.conn.in_transaction:
            raise RuntimeError("Inviolabilidade REQ-OPS-003: Transacao SQL ativa detectada antes da chamada de IA!")

        # Chamada lenta de IA roda livre de locks e transações SQL
        ai_result = ai_invocation_fn(job_lease)

        # Transação curta e atômica final para registrar o resultado
        return self.complete_job(job_lease.job_id, job_lease.lease_token, ai_result)

    def complete_job(
        self,
        job_id: str,
        lease_token: str,
        result_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Conclui a tarefa somente se o lease_token for o vigente e não expirou (REQ-OPS-004).

        Se o lease estiver expirado ou o worker estiver atrasado, o resultado é sumariamente
        descartado e registrado na tabela `discarded_stale_results`.
        """
        now = time.time()
        import json

        payload_str = json.dumps(result_payload, ensure_ascii=False)

        with self.conn:
            # Tenta comitar com proteção de token e lease temporal
            cur = self.conn.execute(
                """
                UPDATE job
                SET status = 'COMPLETED', lease_token = NULL, lease_until = NULL,
                    result_payload = ?, updated_at = ?
                WHERE id = ? AND lease_token = ? AND status = 'LEASED' AND lease_until >= ?
                """,
                (payload_str, now, job_id, lease_token, now),
            )

            if cur.rowcount == 1:
                return {
                    "status": "COMPLETED",
                    "job_id": job_id,
                    "committed": True,
                    "result": result_payload,
                }

            # ACC-OPS-004: Dado um lease expirado, quando o resultado chegar, então é descartado e registrado
            now_iso = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                """
                INSERT INTO discarded_stale_results (job_id, stale_token, reason, discarded_payload, discarded_at)
                VALUES (?, ?, 'LEASE_EXPIRED_OR_SUPERSEDED', ?, ?)
                """,
                (job_id, lease_token, payload_str, now_iso),
            )

        raise StaleWorkerRejectedError(
            f"Resultado atrasado para job {job_id} rejeitado e registrado: lease expirado ou substituido."
        )

    def fail_job(self, job_id: str, lease_token: str, error_code: str) -> str:
        """Registra falha. Se exceder max_attempts, envia para QUARANTINED (DLQ)."""
        now = time.time()
        with self.conn:
            cur = self.conn.execute(
                "SELECT attempts, max_attempts FROM job WHERE id = ? AND lease_token = ?",
                (job_id, lease_token),
            )
            row = cur.fetchone()
            if not row:
                raise LeaseExpiredError("Job nao encontrado ou lease token divergente.")

            attempts, max_attempts = row
            status = "QUARANTINED" if attempts >= max_attempts else "PENDING"

            self.conn.execute(
                """
                UPDATE job
                SET status = ?, lease_token = NULL, lease_until = NULL, last_error = ?, updated_at = ?
                WHERE id = ? AND lease_token = ?
                """,
                (status, error_code, now, job_id, lease_token),
            )
            return status

