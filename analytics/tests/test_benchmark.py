"""Testes de validação da extração por IA: Precisão, Recall, F1 e Cluster Bootstrap (REQ-ANA-006 e REQ-ANA-007)."""
import pytest
from denguepharma_analytics.analyses.benchmark import (
    FieldEvaluation,
    cluster_bootstrap_ci,
    evaluate_benchmark,
    calculate_metrics_summary,
    values_match,
)


@pytest.mark.requirement("REQ-ANA-006")
def test_benchmark_metrics_calculation_and_absence_segregation():
    # Conjunto de teste representativo com:
    # 2 True Positives (1 com sinônimo 'R1626' -> 'Balapiravir')
    # 1 False Positive
    # 1 False Negative
    # 2 True Negatives (ausências corretas)
    evaluations = [
        FieldEvaluation("intervention", "RCT", "PRESENTE", "Balapiravir", "PRESENTE", "R1626"), # TP (sinônimo)
        FieldEvaluation("sample_size", "RCT", "PRESENTE", "100", "PRESENTE", "100"),             # TP (numérico exato)
        FieldEvaluation("severity", "RCT", "PRESENTE", "GRAVE", "PRESENTE", "NAO_GRAVE"),        # FP/FN (mismatch)
        FieldEvaluation("comparator", "RCT", "NAO_INFORMADO", None, "PRESENTE", "Placebo"),     # FN
        FieldEvaluation("adverse_events", "RCT", "NAO_INFORMADO", None, "NAO_INFORMADO", None), # TN (ausência correta)
        FieldEvaluation("limitations", "RCT", "NAO_APLICAVEL", None, "NAO_APLICAVEL", None),    # TN (ausência correta)
    ]

    res = calculate_metrics_summary(evaluations)

    # TP = 2 (Balapiravir, sample_size)
    # FP = 1 (severity com valor incorreto)
    # FN = 2 (severity mismatch + comparator não extraído)
    # TN = 2 (adverse_events, limitations)
    assert res["true_positives"] == 2
    assert res["false_positives"] == 1
    assert res["false_negatives"] == 2
    assert res["correct_absences"] == 2
    assert res["total_absences"] == 2

    # Precisão: TP / (TP + FP) = 2 / 3 ~= 0.6667
    assert res["precision"] == 0.6667

    # Recall: TP / (TP + FN) = 2 / 4 = 0.5000 (Note: os 2 TN não entram no denominador do Recall!)
    assert res["recall"] == 0.5000

    # F1: 2 * (0.6667 * 0.5000) / (0.6667 + 0.5000) = 0.6667 / 1.1667 ~= 0.5714
    assert res["f1"] == 0.5714

    # Acurácia de ausência correta: 2 / 2 = 1.0 (100%)
    assert res["absence_accuracy"] == 1.0


@pytest.mark.requirement("REQ-ANA-006")
def test_synonym_and_numeric_tolerance_rules():
    # Sinônimos farmacológicos
    assert values_match("Balapiravir", "R1626") is True
    assert values_match("Sofosbuvir", "Sovaldi") is True
    assert values_match("Celgosivir", "MX-3253") is True
    assert values_match("Placebo", "Controle_Placebo") is True

    # Tolerância numérica de 2%
    assert values_match("100", "101") is True  # 1% de diferença
    assert values_match("100", "105") is False # 5% de diferença


@pytest.mark.requirement("REQ-ANA-006")
def test_evaluate_benchmark_stratification():
    evals = [
        FieldEvaluation("intervention", "RCT", "PRESENTE", "Balapiravir", "PRESENTE", "Balapiravir"),
        FieldEvaluation("intervention", "OBSERVACIONAL", "PRESENTE", "Ivermectina", "PRESENTE", "Ivermectina"),
        FieldEvaluation("sample_size", "RCT", "PRESENTE", "50", "PRESENTE", "50"),
    ]

    report = evaluate_benchmark(evals)

    assert "overall" in report
    assert "by_field" in report
    assert "by_stratum" in report

    assert "intervention" in report["by_field"]
    assert "sample_size" in report["by_field"]
    assert "RCT" in report["by_stratum"]
    assert "OBSERVACIONAL" in report["by_stratum"]
    assert report["by_stratum"]["RCT"]["true_positives"] == 2
    assert report["by_stratum"]["OBSERVACIONAL"]["true_positives"] == 1


@pytest.mark.requirement("REQ-ANA-007")
def test_cluster_bootstrap_10_studies_1000_replicates():
    # 10 famílias de estudo com 3 registros cada (conforme cenário ACC-ANA-007)
    study_clusters = {}
    for i in range(1, 11):
        sid = f"study-{i}"
        study_clusters[sid] = [
            FieldEvaluation("intervention", "RCT", "PRESENTE", "Balapiravir", "PRESENTE", "Balapiravir"),
            FieldEvaluation("comparator", "RCT", "PRESENTE", "Placebo", "PRESENTE", "Placebo"),
            FieldEvaluation("sample_size", "RCT", "PRESENTE", str(50 + i * 5), "PRESENTE", str(50 + i * 5) if i <= 8 else "999"), # 2 com mismatch
        ]

    ci = cluster_bootstrap_ci(study_clusters, num_replications=1000, confidence_level=0.95, seed=123)

    for metric in ["precision", "recall", "f1"]:
        assert metric in ci
        assert "lower" in ci[metric]
        assert "upper" in ci[metric]
        assert "mean" in ci[metric]
        assert ci[metric]["lower"] <= ci[metric]["mean"] <= ci[metric]["upper"]
        assert 0.0 <= ci[metric]["lower"] <= 1.0
        assert 0.0 <= ci[metric]["upper"] <= 1.0

