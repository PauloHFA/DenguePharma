"""Relatorios Quarto, snapshots determinísticos e painéis acessíveis."""

from .provenance_and_snapshot import (
    ReportProvenance,
    ReportSnapshot,
    MissingProvenanceError,
    SnapshotIntegrityError,
    render_report,
    inspect_report_provenance,
    reproduce_report_from_snapshot,
)
from .executive_panels import (
    AxisPanelState,
    InvalidAxisError,
    get_axis_panel,
    EvaluationGoal,
    EvaluationReport,
    UnfavorableResultOmissionError,
    build_evaluation_report,
    SeriesSpec,
    AccessibleFigureSpec,
    InaccessibleFigureError,
)

__all__ = [
    "ReportProvenance",
    "ReportSnapshot",
    "MissingProvenanceError",
    "SnapshotIntegrityError",
    "render_report",
    "inspect_report_provenance",
    "reproduce_report_from_snapshot",
    "AxisPanelState",
    "InvalidAxisError",
    "get_axis_panel",
    "EvaluationGoal",
    "EvaluationReport",
    "UnfavorableResultOmissionError",
    "build_evaluation_report",
    "SeriesSpec",
    "AccessibleFigureSpec",
    "InaccessibleFigureError",
]
