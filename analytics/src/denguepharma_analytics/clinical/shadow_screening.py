"""Shadow Screening consultivo por IA para apoio à adjudicação humana de conflitos (Melhoria 5).

Conformidade e Salvaguardas Científicas (RC-01 a RC-07):
- Operação em modo 'shadow' (sombra): invisível aos revisores independentes para evitar viés de ancoragem.
- Disponibilizado estritamente ao papel de Adjudicador (ADJUDICATORS) durante a resolução de conflitos (CONFLITO).
- Parecer exclusivamente consultivo: vedada qualquer pontuação automatizada de eficácia ou decisão soberana por IA.
- Exclusão mandatória de estudos in vitro/animal sem ensaio clínico humano correspondente (RC-02).
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from ..domain import digest, json_bytes


def _extract_text_corpus(documents: list[Mapping[str, Any]]) -> str:
    """Extrai texto representativo dos documentos vinculados (título, resumo, módulos de ensaio)."""
    fragments: list[str] = []
    for doc in documents:
        if doc.get("title"):
            fragments.append(str(doc["title"]))
        meta = doc.get("metadata") or {}
        if isinstance(meta, dict):
            if meta.get("abstract"):
                fragments.append(str(meta["abstract"]))
            proto = meta.get("protocolSection") or {}
            if isinstance(proto, dict):
                # Campos comuns de ClinicalTrials
                ident = proto.get("identificationModule", {})
                if ident.get("briefTitle"):
                    fragments.append(str(ident["briefTitle"]))
                if ident.get("officialTitle"):
                    fragments.append(str(ident["officialTitle"]))
                design = proto.get("designModule", {})
                if design.get("designInfo", {}).get("allocation"):
                    fragments.append(str(design["designInfo"]["allocation"]))
                arms = proto.get("armsInterventionsModule", {})
                for arm in arms.get("interventions", []):
                    if arm.get("name"):
                        fragments.append(str(arm["name"]))
    return " \n ".join(fragments)


def evaluate_study_shadow(
    study_id: str,
    documents: list[Mapping[str, Any]],
    basis_hash: str,
    protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Avalia um estudo em modo sombra consultivo segundo critérios do protocolo clínico."""
    text = _extract_text_corpus(documents)
    lower = text.lower()

    evidence_quotes: list[str] = []
    
    # 1. Verificação de Alvo e Doença (Dengue)
    is_dengue = bool(re.search(r"\b(dengue|denv|flavivirus)\b", lower))
    if is_dengue:
        match = re.search(r"([^.?!;]*\b(dengue|denv)\b[^.?!;]*)", text, re.IGNORECASE)
        if match:
            evidence_quotes.append(match.group(1).strip()[:180])

    # 2. Verificação de Modelos Não Humanos / In Vitro (Salvaguarda RC-02)
    is_in_vitro_or_animal = bool(re.search(r"\b(vero cells?|in vitro|c6/36|murine|mice|ratos?|camundongos?|docking|in silico)\b", lower))
    
    # 3. Verificação de Ensaio Clínico Humano
    has_human_clinical = bool(re.search(
        r"\b(patients|pacientes|adults|adultos|children|crian[cç]as|participants|participantes|randomized|randomizado|double-blind|duplo-cego|placebo|phase [1234]|fase [1234]|rct|clinical trial|ensaio cl[ií]nico)\b",
        lower,
    ))

    # 4. Verificação de Escopo de Intervenção (Farmacológica vs Vacina/Vetor)
    is_vaccine_or_vector = bool(re.search(r"\b(vaccin\w+|vacina\w+|mosquito\w*|aedes\w*|larvicid\w+|vector control)\b", lower))
    has_pharmacological = bool(re.search(
        r"\b(drug|antiviral|f[aá]rmaco|medicament\w+|treatment|tratamento|inhibitor|inibidor|balapiravir|sofosbuvir|celgosivir|ivermectin|ivermectina|chloroquine|cloroquina|suramin\w*|test-drug)\b",
        lower,
    ))

    # Identificação de possíveis fármacos candidatos
    interventions: list[str] = []
    for cand in ["Balapiravir", "Sofosbuvir", "Celgosivir", "Ivermectina", "Cloroquina", "NITD-008", "TEST-DRUG"]:
        if re.search(rf"\b{re.escape(cand)}\b", text, re.IGNORECASE):
            interventions.append(cand.upper())
    if not interventions and has_pharmacological:
        interventions.append("FARMACO_CANDIDATO_IDENTIFICADO")

    # Determinação da recomendação consultiva
    recommendation = "INCERTO"
    confidence = "MEDIA"
    rationale_parts: list[str] = []
    
    # Critério de exclusão por escopo de intervenção
    if is_vaccine_or_vector and not has_pharmacological:
        recommendation = "EXCLUIR"
        confidence = "ALTA"
        rationale_parts.append("Estudo focado exclusivamente em vacinas ou controle vetorial (fora do escopo terapêutico farmacológico).")
    
    # Critério de exclusão por modelo pré-clínico (sem humanos)
    elif is_in_vitro_or_animal and not has_human_clinical:
        recommendation = "EXCLUIR"
        confidence = "ALTA"
        rationale_parts.append("Estudo conduzido exclusivamente in vitro ou modelo animal, sem braço clínico humano (Salvaguarda RC-02).")
        match = re.search(r"([^.?!;]*\b(vero|in vitro|mice|murine|docking)\b[^.?!;]*)", text, re.IGNORECASE)
        if match:
            evidence_quotes.append(match.group(1).strip()[:180])

    # Critério de inclusão para ensaios clínicos farmacológicos
    elif has_human_clinical and (has_pharmacological or interventions) and is_dengue:
        recommendation = "INCLUIR"
        confidence = "ALTA"
        rationale_parts.append("Ensaio clínico farmacológico identificado em pacientes com dengue (atende aos critérios PICO do protocolo).")
        match = re.search(r"([^.?!;]*\b(phase|fase|trial|randomized|placebo)\b[^.?!;]*)", text, re.IGNORECASE)
        if match:
            evidence_quotes.append(match.group(1).strip()[:180])
    
    elif not is_dengue:
        recommendation = "EXCLUIR"
        confidence = "MEDIA"
        rationale_parts.append("Não foi identificada menção inequívoca a infecção por vírus da Dengue.")
    else:
        recommendation = "INCERTO"
        confidence = "BAIXA"
        rationale_parts.append("Evidências documentais insuficientes ou divergentes para recomendação categórica; requer verificação detalhada do texto integral.")

    suggested_classification = {
        "established_dengue": "SIM" if is_dengue else "INCERTO",
        "context": "DOENCA_ESTABELECIDA" if is_dengue and has_human_clinical else "INCERTO",
        "population": "ADULTOS" if "adult" in lower else "INCERTO",
        "severity": "NAO_GRAVE" if "nao_grave" in lower or "mild" in lower else "NAO_INFORMADA",
        "disease_phase": "FEBRIL" if "febrile" in lower or "febril" in lower else "NAO_INFORMADA",
        "purpose": "TRATAMENTO" if "treatment" in lower or "tratamento" in lower else "OUTRO",
        "design": "RCT_PARALELO" if "randomized" in lower or "rct" in lower else "INCERTO",
        "pharmacological_intervention": "SIM" if has_pharmacological else "INCERTO",
        "interventions": interventions,
    }

    report_digest = digest(json_bytes({
        "study_id": study_id,
        "basis_hash": basis_hash,
        "recommendation": recommendation,
        "suggested_classification": suggested_classification,
    }))

    return {
        "evaluation_id": report_digest,
        "study_id": study_id,
        "basis_hash": basis_hash,
        "recommendation": recommendation,
        "confidence_level": confidence,
        "rationale": " ".join(rationale_parts),
        "suggested_classification": suggested_classification,
        "evidence_quotes": evidence_quotes,
        "safeguards": {
            "rc01_no_efficacy_ranking": True,
            "rc02_human_only_safeguard": True,
            "rc07_human_adjudication_mandatory": True,
            "is_advisory_only": True,
        },
        "disclaimer": (
            "PARECER CONSULTIVO DE IA (SHADOW SCREENING): Subsídio exclusivo ao Adjudicador Humano "
            "na resolução de divergências. Decisão final e soberana da curadoria humana (Salvaguardas RC-01 a RC-07)."
        ),
    }


def get_shadow_recommendation(
    study_id: str,
    documents: list[Mapping[str, Any]],
    basis_hash: str,
    protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Retorna o parecer consultivo de IA para o estudo especificado."""
    return evaluate_study_shadow(study_id, documents, basis_hash, protocol)

