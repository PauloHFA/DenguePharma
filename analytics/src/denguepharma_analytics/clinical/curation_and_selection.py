"""Módulo de curadoria humana lado a lado, triagem duplo-cega, proteção de evidências e panorama de estudos.

Implementa os requisitos finais do SDD:
- REQ-ANA-001 (ACC-ANA-001): Panorama agregando por study_id com soma igual por finalidade.
- REQ-REV-001 (ACC-REV-001): Curadoria lado a lado (aceitar, corrigir, rejeitar) com trilha de auditoria.
- REQ-REV-002 (ACC-REV-002): Bloqueio de publicação de campos críticos aprovados apenas por revisor comum.
- REQ-REV-003 (ACC-REV-003): Imunidade de valores aprovados contra sobrescrita por IA posterior.
- REQ-REV-004 (ACC-REV-004): Exclusão de rascunhos automáticos de exportações públicas.
- REQ-SEL-001 (ACC-SEL-001): Triagem independente por dois revisores gravando decisões separadas.
- REQ-SEL-002 (ACC-SEL-002): Ocultamento cego de decisões entre revisores e roteamento de conflitos.
- REQ-SEL-003 (ACC-SEL-003): Proibição de exclusão automática por IA (apenas priorização de leitura).
- REQ-SEL-005 (ACC-SEL-005): Preservação de artigos sob paywall como 'somente resumo' e impacto na cobertura.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ReviewAction(str, Enum):
    ACEITAR = "ACEITAR"
    CORRIGIR = "CORRIGIR"
    REJEITAR = "REJEITAR"


class ScreeningDecision(str, Enum):
    INCLUIR = "INCLUIR"
    EXCLUIR = "EXCLUIR"
    DUVIDA = "DUVIDA"


class PublicationDeniedError(Exception):
    """Exceção levantada quando campos críticos não possuem aprovação de adjudicador (REQ-REV-002)."""


class AutonomousAiExclusionError(Exception):
    """Exceção levantada quando um modelo tenta excluir registro sem decisão humana (REQ-SEL-003)."""


# ==============================================================================
# REQ-ANA-001: Panorama de estudos por estudo (study_id)
# ==============================================================================


@dataclass
class StudyOverviewRecord:
    study_id: str
    substance: str
    purpose: str  # "TRATAMENTO", "PROFILAXIA", "SINTOMATICO"
    phase: str
    design: str
    year: int
    country: str
    sponsor: str
    document_ids: List[str] = field(default_factory=list)


class StudyPanoramaGenerator:
    """Gera o panorama de estudos agregando exclusivamente por study_id (REQ-ANA-001).

    Garante que:
    1. A unidade contábil seja o study_id e não documentos/artigos duplicados.
    2. A soma de estudos por finalidade (purpose) seja estritamente igual ao total de study_id.
    3. Exibe denominadores e declaração de limitações metodológicas.
    """

    def generate_panorama(
        self, studies: List[StudyOverviewRecord]
    ) -> Dict[str, Any]:
        # Deduplica estudos por study_id
        unique_studies: Dict[str, StudyOverviewRecord] = {
            s.study_id: s for s in studies
        }
        total_studies = len(unique_studies)

        # Agrupamento por finalidade
        by_purpose: Dict[str, int] = {}
        by_phase: Dict[str, int] = {}
        by_substance: Dict[str, int] = {}
        by_country: Dict[str, int] = {}

        for s in unique_studies.values():
            by_purpose[s.purpose] = by_purpose.get(s.purpose, 0) + 1
            by_phase[s.phase] = by_phase.get(s.phase, 0) + 1
            by_substance[s.substance] = by_substance.get(s.substance, 0) + 1
            by_country[s.country] = by_country.get(s.country, 0) + 1

        purpose_sum = sum(by_purpose.values())

        return {
            "total_studies": total_studies,
            "denominator": total_studies,
            "purpose_sum": purpose_sum,
            "is_sum_consistent": purpose_sum == total_studies,
            "by_purpose": by_purpose,
            "by_phase": by_phase,
            "by_substance": by_substance,
            "by_country": by_country,
            "limitations": [
                "Estudos sem publicação indexada identificada são censurados à data de corte.",
                "Multiplos artigos do mesmo estudo clínico estão colapsados no study_id único.",
            ],
        }


# ==============================================================================
# REQ-REV-001: Curadoria lado a lado e trilha de auditoria
# ==============================================================================


@dataclass
class CorrectionAuditLog:
    field_name: str
    before_value: Any
    after_value: Any
    author_id: str
    reason: str
    timestamp: str
    action: ReviewAction


class SideBySideReviewCurator:
    """Curadoria lado a lado com registro de antes, depois, autor, motivo e hora (REQ-REV-001)."""

    def __init__(self) -> None:
        self.audit_trail: List[CorrectionAuditLog] = []

    def review_field(
        self,
        field_name: str,
        ai_suggestion: Any,
        source_quote: str,
        action: ReviewAction,
        author_id: str,
        corrected_value: Optional[Any] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        before = ai_suggestion

        if action == ReviewAction.ACEITAR:
            after = ai_suggestion
            reason_text = reason or "Sugestão da IA aceita conforme evidência fonte."
        elif action == ReviewAction.CORRIGIR:
            if corrected_value is None:
                raise ValueError("Ação CORRIGIR exige corrected_value.")
            if not reason:
                raise ValueError("Ação CORRIGIR exige motivo explícito.")
            after = corrected_value
            reason_text = reason
        elif action == ReviewAction.REJEITAR:
            after = None
            reason_text = reason or "Sugestão da IA rejeitada por falta de ancoragem."
        else:
            raise ValueError(f"Ação de revisão desconhecida: {action}")

        log_entry = CorrectionAuditLog(
            field_name=field_name,
            before_value=before,
            after_value=after,
            author_id=author_id,
            reason=reason_text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
        )
        self.audit_trail.append(log_entry)

        return {
            "field_name": field_name,
            "source_quote": source_quote,
            "action": action.value,
            "before": before,
            "after": after,
            "author": author_id,
            "reason": reason_text,
            "timestamp": log_entry.timestamp,
        }


# ==============================================================================
# REQ-REV-002: Bloqueio de campos críticos sem aprovação de adjudicador
# ==============================================================================


class CriticalFieldGatekeeper:
    """Impede publicação pública de campos críticos aprovados apenas por revisor (REQ-REV-002)."""

    CRITICAL_FIELDS: Set[str] = {
        "primary_outcome",
        "study_design",
        "intervention_dose",
        "severe_adverse_events",
        "mortality_count",
    }

    def validate_for_publication(
        self,
        fields_approved: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """fields_approved: dict de field_name -> {"value": ..., "approver_role": "REVISOR" | "ADJUDICADOR"}"""
        unauthorized_critical_fields = []

        for f_name, data in fields_approved.items():
            if f_name in self.CRITICAL_FIELDS:
                role = data.get("approver_role", "").upper()
                if role != "ADJUDICADOR":
                    unauthorized_critical_fields.append(
                        f"Campo crítico '{f_name}' possui aprovação apenas de '{role}', exigindo aprovação por ADJUDICADOR."
                    )

        if unauthorized_critical_fields:
            raise PublicationDeniedError(
                f"Publicação Negada (REQ-REV-002): {'; '.join(unauthorized_critical_fields)}"
            )

        return {
            "status": "APPROVED_FOR_PUBLICATION",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "fields_count": len(fields_approved),
        }


# ==============================================================================
# REQ-REV-003: Imunidade de valores aprovados contra sobrescrita por IA posterior
# ==============================================================================


class ApprovedValueProtectionShield:
    """Protege valores aprovados por humanos contra sobrescrita por nova extração de IA (REQ-REV-003)."""

    def __init__(self) -> None:
        # field_key -> {"value": ..., "is_human_approved": bool}
        self.current_state: Dict[str, Dict[str, Any]] = {}
        self.divergence_alerts: List[Dict[str, Any]] = []

    def set_approved_value(self, field_key: str, value: Any, approver: str) -> None:
        self.current_state[field_key] = {
            "value": value,
            "is_human_approved": True,
            "approved_by": approver,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

    def apply_new_ai_extraction(
        self,
        field_key: str,
        new_ai_value: Any,
        model_version: str,
    ) -> Dict[str, Any]:
        existing = self.current_state.get(field_key)

        if existing and existing.get("is_human_approved"):
            if existing["value"] != new_ai_value:
                # O valor aprovado permanece intacto e a divergência gera alerta
                alert = {
                    "field_key": field_key,
                    "approved_value": existing["value"],
                    "divergent_ai_value": new_ai_value,
                    "model_version": model_version,
                    "alert_created_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "Nova extração por IA divergiu de valor humano aprovado.",
                }
                self.divergence_alerts.append(alert)
                return {
                    "field_key": field_key,
                    "active_value": existing["value"],
                    "overwritten": False,
                    "alert_generated": True,
                    "divergence_alert": alert,
                }
            else:
                return {
                    "field_key": field_key,
                    "active_value": existing["value"],
                    "overwritten": False,
                    "alert_generated": False,
                }

        # Não é campo aprovado por humano: aceita sugestão
        self.current_state[field_key] = {
            "value": new_ai_value,
            "is_human_approved": False,
            "suggested_by_model": model_version,
        }
        return {
            "field_key": field_key,
            "active_value": new_ai_value,
            "overwritten": True,
            "alert_generated": False,
        }


# ==============================================================================
# REQ-REV-004: Exclusão de rascunhos de exportações públicas
# ==============================================================================


class DraftSanitizingExporter:
    """Expurga rascunhos automáticos de catálogos e relatórios públicos (REQ-REV-004)."""

    @classmethod
    def export_public_catalog(
        cls, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        public_records = []
        for r in records:
            # Rascunho automático se marcado explicitamente como draft ou status RASCUNHO
            is_draft = r.get("is_draft") or r.get("status") in (
                "RASCUNHO",
                "DRAFT",
                "AUTO_SUGGESTION",
            )
            if not is_draft:
                public_records.append(copy.deepcopy(r))
        return public_records


# ==============================================================================
# REQ-SEL-001 & REQ-SEL-002: Triagem duplo-cega independente e resolução
# ==============================================================================


@dataclass
class ScreeningDecisionRecord:
    item_id: str
    reviewer_id: str
    decision: ScreeningDecision
    reason: str
    timestamp: str


class BlindDualScreeningWorkflow:
    """Workflow de triagem independente duplo-cega com ocultamento e encaminhamento a adjudicação (REQ-SEL-001, REQ-SEL-002)."""

    def __init__(self) -> None:
        # item_id -> {"rev1": ScreeningDecisionRecord, "rev2": ScreeningDecisionRecord, "adjudication": ...}
        self.items: Dict[str, Dict[str, Any]] = {}

    def get_item_for_review(self, item_id: str, reviewer_id: str) -> Dict[str, Any]:
        """Quando o revisor abre o item, as decisões de outros revisores estão estritamente ocultas (REQ-SEL-002)."""
        item_state = self.items.get(item_id, {})
        my_previous_decision = None

        if item_state.get("reviewer_1_id") == reviewer_id:
            my_previous_decision = item_state.get("decision_1")
        elif item_state.get("reviewer_2_id") == reviewer_id:
            my_previous_decision = item_state.get("decision_2")

        return {
            "item_id": item_id,
            "my_reviewer_id": reviewer_id,
            "my_previous_decision": my_previous_decision.decision.value if my_previous_decision else None,
            "other_reviewer_decision": "MASKED_BLINDED",  # Decisão de terceiros oculta!
            "is_blinded": True,
        }

    def submit_decision(
        self,
        item_id: str,
        reviewer_id: str,
        decision: ScreeningDecision,
        reason: str,
    ) -> Dict[str, Any]:
        if item_id not in self.items:
            self.items[item_id] = {
                "reviewer_1_id": reviewer_id,
                "decision_1": ScreeningDecisionRecord(
                    item_id=item_id,
                    reviewer_id=reviewer_id,
                    decision=decision,
                    reason=reason,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                "reviewer_2_id": None,
                "decision_2": None,
                "status": "WAITING_SECOND_REVIEWER",
            }
            return {
                "item_id": item_id,
                "status": "WAITING_SECOND_REVIEWER",
                "both_completed": False,
            }

        state = self.items[item_id]
        if state["reviewer_1_id"] == reviewer_id:
            # Atualização da própria decisão
            state["decision_1"] = ScreeningDecisionRecord(
                item_id=item_id,
                reviewer_id=reviewer_id,
                decision=decision,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            return {"item_id": item_id, "status": state["status"], "both_completed": False}

        # Segundo revisor registrando sua decisão
        state["reviewer_2_id"] = reviewer_id
        state["decision_2"] = ScreeningDecisionRecord(
            item_id=item_id,
            reviewer_id=reviewer_id,
            decision=decision,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        dec1 = state["decision_1"].decision
        dec2 = state["decision_2"].decision

        if dec1 == dec2:
            state["status"] = "CONCORDANT"
            state["final_decision"] = dec1.value
        else:
            # Divergência detectada: encaminhamento compulsório à adjudicação
            state["status"] = "PENDING_ADJUDICATION"
            state["final_decision"] = None

        return {
            "item_id": item_id,
            "status": state["status"],
            "both_completed": True,
            "is_divergent": dec1 != dec2,
        }


# ==============================================================================
# REQ-SEL-003: Proibição de exclusão automática por modelo de IA
# ==============================================================================


class AiTriageRanker:
    """Permite à IA priorizar a fila de leitura, mas proíbe terminantemente exclusão autônoma (REQ-SEL-003)."""

    def rank_reading_queue(
        self, items: List[Dict[str, Any]], relevance_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        # Ordena a fila de leitura de forma decrescente pelo score
        ranked = sorted(
            items,
            key=lambda x: relevance_scores.get(x.get("id", ""), 0.0),
            reverse=True,
        )
        for idx, item in enumerate(ranked, 1):
            item["reading_priority_rank"] = idx
        return ranked

    def attempt_autonomous_exclusion(
        self, item_id: str, model_decision: str
    ) -> None:
        """Tentativa de modelo excluir artigo sem intervenção humana é rejeitada."""
        if model_decision.upper() == "EXCLUIR":
            raise AutonomousAiExclusionError(
                f"Violação de Salvaguarda Metodológica (REQ-SEL-003): "
                f"Modelo não pode excluir o item '{item_id}' automaticamente. Exclusão requer julgamento humano."
            )


# ==============================================================================
# REQ-SEL-005: Preservação de artigos sob paywall e relatório de impacto
# ==============================================================================


class PaywallCoverageAssessor:
    """Preserva artigos sem texto integral (paywall) e reporta seu impacto (REQ-SEL-005)."""

    def assess_document(
        self,
        doc_id: str,
        title: str,
        is_paywalled: bool,
        abstract_available: bool = True,
    ) -> Dict[str, Any]:
        if is_paywalled:
            # Não é excluído da síntese
            status = "SOMENTE_RESUMO" if abstract_available else "TEXTO_NAO_OBTIDO"
            return {
                "doc_id": doc_id,
                "title": title,
                "is_excluded": False,
                "screening_status": status,
                "impact_statement": "Artigo mantido para extração de nível de evidência e caracterização amostral via resumo, sem acesso a tabelas integrais.",
            }
        else:
            return {
                "doc_id": doc_id,
                "title": title,
                "is_excluded": False,
                "screening_status": "TEXTO_COMPLETO_DISPONIVEL",
                "impact_statement": None,
            }

    def generate_coverage_report(
        self, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        total = len(documents)
        paywalled_count = sum(1 for d in documents if d.get("is_paywalled"))
        fulltext_count = total - paywalled_count

        return {
            "total_documents": total,
            "fulltext_available_count": fulltext_count,
            "paywalled_count": paywalled_count,
            "paywall_impact_percentage": round((paywalled_count / total * 100), 1) if total else 0.0,
            "declarations": [
                f"{paywalled_count} de {total} documentos foram triados com status 'SOMENTE_RESUMO' devido a restrições de paywall, sem exclusão arbitrária."
            ],
        }
