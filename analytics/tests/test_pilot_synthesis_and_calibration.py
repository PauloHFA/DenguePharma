"""
Testes de verificação formal para REQ-CLN-006 (ACC-CLN-006).
Calibração da busca clínica, revisão independente do piloto metodológico,
seleção do corpus final e publicação da síntese clínica real.
"""
from pathlib import Path
import pytest

from denguepharma_analytics.clinical.pilot_synthesis_and_calibration import (
    ClinicalGovernanceError,
    UnreviewedStudyError,
    UnapprovedCalibrationError,
    SearchCalibrator,
    PilotMethodologicalReviewer,
    FinalCorpusSelector,
    RealClinicalSynthesisPublisher,
)

PILOT_CSV = Path(__file__).resolve().parents[2] / "backend" / "target" / "runtime" / "piloto-ds3" / "pilot_review.csv"


@pytest.fixture
def sample_raw_documents():
    return [
        {"document_id": "DOC-SENTINEL-1", "title": "Clinical Trial of Chloroquine in Acute Dengue Fever"},
        {"document_id": "DOC-SENTINEL-2", "title": "Safety and Efficacy of AV-1 Antiviral Against Dengue Infection"},
        {"document_id": "DOC-NOISE-1", "title": "Aedes aegypti vector control using larvicide"},
        {"document_id": "DOC-NOISE-2", "title": "Phase 3 trial of tetravalent dengue vaccine (TDV)"},
        {"document_id": "DOC-NOISE-3", "title": "In vitro screening of small molecules against NS5"},
        {"document_id": "DOC-NOISE-4", "title": "Epidemiology and clinical features of dengue: a narrative review"},
    ]


@pytest.mark.requirement("REQ-CLN-006")
def test_search_calibration_detects_noise_and_requires_adjudicator(sample_raw_documents):
    """
    ACC-CLN-006: Calibra busca clínica e exige aprovação formal de adjudicador.
    """
    sentinels = ["DOC-SENTINEL-1", "DOC-SENTINEL-2"]

    # Calibração sem aprovação formal de adjudicador
    calib_unapproved = SearchCalibrator.calibrate(sample_raw_documents, sentinels)
    assert calib_unapproved.sentinel_recall == 1.0
    assert calib_unapproved.is_approved is False
    assert calib_unapproved.noise_signals_detected["CONTROLE_VETORIAL"] == 1
    assert calib_unapproved.noise_signals_detected["IMUNIZACAO_VACINAL"] == 1
    assert calib_unapproved.noise_signals_detected["PRE_CLINICO_IN_VITRO"] == 1
    assert calib_unapproved.noise_signals_detected["EPIDEMIOLOGICO_OU_REVISAO"] == 1

    with pytest.raises(UnapprovedCalibrationError):
        calib_unapproved.validate_for_publication()

    # Calibração com aprovação por adjudicador
    calib_approved = SearchCalibrator.calibrate(
        sample_raw_documents,
        sentinels,
        adjudicator="adjudicador.chefe@denguepharma.org",
        approval_reason="Busca clínica calibrada: ruídos de vacina e vetor filtrados com 100% de recall nos sentinelas.",
    )
    assert calib_approved.is_approved is True
    calib_approved.validate_for_publication()

    # Se um sentinela for omitido da busca, calibração falha
    calib_failing = SearchCalibrator.calibrate(
        sample_raw_documents,
        sentinels + ["DOC-SENTINEL-MISSING"],
        adjudicator="adjudicador.chefe@denguepharma.org",
        approval_reason="Tentativa com sentinela ausente",
    )
    assert calib_failing.sentinel_recall < 1.0
    with pytest.raises(ClinicalGovernanceError, match="Recall de sentinelas insuficiente"):
        calib_failing.validate_for_publication()


@pytest.mark.requirement("REQ-CLN-006")
def test_pilot_methodological_review_and_final_corpus_selection():
    """
    ACC-CLN-006: Revisão independente do piloto metodológico e seleção do corpus final.
    """
    assert PILOT_CSV.exists(), f"Arquivo do piloto deve existir em {PILOT_CSV}"

    summary = PilotMethodologicalReviewer.load_from_csv(PILOT_CSV)

    assert summary.total_screened == 50
    assert summary.included_count == 6  # 6 ensaios/estudos farmacológicos candidatos incluídos
    assert summary.excluded_count == 44
    assert len(summary.reviewers) >= 1
    assert "revisor.metodologico@denguepharma.org" in summary.reviewers

    # Verifica discriminação explícita de motivos de exclusão (sem decisão cega/oculta)
    assert "IMUNIZACAO_VACINAL" in summary.reasons_breakdown or "INTERVENCAO_NAO_ELEGIVEL" in summary.reasons_breakdown
    assert summary.screening_hash and len(summary.screening_hash) == 64

    # Seleção do corpus final
    final_corpus = FinalCorpusSelector.select(summary)
    assert final_corpus.total_included == 6
    included_ids = {s["document_id"] for s in final_corpus.included_studies}

    # Verifica os estudos candidatos selecionados
    assert "16b999a1-1a95-4f7f-8fc1-0f255bb12264" in included_ids  # AV-1
    assert "1a6d61df-10a7-4185-adc8-046c3c62cee3" in included_ids  # Emetine
    assert "39ce0f31-7c69-48b1-92b7-82de65adeb88" in included_ids  # Chloroquine
    assert "55837751-b15b-4210-8528-3b87097631c7" in included_ids  # Andi-d
    assert "93c6aee0-1322-463b-b7e2-ce60996a15da" in included_ids  # Viral Dynamic Model
    assert "9cb08258-e2c7-4cb4-8165-8d3005bfe170" in included_ids  # Clinical Trial Phase 1/2


@pytest.mark.requirement("REQ-CLN-006")
def test_real_clinical_synthesis_publication_with_human_conclusions(sample_raw_documents):
    """
    ACC-CLN-006: Publicação da síntese clínica real subordinada a julgamento humano documentado.
    """
    summary = PilotMethodologicalReviewer.load_from_csv(PILOT_CSV)
    final_corpus = FinalCorpusSelector.select(summary)

    calib = SearchCalibrator.calibrate(
        sample_raw_documents,
        ["DOC-SENTINEL-1", "DOC-SENTINEL-2"],
        adjudicator="adjudicador.chefe@denguepharma.org",
        approval_reason="Calibração clínica auditada e aprovada.",
    )

    # Conclusões humanas documentadas para todos os 6 estudos do corpus final
    human_conclusions = [
        {
            "document_id": "16b999a1-1a95-4f7f-8fc1-0f255bb12264",
            "study_label": "AV-1 Antiviral",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Ensaio de fase inicial com tamanho amostral reduzido; dados preliminares insuficientes para firmar benefício sustentado.",
            "clinical_importance": "Intervenção antiviral promissora que requer confirmação em fase confirmatória.",
            "uncertainty": "Incerteza moderada a alta devido a intervalo de confiança amplo no endpoint primário.",
        },
        {
            "document_id": "1a6d61df-10a7-4185-adc8-046c3c62cee3",
            "study_label": "Emetine (EVOLVE Initiative)",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Atividade inibitória demonstrada, porém desfechos clínicos heterogêneos sem separação nítida de braços.",
            "clinical_importance": "Potencial reposicionamento necessita de monitoramento rigoroso de segurança cardiovascular.",
            "uncertainty": "Incerteza alta decorrente de desfechos sub-rogados.",
        },
        {
            "document_id": "39ce0f31-7c69-48b1-92b7-82de65adeb88",
            "study_label": "Chloroquine Clinical Trial",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Ausência de redução estatisticamente significativa na duração da viremia ou tempo até defervescência frente a controle.",
            "clinical_importance": "Cloroquina não demonstrou benefício terapêutico substantivo em dengue aguda.",
            "uncertainty": "Incerteza baixa quanto à ineficácia; ensaio clínico controlado bem delineado.",
        },
        {
            "document_id": "55837751-b15b-4210-8528-3b87097631c7",
            "study_label": "Andi-d Pilot Study",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Estudo piloto de conveniência com poder estatístico limitado para desfechos clínicos duros.",
            "clinical_importance": "Dados exploratórios preliminares sem validação externa.",
            "uncertainty": "Incerteza muito alta.",
        },
        {
            "document_id": "93c6aee0-1322-463b-b7e2-ce60996a15da",
            "study_label": "Viral Dynamic Model Selection",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Estudo farmacocinético/farmacodinâmico modelado informando seleção de dose, sem desfecho clínico direto de cura.",
            "clinical_importance": "Útil para planejamento posológico de ensaios futuros.",
            "uncertainty": "Incerteza alta para desfechos clínicos.",
        },
        {
            "document_id": "9cb08258-e2c7-4cb4-8165-8d3005bfe170",
            "study_label": "Clinical Trial NCT06917001",
            "category": "EVIDENCIA_INCONCLUSIVA",
            "rationale": "Estudo em andamento com recrutamento ativo; dados cegados sem análise interina autorizada.",
            "clinical_importance": "Aguardar conclusão formal e quebra de mascaramento.",
            "uncertainty": "Incerteza total sobre eficácia enquanto mascarado.",
        },
    ]

    # Publicação bem-sucedida quando todos os requisitos estão atendidos
    synthesis = RealClinicalSynthesisPublisher.publish(
        corpus=final_corpus,
        calibration=calib,
        conclusions=human_conclusions,
        publisher_adjudicator="adjudicador.chefe@denguepharma.org",
        published_at="2026-11-05T03:00:00Z",
    )

    assert synthesis.synthesis_id.startswith("SYNTHESIS-REAL-")
    assert synthesis.synthesis_hash and len(synthesis.synthesis_hash) == 64
    assert len(synthesis.conclusions) == 6

    # Falha se faltar conclusão humana para qualquer estudo do corpus
    with pytest.raises(UnreviewedStudyError):
        RealClinicalSynthesisPublisher.publish(
            corpus=final_corpus,
            calibration=calib,
            conclusions=human_conclusions[:5],  # Faltando 1 estudo
            publisher_adjudicator="adjudicador.chefe@denguepharma.org",
            published_at="2026-11-05T03:00:00Z",
        )

    # Falha se categoria clínica for inválida
    invalid_conclusions = [dict(c) for c in human_conclusions]
    invalid_conclusions[0]["category"] = "EFICACIA_MAGICA_AUTOMATICA"
    with pytest.raises(ClinicalGovernanceError, match="Categoria clínica inválida"):
        RealClinicalSynthesisPublisher.publish(
            corpus=final_corpus,
            calibration=calib,
            conclusions=invalid_conclusions,
            publisher_adjudicator="adjudicador.chefe@denguepharma.org",
            published_at="2026-11-05T03:00:00Z",
        )
