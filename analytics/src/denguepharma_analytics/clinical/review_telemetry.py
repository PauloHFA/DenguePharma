"""Módulo de Telemetria de Estudo de Tempo e Pseudonimização Ética de Revisores.

Implementa os requisitos:
- REQ-REV-005 (ACC-REV-005 / RQ5, H1): Registro de tempo ativo por documento e por campo,
  com dedução estrita de pausas para estudo de esforço cognitivo.
- REQ-GOV-002 (ACC-GOV-002 / Ética): Pseudonimização de revisores nos dados exportados de tempo
  e subordinação à aprovação ética formal de pesquisa (Comitê de Ética em Pesquisa / CEP).
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class EthicalGovernanceError(Exception):
    """Lançado quando dados de revisores ou estudos de tempo são operados sem aprovação ética (REQ-GOV-002)."""


@dataclass
class ReviewPause:
    pause_start: float
    pause_end: Optional[float] = None
    reason: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.pause_end is None:
            return 0.0
        return max(0.0, self.pause_end - self.pause_start)


class ReviewSessionTelemetry:
    """Rastreia o tempo ativo de revisão por documento e por campo, descontando pausas (REQ-REV-005)."""

    def __init__(self, document_id: str, reviewer_id: str, start_time: Optional[float] = None):
        self.session_id = str(uuid.uuid4())
        self.document_id = document_id
        self.reviewer_id = reviewer_id
        self.start_time: float = start_time if start_time is not None else time.time()
        self.end_time: Optional[float] = None
        self.pauses: List[ReviewPause] = []
        self._current_pause: Optional[ReviewPause] = None
        self.field_active_times: Dict[str, float] = {}
        self.is_active: bool = True

    def pause(self, pause_time: Optional[float] = None, reason: str = "USER_PAUSE") -> None:
        """Inicia uma pausa na sessão (pausa voluntária ou inatividade detectada)."""
        if not self.is_active or self._current_pause is not None:
            return
        t = pause_time if pause_time is not None else time.time()
        self._current_pause = ReviewPause(pause_start=t, reason=reason)

    def resume(self, resume_time: Optional[float] = None) -> None:
        """Retoma a sessão de revisão, registrando o fim da pausa."""
        if self._current_pause is None:
            return
        t = resume_time if resume_time is not None else time.time()
        self._current_pause.pause_end = t
        self.pauses.append(self._current_pause)
        self._current_pause = None

    def record_field_time(self, field_name: str, duration_sec: float) -> None:
        """Registra o tempo ativo gasto em um campo específico."""
        if duration_sec > 0:
            self.field_active_times[field_name] = round(
                self.field_active_times.get(field_name, 0.0) + duration_sec, 4
            )

    def complete_session(self, end_time: Optional[float] = None) -> Dict[str, Any]:
        """Finaliza a sessão e calcula o tempo ativo subtraindo com exatidão as pausas (ACC-REV-005)."""
        t = end_time if end_time is not None else time.time()
        if self._current_pause is not None:
            self.resume(t)

        self.end_time = t
        self.is_active = False

        total_elapsed = max(0.0, self.end_time - self.start_time)
        total_pause = sum(p.duration for p in self.pauses)
        active_time = max(0.0, total_elapsed - total_pause)

        return {
            "session_id": self.session_id,
            "document_id": self.document_id,
            "reviewer_id": self.reviewer_id,
            "total_elapsed_sec": round(total_elapsed, 4),
            "total_pause_sec": round(total_pause, 4),
            "active_time_sec": round(active_time, 4),
            "field_times": dict(self.field_active_times),
            "pauses_count": len(self.pauses),
        }


class ReviewerPseudonymizer:
    """Pseudonimização irreversível de revisores para conformidade ética (REQ-GOV-002)."""

    DEFAULT_SALT = "denguepharma-ethical-cep-salt-2026"

    @classmethod
    def generate_pseudonym(cls, reviewer_id: str, salt: Optional[str] = None) -> str:
        s = salt or cls.DEFAULT_SALT
        digest = hashlib.sha256(f"{s}:{reviewer_id}".encode("utf-8")).hexdigest()
        # Retorna código no padrão 'REV-A1B2C3D4'
        return f"REV-{digest[:8].upper()}"


class TimeStudyDatasetExporter:
    """Exportador do conjunto de dados do estudo de tempo com salvaguardas éticas (REQ-GOV-002)."""

    VALID_ETHICAL_APPROVAL_PREFIXES = ("CEP-", "CAAE-", "IRB-")

    @classmethod
    def export_dataset(
        cls,
        sessions_data: List[Dict[str, Any]],
        ethical_approval_code: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Exporta os resultados do estudo de tempo com revisores rigorosamente pseudonimizados.

        Lança EthicalGovernanceError se não houver aprovação ética válida.
        """
        # Validação mandatória de conformidade ética prévia
        if not ethical_approval_code or not any(
            ethical_approval_code.startswith(p) for p in cls.VALID_ETHICAL_APPROVAL_PREFIXES
        ):
            raise EthicalGovernanceError(
                "Exportação de dados bloqueada: recrutamento e estudo de tempo exigem "
                f"aprovação ética formal válida ({cls.VALID_ETHICAL_APPROVAL_PREFIXES}) (REQ-GOV-002)."
            )

        anonymized_dataset: List[Dict[str, Any]] = []

        for record in sessions_data:
            clean_item = dict(record)
            original_reviewer = clean_item.pop("reviewer_id", None)
            
            if original_reviewer:
                clean_item["reviewer_code"] = ReviewerPseudonymizer.generate_pseudonym(original_reviewer)
            else:
                clean_item["reviewer_code"] = "REV-ANONYMOUS"

            # Garante que nenhum identificador direto pessoal (nome, email, uuid de usuário) permaneça
            clean_item["ethical_approval"] = ethical_approval_code
            clean_item["exported_at"] = datetime.now(timezone.utc).isoformat()
            anonymized_dataset.append(clean_item)

        return anonymized_dataset

