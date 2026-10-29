"""Efeitos por estudo. Sem combinacao, continuidade automatica ou classificacao clinica."""
from __future__ import annotations
import math
from statistics import NormalDist
from scipy.stats import t as student_t


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value): raise ValueError("INVALID_NUMBER:"+name)
    return float(value)


def denominator(arm):
    n = arm.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1: raise ValueError("INVALID_DENOMINATOR")
    if arm.get("n_randomized") is not None:
        randomized = arm["n_randomized"]
        if isinstance(randomized, bool) or not isinstance(randomized, int) or randomized < n: raise ValueError("ANALYZED_EXCEEDS_RANDOMIZED")
    return n


def estimate(result):
    kind = result["effect_type"]
    if kind == "REPORTED":
        reported = result.get("reported") or {}
        point = reported.get("estimate")
        if point is None: return {"measure": reported.get("measure"), "estimate": None, "ci_low": None, "ci_high": None, "confidence_level": None, "method": "REPORTED", "state": "NAO_INFORMADO", "note": "Estimativa nao informada; nao inferida."}
        point = number(point, "estimate")
        lo, hi = reported.get("ci_low"), reported.get("ci_high")
        if (lo is None) != (hi is None): raise ValueError("INCOMPLETE_CONFIDENCE_INTERVAL")
        level = reported.get("confidence_level")
        if lo is not None:
            lo, hi = number(lo, "ci_low"), number(hi, "ci_high")
            if not lo <= point <= hi: raise ValueError("INVALID_CONFIDENCE_INTERVAL")
            if level is None or not 0 < number(level, "confidence_level") < 1: raise ValueError("CONFIDENCE_LEVEL_REQUIRED")
        measure = reported.get("measure")
        if measure not in {"RR", "OR", "HR", "MD"}: raise ValueError("UNSUPPORTED_REPORTED_MEASURE")
        if measure in {"RR", "OR", "HR"} and (point <= 0 or (lo is not None and lo <= 0)): raise ValueError("INVALID_RATIO")
        return {"measure": measure, "estimate": point, "ci_low": lo, "ci_high": hi, "confidence_level": level if lo is not None else None, "method": "REPORTED", "state": "PRESENTE", "note": "Estimativa publicada; nao recalculada."}
    if result.get("design") != "RCT_PARALELO" or not result.get("independent_arms"): raise ValueError("INDEPENDENT_RANDOMIZED_PARALLEL_ARMS_REQUIRED")
    a, b = result["treatment"], result["control"]
    n1, n0 = denominator(a), denominator(b)
    if a.get("arm_id") == b.get("arm_id"): raise ValueError("SAME_ARM_COMPARISON")
    if kind == "RR":
        for arm, n in ((a, n1), (b, n0)):
            events = arm.get("events")
            if isinstance(events, bool) or not isinstance(events, int) or not 0 <= events <= n: raise ValueError("INVALID_EVENT_COUNT")
        x1, x0 = a["events"], b["events"]
        if x1 == 0 or x0 == 0 or (x1 == n1 and x0 == n0):
            return {"measure": "RR", "estimate": None, "ci_low": None, "ci_high": None, "confidence_level": .95, "method": "RR_LOG_WALD", "state": "NAO_ESTIMAVEL", "note": "Celula zero ou fronteira degenerada; sem correcao automatica de continuidade."}
        point = (x1/n1)/(x0/n0); se = math.sqrt(1/x1 - 1/n1 + 1/x0 - 1/n0); z = NormalDist().inv_cdf(.975)
        return {"measure": "RR", "estimate": point, "ci_low": math.exp(math.log(point)-z*se), "ci_high": math.exp(math.log(point)+z*se), "confidence_level": .95, "method": "RR_LOG_WALD", "state": "PRESENTE", "note": "Aproximacao log-normal; interpretar com cautela em eventos raros."}
    if kind == "MD":
        if min(n1, n0) < 2: raise ValueError("CONTINUOUS_N_AT_LEAST_TWO")
        mean1, mean0 = number(a.get("mean"), "mean"), number(b.get("mean"), "mean")
        sd1, sd0 = number(a.get("sd"), "sd"), number(b.get("sd"), "sd")
        if min(sd1, sd0) < 0: raise ValueError("NEGATIVE_SD")
        v1, v0 = sd1*sd1/n1, sd0*sd0/n0; se2 = v1+v0; point = mean1-mean0
        if se2 == 0: return {"measure": "MD", "estimate": point, "ci_low": None, "ci_high": None, "confidence_level": .95, "method": "MD_WELCH", "state": "IC_NAO_ESTIMAVEL", "note": "Variancia nula; nao apresentar intervalo artificial."}
        df = se2*se2/(v1*v1/(n1-1)+v0*v0/(n0-1)); margin = float(student_t.ppf(.975, df))*math.sqrt(se2)
        return {"measure": "MD", "estimate": point, "ci_low": point-margin, "ci_high": point+margin, "confidence_level": .95, "method": "MD_WELCH", "state": "PRESENTE", "note": "Diferenca de medias; nao converter mediana em media."}
    raise ValueError("UNSUPPORTED_EFFECT_TYPE")
