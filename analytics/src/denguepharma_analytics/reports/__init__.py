"""Relatorios Quarto, snapshots determinísticos e painéis acessíveis."""

from .executive_panels import (
    AccessibleFigureSpec,
    AxisPanelState,
    EvaluationGoal,
    EvaluationReport,
    InaccessibleFigureError,
    InvalidAxisError,
    SeriesSpec,
    UnfavorableResultOmissionError,
    build_evaluation_report,
    get_axis_panel,
)
from .provenance_and_snapshot import (
    MissingProvenanceError,
    ReportProvenance,
    ReportSnapshot,
    SnapshotIntegrityError,
    inspect_report_provenance,
    render_report,
    reproduce_report_from_snapshot,
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
