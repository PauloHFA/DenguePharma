from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ..domain import digest, json_bytes


@dataclass(frozen=True)
class Principal:
    id: str
    roles: tuple[str, ...]

    def require(self, *roles):
        if not set(self.roles).intersection(roles): raise PermissionError("ROLE_FORBIDDEN")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True, str_strip_whitespace=True)


class Classification(Strict):
    established_dengue: Literal["SIM", "NAO", "INCERTO"]
    context: Literal["DOENCA_ESTABELECIDA", "PROFILAXIA", "VACINA", "VOLUNTARIOS_SAUDAVEIS", "DESAFIO_CONTROLADO", "ANIMAL", "IN_VITRO", "IN_SILICO", "VETORES", "DIAGNOSTICO_ISOLADO", "INCERTO"]
    population: Literal["ADULTOS", "PEDIATRICO", "MISTA_SEM_SEPARACAO", "INCERTO"]
    severity: Literal["NAO_GRAVE", "GRAVE", "MISTA", "NAO_INFORMADA"]
    disease_phase: Literal["FEBRIL", "CRITICA", "RECUPERACAO", "MISTA", "NAO_INFORMADA"]
    purpose: Literal["TRATAMENTO", "MANEJO_SINTOMATICO", "OUTRO"]
    design: Literal["RCT_PARALELO", "RCT_OUTRO", "OBSERVACIONAL", "REVISAO", "OUTRO", "INCERTO"]
    interventions: list[str] = Field(default_factory=list)
    pharmacological_intervention: Literal["SIM","NAO","INCERTO"] = "INCERTO"


class Screen(Strict):
    study_id: str
    basis_hash: str
    decision: Literal["INCLUIR", "EXCLUIR", "INCERTO"]
    classification: Classification
    reason: str = Field(min_length=5)

    @model_validator(mode="after")
    def eligible(self):
        c = self.classification
        if self.decision == "INCLUIR" and (c.pharmacological_intervention!="SIM" or c.established_dengue != "SIM" or c.context != "DOENCA_ESTABELECIDA" or c.population == "INCERTO" or c.purpose == "OUTRO" or c.design not in {"RCT_PARALELO", "RCT_OUTRO", "OBSERVACIONAL"} or not c.interventions):
            raise ValueError("Classificacao incompativel com a sintese principal; registrar exclusao ou incerteza humana.")
        return self


class EvidenceRef(Strict):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False,strict=True,str_strip_whitespace=False)
    field: str
    version_id: str
    text_hash: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)


class Arm(Strict):
    arm_id: str = Field(min_length=1)
    n: int | None = Field(default=None, ge=1, strict=True)
    n_randomized: int | None = Field(default=None, ge=1, strict=True)
    events: int | None = Field(default=None, ge=0, strict=True)
    mean: float | None = None
    sd: float | None = Field(default=None, ge=0)


class Reported(Strict):
    measure: Literal["RR", "OR", "HR", "MD"] = "RR"
    estimate: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    confidence_level: float | None = None


class Result(Strict):
    study_id: str
    basis_hash: str
    comparison_id: str = Field(min_length=1)
    intervention: str = Field(min_length=1)
    comparator: str = Field(min_length=1)
    population: Literal["ADULTOS", "PEDIATRICO", "MISTA_SEM_SEPARACAO"]
    severity: Literal["NAO_GRAVE", "GRAVE", "MISTA", "NAO_INFORMADA"]
    disease_phase: Literal["FEBRIL", "CRITICA", "RECUPERACAO", "MISTA", "NAO_INFORMADA"]
    intervention_timing: str = Field(min_length=1)
    analysis_population: str = Field(min_length=1)
    purpose: Literal["TRATAMENTO", "MANEJO_SINTOMATICO"]
    design: Literal["RCT_PARALELO", "RCT_OUTRO", "OBSERVACIONAL"]
    outcome_code: str
    outcome_definition: str = Field(min_length=3)
    timepoint: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    direction: Literal["MENOR_MELHOR", "MAIOR_MELHOR", "NAO_DEFINIDA"]
    effect_type: Literal["RR", "MD", "REPORTED"]
    treatment: Arm
    control: Arm
    independent_arms: bool = False
    reported: Reported | None = None
    support_care: str = Field(min_length=3)
    limitations: str = Field(min_length=5)
    risk_of_bias: Literal["BAIXO", "ALGUMAS_PREOCUPACOES", "ALTO", "NAO_AVALIADO"]
    risk_of_bias_reason: str = Field(min_length=5)
    risk_of_bias_instrument: str | None = None
    risk_of_bias_domains: dict[str, str] = Field(default_factory=dict)
    absence_states: dict[str, Literal["NAO_INFORMADO", "NAO_APLICAVEL", "NAO_EXTRAIDO", "INCERTO", "NAO_HOUVE_EVENTO"]] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    supersedes: str | None = None
    correction_reason: str | None = None


class Review(Strict):
    result_id: str
    decision: Literal["ACEITAR", "REJEITAR"]
    reason: str = Field(min_length=5)


class DocumentLink(Strict):
    document_id: str
    study_id: str
    reason: str = Field(min_length=5)


class Calibration(Strict):
    selection_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    sentinel_ids: list[str] = Field(min_length=1)
    reason: str = Field(min_length=10)


class Absence(Strict):
    selection_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    intervention: str = Field(min_length=1)
    population: Literal["ADULTOS","PEDIATRICO","MISTA_SEM_SEPARACAO"]
    reason: str = Field(min_length=10)


class Conclusion(Strict):
    selection_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    scope: dict[str, Any]
    result_set_hash: str
    category: Literal["BENEFICIO_SUSTENTADO", "EVIDENCIA_INCONCLUSIVA", "SINAL_DANO"]
    rationale: str = Field(min_length=10)
    clinical_importance: str = Field(min_length=10)
    uncertainty: str = Field(min_length=10)
    consistency: str = Field(min_length=10)
    limitations: str = Field(min_length=10)


GROUP_FIELDS = ["intervention", "comparator", "population", "severity", "disease_phase", "intervention_timing", "analysis_population", "purpose", "design_layer", "outcome_code", "outcome_definition", "timepoint", "unit", "measure", "direction"]


def scope_for(row):
    return {key: row[key] for key in GROUP_FIELDS}


def scope_id(scope): return digest(json_bytes(scope))


def result_set_hash(rows):
    return digest(json_bytes(sorted(pair for row in rows for pair in zip(row.get("document_result_ids",[row["result_id"]]),row.get("document_decision_ids",[row["decision_id"]])))))
