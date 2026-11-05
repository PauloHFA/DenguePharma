"""
Testes de verificação formal para REQ-GOV-001 e REQ-GOV-003.
- REQ-GOV-001 (ACC-GOV-001): Perfis Leitor, Revisor, Adjudicador, Pesquisador, Administrador e teste de acesso cruzado (403 para Leitor).
- REQ-GOV-003 (ACC-GOV-003): Trilha de auditoria completa com autor, instante e valores (before/after).
"""
from fastapi import HTTPException
import pytest

from denguepharma_analytics.clinical.governance import (
    PermissionDeniedError,
    Role,
    Action,
    ROLE_PERMISSIONS,
    UserPrincipal,
    AuditTrailLedger,
    FieldCorrectionRequest,
    AdjudicationRequest,
    create_governance_router,
)


@pytest.fixture
def governance_system():
    ledger = AuditTrailLedger()
    router = create_governance_router(ledger)
    endpoints = {r.path: r.endpoint for r in router.routes}
    return ledger, endpoints


# ============================================================================
# REQ-GOV-001: RBAC e Teste de Acesso Cruzado entre Perfis (ACC-GOV-001)
# ============================================================================

@pytest.mark.requirement("REQ-GOV-001")
def test_cross_profile_access_and_reader_receives_403_on_field_correction(governance_system):
    """
    ACC-GOV-001: Dado um Leitor, quando tentar corrigir um campo, então recebe 403;
    teste de acesso cruzado entre perfis (Leitor, Revisor, Adjudicador, Pesquisador e Administrador).
    """
    ledger, endpoints = governance_system
    correct_field = endpoints["/api/governance/fields/correct"]
    adjudicate_conflict = endpoints["/api/governance/conflicts/adjudicate"]
    get_audit = endpoints["/api/governance/audit"]

    payload = FieldCorrectionRequest(
        entity_id="STUDY-BALAPIRAVIR-01",
        field_name="primary_outcome_measured",
        previous_value="Viremia clearance in hours",
        new_value="Viral load reduction log10 copies/mL at 48h",
        reason="Correção de unidade conforme tabela 2 do protocolo",
    )

    # 1. LEITOR tenta corrigir campo -> DEVE RECEBER 403
    with pytest.raises(HTTPException) as exc_leitor:
        correct_field(
            payload,
            x_user_id="usuario.leitor@denguepharma.org",
            x_user_roles="LEITOR",
        )
    assert exc_leitor.value.status_code == 403
    assert "403 Forbidden" in exc_leitor.value.detail
    assert "LEITOR" in exc_leitor.value.detail

    # 2. PESQUISADOR tenta corrigir campo -> DEVE RECEBER 403 (pesquisa não altera curadoria)
    with pytest.raises(HTTPException) as exc_pesq:
        correct_field(
            payload,
            x_user_id="pesquisador.dados@denguepharma.org",
            x_user_roles="PESQUISADOR",
        )
    assert exc_pesq.value.status_code == 403

    # 3. REVISOR corrige campo -> PERMITIDO (200 OK)
    resp_revisor = correct_field(
        payload,
        x_user_id="revisor.clinico@denguepharma.org",
        x_user_roles="REVISOR",
    )
    assert resp_revisor["status"] == "SUCCESS"
    assert resp_revisor["audit_entry"]["actor_id"] == "revisor.clinico@denguepharma.org"

    # 4. REVISOR tenta adjudicar conflito -> DEVE RECEBER 403
    adj_payload = AdjudicationRequest(
        conflict_id="CONF-001",
        selected_option="INCLUIR",
        rationale="Tentativa indevida de adjudicação por revisor comum",
    )
    with pytest.raises(HTTPException) as exc_rev_adj:
        adjudicate_conflict(
            adj_payload,
            x_user_id="revisor.clinico@denguepharma.org",
            x_user_roles="REVISOR",
        )
    assert exc_rev_adj.value.status_code == 403

    # 5. ADJUDICADOR adjudica conflito -> PERMITIDO (200 OK)
    resp_adjudicador = adjudicate_conflict(
        adj_payload,
        x_user_id="adjudicador.chefe@denguepharma.org",
        x_user_roles="ADJUDICADOR",
    )
    assert resp_adjudicador["status"] == "SUCCESS"

    # 6. ADMINISTRADOR pode corrigir e adjudicar
    resp_admin = correct_field(
        payload,
        x_user_id="admin@denguepharma.org",
        x_user_roles="ADMINISTRADOR",
    )
    assert resp_admin["status"] == "SUCCESS"

    # 7. LEITOR tem permissão de leitura analítica (GET /audit)
    audit_data = get_audit(
        entity_id=None,
        field_name=None,
        x_user_id="usuario.leitor@denguepharma.org",
        x_user_roles="LEITOR",
    )
    assert audit_data["total"] >= 2
    assert audit_data["integrity_verified"] is True


@pytest.mark.requirement("REQ-GOV-001")
def test_user_principal_role_enforcement_and_matrix():
    """Valida métodos de governança e matriz RBAC para os 5 perfis formais."""
    leitor = UserPrincipal.create("usr-1", Role.LEITOR)
    revisor = UserPrincipal.create("usr-2", Role.REVISOR)
    adjudicador = UserPrincipal.create("usr-3", Role.ADJUDICADOR)
    pesquisador = UserPrincipal.create("usr-4", Role.PESQUISADOR)
    admin = UserPrincipal.create("usr-5", Role.ADMINISTRADOR)

    # Leitor
    assert leitor.has_permission(Action.READ_ANALYSIS)
    assert not leitor.has_permission(Action.CORRECT_FIELD)
    with pytest.raises(PermissionDeniedError):
        leitor.require_permission(Action.CORRECT_FIELD)

    # Revisor
    assert revisor.has_permission(Action.CORRECT_FIELD)
    assert not revisor.has_permission(Action.ADJUDICATE_CONFLICT)
    with pytest.raises(PermissionDeniedError):
        revisor.require_permission(Action.ADJUDICATE_CONFLICT)

    # Adjudicador
    assert adjudicador.has_permission(Action.ADJUDICATE_CONFLICT)
    assert adjudicador.has_permission(Action.APPROVE_CALIBRATION)
    assert adjudicador.has_permission(Action.PUBLISH_SYNTHESIS)
    assert not adjudicador.has_permission(Action.MANAGE_USERS)

    # Pesquisador
    assert pesquisador.has_permission(Action.READ_ANALYSIS)
    assert not pesquisador.has_permission(Action.CORRECT_FIELD)

    # Administrador
    assert admin.has_permission(Action.MANAGE_USERS)
    assert admin.has_permission(Action.CORRECT_FIELD)
    assert admin.has_permission(Action.PUBLISH_SYNTHESIS)


# ============================================================================
# REQ-GOV-003: Trilha de Auditoria com Autor, Instante e Valores (ACC-GOV-003)
# ============================================================================

@pytest.mark.requirement("REQ-GOV-003")
def test_audit_trail_records_author_timestamp_and_before_after_values():
    """
    ACC-GOV-003: Dado uma alteração, quando consultada a auditoria,
    então autor, instante e valores constam.
    """
    ledger = AuditTrailLedger()
    revisor = UserPrincipal.create("revisor.metodologico@denguepharma.org", Role.REVISOR)

    # Registra alteração de campo
    entry1 = ledger.record_change(
        actor=revisor,
        action=Action.CORRECT_FIELD,
        entity_type="FIELD",
        entity_id="NCT00849602",
        field_name="substance",
        previous_value="Chloroquin",
        new_value="Chloroquine",
        reason="Correção ortográfica do nome internacional não-proprietário (DCI)",
    )

    # Consulta auditoria pelo ID da entidade
    history = ledger.query(entity_id="NCT00849602")
    assert len(history) == 1
    record = history[0]

    # Valida presença mandatória de autor, instante e valores (ACC-GOV-003)
    assert record.actor_id == "revisor.metodologico@denguepharma.org"
    assert record.timestamp and "T" in record.timestamp  # Instante ISO 8601
    assert record.previous_value == "Chloroquin"         # Valor anterior
    assert record.new_value == "Chloroquine"             # Valor novo
    assert record.reason == "Correção ortográfica do nome internacional não-proprietário (DCI)"

    # Registra segunda alteração encadeada
    adjudicador = UserPrincipal.create("adjudicador.chefe@denguepharma.org", Role.ADJUDICADOR)
    entry2 = ledger.record_change(
        actor=adjudicador,
        action=Action.ADJUDICATE_CONFLICT,
        entity_type="CONFLICT",
        entity_id="CONF-NCT00849602-01",
        field_name="resolution",
        previous_value="DISCORDANCIA",
        new_value="ELEGIVEL",
        reason="Consenso de elegibilidade pós-adjudicação",
    )

    assert entry2.previous_hash == entry1.entry_hash
    assert ledger.verify_integrity() is True

    # Valida que adulteração de registro viola a integridade da trilha
    entry1.new_value = "VALOR_ADULTERADO_FRAUDULENTO"
    assert ledger.verify_integrity() is False
