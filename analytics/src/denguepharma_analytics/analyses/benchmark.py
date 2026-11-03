"""Módulo de Avaliação e Benchmark da Extração por IA (Eixo D - REQ-ANA-006 e REQ-ANA-007).

Implementa:
- Avaliação determinística frente à referência adjudicada (Gold Standard) por campo e estrato.
- Regras congeladas para sinônimos lexicais e tolerância numérica.
- Segregação de ausências verdadeiras (não entram no denominador do Recall).
- Intervalos de confiança de 95% via Cluster Bootstrap por família de estudo (sem fracionar estudos).
"""
from __future__ import annotations

import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


# Dicionário congelado de sinônimos farmacológicos e metodológicos
SYNONYM_GROUPS: list[set[str]] = [
    {"balapiravir", "r1626", "rg1626", "ro4588161"},
    {"sofosbuvir", "sovaldi", "gilead-sofosbuvir", "gs-7977"},
    {"celgosivir", "mx-3253", "castanospermina-profarmaco"},
    {"ivermectina", "ivermectin", "stromectol"},
    {"cloroquina", "chloroquine", "aralen"},
    {"placebo", "controle_placebo", "salina", "veiculo"},
    {"rct", "rct_paralelo", "randomized_controlled_trial", "ensaio_clinico_randomizado"},
    {"adultos", "adults", "maiores_de_18"},
    {"pediatrica", "children", "criancas"},
    {"tratamento", "treatment", "terapeutica"},
    {"profilaxia", "prophylaxis", "prevencao"},
]

SYNONYM_MAP: dict[str, str] = {}
for group in SYNONYM_GROUPS:
    norm_group = {re.sub(r"[\s_-]+", "_", v.strip().lower()) for v in group}
    canonical = sorted(norm_group)[0]
    for variant in norm_group:
        SYNONYM_MAP[variant] = canonical


def normalize_token(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip().lower()
    text = re.sub(r"[\s_-]+", "_", text)
    return SYNONYM_MAP.get(text, text)


def values_match(val_pred: Any, val_ref: Any, field_name: str = "") -> bool:
    """Verifica correspondência entre predição e referência segundo regras congeladas."""
    if val_pred is None and val_ref is None:
        return True
    if val_pred is None or val_ref is None:
        return False

    norm_pred = normalize_token(val_pred)
    norm_ref = normalize_token(val_ref)

    if norm_pred == norm_ref:
        return True

    # Comparação numérica com tolerância de até 2% para medidas contínuas
    try:
        num_p = float(val_pred)
        num_r = float(val_ref)
        if math.isclose(num_p, num_r, rel_tol=0.02, abs_tol=1e-5):
            return True
    except (ValueError, TypeError):
        pass

    return False


@dataclass(frozen=True)
class FieldEvaluation:
    field_name: str
    stratum: str
    predicted_status: str
    predicted_value: Any
    reference_status: str
    reference_value: Any


def evaluate_field_pair(
    pred_status: str,
    pred_val: Any,
    ref_status: str,
    ref_val: Any,
    field_name: str = "",
) -> tuple[str, bool]:
    """Classifica o par: TP, FP, FN ou TN (ausência correta).
    
    Retorna (categoria, match_bool).
    """
    pred_present = pred_status.upper() == "PRESENTE" and pred_val is not None and str(pred_val).strip() != ""
    ref_present = ref_status.upper() == "PRESENTE" and ref_val is not None and str(ref_val).strip() != ""

    if not pred_present and not ref_present:
        return "TN", (pred_status.upper() == ref_status.upper())

    if pred_present and not ref_present:
        return "FP", False

    if not pred_present and ref_present:
        return "FN", False

    # Ambos presentes
    if values_match(pred_val, ref_val, field_name):
        return "TP", True
    return "FP_MISMATCH", False


def calculate_metrics_summary(pairs: Sequence[FieldEvaluation]) -> dict[str, Any]:
    """Calcula Precisão, Recall, F1 e Acurácia de Ausência (REQ-ANA-006)."""
    tp = 0
    fp = 0
    fn = 0
    tn_correct_absence = 0
    total_absences = 0

    for item in pairs:
        cat, match = evaluate_field_pair(
            item.predicted_status,
            item.predicted_value,
            item.reference_status,
            item.reference_value,
            item.field_name,
        )

        if cat == "TP":
            tp += 1
        elif cat in {"FP", "FP_MISMATCH"}:
            fp += 1
            if cat == "FP_MISMATCH":
                # Também constitui uma falha em extrair o valor de referência correto
                fn += 1
        elif cat == "FN":
            fn += 1
        elif cat == "TN":
            total_absences += 1
            if match:
                tn_correct_absence += 1

    extracted_count = tp + fp
    expected_count = tp + fn

    precision = tp / extracted_count if extracted_count > 0 else 0.0
    recall = tp / expected_count if expected_count > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    absence_acc = (tn_correct_absence / total_absences) if total_absences > 0 else 1.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "correct_absences": tn_correct_absence,
        "total_absences": total_absences,
        "total_evaluations": len(pairs),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "absence_accuracy": round(absence_acc, 4),
    }


def evaluate_benchmark(
    evaluations: Sequence[FieldEvaluation],
) -> dict[str, Any]:
    """Avaliação completa com estratificação por campo e estrato (REQ-ANA-006)."""
    overall = calculate_metrics_summary(evaluations)

    # Por campo
    by_field: dict[str, list[FieldEvaluation]] = defaultdict(list)
    for ev in evaluations:
        by_field[ev.field_name].append(ev)
    field_metrics = {f: calculate_metrics_summary(evs) for f, evs in sorted(by_field.items())}

    # Por estrato
    by_stratum: dict[str, list[FieldEvaluation]] = defaultdict(list)
    for ev in evaluations:
        by_stratum[ev.stratum].append(ev)
    stratum_metrics = {s: calculate_metrics_summary(evs) for s, evs in sorted(by_stratum.items())}

    return {
        "overall": overall,
        "by_field": field_metrics,
        "by_stratum": stratum_metrics,
    }


def cluster_bootstrap_ci(
    study_clusters: Mapping[str, Sequence[FieldEvaluation]],
    num_replications: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = 42,
) -> dict[str, dict[str, float]]:
    """Calcula intervalos de confiança de 95% por reamostragem em cluster por família de estudo (REQ-ANA-007).
    
    Regra mandatória: os registros pertencentes a um mesmo study_id são sorteados em bloco,
    preservando intacta a correlação intra-estudo.
    """
    cluster_ids = list(study_clusters.keys())
    k_clusters = len(cluster_ids)
    if k_clusters < 2:
        raise ValueError("Cluster bootstrap requer pelo menos 2 famílias de estudo distintas")

    rng = random.Random(seed)

    boot_precisions: list[float] = []
    boot_recalls: list[float] = []
    boot_f1s: list[float] = []

    for _ in range(num_replications):
        sampled_clusters = rng.choices(cluster_ids, k=k_clusters)
        resampled_pairs: list[FieldEvaluation] = []
        for sid in sampled_clusters:
            resampled_pairs.extend(study_clusters[sid])

        m = calculate_metrics_summary(resampled_pairs)
        boot_precisions.append(m["precision"])
        boot_recalls.append(m["recall"])
        boot_f1s.append(m["f1"])

    boot_precisions.sort()
    boot_recalls.sort()
    boot_f1s.sort()

    alpha = 1.0 - confidence_level
    low_idx = int(math.floor(alpha / 2.0 * num_replications))
    high_idx = int(math.ceil((1.0 - alpha / 2.0) * num_replications)) - 1
    low_idx = max(0, min(low_idx, num_replications - 1))
    high_idx = max(0, min(high_idx, num_replications - 1))

    return {
        "precision": {
            "lower": round(boot_precisions[low_idx], 4),
            "upper": round(boot_precisions[high_idx], 4),
            "mean": round(sum(boot_precisions) / num_replications, 4),
        },
        "recall": {
            "lower": round(boot_recalls[low_idx], 4),
            "upper": round(boot_recalls[high_idx], 4),
            "mean": round(sum(boot_recalls) / num_replications, 4),
        },
        "f1": {
            "lower": round(boot_f1s[low_idx], 4),
            "upper": round(boot_f1s[high_idx], 4),
            "mean": round(sum(boot_f1s) / num_replications, 4),
        },
    }
