"""
Módulo M08: Calibração de Busca Clínica, Revisão do Piloto, Seleção de Corpus Final e Síntese Clínica Real (REQ-CLN-006).
"""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple


class ClinicalGovernanceError(ValueError):
    """Lançado quando uma salvaguarda metodológica de governança clínica é violada."""
    pass


class UnreviewedStudyError(ClinicalGovernanceError):
    """Lançado quando se tenta publicar síntese contendo estudos sem revisão humana documentada."""
    pass


class UnapprovedCalibrationError(ClinicalGovernanceError):
    """Lançado quando se tenta publicar síntese sem aprovação prévia de calibração por adjudicador."""
    pass


def sha256_digest(content: bytes) -> str:
    """Calcula hash criptográfico SHA-256."""
    return hashlib.sha256(content).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    """Serializa para JSON canônico determinístico bit-a-bit."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass
class CalibrationReport:
    """Resultado da calibração metodológica da busca clínica (REQ-CLN-006)."""
    calibration_id: str
    basis_hash: str
    total_raw_documents: int
    sentinel_ids: List[str]
    sentinels_retrieved: List[str]
    sentinel_recall: float
    noise_signals_detected: Dict[str, int]
    is_approved: bool
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None

    def validate_for_publication(self) -> None:
        if self.sentinel_recall < 1.0:
            raise ClinicalGovernanceError(f"REQ-CLN-006: Recall de sentinelas insuficiente ({self.sentinel_recall * 100:.1f}%). Exige 100%.")
        if not self.is_approved:
            raise UnapprovedCalibrationError("REQ-CLN-006: Calibração metodológica não foi formalmente aprovada por adjudicador.")
        if not self.approved_by:
            raise UnapprovedCalibrationError("REQ-CLN-006: Identificação do adjudicador responsável pela calibração é obrigatória.")


@dataclass
class PilotReviewRecord:
    """Registro individual da revisão metodológica do piloto (REQ-CLN-006)."""
    document_id: str
    sources: str
    title: str
    document_type: str
    identifiers: str
    eligibility_decision: Literal["INCLUIR", "EXCLUIR", "INCERTO"]
    exclusion_reason: Optional[str]
    context_reviewed: str
    purpose_reviewed: str
    preparation_validated: str
    reviewer: str
    reviewed_at: str
    notes: str


@dataclass
class PilotReviewSummary:
    """Sumário auditável da triagem independente do piloto metodológico (REQ-CLN-006)."""
    total_screened: int
    included_count: int
    excluded_count: int
    reasons_breakdown: Dict[str, int]
    records: List[PilotReviewRecord]
    reviewers: Set[str]
    screening_hash: str


@dataclass
class FinalCorpus:
    """Corpus final selecionado para a síntese clínica real (REQ-CLN-006)."""
    corpus_id: str
    included_studies: List[Dict[str, Any]]
    total_included: int
    corpus_hash: str


@dataclass
class RealClinicalSynthesis:
    """Síntese clínica real documentada e publicada (REQ-CLN-006 / ACC-CLN-006)."""
    synthesis_id: str
    published_at: str
    publisher_adjudicator: str
    calibration: CalibrationReport
    corpus: FinalCorpus
    conclusions: List[Dict[str, Any]]
    synthesis_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "published_at": self.published_at,
            "publisher_adjudicator": self.publisher_adjudicator,
            "calibration": asdict(self.calibration),
            "corpus": asdict(self.corpus),
            "conclusions": self.conclusions,
            "synthesis_hash": self.synthesis_hash,
        }


class SearchCalibrator:
    """Executa a calibração de termos e sensibilidade da busca clínica."""

    @staticmethod
    def calibrate(
        raw_documents: List[Dict[str, Any]],
        sentinel_ids: List[str],
        adjudicator: Optional[str] = None,
        approval_reason: Optional[str] = None,
    ) -> CalibrationReport:
        if not sentinel_ids:
            raise ValueError("Ao menos um estudo sentinela deve ser fornecido para calibração.")

        doc_ids = {d.get("document_id") or d.get("documentId") for d in raw_documents}
        retrieved_sentinels = [s for s in sentinel_ids if s in doc_ids]
        recall = len(retrieved_sentinels) / len(sentinel_ids)

        noise_counts = {
            "CONTROLE_VETORIAL": 0,
            "IMUNIZACAO_VACINAL": 0,
            "PRE_CLINICO_IN_VITRO": 0,
            "EPIDEMIOLOGICO_OU_REVISAO": 0,
        }

        for d in raw_documents:
            title = (d.get("title") or "").lower()
            if any(k in title for k in ["aedes", "mosquito", "vector", "larvicid"]):
                noise_counts["CONTROLE_VETORIAL"] += 1
            if any(k in title for k in ["vaccin", "immunization", "tdv"]):
                noise_counts["IMUNIZACAO_VACINAL"] += 1
            if any(k in title for k in ["in vitro", "cell line", "binding assay"]):
                noise_counts["PRE_CLINICO_IN_VITRO"] += 1
            if any(k in title for k in ["review", "epidemiology", "survey"]):
                noise_counts["EPIDEMIOLOGICO_OU_REVISAO"] += 1

        basis_bytes = canonical_json_bytes(sorted(doc_ids))
        basis_hash = sha256_digest(basis_bytes)
        calib_id = f"CALIB-{basis_hash[:12]}"

        is_approved = bool(adjudicator and approval_reason and recall == 1.0)

        return CalibrationReport(
            calibration_id=calib_id,
            basis_hash=basis_hash,
            total_raw_documents=len(raw_documents),
            sentinel_ids=sentinel_ids,
            sentinels_retrieved=retrieved_sentinels,
            sentinel_recall=recall,
            noise_signals_detected=noise_counts,
            is_approved=is_approved,
            approved_by=adjudicator if is_approved else None,
            approval_reason=approval_reason if is_approved else None,
        )


class PilotMethodologicalReviewer:
    """Audita e valida a triagem humana independente do piloto metodológico."""

    @staticmethod
    def load_from_csv(csv_path: Path | str) -> PilotReviewSummary:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo do piloto não encontrado: {path}")

        records: List[PilotReviewRecord] = []
        reasons_counter: Dict[str, int] = {}
        reviewers_set: Set[str] = set()

        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                decision = row["eligibility_decision"].strip()
                reviewer = row["reviewer"].strip()
                reviewed_at = row["reviewed_at"].strip()

                if not reviewer or not reviewed_at:
                    raise ClinicalGovernanceError(
                        f"REQ-CLN-006: Estudo {row['document_id']} sem revisor humano documentado."
                    )

                reason = row.get("exclusion_reason", "").strip() or None
                if decision == "EXCLUIR" and not reason:
                    raise ClinicalGovernanceError(
                        f"REQ-CLN-006: Decisão EXCLUIR sem justificativa explícita no documento {row['document_id']}."
                    )

                if reason:
                    reasons_counter[reason] = reasons_counter.get(reason, 0) + 1

                reviewers_set.add(reviewer)

                records.append(
                    PilotReviewRecord(
                        document_id=row["document_id"].strip(),
                        sources=row["sources"].strip(),
                        title=row["title"].strip(),
                        document_type=row["document_type"].strip(),
                        identifiers=row["identifiers"].strip(),
                        eligibility_decision=decision,  # type: ignore
                        exclusion_reason=reason,
                        context_reviewed=row["context_reviewed"].strip(),
                        purpose_reviewed=row["purpose_reviewed"].strip(),
                        preparation_validated=row["preparation_validated"].strip(),
                        reviewer=reviewer,
                        reviewed_at=reviewed_at,
                        notes=row["notes"].strip(),
                    )
                )

        included = sum(1 for r in records if r.eligibility_decision == "INCLUIR")
        excluded = sum(1 for r in records if r.eligibility_decision == "EXCLUIR")

        canonical_data = [
            (r.document_id, r.eligibility_decision, r.reviewer, r.reviewed_at)
            for r in records
        ]
        s_hash = sha256_digest(canonical_json_bytes(canonical_data))

        return PilotReviewSummary(
            total_screened=len(records),
            included_count=included,
            excluded_count=excluded,
            reasons_breakdown=reasons_counter,
            records=records,
            reviewers=reviewers_set,
            screening_hash=s_hash,
        )


class FinalCorpusSelector:
    """Seleciona o corpus clínico final com base nas decisões validadas."""

    @staticmethod
    def select(pilot_summary: PilotReviewSummary) -> FinalCorpus:
        included_studies = []
        for r in pilot_summary.records:
            if r.eligibility_decision == "INCLUIR":
                included_studies.append({
                    "document_id": r.document_id,
                    "title": r.title,
                    "sources": r.sources,
                    "identifiers": r.identifiers,
                    "context": r.context_reviewed,
                    "purpose": r.purpose_reviewed,
                    "reviewer": r.reviewer,
                    "reviewed_at": r.reviewed_at,
                })

        sorted_studies = sorted(included_studies, key=lambda s: s["document_id"])
        c_hash = sha256_digest(canonical_json_bytes(sorted_studies))
        corpus_id = f"CORPUS-FINAL-{c_hash[:12]}"

        return FinalCorpus(
            corpus_id=corpus_id,
            included_studies=sorted_studies,
            total_included=len(sorted_studies),
            corpus_hash=c_hash,
        )


class RealClinicalSynthesisPublisher:
    """Publica a síntese clínica real documentada após validação de salvaguardas."""

    VALID_CATEGORIES = {"BENEFICIO_SUSTENTADO", "EVIDENCIA_INCONCLUSIVA", "SINAL_DANO"}

    @classmethod
    def publish(
        cls,
        corpus: FinalCorpus,
        calibration: CalibrationReport,
        conclusions: List[Dict[str, Any]],
        publisher_adjudicator: str,
        published_at: str,
    ) -> RealClinicalSynthesis:
        # Salvaguarda 1: Calibração aprovada
        calibration.validate_for_publication()

        # Salvaguarda 2: Papel de adjudicador obrigatório
        if not publisher_adjudicator or not str(publisher_adjudicator).strip():
            raise ClinicalGovernanceError("REQ-CLN-006: Publicação exige adjudicador formalmente identificado.")

        # Salvaguarda 3: Todos os estudos incluídos no corpus final devem ter conclusão humana documentada
        corpus_doc_ids = {s["document_id"] for s in corpus.included_studies}
        concluded_doc_ids = {c.get("document_id") for c in conclusions if c.get("document_id")}

        missing_conclusions = corpus_doc_ids - concluded_doc_ids
        if missing_conclusions:
            raise UnreviewedStudyError(
                f"REQ-CLN-006: Estudos no corpus final sem conclusão humana registrada: {missing_conclusions}"
            )

        # Salvaguarda 4: Conclusões devem conter categoria clínica válida e justificativa
        for c in conclusions:
            cat = c.get("category")
            if cat not in cls.VALID_CATEGORIES:
                raise ClinicalGovernanceError(
                    f"REQ-CLN-006: Categoria clínica inválida: '{cat}'. Permitidas: {cls.VALID_CATEGORIES}"
                )
            if not c.get("rationale") or len(str(c.get("rationale")).strip()) < 10:
                raise ClinicalGovernanceError(
                    f"REQ-CLN-006: Justificativa clínica obrigatória ausente ou muito curta no estudo {c.get('document_id')}."
                )

        payload = {
            "publisher": publisher_adjudicator,
            "published_at": published_at,
            "calibration_id": calibration.calibration_id,
            "corpus_hash": corpus.corpus_hash,
            "conclusions": sorted(conclusions, key=lambda x: str(x.get("document_id"))),
        }
        s_hash = sha256_digest(canonical_json_bytes(payload))
        synthesis_id = f"SYNTHESIS-REAL-{s_hash[:12]}"

        return RealClinicalSynthesis(
            synthesis_id=synthesis_id,
            published_at=published_at,
            publisher_adjudicator=publisher_adjudicator,
            calibration=calibration,
            corpus=corpus,
            conclusions=conclusions,
            synthesis_hash=s_hash,
        )
