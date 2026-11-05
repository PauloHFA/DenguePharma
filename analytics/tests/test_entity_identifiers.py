"""Testes unitários para identificadores de entidades, desambiguação e deduplicação clínica.

Cobre os requisitos:
- REQ-IDN-001 (ACC-IDN-001): Resolução de discrepâncias NCT / PMID / PMCID / DOI e bloqueio de fusão.
- REQ-IDN-002 (ACC-IDN-002): Limiar de certeza em vínculos de documentos e desfazimento auditado.
- REQ-IDN-003 (ACC-IDN-003): Normalização ontológica e separação de monoterapias vs combinações.
- REQ-IDN-004 (ACC-IDN-004): Agrupamento sob study_id e deduplicação de contagem de participantes.
"""

import pytest
from denguepharma_analytics.clinical import (
    DocumentIdentifiers,
    DocumentStudyLinkManager,
    IdentifierDiscrepancyResolver,
    LinkStatus,
    StudyDocumentReport,
    StudyParticipantAggregator,
    SubstanceEntity,
    SubstanceNormalizer,
)


def test_req_idn_001_complementary_identifiers_and_discrepancy_resolution():
    """ACC-IDN-001: Dois documentos com o mesmo DOI mas com NCTs distintos geram status DIVERGENT

    e impedem a fusão automática sem intervenção humana.
    """
    resolver = IdentifierDiscrepancyResolver()

    # Cenário 1: Mesmo DOI com NCTs conflitantes
    doc_a = DocumentIdentifiers(
        doc_id="DOC-001",
        doi="10.1016/j.antiviral.2020.104763",
        nct="NCT01234567",
        pmid="32000001",
    )
    doc_b = DocumentIdentifiers(
        doc_id="DOC-002",
        doi="https://doi.org/10.1016/j.antiviral.2020.104763",  # Mesmo DOI em formato URL
        nct="NCT09999999",  # NCT conflitante
        pmid="32000001",
    )

    res_conflict = resolver.resolve(doc_a, doc_b)
    assert res_conflict["status"] == LinkStatus.DIVERGENT
    assert res_conflict["auto_merge_allowed"] is False
    assert res_conflict["requires_human_review"] is True
    assert len(res_conflict["divergences"]) > 0
    assert "conflitantes" in res_conflict["divergences"][0]

    # Cenário 2: Documentos consistentes (mesmo NCT e mesmo DOI)
    doc_c = DocumentIdentifiers(
        doc_id="DOC-003",
        doi="10.1016/j.antiviral.2020.104763",
        nct="NCT01234567",
        pmid="32000001",
    )
    res_match = resolver.resolve(doc_a, doc_c)
    assert res_match["status"] == LinkStatus.AUTO_LINKED
    assert res_match["auto_merge_allowed"] is True
    assert res_match["requires_human_review"] is False
    assert res_match["shared_identifiers"]["nct"] == "NCT01234567"

    # Cenário 3: Identificadores complementares distintos sem match suficiente
    doc_d = DocumentIdentifiers(doc_id="DOC-004", doi="10.1001/jama.2021.001", nct="NCT00000001")
    doc_e = DocumentIdentifiers(doc_id="DOC-005", doi="10.1002/art.2022.002", nct="NCT00000002")
    res_pending = resolver.resolve(doc_d, doc_e)
    assert res_pending["status"] == LinkStatus.PENDING_HUMAN_CONFIRMATION
    assert res_pending["auto_merge_allowed"] is False
    assert res_pending["requires_human_review"] is True


def test_req_idn_002_link_confidence_threshold_and_audited_undo():
    """ACC-IDN-002: Confiança de vínculo abaixo do limiar exige confirmação humana

    e qualquer fusão/vínculo pode ser desfeito auditadamente restaurando o estado anterior.
    """
    manager = DocumentStudyLinkManager(confidence_threshold=0.85)

    # 1. Tentativa de vínculo com confiança baixa (0.70 < 0.85)
    low_conf_result = manager.link_document(
        doc_id="PUBMED-987654",
        study_id="STUDY-DEN-001",
        confidence=0.70,
        actor="heuristics_engine",
        reason="Vínculo por correspondência de título parcial",
    )
    assert low_conf_result["status"] == LinkStatus.PENDING_HUMAN_CONFIRMATION
    assert low_conf_result["study_id"] is None
    assert low_conf_result["requires_human_confirmation"] is True
    assert "PUBMED-987654" not in manager.links

    # 2. Confirmação humana explícita
    confirm_result = manager.confirm_link(
        doc_id="PUBMED-987654",
        study_id="STUDY-DEN-001",
        reviewer_id="rev_senior_dr_alves",
        notes="Confirmado por cruzamento do número de protocolo no apêndice.",
    )
    assert confirm_result["status"] == LinkStatus.HUMAN_CONFIRMED
    assert manager.links["PUBMED-987654"] == "STUDY-DEN-001"

    # 3. Vínculo automático de alta confiança (0.95 >= 0.85)
    high_conf_result = manager.link_document(
        doc_id="PUBMED-112233",
        study_id="STUDY-DEN-002",
        confidence=0.95,
        actor="exact_nct_matcher",
    )
    assert high_conf_result["status"] == LinkStatus.AUTO_LINKED
    assert high_conf_result["study_id"] == "STUDY-DEN-002"
    assert manager.links["PUBMED-112233"] == "STUDY-DEN-002"

    # 4. Desfazer auditado (undo_link)
    undo_result = manager.undo_link(
        doc_id="PUBMED-112233",
        reviewer_id="rev_curator_marta",
        reason="Artigo trata de estudo de fase 1 separado com mesmo patrocinador.",
    )
    assert undo_result["status"] == LinkStatus.UNLINKED
    assert undo_result["previous_study_id"] == "STUDY-DEN-002"
    assert "PUBMED-112233" not in manager.links

    # 5. Validação da integridade da trilha de auditoria
    audit = manager.audit_log
    assert len(audit) == 4
    assert audit[-1].action == "UNDO_LINK"
    assert audit[-1].actor == "rev_curator_marta"
    assert audit[-1].previous_state["study_id"] == "STUDY-DEN-002"


def test_req_idn_003_substance_normalization_and_combination_isolation():
    """ACC-IDN-003: Substâncias mapeadas em ontologias (PubChem/ChEMBL)

    e combinações de drogas tratadas como entidades separadas sem fusão às monoterapias.
    """
    normalizer = SubstanceNormalizer()

    # Monoterapia: Artesunato com alias em português
    art_pt = normalizer.normalize("artesunato")
    assert art_pt.canonical_name == "Artesunate"
    assert art_pt.pubchem_cid == 6917864
    assert art_pt.chembl_id == "CHEMBL37072"
    assert art_pt.is_combination is False

    # Monoterapia: Amodiaquina
    amod = normalizer.normalize("Amodiaquine")
    assert amod.canonical_name == "Amodiaquine"
    assert amod.pubchem_cid == 2165
    assert amod.chembl_id == "CHEMBL697"
    assert amod.is_combination is False

    # Combinação 'Artesunate + Amodiaquine' NÃO deve ser fundida à monoterapia 'Artesunate'
    combo = normalizer.normalize("Artesunate + Amodiaquine")
    assert combo.is_combination is True
    assert set(combo.components) == {"Amodiaquine", "Artesunate"}
    assert combo.canonical_name == "Amodiaquine + Artesunate"
    assert combo.canonical_name != art_pt.canonical_name
    assert combo.canonical_name != amod.canonical_name

    # Combinação com aliases e formato 'e' ou '/'
    combo_pt = normalizer.normalize("artesunato / amodiaquina")
    assert combo_pt.is_combination is True
    assert set(combo_pt.components) == {"Amodiaquine", "Artesunate"}
    assert combo_pt.canonical_name == "Amodiaquine + Artesunate"

    # Outro exemplo: Cloroquina
    cloro = normalizer.normalize("cloroquina")
    assert cloro.canonical_name == "Chloroquine"
    assert cloro.pubchem_cid == 2719


def test_req_idn_004_participant_deduplication_under_study_id():
    """ACC-IDN-004: Agrupamento sob study_id garante que registros de ensaios, publicações

    primárias e artigos de seguimento deduplicam o N amostral e impedem inflação.
    """
    aggregator = StudyParticipantAggregator()
    study_id = "STUDY-CELGOSIVIR-01"

    # 1. Registro no ClinicalTrials.gov (N planejado/recrutado: 180)
    doc_registry = StudyDocumentReport(
        doc_id="NCT01614964",
        doc_type="trial_registry",
        n_enrolled=180,
    )
    # 2. Artigo principal na revista médica (N randomizado: 180, N completado: 172)
    doc_primary = StudyDocumentReport(
        doc_id="PMID-24831813",
        doc_type="primary_publication",
        n_enrolled=180,
        n_completed=172,
        published_year=2014,
    )
    # 3. Artigo de seguimento de cinética viral secundária (mesmos 180 pacientes avaliados)
    doc_followup = StudyDocumentReport(
        doc_id="PMID-25987654",
        doc_type="follow_up",
        n_enrolled=180,
        n_completed=170,
        published_year=2015,
    )

    aggregator.add_document(study_id, doc_registry)
    aggregator.add_document(study_id, doc_primary)
    aggregator.add_document(study_id, doc_followup)

    result = aggregator.aggregate_study_sample_size(study_id)

    # Verificação de prevenção de inflação amostral
    # Soma ingênua: 180 + 180 + 180 = 540 pacientes (inflação de 360 pacientes)
    assert result["naive_sum_sample_size"] == 540
    # Tamanho deduplicado sob study_id: exatamente 180 pacientes reais
    assert result["deduplicated_sample_size"] == 180
    assert result["inflation_prevented"] == 360
    assert result["n_documents"] == 3

