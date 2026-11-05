"""
Módulo M07: Painéis por Eixo, Metas Não Atingidas e Figuras Acessíveis (REQ-REL-003, REQ-REL-004, REQ-REL-005).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set


# ============================================================================
# REQ-REL-003: Painéis por Eixo com Estados Vazios e Acesso Limitado
# ============================================================================

class InvalidAxisError(ValueError):
    """Lançado quando um código de eixo inexistente é fornecido."""
    pass


AXIS_METADATA = {
    "A": {
        "title": "Diagnóstico de Corpus e Panorama Geral",
        "empty_explanation": "Sem registros coletados para os parâmetros informados. A ausência de dados decorre de filtros restritivos ou de nova execução pendente.",
    },
    "B": {
        "title": "Eficácia Clínica e Análise de Sobrevivência",
        "empty_explanation": "Sem resultados clínicos revisados. A revisão humana permanece pendente; isto não significa ausência de benefício terapêutico ou evidência inconclusiva.",
    },
    "C": {
        "title": "Carga Global de Doença e Desertos Epidemiológicos",
        "empty_explanation": "Sem série histórica epidemiológica correspondente aos locais dos ensaios informados. Dados SINAN/GBD pendentes de agregação.",
    },
    "D": {
        "title": "Extração Assistida por IA e Benchmark Metrológico",
        "empty_explanation": "Nenhuma extração por modelo executada para este corpus. Fila de inferência vazia ou modelo em calibração.",
    },
    "E": {
        "title": "Grafo de Evidências Clínicas e Redes de Tratamento",
        "empty_explanation": "Nenhuma aresta de evidência adjudicada disponível. Rascunhos da IA e dados sob revisão não integram o grafo formal.",
    },
}


@dataclass
class AxisPanelState:
    """Representa o estado visual e semântico de um painel por eixo (REQ-REL-003)."""
    axis_code: str
    axis_title: str
    is_empty: bool
    pending_update: bool
    empty_explanation: Optional[str]
    full_text_access_policy: str
    data_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_axis_panel(
    axis_code: str,
    data: Optional[List[Dict[str, Any]]] = None,
    pending_update: bool = False,
    full_text_access_policy: str = "acesso_limitado_por_licenca",
) -> AxisPanelState:
    """
    Retorna o estado do painel de um determinado eixo (REQ-REL-003 / ACC-REL-003).
    Se não houver dados, retorna obrigatoriamente um estado vazio explicativo padronizado.
    """
    axis_key = axis_code.upper().strip()
    if axis_key not in AXIS_METADATA:
        raise InvalidAxisError(f"Eixo desconhecido: '{axis_code}'. Eixos válidos: {list(AXIS_METADATA.keys())}")

    meta = AXIS_METADATA[axis_key]
    rows = list(data or [])
    is_empty = len(rows) == 0

    return AxisPanelState(
        axis_code=axis_key,
        axis_title=meta["title"],
        is_empty=is_empty,
        pending_update=pending_update,
        empty_explanation=meta["empty_explanation"] if is_empty else None,
        full_text_access_policy=full_text_access_policy,
        data_rows=rows,
    )


# ============================================================================
# REQ-REL-004: Relatórios com Destaque para Metas Não Atingidas e Resultados Desfavoráveis
# ============================================================================

class UnfavorableResultOmissionError(ValueError):
    """Lançado se houver tentativa de omitir ou mascarar metas não atingidas ou resultados desfavoráveis."""
    pass


@dataclass
class EvaluationGoal:
    goal_id: str
    description: str
    target_metric: str
    target_value: float
    observed_value: float
    achieved: bool
    status: Literal["ATINGIDA", "META_NAO_ATINGIDA", "DESFAVORAVEL"]
    clinical_implication: str


@dataclass
class EvaluationReport:
    report_id: str
    title: str
    total_goals: int
    unmet_count: int
    favorable_count: int
    goals: List[EvaluationGoal]
    highlighted_unmet_section: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_evaluation_report(
    report_id: str,
    title: str,
    goals_data: List[Dict[str, Any]],
) -> EvaluationReport:
    """
    Gera relatório de avaliação garantindo destaque explícito para resultados desfavoráveis
    e metas não atingidas (REQ-REL-004 / ACC-REL-004).
    """
    if not goals_data:
        raise ValueError("goals_data não pode ser vazio.")

    parsed_goals: List[EvaluationGoal] = []
    unmet_goals: List[EvaluationGoal] = []

    for item in goals_data:
        target = float(item["target_value"])
        observed = float(item["observed_value"])
        achieved = bool(item.get("achieved", observed >= target))
        status = "ATINGIDA" if achieved else item.get("status", "META_NAO_ATINGIDA")

        goal = EvaluationGoal(
            goal_id=str(item["goal_id"]),
            description=str(item["description"]),
            target_metric=str(item["target_metric"]),
            target_value=target,
            observed_value=observed,
            achieved=achieved,
            status=status,
            clinical_implication=str(item.get("clinical_implication", "Requer reavaliação metodológica")),
        )
        parsed_goals.append(goal)
        if not achieved or status in ("META_NAO_ATINGIDA", "DESFAVORAVEL"):
            unmet_goals.append(goal)

    # Construção da seção com destaque obrigatório
    highlighted_section = {
        "title": "Resultados Desfavoráveis e Metas Não Atingidas (Alerta Metodológico)",
        "prominence": "HIGH_ALERT",
        "has_unmet_goals": len(unmet_goals) > 0,
        "items": [
            {
                "goal_id": g.goal_id,
                "badge": g.status,
                "description": g.description,
                "discrepancy": f"Meta: {g.target_value} {g.target_metric} | Observado: {g.observed_value} {g.target_metric}",
                "implication": g.clinical_implication,
            }
            for g in unmet_goals
        ],
    }

    return EvaluationReport(
        report_id=report_id,
        title=title,
        total_goals=len(parsed_goals),
        unmet_count=len(unmet_goals),
        favorable_count=len(parsed_goals) - len(unmet_goals),
        goals=parsed_goals,
        highlighted_unmet_section=highlighted_section,
    )


# ============================================================================
# REQ-REL-005: Legenda Completa com Denominador, Período e Marcadores Além da Cor
# ============================================================================

class InaccessibleFigureError(ValueError):
    """Lançado quando uma figura viola requisitos de acessibilidade visual."""
    pass


@dataclass
class SeriesSpec:
    label: str
    n_sample: int
    color: str
    marker_shape: str   # ex: "circle", "triangle", "square", "diamond", "star"
    line_style: str     # ex: "solid", "dashed", "dotted", "dashdot"
    hatch_pattern: Optional[str] = None  # ex: "/", "\\", "x", "."


@dataclass
class AccessibleFigureSpec:
    figure_id: str
    title: str
    denominator_total: int
    period_start_year: int
    period_end_year: int
    series: List[SeriesSpec]

    def validate(self) -> None:
        if self.denominator_total <= 0:
            raise InaccessibleFigureError("REQ-REL-005: Denominador total (N) deve ser positivo.")
        if self.period_start_year > self.period_end_year:
            raise InaccessibleFigureError("REQ-REL-005: Período inválido (ano inicial maior que ano final).")
        if not self.series:
            raise InaccessibleFigureError("REQ-REL-005: A figura deve conter ao menos uma série de dados.")

        # Validação de não dependência exclusiva de cor:
        # Se houver mais de uma série, elas devem possuir marcadores ou estilos distintos
        if len(self.series) > 1:
            shapes = {s.marker_shape for s in self.series}
            styles = {s.line_style for s in self.series}
            hatches = {s.hatch_pattern for s in self.series if s.hatch_pattern}
            # Se todas as séries tiverem exatamente a mesma forma, mesmo estilo e sem hachura distinta, falha
            if len(shapes) <= 1 and len(styles) <= 1 and len(hatches) <= 1:
                raise InaccessibleFigureError(
                    "REQ-REL-005: A figura depende exclusivamente de cor. Séries devem ter marcadores ou estilos distintos."
                )

    def generate_caption(self) -> str:
        """Gera a legenda acessível completa contendo denominador, período e codificação das séries."""
        self.validate()
        series_desc = []
        for s in self.series:
            series_desc.append(
                f"{s.label} (n={s.n_sample}, marcador: {s.marker_shape}, linha: {s.line_style})"
            )
        return (
            f"Figura: {self.title}. "
            f"Denominador Total: N={self.denominator_total} participantes. "
            f"Período: {self.period_start_year} a {self.period_end_year}. "
            f"Séries: {'; '.join(series_desc)}."
        )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "figure_id": self.figure_id,
            "title": self.title,
            "caption": self.generate_caption(),
            "denominator_total": self.denominator_total,
            "period": f"{self.period_start_year}-{self.period_end_year}",
            "accessible_markers_present": True,
            "series": [asdict(s) for s in self.series],
        }

