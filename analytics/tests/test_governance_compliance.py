"""
Testes de verificação formal para REQ-GOV-004, REQ-GOV-005 e REQ-GOV-006.
- REQ-GOV-004 (ACC-GOV-004): Sanitização e varredura do pacote público sem segredos nem textos sem licença (T9).
- REQ-GOV-005 (ACC-GOV-005): Exibição compulsória de aviso de uso em pesquisa e ausência de recomendação clínica.
- REQ-GOV-006 (ACC-GOV-006): Congelamento de protocolo e plano estatístico por commit prévio ao teste final.
"""
from datetime import datetime, timezone
import pytest

from denguepharma_analytics.clinical.governance_compliance import (
    SecretLeakError,
    PIILeakError,
    UnlicensedContentLeakError,
    MissingClinicalNoticeError,
    UnfrozenProtocolExecutionError,
    scan_public_package,
    PublicPackageSanitizer,
    EvidenceNoticeValidator,
    ProtocolFreezeManager,
)


# ============================================================================
# REQ-GOV-004: Sanitização e Varredura do Pacote Público (ACC-GOV-004 / T9)
# ============================================================================

@pytest.mark.requirement("REQ-GOV-004")
def test_public_package_sanitization_and_scanner_catches_secrets_and_unlicensed_content():
    """
    ACC-GOV-004: Dado o pacote gerado, quando varrido, então não há segredos nem texto sem licença (T9).
    """
    raw_docs = [
        {
            "document_id": "DOC-OPEN-01",
            "document_type": "PUBLICACAO",
            "identifiers": ["PMID:42572208", "DOI:10.1002/cpt.70439"],
            "content_hash": "a" * 64,
            "license": "CC-BY-4.0",
            "title": "Open Access Dengue Pharmacology Study",
            "full_text": "Texto científico integral com permissão de redistribuição aberta.",
        },
        {
            "document_id": "DOC-CLOSED-02",
            "document_type": "PUBLICACAO",
            "identifiers": ["PMID:41586633"],
            "content_hash": "b" * 64,
            "license": "CLOSED",
            "title": "Closed Access Proprietary Study",
            "full_text": "Conteúdo proprietário comercial restrito sob copyright da editora.",
        },
    ]

    metrics = {
        "total_screened": 50,
        "eligible_trials": 6,
        "proportion_open_access": 0.5,
    }

    # 1. Sanitização
    sanitized = PublicPackageSanitizer.sanitize(raw_docs, metrics)

    # Valida preservação de identificadores, hashes e métricas
    assert sanitized["identifiers_count"] == 2
    assert sanitized["metrics"]["eligible_trials"] == 6

    docs = {d["document_id"]: d for d in sanitized["documents"]}
    # Documento CC-BY preserva full_text
    assert "full_text" in docs["DOC-OPEN-01"]
    # Documento CLOSED teve o full_text omitido
    assert "full_text" not in docs["DOC-CLOSED-02"]

    # 2. Scanner em pacote sanitizado aprova conformidade
    scan_result = scan_public_package(sanitized)
    assert scan_result.is_clean is True
    assert scan_result.total_elements_scanned > 10

    # 3. Scanner detecta vazamento de chave secreta / token
    leaky_package_secret = dict(sanitized)
    leaky_package_secret["api_secret_key"] = "sk-abcdef12345678901234567890"
    with pytest.raises(SecretLeakError, match="Segredos detectados"):
        scan_public_package(leaky_package_secret)

    # 4. Scanner detecta marcador de fulltext privado
    leaky_marker = {"documents": [{"id": "D1", "notes": "Contém PRIVATE_FULLTEXT não filtrado"}]}
    with pytest.raises(SecretLeakError, match="Marcador de conteúdo privado"):
        scan_public_package(leaky_marker)

    # 5. Scanner detecta vazamento de PII (email pessoal)
    leaky_package_pii = {"contact_info": {"patient_email": "paciente.silva@hospital.com.br"}}
    with pytest.raises(PIILeakError, match="Dados pessoais detectados"):
        scan_public_package(leaky_package_pii)

    # 6. Scanner detecta texto com licença restritiva
    unlicensed_package = {
        "documents": [
            {
                "license": "CLOSED",
                "text": "Texto integral publicado sem autorização legal de licença aberta",
            }
        ]
    }
    with pytest.raises(UnlicensedContentLeakError, match="Texto sem licença aberta"):
        scan_public_package(unlicensed_package)


# ============================================================================
# REQ-GOV-005: Aviso de Uso em Pesquisa em Telas e Relatórios (ACC-GOV-005)
# ============================================================================

@pytest.mark.requirement("REQ-GOV-005")
def test_evidence_screen_and_reports_must_display_mandatory_clinical_notice():
    """
    ACC-GOV-005: Dado qualquer tela de evidência, quando aberta, então o aviso está visível.
    """
    valid_view = {
        "screen_id": "VIEW-EVIDENCE-SYNTHESIS",
        "title": "Síntese Clínica de Tratamentos para Dengue",
        "notice": (
            "Uso estrito em pesquisa acadêmica. As informações catalogadas "
            "não constituem prescrição médica nem recomendação clínica individual."
        ),
        "results": [{"compound": "Balapiravir", "status": "EVIDENCIA_INCONCLUSIVA"}],
    }

    # Validação bem-sucedida em tela com aviso completo
    assert EvidenceNoticeValidator.validate_view_notice(valid_view) is True

    # Falha se aviso estiver ausente
    invalid_view_no_notice = {
        "screen_id": "VIEW-INVALID",
        "title": "Tela sem aviso",
        "results": [],
    }
    with pytest.raises(MissingClinicalNoticeError, match="Aviso obrigatório ausente"):
        EvidenceNoticeValidator.validate_view_notice(invalid_view_no_notice)

    # Falha se omitir a cláusula de não-recomendação individual
    partial_notice_view = {
        "screen_id": "VIEW-PARTIAL",
        "notice": "Uso em pesquisa farmacológica apenas.",  # Faltando cláusula de ausência de recomendação individual
    }
    with pytest.raises(MissingClinicalNoticeError, match="ausência de recomendação individual"):
        EvidenceNoticeValidator.validate_view_notice(partial_notice_view)

    # Auto-anexo de aviso padronizado
    attached_view = EvidenceNoticeValidator.attach_notice(invalid_view_no_notice)
    assert attached_view["research_notice"]["is_visible"] is True
    # Valida texto do aviso anexado
    assert EvidenceNoticeValidator.validate_view_notice(attached_view["research_notice"]["text"]) is True


# ============================================================================
# REQ-GOV-006: Congelamento de Protocolo e Plano Estatístico (ACC-GOV-006)
# ============================================================================

@pytest.mark.requirement("REQ-GOV-006")
def test_protocol_and_statistical_plan_frozen_before_final_test():
    """
    ACC-GOV-006: Dado o teste final, quando iniciado, então existe um commit
    do plano com data anterior ao início do teste.
    """
    protocol_spec = {
        "code": "PROTOCOLO-DENGUE-2026",
        "design": "SISTEMATICO_INTERVENCIONAL",
        "pico": {
            "population": "Pacientes com dengue aguda confirmada",
            "intervention": "Antivirais e imunomoduladores farmacológicos",
            "comparator": "Placebo ou tratamento suporte padrão",
            "outcomes": ["tempo_defervescencia", "reducao_carga_viral", "eventos_adversos_graves"],
        },
    }

    statistical_plan = {
        "primary_analysis": "Diferença padronizada de médias e Risco Relativo",
        "meta_regression": "DerSimonian-Laird com correção de Knapp-Hartung",
        "alpha_significance": 0.05,
        "cluster_bootstrap_replicates": 1000,
    }

    commit_hash = "5098e223b18538efadbb746f363c467a90f135b7"
    frozen_timestamp = "2026-10-27T08:00:00Z"

    # Congelamento do protocolo
    frozen = ProtocolFreezeManager.freeze(
        protocol_spec=protocol_spec,
        statistical_plan=statistical_plan,
        commit_hash=commit_hash,
        frozen_at=frozen_timestamp,
        version="1.0.0",
    )

    assert frozen.status == "FROZEN"
    assert frozen.snapshot_hash and len(frozen.snapshot_hash) == 64

    # 1. Teste final executado POSTERIORMENTE ao congelamento -> DEVE PASSAR
    final_test_start_time = "2026-11-05T02:00:00Z"
    assert ProtocolFreezeManager.verify_precondition_for_final_test(
        frozen,
        test_start_timestamp=final_test_start_time,
    ) is True

    # 2. Teste final iniciado ANTES ou NO MESMO INSTANTE do congelamento -> DEVE FALHAR
    invalid_test_time_prior = "2026-10-26T12:00:00Z"
    with pytest.raises(UnfrozenProtocolExecutionError, match="Violação temporal"):
        ProtocolFreezeManager.verify_precondition_for_final_test(
            frozen,
            test_start_timestamp=invalid_test_time_prior,
        )

    # 3. Adulteração no snapshot congelado é detectada e bloqueia o teste
    frozen.protocol_spec["design"] = "ADULTERADO_POS_CONGELAMENTO"
    with pytest.raises(UnfrozenProtocolExecutionError, match="Adulteração detectada"):
        ProtocolFreezeManager.verify_precondition_for_final_test(
            frozen,
            test_start_timestamp=final_test_start_time,
        )
