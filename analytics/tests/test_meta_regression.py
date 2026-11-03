"""Testes formais de meta-regressão e salvaguardas contextuais e anti-ranking.

Atende aos requisitos do SDD:
- REQ-ANA-002: Impedir síntese que combine contextos incompatíveis
- REQ-ANA-009: Impedir produção de ranking de eficácia ou melhor fármaco
"""
import pytest
from denguepharma_analytics.analyses.meta_regression import (
    IncompatibleContextError,
    ForbiddenRankingError,
    validate_compatible_contexts,
    assert_no_efficacy_ranking,
    fit_random_effects_meta_regression,
    subgroup_meta_analysis,
)


@pytest.mark.requirement("REQ-ANA-002")
def test_blocks_incompatible_biological_contexts_human_and_in_vitro():
    """REQ-ANA-002: Bloqueia tentativa de agregar contextos incompatíveis (humano e in vitro)."""
    studies = [
        {"study_id": "s1", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": 0.85, "variance": 0.04, "cov": 1.0},
        {"study_id": "s2", "context": "IN_VITRO", "purpose": "TRATAMENTO", "effect": 0.40, "variance": 0.02, "cov": 2.0},
    ]

    with pytest.raises(IncompatibleContextError, match="incompatíveis"):
        validate_compatible_contexts(studies)

    with pytest.raises(IncompatibleContextError, match="incompatíveis"):
        fit_random_effects_meta_regression(studies, "cov")


@pytest.mark.requirement("REQ-ANA-002")
def test_blocks_incompatible_clinical_purposes_prophylaxis_and_treatment():
    """REQ-ANA-002: Bloqueia tentativa de agregar finalidades incompatíveis (profilaxia e tratamento)."""
    studies = [
        {"study_id": "s1", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": 0.85, "variance": 0.04, "cov": 1.0},
        {"study_id": "s2", "context": "HUMANO", "purpose": "PROFILAXIA", "effect": 0.90, "variance": 0.05, "cov": 1.5},
    ]

    with pytest.raises(IncompatibleContextError, match="incompatíveis"):
        validate_compatible_contexts(studies)

    with pytest.raises(IncompatibleContextError, match="incompatíveis"):
        subgroup_meta_analysis(studies, "purpose")


@pytest.mark.requirement("REQ-ANA-009")
def test_blocks_reports_with_ranking_or_best_drug():
    """REQ-ANA-009: O sistema não deve produzir ranking de eficácia nem 'melhor fármaco'."""
    invalid_report_1 = {
        "analysis": "META_SYNTHESIS",
        "ranking": [{"rank": 1, "substance": "Balapiravir"}],
    }
    with pytest.raises(ForbiddenRankingError, match="Campo proibido detectado"):
        assert_no_efficacy_ranking(invalid_report_1)

    invalid_report_2 = {
        "analysis": "META_SYNTHESIS",
        "melhor_farmaco": "Sofosbuvir",
    }
    with pytest.raises(ForbiddenRankingError, match="Campo proibido detectado"):
        assert_no_efficacy_ranking(invalid_report_2)

    invalid_report_3 = {
        "analysis": "META_SYNTHESIS",
        "conclusion": "Balapiravir é considerado o melhor fármaco para tratamento de dengue.",
    }
    with pytest.raises(ForbiddenRankingError, match="Texto proibido de ranqueamento"):
        assert_no_efficacy_ranking(invalid_report_3)


@pytest.mark.requirement("REQ-ANA-002")
@pytest.mark.requirement("REQ-ANA-009")
def test_meta_regression_clean_estimation_and_no_ranking():
    """Valida o cálculo do modelo de meta-regressão aleatória e ausência de rankings."""
    compatible_studies = [
        {"study_id": "s1", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": -0.80, "variance": 0.04, "timing": 24.0, "stratum": "EARLY"},
        {"study_id": "s2", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": -0.50, "variance": 0.05, "timing": 48.0, "stratum": "EARLY"},
        {"study_id": "s3", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": -0.20, "variance": 0.06, "timing": 72.0, "stratum": "LATE"},
        {"study_id": "s4", "context": "HUMANO", "purpose": "TRATAMENTO", "effect": -0.05, "variance": 0.04, "timing": 96.0, "stratum": "LATE"},
    ]

    result = fit_random_effects_meta_regression(compatible_studies, "timing")

    assert result["model"] == "RANDOM_EFFECTS_META_REGRESSION"
    assert result["k_studies"] == 4
    assert result["covariate"] == "timing"
    assert "coefficients" in result
    assert "intercept" in result["coefficients"]
    assert "timing" in result["coefficients"]

    # Beta1 deve ser positivo (tempo maior reduz magnitude do benefício de -0.80 para -0.05)
    beta1 = result["coefficients"]["timing"]["estimate"]
    assert beta1 > 0

    # Salvaguarda RC-07: sem chaves de ranqueamento
    assert "ranking" not in result
    assert "melhor_farmaco" not in result

    # Análise de subgrupos
    subgroups = subgroup_meta_analysis(compatible_studies, "stratum")
    assert "EARLY" in subgroups["subgroups"]
    assert "LATE" in subgroups["subgroups"]
    assert subgroups["subgroups"]["EARLY"]["k_studies"] == 2
    assert subgroups["subgroups"]["LATE"]["k_studies"] == 2
