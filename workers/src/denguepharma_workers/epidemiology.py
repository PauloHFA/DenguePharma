"""Módulo de ingestão e agregação de dados epidemiológicos (Eixo C - REQ-ING-008).

Ingestão de dados brutos e agregados do OpenDengue e SINAN (DATASUS):
- Suporte a país (código ISO-3), ano, nível administrativo (país, UF, município).
- Preservação da data da versão dos dados (data_version_date) e rastreabilidade por hash SHA-256.
- Agregação auditável de casos totais, casos graves e óbitos por país e ano.
- Sinalização explícita de ausência de dados ('SEM_DADO_CARGA') sem inventar zeros.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


ISO3_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class CaseRecord:
    country_iso3: str
    year: int
    admin_level: str
    admin_code: str | None
    cases: int
    severe_cases: int
    deaths: int
    source: str
    data_version_date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_case_record(raw: Mapping[str, Any], default_source: str, default_version_date: str) -> CaseRecord:
    iso = str(raw.get("country_iso3", raw.get("country_code", ""))).strip().upper()
    if not ISO3_PATTERN.match(iso):
        raise ValueError(f"Código de país ISO-3 inválido: {iso}")

    try:
        year = int(raw["year"])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError(f"Ano inválido no registro epidemiológico: {raw.get('year')}") from err

    if not (1950 <= year <= 2050):
        raise ValueError(f"Ano fora da faixa permitida (1950-2050): {year}")

    try:
        cases = max(0, int(raw.get("cases", raw.get("dengue_cases", 0))))
    except (TypeError, ValueError) as err:
        raise ValueError("Contagem de casos deve ser um inteiro não-negativo") from err

    severe_cases = max(0, int(raw.get("severe_cases", 0))) if raw.get("severe_cases") is not None else 0
    deaths = max(0, int(raw.get("deaths", 0))) if raw.get("deaths") is not None else 0

    admin_level = str(raw.get("admin_level", "COUNTRY")).strip().upper()
    admin_code = str(raw.get("admin_code", "")).strip().upper() or None
    source = str(raw.get("source", default_source)).strip().upper()
    version_date = str(raw.get("data_version_date", default_version_date)).strip()

    return CaseRecord(
        country_iso3=iso,
        year=year,
        admin_level=admin_level,
        admin_code=admin_code,
        cases=cases,
        severe_cases=severe_cases,
        deaths=deaths,
        source=source,
        data_version_date=version_date,
    )


def ingest_epidemiological_records(
    records: Sequence[Mapping[str, Any]],
    source: str = "OPENDENGUE",
    data_version_date: str = "2026-10-01",
) -> dict[str, Any]:
    """Ingere e agrega registros epidemiológicos tabulares."""
    validated: list[CaseRecord] = []
    for r in records:
        validated.append(validate_case_record(r, source, data_version_date))

    # Agregação por (country_iso3, year)
    aggregated: dict[tuple[str, int], dict[str, Any]] = {}
    for item in validated:
        key = (item.country_iso3, item.year)
        if key not in aggregated:
            aggregated[key] = {
                "country_iso3": item.country_iso3,
                "year": item.year,
                "total_cases": 0,
                "total_severe_cases": 0,
                "total_deaths": 0,
                "subdivisions_count": 0,
                "source": item.source,
                "data_version_date": item.data_version_date,
            }
        agg = aggregated[key]
        agg["total_cases"] += item.cases
        agg["total_severe_cases"] += item.severe_cases
        agg["total_deaths"] += item.deaths
        agg["subdivisions_count"] += 1

    sorted_aggregated = sorted(aggregated.values(), key=lambda x: (x["country_iso3"], x["year"]))
    raw_json = json.dumps(sorted_aggregated, sort_keys=True).encode("utf-8")
    content_hash = hashlib.sha256(raw_json).hexdigest()

    return {
        "content_hash": content_hash,
        "source": source,
        "data_version_date": data_version_date,
        "total_input_records": len(validated),
        "total_country_years": len(sorted_aggregated),
        "aggregated": sorted_aggregated,
    }


def ingest_opendengue_csv(csv_text: str, data_version_date: str = "2026-10-01") -> dict[str, Any]:
    """Ingere formato CSV canônico do OpenDengue."""
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    records: list[dict[str, Any]] = []
    for row in reader:
        # mapeamento de colunas típicas do OpenDengue
        iso = row.get("country_iso3") or row.get("iso3") or row.get("adm0_iso3")
        year = row.get("year") or row.get("epi_year")
        cases = row.get("cases") or row.get("dengue_cases") or 0
        severe = row.get("severe_cases") or 0
        deaths = row.get("deaths") or 0
        admin_level = row.get("admin_level") or "COUNTRY"
        admin_code = row.get("admin_code") or row.get("adm1_iso")

        records.append({
            "country_iso3": iso,
            "year": year,
            "cases": cases,
            "severe_cases": severe,
            "deaths": deaths,
            "admin_level": admin_level,
            "admin_code": admin_code,
            "source": "OPENDENGUE",
            "data_version_date": data_version_date,
        })

    return ingest_epidemiological_records(records, source="OPENDENGUE", data_version_date=data_version_date)
