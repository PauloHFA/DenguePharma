"""Testes unitários e de conformidade do modelo Kaplan-Meier (Eixo B - REQ-ANA-003)."""
import math
import pytest
from denguepharma_analytics.analyses.survival import calculate_kaplan_meier, analyze_trials_survival


@pytest.mark.requirement("REQ-ANA-003")
def test_kaplan_meier_with_10_known_trials_matches_manual_reference():
    # 10 ensaios com tempos de observação (meses) e eventos (1=publicou, 0=censurado na data de corte)
    # Tempos ordenados: [2, 4, 6(c), 8, 10, 12(c), 14, 16, 18(c), 20]
    times = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    events = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1]

    km = calculate_kaplan_meier(times, events)

    assert km["total_trials"] == 10
    assert km["total_events"] == 7
    assert km["total_censored"] == 3

    # Verificação manual passo a passo da probabilidade de sobrevida S(t):
    # t=0: S(0) = 1.0, at_risk = 10
    assert km["survival_probability"][0] == 1.0
    assert km["reporting_probability"][0] == 0.0

    # t=2: d=1, n=10 -> S(2) = 1 * (1 - 1/10) = 0.90
    assert km["survival_probability"][1] == 0.90
    assert km["reporting_probability"][1] == 0.10

    # t=4: d=1, n=9 -> S(4) = 0.90 * (1 - 1/9) = 0.90 * (8/9) = 0.80
    assert km["survival_probability"][2] == 0.80

    # t=6: censurado (d=0, c=1), n=8 -> S(6) permanece 0.80
    assert km["survival_probability"][3] == 0.80

    # t=8: d=1, n=7 -> S(8) = 0.80 * (1 - 1/7) = 0.80 * (6/7) ~= 0.68571
    assert math.isclose(km["survival_probability"][4], 0.68571, rel_tol=1e-4)

    # t=10: d=1, n=6 -> S(10) = (6/7 * 0.80) * (5/6) = 0.57143
    assert math.isclose(km["survival_probability"][5], 0.57143, rel_tol=1e-4)

    # t=14: d=1, n=4 -> cruza a mediana (S(t) <= 0.5)
    # S(14) = 0.57143 * 3/4 = 0.42857
    assert km["median_survival"] == 14.0


@pytest.mark.requirement("REQ-ANA-003")
def test_analyze_trials_survival_handles_cohort_and_stratification():
    trials = [
        # Indústria: 3 ensaios rápidos
        {"nct_id": "NCT00000001", "sponsor_type": "INDUSTRY", "primary_completion_date": "2020-01-01", "results_date": "2020-07-01"},
        {"nct_id": "NCT00000002", "sponsor_type": "INDUSTRY", "primary_completion_date": "2020-03-01", "results_date": "2020-11-01"},
        {"nct_id": "NCT00000003", "sponsor_type": "INDUSTRY", "primary_completion_date": "2021-01-01", "results_date": None}, # censurado
        # Academia/Governo: 3 ensaios mais lentos / censurados
        {"nct_id": "NCT00000004", "sponsor_type": "GOVERNMENT", "primary_completion_date": "2020-01-01", "results_date": "2022-01-01"},
        {"nct_id": "NCT00000005", "sponsor_type": "OTHER", "primary_completion_date": "2021-06-01", "results_date": None}, # censurado
        {"nct_id": "NCT00000006", "sponsor_type": "ACADEMIA", "primary_completion_date": "2022-01-01", "results_date": None}, # censurado
    ]

    result = analyze_trials_survival(trials, cutoff_date_str="2023-01-01")

    assert result["cohort_size"] == 6
    assert result["global_curve"]["total_trials"] == 6
    assert result["global_curve"]["total_events"] == 3
    assert result["global_curve"]["total_censored"] == 3

    assert "INDUSTRIA" in result["strata"]
    assert "ACADEMIA_GOVERNO" in result["strata"]
    assert result["strata"]["INDUSTRIA"]["total_trials"] == 3
    assert result["strata"]["INDUSTRIA"]["total_events"] == 2
    assert result["strata"]["ACADEMIA_GOVERNO"]["total_trials"] == 3
    assert result["strata"]["ACADEMIA_GOVERNO"]["total_events"] == 1


@pytest.mark.requirement("REQ-ANA-003")
def test_kaplan_meier_empty_and_no_event_edge_cases():
    empty_km = calculate_kaplan_meier([], [])
    assert empty_km["total_trials"] == 0
    assert empty_km["median_survival"] is None

    # Todos censurados
    times = [5.0, 10.0, 15.0]
    events = [0, 0, 0]
    km = calculate_kaplan_meier(times, events)
    assert km["total_events"] == 0
    assert km["total_censored"] == 3
    assert all(s == 1.0 for s in km["survival_probability"])
    assert km["median_survival"] is None
