"""Testes automatizados para Curadoria Humana, Triagem Duplo-Cega e Panorama de Estudos.

Cobre os requisitos finais do SDD:
- REQ-ANA-001 (ACC-ANA-001): Panorama agregando por study_id com soma de categorias igual ao total.
- REQ-REV-001 (ACC-REV-001): Curadoria lado a lado registrando antes, depois, autor, motivo e data/hora.
- REQ-REV-002 (ACC-REV-002): Bloqueio de publicação de campos críticos aprovados apenas por revisor.
- REQ-REV-003 (ACC-REV-003): Preservação de valores aprovados contra sobrescrita por extração de IA posterior.
- REQ-REV-004 (ACC-REV-004): Exclusão de rascunhos automáticos em exportações públicas.
- REQ-SEL-001 (ACC-SEL-001): Triagem independente por dois revisores gravando decisões separadas.
- REQ-SEL-002 (ACC-SEL-002): Ocultamento cego de decisões entre revisores e encaminhamento à adjudicação.
- REQ-SEL-003 (ACC-SEL-003): Proibição estrita de exclusão autônoma por IA (apenas priorização de leitura).
- REQ-SEL-005 (ACC-SEL-005): Preservação de artigos em paywall como 'somente resumo' e impacto na cobertura.
"""

import pytest
from denguepharma_analytics.clinical import (
    AiTriageRanker,
    ApprovedValueProtectionShield,
    AutonomousAiExclusionError,
    BlindDualScreeningWorkflow,
    CriticalFieldGatekeeper,
    DraftSanitizingExporter,
    PaywallCoverageAssessor,
    PublicationDeniedError,
    ReviewAction,
    ScreeningDecision,
    SideBySideReviewCurator,
    StudyOverviewRecord,
    StudyPanoramaGenerator,
)


def test_req_ana_001_study_panorama_counts_studies_and_consistent_sum():
    """ACC-ANA-001: Dado um conjunto de teste, quando agrupar por finalidade,

    então a soma das categorias é igual ao total de study_id.
    """
    generator = StudyPanoramaGenerator()

    # 4 estudos distintos (com múltiplos documentos associados a um mesmo estudo)
    studies_dataset = [
        StudyOverviewRecord(
            study_id="STUDY-001",
            substance="Celgosivir",
            purpose="TRATAMENTO",
            phase="PHASE1_PHASE2",
            design="RANDOMIZED_CONTROLLED_TRIAL",
            year=2014,
            country="Singapore",
            sponsor="SingHealth",
            document_ids=["DOC-001-A", "DOC-001-B"],
        ),
        StudyOverviewRecord(
            study_id="STUDY-002",
            substance="Balapiravir",
            purpose="TRATAMENTO",
            phase="PHASE2",
            design="RANDOMIZED_CONTROLLED_TRIAL",
            year=2012,
            country="Vietnam",
            sponsor="Roche",
            document_ids=["DOC-002-A"],
        ),
        StudyOverviewRecord(
            study_id="STUDY-003",
            substance="Chloroquine",
            purpose="PROFILAXIA",
            phase="PHASE3",
            design="DOUBLE_BLIND_RCT",
            year=2018,
            country="Brazil",
            sponsor="Fiocruz",
            document_ids=["DOC-003-A", "DOC-003-B", "DOC-003-C"],
        ),
        StudyOverviewRecord(
            study_id="STUDY-004",
            substance="Prednisolone",
            purpose="SINTOMATICO",
            phase="PHASE2",
            design="OPEN_LABEL",
            year=2013,
            country="Indonesia",
            sponsor="Ministry of Health",
            document_ids=["DOC-004-A"],
        ),
    ]

    res = generator.generate_panorama(studies_dataset)

    # Total de estudos é exatamente 4
    assert res["total_studies"] == 4
    assert res["denominator"] == 4

    # Soma das categorias por finalidade é estritamente igual ao total de study_id
    assert res["purpose_sum"] == 4
    assert res["is_sum_consistent"] is True
    assert res["by_purpose"] == {
        "TRATAMENTO": 2,
        "PROFILAXIA": 1,
        "SINTOMATICO": 1,
    }
    assert len(res["limitations"]) > 0


def test_req_rev_001_side_by_side_curation_records_audit_trail():
    """ACC-REV-001: Dado uma sugestão corrigida, quando salva,

    então o histórico mostra antes, depois, autor, motivo e hora.
    """
    curator = SideBySideReviewCurator()

    result = curator.review_field(
        field_name="primary_outcome",
        ai_suggestion="Clearance viral em 48h",
        source_quote="The primary endpoint was time to viral clearance, evaluated up to 72 hours.",
        action=ReviewAction.CORRIGIR,
        author_id="dr_silva_revisor",
        corrected_value="Clearance viral em 72h",
        reason="O trecho literal do protocolo explicita 72 horas e não 48 horas.",
    )

    assert result["field_name"] == "primary_outcome"
    assert result["before"] == "Clearance viral em 48h"
    assert result["after"] == "Clearance viral em 72h"
    assert result["author"] == "dr_silva_revisor"
    assert result["reason"] == "O trecho literal do protocolo explicita 72 horas e não 48 horas."
    assert result["timestamp"] is not None

    # Trilha de auditoria preserva os dados
    assert len(curator.audit_trail) == 1
    log = curator.audit_trail[0]
    assert log.before_value == "Clearance viral em 48h"
    assert log.after_value == "Clearance viral em 72h"
    assert log.author_id == "dr_silva_revisor"


def test_req_rev_002_critical_fields_require_adjudicator_approval():
    """ACC-REV-002: Dado um campo crítico aprovado só por um revisor,

    quando tentar publicar, então a publicação é negada.
    """
    gatekeeper = CriticalFieldGatekeeper()

    # Cenário 1: Campo crítico (primary_outcome) aprovado apenas por REVISOR comum
    fields_revisor_only = {
        "primary_outcome": {
            "value": "Redução de carga viral",
            "approver_role": "REVISOR",
        },
        "sample_size": {
            "value": 180,
            "approver_role": "REVISOR",
        },
    }

    with pytest.raises(PublicationDeniedError, match="Publicação Negada"):
        gatekeeper.validate_for_publication(fields_revisor_only)

    # Cenário 2: Campo crítico aprovado por ADJUDICADOR
    fields_with_adjudicator = {
        "primary_outcome": {
            "value": "Redução de carga viral",
            "approver_role": "ADJUDICADOR",
        },
        "sample_size": {
            "value": 180,
            "approver_role": "REVISOR",
        },
    }

    res = gatekeeper.validate_for_publication(fields_with_adjudicator)
    assert res["status"] == "APPROVED_FOR_PUBLICATION"


def test_req_rev_003_approved_value_protected_against_ai_overwrite():
    """ACC-REV-003: Dado um valor aprovado, quando nova extração divergir,

    então o valor aprovado permanece e a divergência vira alerta.
    """
    shield = ApprovedValueProtectionShield()

    # 1. Valor humano previamente aprovado
    shield.set_approved_value(
        field_key="trial_phase",
        value="PHASE2",
        approver="dr_costa_adjudicador",
    )

    # 2. Nova extração por modelo mais recente divergindo (sugere PHASE3)
    res = shield.apply_new_ai_extraction(
        field_key="trial_phase",
        new_ai_value="PHASE3",
        model_version="gemini-1.5-pro-v2",
    )

    # O valor aprovado permanece estritamente intacto
    assert res["active_value"] == "PHASE2"
    assert res["overwritten"] is False
    assert res["alert_generated"] is True

    # Alerta registrado na lista
    assert len(shield.divergence_alerts) == 1
    alert = shield.divergence_alerts[0]
    assert alert["field_key"] == "trial_phase"
    assert alert["approved_value"] == "PHASE2"
    assert alert["divergent_ai_value"] == "PHASE3"


def test_req_rev_004_drafts_sanitized_from_public_exports():
    """ACC-REV-004: Dado um rascunho, quando exportar o catálogo público,

    então ele não aparece.
    """
    mixed_records = [
        {"id": "REC-001", "name": "Balapiravir", "status": "APROVADO", "is_draft": False},
        {"id": "REC-002", "name": "Composto Y", "status": "RASCUNHO", "is_draft": True},
        {"id": "REC-003", "name": "Celgosivir", "status": "APROVADO", "is_draft": False},
        {"id": "REC-004", "name": "Extrato Z", "status": "AUTO_SUGGESTION", "is_draft": True},
    ]

    public_catalog = DraftSanitizingExporter.export_public_catalog(mixed_records)

    # Apenas os 2 registros formais aprovados constam na exportação pública
    assert len(public_catalog) == 2
    public_ids = [r["id"] for r in public_catalog]
    assert public_ids == ["REC-001", "REC-003"]
    assert "REC-002" not in public_ids
    assert "REC-004" not in public_ids


def test_req_sel_001_and_002_dual_blind_screening_and_conflict_escalation():
    """ACC-SEL-001 & ACC-SEL-002: Dado dois revisores, quando ambos decidirem,

    então as duas decisões ficam gravadas separadamente.
    Quando o segundo revisor abrir o item, a decisão do primeiro está oculta,
    e sob divergência o item é encaminhado para adjudicação.
    """
    workflow = BlindDualScreeningWorkflow()
    item_id = "STUDY-DEN-2024-09"

    # Revisor 1 submete sua decisão
    step1 = workflow.submit_decision(
        item_id=item_id,
        reviewer_id="rev_1_almeida",
        decision=ScreeningDecision.INCLUIR,
        reason="Ensaio clínico de fase 2 com critério de inclusão claro.",
    )
    assert step1["status"] == "WAITING_SECOND_REVIEWER"
    assert step1["both_completed"] is False

    # Revisor 2 abre o item para triagem: a decisão do Revisor 1 está oculta (cegamento)
    view_rev2 = workflow.get_item_for_review(item_id=item_id, reviewer_id="rev_2_souza")
    assert view_rev2["other_reviewer_decision"] == "MASKED_BLINDED"
    assert view_rev2["is_blinded"] is True

    # Revisor 2 submete decisão divergente
    step2 = workflow.submit_decision(
        item_id=item_id,
        reviewer_id="rev_2_souza",
        decision=ScreeningDecision.EXCLUIR,
        reason="População do estudo inclui co-infecção por Chikungunya sem separação.",
    )

    # Ambas as decisões estão gravadas separadamente
    assert step2["both_completed"] is True
    assert step2["is_divergent"] is True
    assert step2["status"] == "PENDING_ADJUDICATION"

    item_stored = workflow.items[item_id]
    assert item_stored["decision_1"].decision == ScreeningDecision.INCLUIR
    assert item_stored["decision_1"].reviewer_id == "rev_1_almeida"
    assert item_stored["decision_2"].decision == ScreeningDecision.EXCLUIR
    assert item_stored["decision_2"].reviewer_id == "rev_2_souza"


def test_req_sel_003_ai_model_cannot_autonomously_exclude_records():
    """ACC-SEL-003: Dado um modelo de priorização, quando a triagem terminar,

    então nenhum registro está 'excluído' sem decisão humana registrada.
    O modelo só pode ordenar a fila de leitura.
    """
    ranker = AiTriageRanker()

    items = [
        {"id": "ART-01", "title": "Estudo A"},
        {"id": "ART-02", "title": "Estudo B"},
        {"id": "ART-03", "title": "Estudo C"},
    ]
    scores = {"ART-01": 0.45, "ART-02": 0.95, "ART-03": 0.70}

    # Modelo reordena fila de leitura com sucesso
    ranked = ranker.rank_reading_queue(items, scores)
    assert ranked[0]["id"] == "ART-02"  # Maior score (0.95)
    assert ranked[0]["reading_priority_rank"] == 1
    assert ranked[1]["id"] == "ART-03"
    assert ranked[2]["id"] == "ART-01"

    # Tentativa de exclusão autônoma por IA é rejeitada
    with pytest.raises(AutonomousAiExclusionError, match="não pode excluir o item"):
        ranker.attempt_autonomous_exclusion(item_id="ART-01", model_decision="EXCLUIR")


def test_req_sel_005_paywalled_articles_preserved_and_coverage_reported():
    """ACC-SEL-005: Dado um artigo atrás de paywall, quando triado,

    então não é excluído e aparece no relatório de cobertura.
    """
    assessor = PaywallCoverageAssessor()

    doc_paywalled = assessor.assess_document(
        doc_id="DOC-LANCET-2023",
        title="Antiviral Treatment for Dengue Fever in Adults",
        is_paywalled=True,
        abstract_available=True,
    )

    # Não é excluído
    assert doc_paywalled["is_excluded"] is False
    assert doc_paywalled["screening_status"] == "SOMENTE_RESUMO"
    assert "resumo" in doc_paywalled["impact_statement"]

    # Relatório de cobertura documental
    docs_collection = [
        {"id": "D1", "is_paywalled": False},
        {"id": "D2", "is_paywalled": True},
        {"id": "D3", "is_paywalled": False},
        {"id": "D4", "is_paywalled": True},
    ]

    report = assessor.generate_coverage_report(docs_collection)
    assert report["total_documents"] == 4
    assert report["paywalled_count"] == 2
    assert report["fulltext_available_count"] == 2
    assert report["paywall_impact_percentage"] == 50.0
    assert len(report["declarations"]) == 1
    assert "SOMENTE_RESUMO" in report["declarations"][0]
