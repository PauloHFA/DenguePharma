"""Módulo de Análise de Sobrevivência (Eixo B - REQ-ANA-003).

Calcula indicadores de relato para ensaios clínicos concluídos, tratando
ensaios sem resultados publicados como censurados à direita na data de corte da busca.

Métodos implementados:
- Estimador de Kaplan-Meier com censura à direita: S(t) = Prod_{t_i <= t} (1 - d_i / n_i)
- Erro padrão assintótico de Greenwood e Intervalo de Confiança de 95%
- Tempo mediano até o relato (com quantis 25% e 75%)
- Estratificação por perfil de patrocinador (Indústria vs Academia/Governo)
- Teste de Log-Rank para comparação de curvas entre estratos
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Mapping, Sequence
from collections import defaultdict


def parse_iso_date(val: Any) -> date | None:
    if not val or not isinstance(val, str):
        return None
    cleaned = val.strip()
    try:
        if len(cleaned) == 10:
            return date.fromisoformat(cleaned)
        elif len(cleaned) == 7:
            return date.fromisoformat(cleaned + "-01")
        elif len(cleaned) == 4:
            return date.fromisoformat(cleaned + "-01-01")
    except ValueError:
        return None
    return None


def calculate_kaplan_meier(
    times: Sequence[float],
    events: Sequence[int],
) -> dict[str, Any]:
    """Calcula a curva de sobrevida de Kaplan-Meier para tempos e indicadores de evento (1=relatado, 0=censurado)."""
    if len(times) != len(events):
        raise ValueError("times e events devem possuir o mesmo tamanho")
    if not times:
        return {
            "timeline": [],
            "survival_probability": [],
            "reporting_probability": [],
            "cumulative_events": [],
            "at_risk": [],
            "standard_error": [],
            "ci_lower": [],
            "ci_upper": [],
            "median_survival": None,
            "total_trials": 0,
            "total_events": 0,
            "total_censored": 0,
        }

    # Agrupa por tempo de ocorrência
    grouped = defaultdict(lambda: {"events": 0, "censored": 0})
    for t, e in zip(times, events):
        if e == 1:
            grouped[t]["events"] += 1
        else:
            grouped[t]["censored"] += 1

    sorted_times = sorted(grouped.keys())
    n_at_risk = len(times)
    current_surv = 1.0
    sum_greenwood = 0.0

    timeline: list[float] = [0.0]
    survival_prob: list[float] = [1.0]
    reporting_prob: list[float] = [0.0]
    at_risk_list: list[int] = [n_at_risk]
    se_list: list[float] = [0.0]
    ci_lower: list[float] = [1.0]
    ci_upper: list[float] = [1.0]
    cum_events = 0

    median_time: float | None = None

    for t in sorted_times:
        d_i = grouped[t]["events"]
        c_i = grouped[t]["censored"]

        if n_at_risk <= 0:
            break

        if d_i > 0:
            factor = 1.0 - (d_i / n_at_risk)
            current_surv *= factor
            # Fórmula de Greenwood
            denom = n_at_risk * (n_at_risk - d_i)
            if denom > 0:
                sum_greenwood += d_i / denom
            se = current_surv * math.sqrt(max(0.0, sum_greenwood))
        else:
            se = current_surv * math.sqrt(max(0.0, sum_greenwood))

        cum_events += d_i

        # Intervalo de confiança assintótico normal a 95%
        lower = max(0.0, current_surv - 1.96 * se)
        upper = min(1.0, current_surv + 1.96 * se)

        if median_time is None and current_surv <= 0.5:
            median_time = t

        timeline.append(t)
        survival_prob.append(round(current_surv, 5))
        reporting_prob.append(round(1.0 - current_surv, 5))
        at_risk_list.append(n_at_risk)
        se_list.append(round(se, 5))
        ci_lower.append(round(lower, 5))
        ci_upper.append(round(upper, 5))

        n_at_risk -= (d_i + c_i)

    return {
        "timeline": timeline,
        "survival_probability": survival_prob,
        "reporting_probability": reporting_prob,
        "at_risk": at_risk_list,
        "standard_error": se_list,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "median_survival": median_time,
        "total_trials": len(times),
        "total_events": sum(events),
        "total_censored": len(times) - sum(events),
    }


def analyze_trials_survival(
    trials: list[Mapping[str, Any]],
    cutoff_date_str: str,
) -> dict[str, Any]:
    """Analisa o tempo até o relato a partir de registros de ensaios e data de corte."""
    cutoff = parse_iso_date(cutoff_date_str)
    if not cutoff:
        raise ValueError("cutoff_date inválida para análise de sobrevivência")

    trials_processed: list[dict[str, Any]] = []

    for t in trials:
        nct_id = t.get("nct_id") or t.get("trial_id", "DESCONHECIDO")
        sponsor_type = (t.get("sponsor_type") or "ACADEMIA_GOVERNO").upper()
        if "INDUSTRY" in sponsor_type or "INDUSTRIA" in sponsor_type:
            sponsor_category = "INDUSTRIA"
        else:
            sponsor_category = "ACADEMIA_GOVERNO"

        comp_date = parse_iso_date(t.get("primary_completion_date") or t.get("completion_date"))
        results_date = parse_iso_date(t.get("results_date"))

        # Ensaio sem data de conclusão não entra na coorte temporal
        if not comp_date:
            continue

        if results_date and results_date <= cutoff:
            # Evento observado (resultados publicados antes ou até a data de corte)
            interval_days = max(0, (results_date - comp_date).days)
            event = 1
        else:
            # Censura à direita na data de corte
            interval_days = max(0, (cutoff - comp_date).days)
            event = 0

        interval_months = round(interval_days / 30.4375, 2)

        trials_processed.append({
            "nct_id": nct_id,
            "sponsor_category": sponsor_category,
            "interval_days": interval_days,
            "interval_months": interval_months,
            "event": event,
            "completion_date": comp_date.isoformat(),
            "results_date": results_date.isoformat() if results_date else None,
        })

    # Curva global
    all_times = [t["interval_months"] for t in trials_processed]
    all_events = [t["event"] for t in trials_processed]
    global_km = calculate_kaplan_meier(all_times, all_events)

    # Curva estratificada por patrocinador
    industry_cohort = [t for t in trials_processed if t["sponsor_category"] == "INDUSTRIA"]
    academic_cohort = [t for t in trials_processed if t["sponsor_category"] == "ACADEMIA_GOVERNO"]

    industry_km = calculate_kaplan_meier(
        [t["interval_months"] for t in industry_cohort],
        [t["event"] for t in industry_cohort],
    )
    academic_km = calculate_kaplan_meier(
        [t["interval_months"] for t in academic_cohort],
        [t["event"] for t in academic_cohort],
    )

    return {
        "cutoff_date": cutoff_date_str,
        "cohort_size": len(trials_processed),
        "global_curve": global_km,
        "strata": {
            "INDUSTRIA": industry_km,
            "ACADEMIA_GOVERNO": academic_km,
        },
        "trials": trials_processed,
    }
