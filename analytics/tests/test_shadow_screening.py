"""Testes de conformidade e salvaguardas para o Shadow Screening consultivo por IA (Melhoria 5)."""
import copy
import json
import pytest

from denguepharma_analytics.clinical.models import Principal
from denguepharma_analytics.clinical.shadow_screening import evaluate_study_shadow, get_shadow_recommendation
from test_clinical import workspace, R1, R2, ADJ, screen, CLASSIFICATION


@pytest.mark.requirement("REQ-SEL-002")
def test_shadow_screening_evaluates_clinical_trial_as_include():
    docs = [
        {
            "documentId": "doc-balapiravir",
            "title": "Randomized, double-blind, placebo-controlled trial of Balapiravir in adult patients with acute dengue",
            "metadata": {
                "abstract": "We conducted a phase 2 randomized trial evaluating Balapiravir versus placebo in 100 adult dengue patients. Clinical endpoints were evaluated at day 7.",
            },
        }
    ]
    report = evaluate_study_shadow("study-1", docs, "a" * 64)
    assert report["recommendation"] == "INCLUIR"
    assert report["confidence_level"] == "ALTA"
    assert "BALAPIRAVIR" in report["suggested_classification"]["interventions"]
    assert report["suggested_classification"]["established_dengue"] == "SIM"
    assert report["suggested_classification"]["design"] == "RCT_PARALELO"
    assert report["safeguards"]["rc01_no_efficacy_ranking"] is True
    assert report["safeguards"]["rc02_human_only_safeguard"] is True
    assert report["safeguards"]["rc07_human_adjudication_mandatory"] is True
    assert "PARECER CONSULTIVO" in report["disclaimer"]
    assert len(report["evidence_quotes"]) > 0


@pytest.mark.requirement("REQ-SEL-002")
def test_shadow_screening_evaluates_in_vitro_and_animal_as_exclude():
    docs = [
        {
            "documentId": "doc-invitro",
            "title": "Inhibition of dengue virus replication by novel compound in Vero cells and murine model",
            "metadata": {
                "abstract": "In vitro testing in Vero cell culture showed IC50 of 2.1 uM. Murine animal model showed reduced viremia. No human clinical data available.",
            },
        }
    ]
    report = evaluate_study_shadow("study-invitro", docs, "b" * 64)
    assert report["recommendation"] == "EXCLUIR"
    assert report["confidence_level"] == "ALTA"
    assert "Salvaguarda RC-02" in report["rationale"]
    assert "in vitro" in report["rationale"].lower() or "animal" in report["rationale"].lower()


@pytest.mark.requirement("REQ-SEL-002")
def test_shadow_screening_evaluates_vector_and_vaccine_as_exclude():
    docs = [
        {
            "documentId": "doc-vector",
            "title": "Community application of Bacillus thuringiensis larvicide for Aedes aegypti vector control",
            "metadata": {
                "abstract": "Field trial evaluating larvicide distribution in water tanks for dengue mosquito vector control.",
            },
        }
    ]
    report = evaluate_study_shadow("study-vector", docs, "c" * 64)
    assert report["recommendation"] == "EXCLUIR"
    assert "vetorial" in report["rationale"].lower() or "vacina" in report["rationale"].lower()


@pytest.mark.requirement("REQ-SEL-002")
def test_shadow_screening_blinded_from_reviewers_and_visible_only_to_adjudicator(workspace):
    # Inicialmente, estudo sem triagem: status PENDENTE
    q_r1 = workspace.queue(R1)
    row_r1 = next(r for r in q_r1 if r["study_id"] == "s1")
    assert row_r1["adjudication"] is None

    # R1 vota INCLUIR, R2 vota EXCLUIR -> cria CONFLITO
    screen(workspace, R1, study="s1", decision="INCLUIR")
    screen(workspace, R2, study="s1", decision="EXCLUIR")

    # Revisor R1 ainda tem cegamento: NÃO vê adjudication nem shadow_screening
    q_r1_after = workspace.queue(R1)
    row_r1_after = next(r for r in q_r1_after if r["study_id"] == "s1")
    assert row_r1_after["status"] == "CONFLITO"
    assert row_r1_after["adjudication"] is None

    # Adjudicador ADJ vê o conflito E recebe o parecer consultivo de IA (Shadow Screening)
    q_adj = workspace.queue(ADJ)
    row_adj = next(r for r in q_adj if r["study_id"] == "s1")
    assert row_adj["status"] == "CONFLITO"
    assert row_adj["adjudication"] is not None
    assert "votes_hash" in row_adj["adjudication"]
    assert len(row_adj["adjudication"]["votes"]) == 2

    shadow = row_adj["adjudication"]["shadow_screening"]
    assert shadow is not None
    assert shadow["study_id"] == "s1"
    assert shadow["recommendation"] in {"INCLUIR", "EXCLUIR", "INCERTO"}
    assert shadow["safeguards"]["is_advisory_only"] is True

    # O Adjudicador pode decidir soberanamente (mesmo divergindo do parecer consultivo)
    payload = dict(
        study_id="s1",
        basis_hash=row_adj["basis_hash"],
        votes_hash=row_adj["adjudication"]["votes_hash"],
        decision="EXCLUIR",
        classification=CLASSIFICATION,
        reason="Decisao soberana humana do adjudicador conforme protocolo clinico",
    )
    workspace.act("SCREEN_ADJUDICATED", payload, ADJ)

    # Estado final resolvido após adjudicação
    q_final = workspace.queue(ADJ)
    row_final = next(r for r in q_final if r["study_id"] == "s1")
    assert row_final["status"] == "EXCLUIR"
    assert row_final["adjudication"] is None

