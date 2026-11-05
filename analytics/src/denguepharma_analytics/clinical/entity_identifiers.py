"""Módulo de resolução de identificadores, vínculos de entidades e deduplicação clínica.

Implementa requisitos da família REQ-IDN:
- REQ-IDN-001: Resolução de discrepâncias entre NCT, PMID, PMCID e DOI.
- REQ-IDN-002: Gestão de vínculos de documentos a estudos com limiar de certeza e desfazer auditado.
- REQ-IDN-003: Normalização de substâncias com ontologias (PubChem/ChEMBL) e separação de combinações.
- REQ-IDN-004: Deduplicação de participantes sob study_id único evitando inflação de N amostral.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class LinkStatus(str, Enum):
    AUTO_LINKED = "auto_linked"
    PENDING_HUMAN_CONFIRMATION = "pending_human_confirmation"
    HUMAN_CONFIRMED = "human_confirmed"
    DIVERGENT = "divergent"
    UNLINKED = "unlinked"


@dataclass(frozen=True)
class DocumentIdentifiers:
    doc_id: str
    doi: Optional[str] = None
    nct: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    title: Optional[str] = None

    def normalized_doi(self) -> Optional[str]:
        if not self.doi:
            return None
        doi_clean = self.doi.strip().lower()
        doi_clean = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi_clean)
        return doi_clean

    def normalized_nct(self) -> Optional[str]:
        if not self.nct:
            return None
        nct_clean = self.nct.strip().upper()
        match = re.search(r"NCT\d{8}", nct_clean)
        return match.group(0) if match else nct_clean

    def normalized_pmid(self) -> Optional[str]:
        if not self.pmid:
            return None
        return re.sub(r"[^\d]", "", self.pmid.strip())

    def normalized_pmcid(self) -> Optional[str]:
        if not self.pmcid:
            return None
        val = self.pmcid.strip().upper()
        if not val.startswith("PMC"):
            val = f"PMC{val}"
        return val


class IdentifierDiscrepancyResolver:
    """Resolve vínculos entre pares de documentos e detecta discrepâncias de identificadores (REQ-IDN-001).

    Regras:
    1. NCT, PMID, PMCID e DOI são complementares e não intercambiáveis.
    2. Dois documentos com o mesmo DOI mas com NCTs distintos declarados geram status DIVERGENT
       e impedem a fusão automática, exigindo adjudicação/revisão humana.
    3. Documentos com NCT idêntico e sem divergência em DOI/PMID podem ser associados.
    """

    def resolve(
        self, doc_a: DocumentIdentifiers, doc_b: DocumentIdentifiers
    ) -> Dict[str, Any]:
        doi_a = doc_a.normalized_doi()
        doi_b = doc_b.normalized_doi()
        nct_a = doc_a.normalized_nct()
        nct_b = doc_b.normalized_nct()
        pmid_a = doc_a.normalized_pmid()
        pmid_b = doc_b.normalized_pmid()

        divergences: List[str] = []

        # Regra crítica: mesmo DOI com NCTs diferentes
        if doi_a and doi_b and doi_a == doi_b:
            if nct_a and nct_b and nct_a != nct_b:
                divergences.append(
                    f"Mesmo DOI ({doi_a}) com registros NCT conflitantes: '{nct_a}' vs '{nct_b}'"
                )

        # Mesmo NCT com DOIs diferentes (pode ser artigo de protocolo vs artigo de resultados - complementar)
        # Mas mesmo PMID com NCTs diferentes é divergência crítica
        if pmid_a and pmid_b and pmid_a == pmid_b:
            if nct_a and nct_b and nct_a != nct_b:
                divergences.append(
                    f"Mesmo PMID ({pmid_a}) com registros NCT conflitantes: '{nct_a}' vs '{nct_b}'"
                )

        if divergences:
            return {
                "status": LinkStatus.DIVERGENT,
                "auto_merge_allowed": False,
                "requires_human_review": True,
                "divergences": divergences,
                "reason": "Conflito irreconciliável de identificadores primários (REQ-IDN-001).",
            }

        # Verificar concordância
        has_shared_nct = bool(nct_a and nct_b and nct_a == nct_b)
        has_shared_doi = bool(doi_a and doi_b and doi_a == doi_b)
        has_shared_pmid = bool(pmid_a and pmid_b and pmid_a == pmid_b)

        if has_shared_nct or has_shared_doi or has_shared_pmid:
            return {
                "status": LinkStatus.AUTO_LINKED,
                "auto_merge_allowed": True,
                "requires_human_review": False,
                "shared_identifiers": {
                    "doi": doi_a if has_shared_doi else None,
                    "nct": nct_a if has_shared_nct else None,
                    "pmid": pmid_a if has_shared_pmid else None,
                },
                "divergences": [],
            }

        return {
            "status": LinkStatus.PENDING_HUMAN_CONFIRMATION,
            "auto_merge_allowed": False,
            "requires_human_review": True,
            "divergences": [],
            "reason": "Nenhum identificador primário compartilhado com certeza suficiente.",
        }


@dataclass
class LinkAuditRecord:
    timestamp: str
    action: str  # "LINK", "CONFIRM", "UNLINK"
    study_id: str
    doc_id: str
    actor: str
    confidence: float
    previous_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class DocumentStudyLinkManager:
    """Gerencia vinculação de documentos a estudos com limiares e reversão auditada (REQ-IDN-002).

    - Confiança abaixo do threshold (default: 0.85) exige confirmação humana.
    - Suporta 'undo_link' / 'unlink', restaurando o estado anterior do documento de forma auditada.
    """

    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold
        # doc_id -> study_id
        self.links: Dict[str, str] = {}
        # doc_id -> LinkStatus
        self.statuses: Dict[str, LinkStatus] = {}
        # Trilha auditada de operações
        self.audit_log: List[LinkAuditRecord] = []

    def link_document(
        self,
        doc_id: str,
        study_id: str,
        confidence: float,
        actor: str = "system",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        prev_study = self.links.get(doc_id)
        prev_status = self.statuses.get(doc_id)
        prev_state = {"study_id": prev_study, "status": prev_status.value if prev_status else None}

        if confidence >= self.confidence_threshold:
            status = LinkStatus.AUTO_LINKED
            self.links[doc_id] = study_id
            self.statuses[doc_id] = status
            action = "AUTO_LINK"
        else:
            status = LinkStatus.PENDING_HUMAN_CONFIRMATION
            self.statuses[doc_id] = status
            action = "PROPOSE_LINK_PENDING_CONFIRMATION"

        record = LinkAuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            study_id=study_id,
            doc_id=doc_id,
            actor=actor,
            confidence=confidence,
            previous_state=prev_state,
            reason=reason,
        )
        self.audit_log.append(record)

        return {
            "doc_id": doc_id,
            "study_id": study_id if status == LinkStatus.AUTO_LINKED else None,
            "status": status,
            "confidence": confidence,
            "requires_human_confirmation": status == LinkStatus.PENDING_HUMAN_CONFIRMATION,
        }

    def confirm_link(
        self,
        doc_id: str,
        study_id: str,
        reviewer_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        prev_study = self.links.get(doc_id)
        prev_status = self.statuses.get(doc_id)
        prev_state = {"study_id": prev_study, "status": prev_status.value if prev_status else None}

        self.links[doc_id] = study_id
        self.statuses[doc_id] = LinkStatus.HUMAN_CONFIRMED

        record = LinkAuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="CONFIRM_LINK",
            study_id=study_id,
            doc_id=doc_id,
            actor=reviewer_id,
            confidence=1.0,
            previous_state=prev_state,
            reason=notes,
        )
        self.audit_log.append(record)

        return {
            "doc_id": doc_id,
            "study_id": study_id,
            "status": LinkStatus.HUMAN_CONFIRMED,
            "confirmed_by": reviewer_id,
        }

    def undo_link(
        self,
        doc_id: str,
        reviewer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Desfaz o vínculo ativo, restaurando o estado prévio de forma 100% auditada."""
        if doc_id not in self.links and doc_id not in self.statuses:
            raise KeyError(f"Documento '{doc_id}' não possui vínculo registrado.")

        prev_study = self.links.get(doc_id)
        prev_status = self.statuses.get(doc_id)
        prev_state = {"study_id": prev_study, "status": prev_status.value if prev_status else None}

        # Restaura desvinculado
        self.links.pop(doc_id, None)
        self.statuses[doc_id] = LinkStatus.UNLINKED

        record = LinkAuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="UNDO_LINK",
            study_id=prev_study or "NONE",
            doc_id=doc_id,
            actor=reviewer_id,
            confidence=0.0,
            previous_state=prev_state,
            reason=reason,
        )
        self.audit_log.append(record)

        return {
            "doc_id": doc_id,
            "previous_study_id": prev_study,
            "status": LinkStatus.UNLINKED,
            "undone_by": reviewer_id,
            "reason": reason,
        }


@dataclass(frozen=True)
class SubstanceEntity:
    canonical_name: str
    pubchem_cid: Optional[int]
    chembl_id: Optional[str]
    is_combination: bool
    components: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()


class SubstanceNormalizer:
    """Normaliza nomes de substâncias farmacológicas e gerencia combinações (REQ-IDN-003).

    Regras:
    1. Substâncias em monoterapia mapeiam para seus IDs ontológicos (PubChem CID, ChEMBL ID).
    2. Combinações fixas ou terapias combinadas (e.g., 'Artesunato + Amodiaquina') devem ser
       tratadas como entidades distintas, mantendo seus componentes individuais e NÃO
       sendo fundidas à monoterapia de qualquer um dos seus componentes.
    """

    KNOWN_SUBSTANCES: Dict[str, SubstanceEntity] = {
        "artesunate": SubstanceEntity(
            canonical_name="Artesunate",
            pubchem_cid=6917864,
            chembl_id="CHEMBL37072",
            is_combination=False,
            aliases=("artesunato", "artesunic acid"),
        ),
        "amodiaquine": SubstanceEntity(
            canonical_name="Amodiaquine",
            pubchem_cid=2165,
            chembl_id="CHEMBL697",
            is_combination=False,
            aliases=("amodiaquina", "camorquin"),
        ),
        "chloroquine": SubstanceEntity(
            canonical_name="Chloroquine",
            pubchem_cid=2719,
            chembl_id="CHEMBL76",
            is_combination=False,
            aliases=("cloroquina", "aralen"),
        ),
        "ivermectin": SubstanceEntity(
            canonical_name="Ivermectin",
            pubchem_cid=6321424,
            chembl_id="CHEMBL4594396",
            is_combination=False,
            aliases=("ivermectina", "stromectol"),
        ),
        "balapiravir": SubstanceEntity(
            canonical_name="Balapiravir",
            pubchem_cid=11314340,
            chembl_id="CHEMBL465538",
            is_combination=False,
            aliases=("rg1626", "r1626"),
        ),
        "celgosivir": SubstanceEntity(
            canonical_name="Celgosivir",
            pubchem_cid=9808933,
            chembl_id="CHEMBL483254",
            is_combination=False,
            aliases=("mxl-001", "castanospermine prodrug"),
        ),
        "prednisolone": SubstanceEntity(
            canonical_name="Prednisolone",
            pubchem_cid=5755,
            chembl_id="CHEMBL131",
            is_combination=False,
            aliases=("prednisolona", "deltacortril"),
        ),
        "lovastatin": SubstanceEntity(
            canonical_name="Lovastatin",
            pubchem_cid=53232,
            chembl_id="CHEMBL503",
            is_combination=False,
            aliases=("lovastatina", "mevinolin"),
        ),
    }

    def __init__(self) -> None:
        # Mapeamento reverso de aliases minúsculos para canonical_name
        self.alias_lookup: Dict[str, str] = {}
        for key, entity in self.KNOWN_SUBSTANCES.items():
            self.alias_lookup[key.lower()] = entity.canonical_name
            self.alias_lookup[entity.canonical_name.lower()] = entity.canonical_name
            for alias in entity.aliases:
                self.alias_lookup[alias.lower()] = entity.canonical_name

    def normalize(self, term: str) -> SubstanceEntity:
        raw = term.strip()
        lower = raw.lower()

        # Detecção de combinações explícitas (e.g. ' + ', ' / ', ' and ', ' e ')
        delimiters = [r"\s+\+\s+", r"\s+/\s+", r"\s+and\s+", r"\s+e\s+", r"\s*,\s*"]
        pattern = "|".join(delimiters)
        parts = [p.strip() for p in re.split(pattern, lower, flags=re.IGNORECASE) if p.strip()]

        if len(parts) > 1:
            canonical_components = []
            for part in parts:
                canon = self.alias_lookup.get(part, part.capitalize())
                canonical_components.append(canon)

            canonical_name = " + ".join(sorted(canonical_components))
            return SubstanceEntity(
                canonical_name=canonical_name,
                pubchem_cid=None,  # Combinação não possui um único CID monoterapêutico padrão
                chembl_id=None,
                is_combination=True,
                components=tuple(sorted(canonical_components)),
                aliases=(raw,),
            )

        # Monoterapia
        if lower in self.alias_lookup:
            canon = self.alias_lookup[lower]
            for ent in self.KNOWN_SUBSTANCES.values():
                if ent.canonical_name == canon:
                    return ent

        # Desconhecida / fallback
        return SubstanceEntity(
            canonical_name=raw.capitalize(),
            pubchem_cid=None,
            chembl_id=None,
            is_combination=False,
            components=(raw.capitalize(),),
            aliases=(raw,),
        )


@dataclass
class StudyDocumentReport:
    doc_id: str
    doc_type: str  # "trial_registry", "primary_publication", "follow_up", "secondary_analysis"
    n_enrolled: Optional[int] = None
    n_completed: Optional[int] = None
    published_year: Optional[int] = None


class StudyParticipantAggregator:
    """Agrupa múltiplos documentos sob o mesmo study_id e deduplica participantes (REQ-IDN-004).

    Garante que registros de ensaios, publicações primárias e artigos de seguimento
    do mesmo estudo clínico não dupliquem a contagem amostral de participantes (N total).
    """

    def __init__(self) -> None:
        # study_id -> list of StudyDocumentReport
        self.studies: Dict[str, List[StudyDocumentReport]] = {}

    def add_document(self, study_id: str, report: StudyDocumentReport) -> None:
        if study_id not in self.studies:
            self.studies[study_id] = []
        self.studies[study_id].append(report)

    def aggregate_study_sample_size(self, study_id: str) -> Dict[str, Any]:
        """Calcula o tamanho amostral consolidado do estudo sem dupla contagem."""
        reports = self.studies.get(study_id, [])
        if not reports:
            return {
                "study_id": study_id,
                "n_studies": 0,
                "n_documents": 0,
                "deduplicated_sample_size": 0,
                "documents": [],
                "deduplication_method": "none",
            }

        # Extração de participantes reportados
        enrolled_candidates = [
            r.n_enrolled for r in reports if r.n_enrolled is not None and r.n_enrolled > 0
        ]
        completed_candidates = [
            r.n_completed for r in reports if r.n_completed is not None and r.n_completed > 0
        ]

        # Prioridade para N oficial: registro primário ou artigo principal
        # Se múltiplos relatos diferem levemente (ex: 200 no registro, 198 no artigo final por exclusão pré-randomização),
        # adota o valor máximo do ensaio ou do artigo primário sem NUNCA somá-los (evitando 200 + 198 = 398).
        if enrolled_candidates:
            # Em ensaios clínicos, o tamanho real é max(enrolled) entre relatos do mesmo ensaio,
            # nunca a soma direta.
            deduplicated_n = max(enrolled_candidates)
            method = "primary_or_max_enrolled_across_linked_docs"
        elif completed_candidates:
            deduplicated_n = max(completed_candidates)
            method = "primary_or_max_completed_across_linked_docs"
        else:
            deduplicated_n = 0
            method = "unspecified"

        sum_naive = sum(r.n_enrolled or 0 for r in reports)

        return {
            "study_id": study_id,
            "n_documents": len(reports),
            "naive_sum_sample_size": sum_naive,
            "deduplicated_sample_size": deduplicated_n,
            "inflation_prevented": max(0, sum_naive - deduplicated_n),
            "deduplication_method": method,
            "linked_documents": [
                {
                    "doc_id": r.doc_id,
                    "doc_type": r.doc_type,
                    "n_enrolled": r.n_enrolled,
                    "n_completed": r.n_completed,
                }
                for r in reports
            ],
        }

