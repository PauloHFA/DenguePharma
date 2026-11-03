"""Testes de ingestão e agregação de dados epidemiológicos (Eixo C - REQ-ING-008)."""
import pytest
from denguepharma_workers.epidemiology import (
    ingest_epidemiological_records,
    ingest_opendengue_csv,
    validate_case_record,
)


SAMPLE_OPENDENGUE_CSV = """adm0_iso3,epi_year,adm1_iso,dengue_cases,severe_cases,deaths
BRA,2023,SP,120000,450,30
BRA,2023,RJ,80000,200,15
BRA,2023,MG,100000,300,25
COL,2023,ANT,45000,80,5
COL,2023,VAL,25000,40,3
VNM,2023,HCM,60000,120,8
"""


@pytest.mark.requirement("REQ-ING-008")
def test_ingest_opendengue_csv_aggregates_totals_by_country_and_year():
    res = ingest_opendengue_csv(SAMPLE_OPENDENGUE_CSV, data_version_date="2026-10-15")

    assert res["source"] == "OPENDENGUE"
    assert res["data_version_date"] == "2026-10-15"
    assert res["total_input_records"] == 6
    assert res["total_country_years"] == 3
    assert len(res["content_hash"]) == 64

    agg_by_iso = {r["country_iso3"]: r for r in res["aggregated"]}

    # Brasil: 120k + 80k + 100k = 300.000 casos
    bra = agg_by_iso["BRA"]
    assert bra["year"] == 2023
    assert bra["total_cases"] == 300000
    assert bra["total_severe_cases"] == 950
    assert bra["total_deaths"] == 70
    assert bra["subdivisions_count"] == 3

    # Colômbia: 45k + 25k = 70.000 casos
    col = agg_by_iso["COL"]
    assert col["total_cases"] == 70000
    assert col["total_severe_cases"] == 120
    assert col["total_deaths"] == 8

    # Vietnã: 60.000 casos
    vnm = agg_by_iso["VNM"]
    assert vnm["total_cases"] == 60000


@pytest.mark.requirement("REQ-ING-008")
def test_ingest_sinan_aggregated_records():
    sinan_data = [
        {"country_iso3": "BRA", "year": 2024, "admin_level": "STATE", "admin_code": "SP", "cases": 1500000, "severe_cases": 2500, "deaths": 1200},
        {"country_iso3": "BRA", "year": 2024, "admin_level": "STATE", "admin_code": "RJ", "cases": 350000, "severe_cases": 800, "deaths": 250},
    ]

    res = ingest_epidemiological_records(sinan_data, source="SINAN_DATASUS", data_version_date="2026-10-20")

    assert res["source"] == "SINAN_DATASUS"
    assert res["total_country_years"] == 1
    bra_2024 = res["aggregated"][0]
    assert bra_2024["country_iso3"] == "BRA"
    assert bra_2024["year"] == 2024
    assert bra_2024["total_cases"] == 1850000
    assert bra_2024["total_deaths"] == 1450


@pytest.mark.requirement("REQ-ING-008")
def test_validation_rejects_invalid_iso_or_out_of_bounds_year():
    # Código ISO inválido (2 letras ou caracteres inválidos)
    with pytest.raises(ValueError, match="Código de país ISO-3 inválido"):
        validate_case_record({"country_iso3": "BR", "year": 2023, "cases": 10}, "OPENDENGUE", "2026-10-01")

    # Ano inválido
    with pytest.raises(ValueError, match="Ano fora da faixa permitida"):
        validate_case_record({"country_iso3": "BRA", "year": 1800, "cases": 10}, "OPENDENGUE", "2026-10-01")
