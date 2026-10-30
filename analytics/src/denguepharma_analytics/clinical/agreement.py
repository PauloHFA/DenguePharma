"""Concordância inter-avaliadores na triagem duplo-cega (Etapa 0.22.0).

Calcula métricas de concordância entre revisores independentes:
- Percentual de concordância observada (P_o).
- Kappa de Cohen (k) com intervalo de confiança assintótico.
- Coeficiente AC1 de Gwet (robusto ao paradoxo de alta concordância e alta prevalência).
- Matriz de confusão / contingência detalhada por decisão (INCLUIR, EXCLUIR, INCERTO).
- Rastreabilidade estrita: não inventa votos, não decide conflitos e preserva ausências.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any


def cohen_kappa(contingency: dict[str, dict[str, int]], categories: list[str]) -> dict[str, float | None]:
    """Calcula o Kappa de Cohen a partir da matriz de contingência quadrada.

    k = (P_o - P_e) / (1 - P_e)
    """
    total = sum(contingency[r][c] for r in categories for c in categories)
    if total == 0:
        return {"observed_agreement": None, "expected_agreement": None, "kappa": None, "se_kappa": None}

    # P_o: concordância observada (soma da diagonal / total)
    po = sum(contingency[cat][cat] for cat in categories) / total

    # P_e: concordância esperada pelo acaso
    pe = 0.0
    row_totals = {r: sum(contingency[r][c] for c in categories) for r in categories}
    col_totals = {c: sum(contingency[r][c] for r in categories) for c in categories}

    for cat in categories:
        p_row = row_totals[cat] / total
        p_col = col_totals[cat] / total
        pe += p_row * p_col

    if math.isclose(pe, 1.0):
        # Se P_e for 1.0 (todos na mesma categoria), concordância perfeita esperada
        kappa = 1.0 if math.isclose(po, 1.0) else 0.0
        se_kappa = 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)
        # Erro padrão aproximado de Cohen (1960)
        try:
            var_kappa = (po * (1.0 - po)) / (total * ((1.0 - pe) ** 2))
            se_kappa = math.sqrt(max(0.0, var_kappa))
        except (ZeroDivisionError, ValueError):
            se_kappa = None

    return {
        "observed_agreement": round(po, 4),
        "expected_agreement": round(pe, 4),
        "kappa": round(kappa, 4),
        "se_kappa": round(se_kappa, 4) if se_kappa is not None else None,
    }


def gwet_ac1(contingency: dict[str, dict[str, int]], categories: list[str]) -> dict[str, float | None]:
    """Calcula o coeficiente AC1 de Gwet (2008), imune ao paradoxo de prevalência de Feinstein-Cicchetti.

    AC1 = (P_o - P_e_gwet) / (1 - P_e_gwet)
    onde P_e_gwet = 2 * sum(pi_k * (1 - pi_k)) / (q * (q - 1)) ou formula de Gwet para 2 avaliadores:
    pi_k = (row_k + col_k) / (2 * N)
    P_e_gwet = 1 / (q - 1) * sum(pi_k * (1 - pi_k))
    """
    q = len(categories)
    if q < 2:
        return {"ac1": None, "pe_gwet": None}

    total = sum(contingency[r][c] for r in categories for c in categories)
    if total == 0:
        return {"ac1": None, "pe_gwet": None}

    po = sum(contingency[cat][cat] for cat in categories) / total

    row_totals = {r: sum(contingency[r][c] for c in categories) for r in categories}
    col_totals = {c: sum(contingency[r][c] for r in categories) for c in categories}

    sum_pi = 0.0
    for cat in categories:
        pi_k = (row_totals[cat] + col_totals[cat]) / (2.0 * total)
        sum_pi += pi_k * (1.0 - pi_k)

    pe_gwet = (1.0 / (q - 1.0)) * sum_pi

    if math.isclose(pe_gwet, 1.0):
        ac1 = 1.0 if math.isclose(po, 1.0) else 0.0
    else:
        ac1 = (po - pe_gwet) / (1.0 - pe_gwet)

    return {
        "ac1": round(ac1, 4),
        "pe_gwet": round(pe_gwet, 4),
    }


def interpret_agreement(score: float | None) -> str:
    """Classificação descritiva qualitativa clássica de Landis & Koch (1977)."""
    if score is None:
        return "INDETERMINADO"
    if score < 0.0:
        return "CONCORDANCIA_INFERIOR_AO_ACASO"
    if score <= 0.20:
        return "LEVE"
    if score <= 0.40:
        return "RAZOAVEL"
    if score <= 0.60:
        return "MODERADA"
    if score <= 0.80:
        return "SUBSTANCIAL"
    return "QUASE_PERFEITA"


def compute_inter_rater_agreement(
    pair_reviews: list[tuple[str, str]],
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Recebe pares de votos independentes (decisao_r1, decisao_r2) e gera o sumário de concordância."""
    default_cats = ["INCLUIR", "EXCLUIR", "INCERTO"]
    cats = categories or default_cats

    # Inicializa matriz quadrada
    matrix: dict[str, dict[str, int]] = {r: {c: 0 for c in cats} for r in cats}

    valid_pairs = 0
    excluded_unpaired = 0

    for d1, d2 in pair_reviews:
        if not d1 or not d2 or d1 not in matrix or d2 not in matrix:
            excluded_unpaired += 1
            continue
        matrix[d1][d2] += 1
        valid_pairs += 1

    if valid_pairs == 0:
        return {
            "total_studies_evaluated": 0,
            "valid_paired_studies": 0,
            "excluded_unpaired": excluded_unpaired,
            "categories": cats,
            "contingency_matrix": matrix,
            "observed_agreement": None,
            "cohen_kappa": None,
            "gwet_ac1": None,
            "interpretation_kappa": "SEM_DADOS_SUFICIENTES",
            "interpretation_ac1": "SEM_DADOS_SUFICIENTES",
            "notice": "Necessários ao menos dois votos pareados para calcular concordância inter-avaliadores.",
        }

    kappa_res = cohen_kappa(matrix, cats)
    gwet_res = gwet_ac1(matrix, cats)

    return {
        "total_studies_evaluated": valid_pairs + excluded_unpaired,
        "valid_paired_studies": valid_pairs,
        "excluded_unpaired": excluded_unpaired,
        "categories": cats,
        "contingency_matrix": matrix,
        "observed_agreement": kappa_res["observed_agreement"],
        "expected_agreement": kappa_res["expected_agreement"],
        "cohen_kappa": kappa_res["kappa"],
        "se_kappa": kappa_res["se_kappa"],
        "gwet_ac1": gwet_res["ac1"],
        "interpretation_kappa": interpret_agreement(kappa_res["kappa"]),
        "interpretation_ac1": interpret_agreement(gwet_res["ac1"]),
        "notice": "Métricas descritivas da triagem duplo-cega. Não resolvem divergências nem substituem a adjudicação humana.",
    }


def evaluate_workspace_agreement(workspace, actor) -> dict[str, Any]:
    """Avalia a concordância dos estudos triados no workspace."""
    from .workspace import REVIEW_ROLES

    actor.require(*REVIEW_ROLES)
    with workspace.transaction() as db:
        events = workspace.events(db)
        catalog = workspace.catalog(events)
        paired_votes: list[tuple[str, str]] = []

        for study in sorted(catalog):
            screening_state = workspace.screening(db, study, events)
            votes = screening_state.get("votes", [])
            if len(votes) >= 2:
                # Ordena por actor_id para reprodutibilidade no par
                sorted_votes = sorted(votes, key=lambda v: v.get("actor_id", ""))
                v1 = sorted_votes[0].get("decision")
                v2 = sorted_votes[1].get("decision")
                if v1 and v2:
                    paired_votes.append((v1, v2))

        return compute_inter_rater_agreement(paired_votes)
