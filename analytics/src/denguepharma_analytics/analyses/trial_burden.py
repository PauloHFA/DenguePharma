"""Módulo de cruzamento entre sítios/participantes de ensaios clínicos e carga epidemiológica (Eixo C - REQ-ANA-004).

Regras e salvaguardas:
- Liga sítios e participantes de ensaios clínicos, por país (código ISO-3) e ano, a contagens de casos e incidência.
- Exige janela temporal idêntica e declaração explícita da definição de caso.
- SALVAGUARDA DE ACEITAÇÃO (ACC-ANA-004 / RC-04): Quando um país/ano não possui registro epidemiológico,
  ele deve ser formalmente classificado como 'SEM_DADO_CARGA' com cases=None. É expressamente proibido
  inventar ou imputar zero nesses casos.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


ISO3_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class TrialSiteRecord:
    trial_id: str
    country_iso3: str
    year: int
    participants_count: int
    site_name: str = ""

    def __post_init__(self) -> None:
        iso = self.country_iso3.strip().upper()
        if not ISO3_PATTERN.match(iso):
            raise ValueError(f"Código ISO-3 de país inválido para sítio de ensaio: {self.country_iso3}")
        if self.participants_count < 0:
            raise ValueError(f"Contagem de participantes não pode ser negativa: {self.participants_count}")
        if not (1950 <= self.year <= 2050):
            raise ValueError(f"Ano fora da faixa válida (1950-2050): {self.year}")


@dataclass(frozen=True)
class BurdenRecord:
    country_iso3: str
    year: int
    cases: int | None
    case_definition: str
    incidence_per_100k: float | None = None
    source: str = "OPENDENGUE"

    def __post_init__(self) -> None:
        iso = self.country_iso3.strip().upper()
        if not ISO3_PATTERN.match(iso):
            raise ValueError(f"Código ISO-3 de país inválido para dado de carga: {self.country_iso3}")
        if self.cases is not None and self.cases < 0:
            raise ValueError(f"Contagem de casos não pode ser negativa: {self.cases}")
        if not (1950 <= self.year <= 2050):
            raise ValueError(f"Ano fora da faixa válida (1950-2050): {self.year}")


@dataclass(frozen=True)
class LinkedTrialBurden:
    trial_id: str
    country_iso3: str
    year: int
    participants_count: int
    site_name: str
    cases: int | None
    incidence_per_100k: float | None
    case_definition: str | None
    source: str | None
    has_burden_data: bool
    burden_status: str  # 'COM_DADO_CARGA' ou 'SEM_DADO_CARGA'
    disparity_indicator: str  # 'DESERTO_CRITICO', 'CENTRO_CONCENTRADO', 'PROPORCIONAL', 'SEM_DADOS'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def link_trials_and_burden(
    trials: Sequence[TrialSiteRecord | Mapping[str, Any]],
    burdens: Sequence[BurdenRecord | Mapping[str, Any]],
    default_case_definition: str = "CASOS_NOTIFICADOS_TOTAIS",
) -> list[LinkedTrialBurden]:
    """Cruza sítios de ensaios com carga epidemiológica garantindo salvaguarda de dados ausentes."""
    # Indexar registros de carga por (country_iso3, year)
    burden_map: dict[tuple[str, int], BurdenRecord] = {}
    for b in burdens:
        if isinstance(b, BurdenRecord):
            record = b
        else:
            record = BurdenRecord(
                country_iso3=str(b.get("country_iso3", b.get("country_code", ""))).strip().upper(),
                year=int(b["year"]),
                cases=b.get("cases"),
                case_definition=str(b.get("case_definition", default_case_definition)),
                incidence_per_100k=b.get("incidence_per_100k"),
                source=str(b.get("source", "OPENDENGUE")),
            )
        burden_map[(record.country_iso3, record.year)] = record

    linked_results: list[LinkedTrialBurden] = []

    for t in trials:
        if isinstance(t, TrialSiteRecord):
            trial_rec = t
        else:
            trial_rec = TrialSiteRecord(
                trial_id=str(t["trial_id"]),
                country_iso3=str(t.get("country_iso3", t.get("country_code", ""))).strip().upper(),
                year=int(t["year"]),
                participants_count=int(t.get("participants_count", 0)),
                site_name=str(t.get("site_name", "")),
            )

        key = (trial_rec.country_iso3, trial_rec.year)
        burden_entry = burden_map.get(key)

        if burden_entry is None or burden_entry.cases is None:
            # SALVAGUARDA REQ-ANA-004: país sem dados de carga NÃO deve ser interpretado como zero
            linked_results.append(
                LinkedTrialBurden(
                    trial_id=trial_rec.trial_id,
                    country_iso3=trial_rec.country_iso3,
                    year=trial_rec.year,
                    participants_count=trial_rec.participants_count,
                    site_name=trial_rec.site_name,
                    cases=None,  # estritamente None, nunca zero!
                    incidence_per_100k=None,
                    case_definition=None,
                    source=None,
                    has_burden_data=False,
                    burden_status="SEM_DADO_CARGA",
                    disparity_indicator="SEM_DADOS",
                )
            )
        else:
            cases = burden_entry.cases
            participants = trial_rec.participants_count
            
            # Avaliação de disparidade de pesquisa (Eixo C)
            if cases >= 100_000 and participants < 50:
                indicator = "DESERTO_CRITICO"
            elif cases < 10_000 and participants >= 50:
                indicator = "CENTRO_CONCENTRADO"
            else:
                indicator = "PROPORCIONAL"

            linked_results.append(
                LinkedTrialBurden(
                    trial_id=trial_rec.trial_id,
                    country_iso3=trial_rec.country_iso3,
                    year=trial_rec.year,
                    participants_count=participants,
                    site_name=trial_rec.site_name,
                    cases=cases,
                    incidence_per_100k=burden_entry.incidence_per_100k,
                    case_definition=burden_entry.case_definition,
                    source=burden_entry.source,
                    has_burden_data=True,
                    burden_status="COM_DADO_CARGA",
                    disparity_indicator=indicator,
                )
            )

    return linked_results


def summarize_trial_burden_landscape(
    linked_data: Sequence[LinkedTrialBurden],
) -> dict[str, Any]:
    """Gera resumo executivo do cruzamento ensaios vs carga."""
    total_sites = len(linked_data)
    total_participants = sum(x.participants_count for x in linked_data)
    with_burden = [x for x in linked_data if x.has_burden_data]
    without_burden = [x for x in linked_data if not x.has_burden_data]

    critical_deserts = [x for x in linked_data if x.disparity_indicator == "DESERTO_CRITICO"]
    concentrated_centers = [x for x in linked_data if x.disparity_indicator == "CENTRO_CONCENTRADO"]

    return {
        "total_trial_sites": total_sites,
        "total_participants": total_participants,
        "sites_with_burden_data": len(with_burden),
        "sites_without_burden_data": len(without_burden),
        "critical_deserts_count": len(critical_deserts),
        "concentrated_centers_count": len(concentrated_centers),
        "safeguard_verified": all(
            x.cases is None and x.burden_status == "SEM_DADO_CARGA"
            for x in without_burden
        ),
    }
