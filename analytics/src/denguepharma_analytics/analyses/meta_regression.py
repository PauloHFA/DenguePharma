"""Meta-regressão por efeitos aleatórios e salvaguardas metodológicas (Eixo A / B).

Atende rigorosamente aos requisitos:
- REQ-ANA-002: Impedir síntese que combine contextos incompatíveis (in silico, in vitro,
  animal e humano; profilaxia, tratamento e sintomático).
- REQ-ANA-009: Impedir produção de ranking de eficácia, pontuação do "melhor fármaco"
  ou atribuição de certeza GRADE automática (Salvaguarda RC-07).
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence
from statistics import NormalDist


VALID_BIOLOGICAL_CONTEXTS = {"HUMANO", "ANIMAL", "IN_VITRO", "IN_SILICO"}
VALID_CLINICAL_PURPOSES = {"TRATAMENTO", "PROFILAXIA", "SINTOMATICO"}


class IncompatibleContextError(ValueError):
    """Exceção levantada quando há tentativa de agregar contextos científicos incompatíveis."""
    pass


class ForbiddenRankingError(ValueError):
    """Exceção levantada quando há tentativa de computar ranking ou melhor fármaco."""
    pass


def validate_compatible_contexts(studies: Sequence[Mapping[str, Any]]) -> None:
    """Valida se todos os estudos pertencem a contextos metodológicos e biológicos compatíveis.

    REQ-ANA-002: Bloqueia agregação de in silico, in vitro, animal e humano, ou
    mistura de profilaxia, tratamento e sintomático.
    """
    if not studies:
        return

    contexts = set()
    purposes = set()

    for idx, s in enumerate(studies):
        ctx = str(s.get("context", s.get("biological_context", ""))).strip().upper()
        if ctx:
            contexts.add(ctx)

        purp = str(s.get("purpose", s.get("clinical_purpose", ""))).strip().upper()
        if purp:
            purposes.add(purp)

    if len(contexts) > 1:
        raise IncompatibleContextError(
            f"Tentativa de agregação de contextos biológicos incompatíveis: {sorted(contexts)}. "
            "A síntese clínica humana não pode ser combinada com modelos pré-clínicos ou in vitro (REQ-ANA-002 / RC-02)."
        )

    if len(purposes) > 1:
        raise IncompatibleContextError(
            f"Tentativa de agregação de finalidades clínicas incompatíveis: {sorted(purposes)}. "
            "Estudos de profilaxia e tratamento não podem ser sintetizados no mesmo modelo agregado (REQ-ANA-002)."
        )


def assert_no_efficacy_ranking(report: Mapping[str, Any]) -> None:
    """Garante que a saída do modelo não contenha campos ou termos de ranking de eficácia.

    REQ-ANA-009 / RC-07: Proíbe terminantemente ranqueamento, melhor fármaco ou GRADE automático.
    """
    forbidden_terms = {
        "ranking", "rank", "melhor_farmaco", "best_drug",
        "score_ranqueamento", "grade_automatica", "hierarquia_farmacos"
    }

    def check_recursive(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lower_k = str(k).lower()
                for term in forbidden_terms:
                    if term in lower_k:
                        raise ForbiddenRankingError(
                            f"Campo proibido detectado no relatório: '{k}' (em {path}). "
                            "O sistema não deve produzir ranking de eficácia nem ordenar 'melhor fármaco' (REQ-ANA-009 / RC-07)."
                        )
                check_recursive(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                check_recursive(item, f"{path}[{i}]")
        elif isinstance(obj, str):
            lower_s = obj.lower()
            if "melhor fármaco" in lower_s or "melhor farmaco" in lower_s or "ranking de eficácia" in lower_s:
                raise ForbiddenRankingError(
                    f"Texto proibido de ranqueamento identificado em {path}: '{obj}'. "
                    "Salvaguarda RC-07: rankings automáticos de intervenções são expressamente vedados."
                )

    check_recursive(report)


def fit_random_effects_meta_regression(
    studies: Sequence[Mapping[str, Any]],
    covariate_name: str,
) -> dict[str, Any]:
    """Ajusta uma meta-regressão de efeitos aleatórios univariada (DerSimonian-Laird).

    Parâmetros:
    - studies: Lista de dicionários contendo ao menos 'effect' (theta_i), 'variance' (v_i),
      e o moderador definido por covariate_name (ex: 'baseline_severity' ou 'treatment_timing').
    - covariate_name: Nome do moderador contínuo ou ordinal.

    Retorna dicionário estruturado com coeficientes, erros padrão, IC 95%, estatística Q e tau^2.
    """
    validate_compatible_contexts(studies)

    if len(studies) < 2:
        raise ValueError("Meta-regressão exige ao menos 2 estudos independentes elegíveis.")

    theta = []
    v = []
    x = []

    for s in studies:
        eff = float(s["effect"])
        var = float(s["variance"])
        cov = float(s[covariate_name])

        if var <= 0:
            raise ValueError(f"Variância do estudo deve ser estritamente positiva, obtido: {var}")

        theta.append(eff)
        v.append(var)
        x.append(cov)

    k = len(theta)

    # 1. Pesos de efeitos fixos iniciais: w_i = 1 / v_i
    w_fe = [1.0 / vi for vi in v]
    sum_w_fe = sum(w_fe)
    pooled_fe = sum(w * t for w, t in zip(w_fe, theta)) / sum_w_fe

    # 2. Estatística Q de Cochrane
    q = sum(w * ((t - pooled_fe) ** 2) for w, t in zip(w_fe, theta))
    df = k - 1

    # 3. Estimador DerSimonian-Laird para tau^2
    sum_w_fe_sq = sum(w ** 2 for w in w_fe)
    denom = sum_w_fe - (sum_w_fe_sq / sum_w_fe)
    tau2 = max(0.0, (q - df) / denom) if denom > 0 else 0.0

    # 4. Pesos de efeitos aleatórios: w_i^* = 1 / (v_i + tau^2)
    w_re = [1.0 / (vi + tau2) for vi in v]

    # 5. Mínimos Quadrados Ponderados (WLS) para [beta_0, beta_1]
    # Matriz X = [1, x_i]
    sum_w = sum(w_re)
    sum_w_x = sum(w * xi for w, xi in zip(w_re, x))
    sum_w_x2 = sum(w * (xi ** 2) for w, xi in zip(w_re, x))
    sum_w_y = sum(w * yi for w, yi in zip(w_re, theta))
    sum_w_xy = sum(w * xi * yi for w, xi, yi in zip(w_re, x, theta))

    det = sum_w * sum_w_x2 - (sum_w_x ** 2)
    if abs(det) < 1e-12:
        # Colinearidade perfeita ou covariável constante
        beta0 = sum_w_y / sum_w
        beta1 = 0.0
        se_beta0 = math.sqrt(1.0 / sum_w)
        se_beta1 = 0.0
    else:
        beta0 = (sum_w_x2 * sum_w_y - sum_w_x * sum_w_xy) / det
        beta1 = (sum_w * sum_w_xy - sum_w_x * sum_w_y) / det
        se_beta0 = math.sqrt(max(0.0, sum_w_x2 / det))
        se_beta1 = math.sqrt(max(0.0, sum_w / det))

    z_crit = NormalDist().inv_cdf(0.975)

    # Heterogeneidade residual I^2
    i2 = max(0.0, (q - df) / q) if q > 0 else 0.0

    result = {
        "model": "RANDOM_EFFECTS_META_REGRESSION",
        "method": "DerSimonian-Laird",
        "k_studies": k,
        "covariate": covariate_name,
        "tau2": round(tau2, 6),
        "i2": round(i2, 4),
        "q_stat": round(q, 4),
        "coefficients": {
            "intercept": {
                "estimate": round(beta0, 4),
                "se": round(se_beta0, 4),
                "ci_95": [round(beta0 - z_crit * se_beta0, 4), round(beta0 + z_crit * se_beta0, 4)],
            },
            covariate_name: {
                "estimate": round(beta1, 4),
                "se": round(se_beta1, 4),
                "ci_95": [round(beta1 - z_crit * se_beta1, 4), round(beta1 + z_crit * se_beta1, 4)],
            },
        },
        "methodological_notice": (
            "Meta-regressão agregada descritiva para exploração de heterogeneidade. "
            "Não estabelece causalidade biológica direta e não gera ranking terapêutico (Salvaguardas RC-01 a RC-07)."
        ),
    }

    assert_no_efficacy_ranking(result)
    return result


def subgroup_meta_analysis(
    studies: Sequence[Mapping[str, Any]],
    subgroup_field: str,
) -> dict[str, Any]:
    """Calcula síntese por subgrupos independentes garantindo compatibilidade contextual."""
    validate_compatible_contexts(studies)

    groups: dict[str, list[dict[str, Any]]] = {}
    for s in studies:
        grp = str(s.get(subgroup_field, "NAO_INFORMADO")).strip()
        groups.setdefault(grp, []).append(dict(s))

    subgroup_results = {}
    z_crit = NormalDist().inv_cdf(0.975)

    for grp_name, grp_studies in groups.items():
        if not grp_studies:
            continue

        theta = [float(s["effect"]) for s in grp_studies]
        v = [float(s["variance"]) for s in grp_studies]
        w = [1.0 / vi for vi in v]
        sum_w = sum(w)
        pooled = sum(wi * ti for wi, ti in zip(w, theta)) / sum_w
        se_pooled = math.sqrt(1.0 / sum_w)

        subgroup_results[grp_name] = {
            "k_studies": len(grp_studies),
            "pooled_effect": round(pooled, 4),
            "se": round(se_pooled, 4),
            "ci_95": [round(pooled - z_crit * se_pooled, 4), round(pooled + z_crit * se_pooled, 4)],
        }

    report = {
        "analysis": "SUBGROUP_META_ANALYSIS",
        "subgroup_field": subgroup_field,
        "subgroups": subgroup_results,
        "notice": "Análise exploratória estratificada. Proibida inferência cruzada entre contextos heterogêneos.",
    }

    assert_no_efficacy_ranking(report)
    return report
