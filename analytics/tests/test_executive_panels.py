"""
Testes de verificação formal para REQ-REL-003, REQ-REL-004 e REQ-REL-005.
"""
import pytest

from denguepharma_analytics.reports.executive_panels import (
    AxisPanelState,
    InvalidAxisError,
    get_axis_panel,
    EvaluationGoal,
    EvaluationReport,
    build_evaluation_report,
    SeriesSpec,
    AccessibleFigureSpec,
    InaccessibleFigureError,
)


# ============================================================================
# REQ-REL-003: Painéis por Eixo e Estados Vazios
# ============================================================================

@pytest.mark.requirement("REQ-REL-003")
def test_axis_panel_empty_state_and_full_text_policy():
    """
    ACC-REL-003: Dado um eixo sem dados, quando aberto, então exibe estado vazio explicativo.
    """
    # Eixo B sem dados (revisão clínica pendente)
    panel_b = get_axis_panel(axis_code="B", data=[], pending_update=True)
    assert panel_b.is_empty is True
    assert panel_b.empty_explanation is not None
    assert "revisão humana permanece pendente" in panel_b.empty_explanation
    assert panel_b.pending_update is True
    assert panel_b.full_text_access_policy == "acesso_limitado_por_licenca"

    # Eixo E sem dados (grafo de evidências sem arestas adjudicadas)
    panel_e = get_axis_panel(axis_code="E", data=None)
    assert panel_e.is_empty is True
    assert "Nenhuma aresta de evidência" in panel_e.empty_explanation

    # Eixo A com dados
    sample_data = [{"doc_id": "DOC-001", "title": "Estudo Fase 2"}]
    panel_a = get_axis_panel(axis_code="A", data=sample_data)
    assert panel_a.is_empty is False
    assert panel_a.empty_explanation is None
    assert len(panel_a.data_rows) == 1

    # Eixo inválido
    with pytest.raises(InvalidAxisError):
        get_axis_panel(axis_code="Z")


# ============================================================================
# REQ-REL-004: Metas Não Atingidas e Resultados Desfavoráveis
# ============================================================================

@pytest.mark.requirement("REQ-REL-004")
def test_evaluation_report_highlights_unmet_goals_and_unfavorable_outcomes():
    """
    ACC-REL-004: Dado uma meta não atingida, quando o relatório for gerado,
    então ela aparece com destaque.
    """
    goals_data = [
        {
            "goal_id": "GOAL-01",
            "description": "Redução de carga viral em 48h >= 2.0 log10",
            "target_metric": "log10 cópias/mL",
            "target_value": 2.0,
            "observed_value": 1.1,
            "achieved": False,
            "status": "META_NAO_ATINGIDA",
            "clinical_implication": "Eficácia antiviral insuficiente no desfecho primário",
        },
        {
            "goal_id": "GOAL-02",
            "description": "Incidência de eventos adversos graves <= 5%",
            "target_metric": "%",
            "target_value": 5.0,
            "observed_value": 4.2,
            "achieved": True,
            "status": "ATINGIDA",
            "clinical_implication": "Perfil de segurança adequado",
        },
        {
            "goal_id": "GOAL-03",
            "description": "Taxa de adesão ao tratamento >= 90%",
            "target_metric": "%",
            "target_value": 90.0,
            "observed_value": 74.0,
            "achieved": False,
            "status": "DESFAVORAVEL",
            "clinical_implication": "Alta descontinuação por intolerância gastrointestinal",
        },
    ]

    report = build_evaluation_report(
        report_id="EVAL-2026-001",
        title="Avaliação Clínica Balapiravir - Ensaio de Fase 2",
        goals_data=goals_data,
    )

    assert report.total_goals == 3
    assert report.unmet_count == 2
    assert report.favorable_count == 1

    # Verifica que a seção de alerta com destaque está presente e contém as metas não atingidas
    highlighted = report.highlighted_unmet_section
    assert highlighted["prominence"] == "HIGH_ALERT"
    assert highlighted["has_unmet_goals"] is True
    assert len(highlighted["items"]) == 2

    # Verifica os badges e discrepâncias detalhadas
    unmet_ids = [item["goal_id"] for item in highlighted["items"]]
    assert "GOAL-01" in unmet_ids
    assert "GOAL-03" in unmet_ids

    goal_01 = next(item for item in highlighted["items"] if item["goal_id"] == "GOAL-01")
    assert goal_01["badge"] == "META_NAO_ATINGIDA"
    assert "Meta: 2.0 log10 cópias/mL | Observado: 1.1 log10 cópias/mL" in goal_01["discrepancy"]


# ============================================================================
# REQ-REL-005: Legenda Completa com Denominador, Período e Marcadores Além da Cor
# ============================================================================

@pytest.mark.requirement("REQ-REL-005")
def test_accessible_figure_spec_requires_denominator_period_and_non_color_markers():
    """
    ACC-REL-005: Dado uma figura, quando inspecionada, então tem legenda completa
    (com denominador e período) e marcadores além da cor.
    """
    # Figura acessível válida: cores diferentes E marcadores/estilos diferentes
    fig_spec = AccessibleFigureSpec(
        figure_id="FIG-001",
        title="Curva de Sobrevivência Livre de Eventos Clínicos por Braço",
        denominator_total=450,
        period_start_year=2021,
        period_end_year=2025,
        series=[
            SeriesSpec(
                label="Braço Intervenção (Balapiravir)",
                n_sample=225,
                color="#0284c7",
                marker_shape="circle",
                line_style="solid",
            ),
            SeriesSpec(
                label="Braço Controle (Placebo)",
                n_sample=225,
                color="#dc2626",
                marker_shape="triangle",
                line_style="dashed",
            ),
        ],
    )

    fig_spec.validate()
    caption = fig_spec.generate_caption()

    # Valida presença de denominador e período na legenda
    assert "Denominador Total: N=450 participantes" in caption
    assert "Período: 2021 a 2025" in caption
    assert "marcador: circle" in caption
    assert "marcador: triangle" in caption
    assert "linha: solid" in caption
    assert "linha: dashed" in caption

    # Falha se denominador for zero ou negativo
    with pytest.raises(InaccessibleFigureError, match="Denominador total"):
        AccessibleFigureSpec(
            figure_id="FIG-INVALID-1",
            title="Invalida Denominador",
            denominator_total=0,
            period_start_year=2020,
            period_end_year=2022,
            series=[SeriesSpec(label="A", n_sample=0, color="#000", marker_shape="c", line_style="s")],
        ).validate()

    # Falha se período for inconsistente
    with pytest.raises(InaccessibleFigureError, match="Período inválido"):
        AccessibleFigureSpec(
            figure_id="FIG-INVALID-2",
            title="Invalida Periodo",
            denominator_total=100,
            period_start_year=2025,
            period_end_year=2020,
            series=[SeriesSpec(label="A", n_sample=100, color="#000", marker_shape="c", line_style="s")],
        ).validate()

    # Falha se depender exclusivamente de cores (mesmo marcador e mesma linha para todas as séries)
    with pytest.raises(InaccessibleFigureError, match="depende exclusivamente de cor"):
        AccessibleFigureSpec(
            figure_id="FIG-COLOR-ONLY",
            title="Figura Inacessível Apenas Cores",
            denominator_total=200,
            period_start_year=2022,
            period_end_year=2024,
            series=[
                SeriesSpec(label="Série 1", n_sample=100, color="#ff0000", marker_shape="circle", line_style="solid"),
                SeriesSpec(label="Série 2", n_sample=100, color="#00ff00", marker_shape="circle", line_style="solid"),
            ],
        ).validate()
