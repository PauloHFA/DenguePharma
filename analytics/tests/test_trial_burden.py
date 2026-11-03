"""Testes para o cruzamento de sítios/participantes de ensaios e carga epidemiológica (REQ-ANA-004)."""
from __future__ import annotations

import pytest

from denguepharma_analytics.analyses.trial_burden import (
    BurdenRecord,
    TrialSiteRecord,
    link_trials_and_burden,
    summarize_trial_burden_landscape,
)


@pytest.mark.requirement("REQ-ANA-004")
def test_trial_burden_link_and_missing_data_safeguard():
    """Valida que sítios de ensaios são correlacionados à carga epidemiológica,

    e que países sem registros epidemiológicos são explicitamente marcados como
    'SEM_DADO_CARGA', sem inventar ou imputar zero (ACC-ANA-004).
    """
    trials = [
        # Brasil - alta carga, ensaio ativo
        TrialSiteRecord(
            trial_id="NCT01234001",
            country_iso3="BRA",
            year=2022,
            participants_count=350,
            site_name="Hospital das Clínicas da FMUSP",
        ),
        # Índia - altíssima carga, poucos participantes (Deserto Crítico)
        TrialSiteRecord(
            trial_id="NCT01234002",
            country_iso3="IND",
            year=2022,
            participants_count=30,
            site_name="AIIMS New Delhi",
        ),
        # Cingapura - baixa carga endêmica, muitos participantes (Centro Concentrado)
        TrialSiteRecord(
            trial_id="NCT01234003",
            country_iso3="SGP",
            year=2022,
            participants_count=180,
            site_name="Singapore General Hospital",
        ),
        # França - sítio de coordenação/estudo sem registro de carga endêmica local
        TrialSiteRecord(
            trial_id="NCT01234004",
            country_iso3="FRA",
            year=2022,
            participants_count=50,
            site_name="Hôpital Pitié-Salpêtrière",
        ),
    ]

    burdens = [
        BurdenRecord(
            country_iso3="BRA",
            year=2022,
            cases=1450000,
            case_definition="CASOS_NOTIFICADOS_SINAN",
            incidence_per_100k=680.5,
            source="SINAN/DATASUS",
        ),
        BurdenRecord(
            country_iso3="IND",
            year=2022,
            cases=2300000,
            case_definition="CASOS_ESTIMADOS_OPENDENGUE",
            incidence_per_100k=164.2,
            source="OPENDENGUE",
        ),
        BurdenRecord(
            country_iso3="SGP",
            year=2022,
            cases=8500,
            case_definition="CASOS_LABORATORIAIS_CONFIRMADOS",
            incidence_per_100k=145.0,
            source="MOH_SINGAPORE",
        ),
        # Note: França (FRA) NÃO possui registro em burdens propositalmente
    ]

    linked = link_trials_and_burden(trials, burdens)
    assert len(linked) == 4

    # 1. Brasil (BRA)
    bra = next(x for x in linked if x.country_iso3 == "BRA")
    assert bra.has_burden_data is True
    assert bra.cases == 1450000
    assert bra.case_definition == "CASOS_NOTIFICADOS_SINAN"
    assert bra.burden_status == "COM_DADO_CARGA"
    assert bra.disparity_indicator == "PROPORCIONAL"

    # 2. Índia (IND) - Deserto Crítico
    ind = next(x for x in linked if x.country_iso3 == "IND")
    assert ind.has_burden_data is True
    assert ind.cases == 2300000
    assert ind.participants_count == 30
    assert ind.burden_status == "COM_DADO_CARGA"
    assert ind.disparity_indicator == "DESERTO_CRITICO"

    # 3. Cingapura (SGP) - Centro Concentrado
    sgp = next(x for x in linked if x.country_iso3 == "SGP")
    assert sgp.has_burden_data is True
    assert sgp.cases == 8500
    assert sgp.participants_count == 180
    assert sgp.burden_status == "COM_DADO_CARGA"
    assert sgp.disparity_indicator == "CENTRO_CONCENTRADO"

    # 4. CRITÉRIO DE ACEITAÇÃO ACC-ANA-004: França (FRA) sem registro de casos
    fra = next(x for x in linked if x.country_iso3 == "FRA")
    assert fra.has_burden_data is False
    assert fra.burden_status == "SEM_DADO_CARGA"
    assert fra.cases is None  # ESTRITAMENTE None; PROIBIDO IMPUTAR ZERO!
    assert fra.incidence_per_100k is None
    assert fra.disparity_indicator == "SEM_DADOS"

    # 5. Resumo consolidado e verificação de salvaguarda
    summary = summarize_trial_burden_landscape(linked)
    assert summary["total_trial_sites"] == 4
    assert summary["total_participants"] == 610
    assert summary["sites_with_burden_data"] == 3
    assert summary["sites_without_burden_data"] == 1
    assert summary["critical_deserts_count"] == 1
    assert summary["concentrated_centers_count"] == 1
    assert summary["safeguard_verified"] is True
