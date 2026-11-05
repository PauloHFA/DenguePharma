"""Módulo de Backoff Exponencial com Jitter, Quarentena Auditada e Governança Orçamentária de IA.

Implementa os requisitos:
- REQ-OPS-005 (ACC-OPS-005 / RF-11): Backoff com jitter, limite de tentativas, quarentena visível
  e reprocessamento autorizado com auditoria formal.
- REQ-OPS-006 (ACC-OPS-006 / RNF): Controle de orçamento de IA por execução, registro cumulativo
  de custos e suspensão preventiva com alerta ao atingir o teto orçamentário.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class AIBudgetExceededError(Exception):
    """Lançado quando uma chamada de IA excederia o teto de orçamento configurado (REQ-OPS-006)."""


@dataclass
class BackoffPolicy:
    """Configuração de retentativas com backoff exponencial e jitter (REQ-OPS-005)."""
    base_seconds: float = 1.0
    factor: float = 2.0
    max_seconds: float = 300.0
    max_jitter_seconds: float = 3.0
    max_attempts: int = 3

    def compute_delay(self, attempt: int, seed: Optional[int] = None) -> float:
        """Calcula delay com backoff exponencial truncado somado a jitter aleatório.

        Fórmula: delay = min(max_seconds, base * (factor ^ min(attempt, 8))) + random(0, jitter_max)
        """
        capped_attempt = min(max(0, attempt), 8)
        exp_delay = min(self.max_seconds, self.base_seconds * (self.factor ** capped_attempt))
        
        rng = random.Random(seed) if seed is not None else random
        jitter = rng.uniform(0.0, self.max_jitter_seconds)
        return exp_delay + jitter

    def should_quarantine(self, attempts: int) -> bool:
        """Determina se a tarefa excedeu o limite de tentativas e deve ir para quarentena."""
        return attempts >= self.max_attempts


@dataclass
class AuditRecord:
    actor: str
    action: str
    target_type: str
    target_id: str
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QuarantineManager:
    """Gerenciador de tarefas em quarentena (Dead Letter Queue) com reprocessamento auditado (REQ-OPS-005)."""

    def __init__(self, policy: Optional[BackoffPolicy] = None):
        self.policy = policy or BackoffPolicy()
        self.quarantined_jobs: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[AuditRecord] = []

    def register_failure(
        self,
        job_id: str,
        current_attempts: int,
        error_code: str,
        payload: Dict[str, Any],
    ) -> Tuple[str, Optional[float]]:
        """Registra falha e decide entre novo agendamento com backoff ou quarentena."""
        if self.policy.should_quarantine(current_attempts):
            status = "QUARANTINED"
            self.quarantined_jobs[job_id] = {
                "job_id": job_id,
                "status": "QUARANTINED",
                "attempts": current_attempts,
                "last_error": error_code,
                "payload": payload,
                "quarantined_at": datetime.now(timezone.utc).isoformat(),
            }
            return status, None

        status = "PENDING"
        delay = self.policy.compute_delay(current_attempts)
        return status, delay

    def authorize_retry(
        self,
        job_id: str,
        actor: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Autoriza e audita a retomada de uma tarefa em quarentena (ACC-OPS-005)."""
        if job_id not in self.quarantined_jobs:
            raise ValueError(f"Job {job_id} nao encontrado na quarentena.")

        job_data = self.quarantined_jobs.pop(job_id)
        job_data["status"] = "PENDING"
        job_data["attempts"] = 0  # Reseta contador para nova tentativa autorizada
        job_data["retried_at"] = datetime.now(timezone.utc).isoformat()

        # Auditoria compulsória da autorização humana/administrativa
        audit_entry = AuditRecord(
            actor=actor,
            action="JOB_RETRY_AUTHORIZED",
            target_type="job",
            target_id=job_id,
            reason=reason,
        )
        self.audit_log.append(audit_entry)

        return {
            "job_id": job_id,
            "status": "PENDING",
            "audit": audit_entry,
        }


@dataclass
class BudgetAlert:
    alert_type: str
    message: str
    current_spend_usd: float
    ceiling_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AIBudgetGuard:
    """Guarda de Orçamento e Custos de IA por execução (REQ-OPS-006).

    Monitora e acumula gastos com modelos de linguagem/visão, calculando custos
    a partir de tokens de entrada e saída. Ao atingir o teto, suspende preventivamente
    novas invocações e emite alerta estruturado.
    """

    # Tarifas de referência por 1k tokens (ex: GPT-4o-mini / Gemini Flash)
    RATES_PER_1K = {
        "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
        "gemini-1.5-pro": {"prompt": 0.00125, "completion": 0.005},
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "default": {"prompt": 0.0005, "completion": 0.0015},
    }

    def __init__(self, ceiling_usd: float):
        self.ceiling_usd = ceiling_usd
        self.cumulative_spend_usd: float = 0.0
        self.execution_runs: List[Dict[str, Any]] = []
        self.alerts: List[BudgetAlert] = []
        self.is_suspended: bool = False

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rate = self.RATES_PER_1K.get(model, self.RATES_PER_1K["default"])
        cost = (prompt_tokens / 1000.0 * rate["prompt"]) + (completion_tokens / 1000.0 * rate["completion"])
        return round(cost, 6)

    def authorize_and_record_run(
        self,
        run_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Dict[str, Any]:
        """Verifica se a chamada cabe no teto antes de cometer o custo (ACC-OPS-006).

        Se a chamada atingir ou exceder o teto, suspende novas chamadas e emite alerta.
        """
        estimated_cost = self.estimate_cost(model, prompt_tokens, completion_tokens)
        projected_spend = round(self.cumulative_spend_usd + estimated_cost, 6)

        if self.is_suspended or projected_spend > self.ceiling_usd:
            self.is_suspended = True
            alert = BudgetAlert(
                alert_type="BUDGET_CEILING_REACHED",
                message=f"Teto orcamentario de USD ${self.ceiling_usd:.2f} excedido ou atingido (projetado: ${projected_spend:.4f}). Novas chamadas suspensas.",
                current_spend_usd=self.cumulative_spend_usd,
                ceiling_usd=self.ceiling_usd,
            )
            self.alerts.append(alert)
            raise AIBudgetExceededError(alert.message)

        # Registra a execução com sucesso
        self.cumulative_spend_usd = projected_spend
        run_record = {
            "run_id": run_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": estimated_cost,
            "cumulative_spend_usd": self.cumulative_spend_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.execution_runs.append(run_record)

        # Se após a execução o gasto alcançou o teto com exatidão
        if self.cumulative_spend_usd >= self.ceiling_usd:
            self.is_suspended = True
            alert = BudgetAlert(
                alert_type="BUDGET_CEILING_REACHED",
                message=f"Teto orcamentario de USD ${self.ceiling_usd:.2f} atingido exatamente. Novas chamadas suspensas.",
                current_spend_usd=self.cumulative_spend_usd,
                ceiling_usd=self.ceiling_usd,
            )
            self.alerts.append(alert)

        return run_record

    def get_status(self) -> Dict[str, Any]:
        return {
            "ceiling_usd": self.ceiling_usd,
            "cumulative_spend_usd": self.cumulative_spend_usd,
            "remaining_usd": max(0.0, round(self.ceiling_usd - self.cumulative_spend_usd, 6)),
            "usage_percentage": round((self.cumulative_spend_usd / self.ceiling_usd) * 100.0, 2) if self.ceiling_usd > 0 else 100.0,
            "is_suspended": self.is_suspended,
            "total_runs": len(self.execution_runs),
            "alerts_count": len(self.alerts),
        }

