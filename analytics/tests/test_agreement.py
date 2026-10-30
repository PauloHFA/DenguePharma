import pytest

from denguepharma_analytics.clinical.agreement import (
    cohen_kappa,
    gwet_ac1,
    interpret_agreement,
    compute_inter_rater_agreement,
)


def test_cohen_kappa_perfect_agreement():
    # 20 estudos: 10 ambos INCLUIR, 10 ambos EXCLUIR
    matrix = {
        "INCLUIR": {"INCLUIR": 10, "EXCLUIR": 0, "INCERTO": 0},
        "EXCLUIR": {"INCLUIR": 0, "EXCLUIR": 10, "INCERTO": 0},
        "INCERTO": {"INCLUIR": 0, "EXCLUIR": 0, "INCERTO": 0},
    }
    cats = ["INCLUIR", "EXCLUIR", "INCERTO"]
    res = cohen_kappa(matrix, cats)
    assert res["observed_agreement"] == 1.0
    assert res["kappa"] == 1.0
    assert res["expected_agreement"] == 0.5


def test_cohen_kappa_chance_agreement():
    # Concordância exatamente igual ao acaso
    matrix = {
        "INCLUIR": {"INCLUIR": 25, "EXCLUIR": 25, "INCERTO": 0},
        "EXCLUIR": {"INCLUIR": 25, "EXCLUIR": 25, "INCERTO": 0},
        "INCERTO": {"INCLUIR": 0, "EXCLUIR": 0, "INCERTO": 0},
    }
    cats = ["INCLUIR", "EXCLUIR", "INCERTO"]
    res = cohen_kappa(matrix, cats)
    assert res["observed_agreement"] == 0.5
    assert res["expected_agreement"] == 0.5
    assert res["kappa"] == 0.0


def test_gwet_ac1_prevalence_paradox():
    # Paradoxo de alta concordância com alta prevalência de EXCLUIR
    # 90 ambos EXCLUIR, 5 ambos INCLUIR, 3 discordantes (r1=INCLUIR, r2=EXCLUIR), 2 discordantes (r1=EXCLUIR, r2=INCLUIR)
    # Total = 100. P_o = 95/100 = 0.95.
    matrix = {
        "INCLUIR": {"INCLUIR": 5, "EXCLUIR": 3, "INCERTO": 0},
        "EXCLUIR": {"INCLUIR": 2, "EXCLUIR": 90, "INCERTO": 0},
        "INCERTO": {"INCLUIR": 0, "EXCLUIR": 0, "INCERTO": 0},
    }
    cats = ["INCLUIR", "EXCLUIR", "INCERTO"]
    k_res = cohen_kappa(matrix, cats)
    g_res = gwet_ac1(matrix, cats)

    assert k_res["observed_agreement"] == 0.95
    # Kappa sofre penalidade pelo desbalanceamento (P_e alto)
    assert k_res["expected_agreement"] > 0.80
    assert k_res["kappa"] < 0.70

    # AC1 de Gwet é estável frente ao paradoxo de prevalência
    assert g_res["ac1"] > 0.90


def test_compute_inter_rater_agreement_empty_or_unpaired():
    # Sem pares
    res = compute_inter_rater_agreement([])
    assert res["valid_paired_studies"] == 0
    assert res["cohen_kappa"] is None
    assert res["gwet_ac1"] is None
    assert res["interpretation_kappa"] == "SEM_DADOS_SUFICIENTES"

    # Apenas votos com categorias inválidas
    res_invalid = compute_inter_rater_agreement([("INCLUIR", "INVALIDO"), ("OUTRO", "EXCLUIR")])
    assert res_invalid["valid_paired_studies"] == 0
    assert res_invalid["excluded_unpaired"] == 2


def test_compute_inter_rater_agreement_realistic_pilot():
    # 20 estudos com triagem duplo-cega
    votes = [
        ("INCLUIR", "INCLUIR"),
        ("INCLUIR", "INCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("INCERTO", "EXCLUIR"),  # divergência
        ("INCLUIR", "EXCLUIR"),  # divergência
        ("INCERTO", "INCERTO"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
        ("EXCLUIR", "EXCLUIR"),
    ]
    res = compute_inter_rater_agreement(votes)
    assert res["valid_paired_studies"] == 20
    assert res["observed_agreement"] == 18 / 20  # 90%
    assert res["cohen_kappa"] is not None
    assert res["gwet_ac1"] is not None
    assert res["interpretation_kappa"] in {"SUBSTANCIAL", "QUASE_PERFEITA", "MODERADA"}
    assert res["contingency_matrix"]["INCLUIR"]["INCLUIR"] == 2
    assert res["contingency_matrix"]["EXCLUIR"]["EXCLUIR"] == 15
    assert res["contingency_matrix"]["INCERTO"]["INCERTO"] == 1


def test_interpret_agreement():
    assert interpret_agreement(None) == "INDETERMINADO"
    assert interpret_agreement(-0.1) == "CONCORDANCIA_INFERIOR_AO_ACASO"
    assert interpret_agreement(0.15) == "LEVE"
    assert interpret_agreement(0.35) == "RAZOAVEL"
    assert interpret_agreement(0.55) == "MODERADA"
    assert interpret_agreement(0.75) == "SUBSTANCIAL"
    assert interpret_agreement(0.95) == "QUASE_PERFEITA"
