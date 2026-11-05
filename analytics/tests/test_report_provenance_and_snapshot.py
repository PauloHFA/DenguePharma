"""
Testes de verificação formal para REQ-REL-001 e REQ-REL-002.
"""
from datetime import datetime, timezone
import pytest

from denguepharma_analytics.reports.provenance_and_snapshot import (
    ReportProvenance,
    ReportSnapshot,
    MissingProvenanceError,
    SnapshotIntegrityError,
    render_report,
    inspect_report_provenance,
    reproduce_report_from_snapshot,
)


@pytest.fixture
def valid_provenance():
    return ReportProvenance(
        sources=["ClinicalTrials.gov", "PubMed", "ChEMBL"],
        query_date="2026-10-27",
        versions={"pipeline": "0.42.0", "schema": "1.0.0"},
        filters={"cutoff_date": "2026-10-27", "serotype": "DENV-1", "phase": ["PHASE2", "PHASE3"]},
        evidence_status="revisado",
        limitations=[
            "Estudos observacionais excluídos do cálculo de eficácia primária",
            "Uso estrito em pesquisa acadêmica; não constitui prescrição médica individual",
        ],
    )


@pytest.fixture
def sample_records():
    return [
        {"trial_id": "NCT00000001", "substance": "Balapiravir", "phase": "PHASE2", "enrolled": 120},
        {"trial_id": "NCT00000002", "substance": "Celgosivir", "phase": "PHASE1b", "enrolled": 45},
        {"trial_id": "NCT00000003", "substance": "Chloroquine", "phase": "PHASE3", "enrolled": 300},
    ]


@pytest.mark.requirement("REQ-REL-001")
def test_all_reports_must_include_full_provenance(valid_provenance, sample_records):
    """
    ACC-REL-001: Dado um relatório gerado (PDF, CSV ou JSON), quando inspecionado,
    então todos esses itens estão presentes: fontes, data de consulta, versões,
    filtros, status da evidência e limitações.
    """
    snapshot = ReportSnapshot.create(
        snapshot_id="SNAP-20261027-001",
        created_at="2026-10-27T10:00:00Z",
        provenance=valid_provenance,
        raw_records=sample_records,
    )

    for fmt in ("json", "csv", "pdf"):
        report_bytes = render_report(snapshot, format=fmt)
        inspected = inspect_report_provenance(report_bytes, format=fmt)

        assert "sources" in inspected and inspected["sources"]
        assert "query_date" in inspected and inspected["query_date"]
        assert "versions" in inspected and inspected["versions"]
        assert "filters" in inspected
        assert "evidence_status" in inspected and inspected["evidence_status"]
        assert "limitations" in inspected and inspected["limitations"]

    # Valida falhas na ausência de campos mandatórios
    with pytest.raises(MissingProvenanceError):
        invalid_prov = ReportProvenance(
            sources=[],  # vazio
            query_date="2026-10-27",
            versions={"pipeline": "0.42.0"},
            filters={},
            evidence_status="revisado",
            limitations=["Limitação teste"],
        )
        invalid_prov.validate()

    with pytest.raises(MissingProvenanceError):
        invalid_prov = ReportProvenance(
            sources=["PubMed"],
            query_date="",  # vazio
            versions={"pipeline": "0.42.0"},
            filters={},
            evidence_status="revisado",
            limitations=["Limitação teste"],
        )
        invalid_prov.validate()

    with pytest.raises(MissingProvenanceError):
        invalid_prov = ReportProvenance(
            sources=["PubMed"],
            query_date="2026-10-27",
            versions={"pipeline": "0.42.0"},
            filters={},
            evidence_status="revisado",
            limitations=[],  # vazio
        )
        invalid_prov.validate()


@pytest.mark.requirement("REQ-REL-002")
def test_reproduce_report_from_snapshot_is_bit_identical(valid_provenance, sample_records):
    """
    ACC-REL-002: Dado um relatório de ontem, quando regenerado hoje a partir do
    ReportSnapshot, então o hash do conteúdo é exatamente igual.
    """
    snapshot_yesterday = ReportSnapshot.create(
        snapshot_id="SNAP-20261027-002",
        created_at="2026-10-27T14:30:00Z",
        provenance=valid_provenance,
        raw_records=sample_records,
    )

    for fmt in ("json", "csv", "pdf"):
        bytes_yesterday, hash_yesterday = reproduce_report_from_snapshot(snapshot_yesterday, format=fmt)

        # Simula passagem de tempo ("hoje") e fontes upstream modificadas com novos registros
        live_database = sample_records + [
            {"trial_id": "NCT99999999", "substance": "NovoComposto", "phase": "PHASE1", "enrolled": 10}
        ]

        # Regenera hoje a partir do snapshot
        bytes_today, hash_today = reproduce_report_from_snapshot(snapshot_yesterday, format=fmt)

        assert hash_today == hash_yesterday, f"Falha de determinismo no formato {fmt}"
        assert bytes_today == bytes_yesterday, f"Bytes divergentes no formato {fmt}"

    # Valida que adulteração nos registros internos do snapshot lança SnapshotIntegrityError
    snapshot_yesterday.raw_records.append({"trial_id": "ADULTERADO", "substance": "X"})
    with pytest.raises(SnapshotIntegrityError):
        render_report(snapshot_yesterday, format="json")

