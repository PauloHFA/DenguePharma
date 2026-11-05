"""
Módulo M02: Governança, Controle de Acesso Baseado em Perfis (RBAC) e Trilha de Auditoria (REQ-GOV-001, REQ-GOV-003).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field


class PermissionDeniedError(PermissionError):
    """Lançado quando um perfil tenta executar uma ação não autorizada (HTTP 403 / REQ-GOV-001)."""
    pass


class Role(str, Enum):
    """Perfis de usuário previstos no SDD (REQ-GOV-001)."""
    LEITOR = "LEITOR"
    REVISOR = "REVISOR"
    ADJUDICADOR = "ADJUDICADOR"
    PESQUISADOR = "PESQUISADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class Action(str, Enum):
    """Ações controladas pelo RBAC."""
    READ_ANALYSIS = "READ_ANALYSIS"
    SUBMIT_SCREENING = "SUBMIT_SCREENING"
    CORRECT_FIELD = "CORRECT_FIELD"
    ADJUDICATE_CONFLICT = "ADJUDICATE_CONFLICT"
    APPROVE_CALIBRATION = "APPROVE_CALIBRATION"
    PUBLISH_SYNTHESIS = "PUBLISH_SYNTHESIS"
    MANAGE_USERS = "MANAGE_USERS"


# Matriz de controle de acesso cruzado formal (REQ-GOV-001)
ROLE_PERMISSIONS: Dict[Role, Set[Action]] = {
    Role.LEITOR: {
        Action.READ_ANALYSIS,
    },
    Role.REVISOR: {
        Action.READ_ANALYSIS,
        Action.SUBMIT_SCREENING,
        Action.CORRECT_FIELD,
    },
    Role.ADJUDICADOR: {
        Action.READ_ANALYSIS,
        Action.SUBMIT_SCREENING,
        Action.CORRECT_FIELD,
        Action.ADJUDICATE_CONFLICT,
        Action.APPROVE_CALIBRATION,
        Action.PUBLISH_SYNTHESIS,
    },
    Role.PESQUISADOR: {
        Action.READ_ANALYSIS,
    },
    Role.ADMINISTRADOR: {
        Action.READ_ANALYSIS,
        Action.SUBMIT_SCREENING,
        Action.CORRECT_FIELD,
        Action.ADJUDICATE_CONFLICT,
        Action.APPROVE_CALIBRATION,
        Action.PUBLISH_SYNTHESIS,
        Action.MANAGE_USERS,
    },
}


@dataclass(frozen=True)
class UserPrincipal:
    """Entidade de identidade com verificação de papéis (REQ-GOV-001)."""
    user_id: str
    roles: Tuple[Role, ...]

    @classmethod
    def create(cls, user_id: str, *roles: str | Role) -> UserPrincipal:
        parsed_roles: List[Role] = []
        for r in roles:
            if isinstance(r, Role):
                parsed_roles.append(r)
            else:
                try:
                    parsed_roles.append(Role(str(r).upper().strip()))
                except ValueError:
                    raise ValueError(f"Perfil inválido: '{r}'. Perfis válidos: {[e.value for e in Role]}")
        return cls(user_id=user_id, roles=tuple(parsed_roles))

    def has_permission(self, action: Action) -> bool:
        return any(action in ROLE_PERMISSIONS.get(role, set()) for role in self.roles)

    def require_permission(self, action: Action) -> None:
        if not self.has_permission(action):
            roles_str = ", ".join(r.value for r in self.roles)
            raise PermissionDeniedError(
                f"403 Forbidden: Usuário '{self.user_id}' com perfil(is) [{roles_str}] "
                f"não possui permissão para executar '{action.value}' (REQ-GOV-001)."
            )


@dataclass
class AuditEntry:
    """Registro individual de trilha de auditoria (REQ-GOV-003)."""
    entry_id: str
    timestamp: str
    actor_id: str
    actor_roles: List[str]
    action: str
    entity_type: str
    entity_id: str
    field_name: str
    previous_value: Any
    new_value: Any
    reason: Optional[str]
    previous_hash: str
    entry_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditTrailLedger:
    """
    Trilha de auditoria imutável e encadeada por hash (tamper-evident)
    de todas as alterações de campos e decisões (REQ-GOV-003 / ACC-GOV-003).
    """

    def __init__(self) -> None:
        self.entries: List[AuditEntry] = []
        self._last_hash: str = "0" * 64

    def record_change(
        self,
        actor: UserPrincipal,
        action: Action | str,
        entity_type: str,
        entity_id: str,
        field_name: str,
        previous_value: Any,
        new_value: Any,
        reason: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> AuditEntry:
        # Se for Action enum, valida permissão do ator (lança PermissionDeniedError se não tiver)
        if isinstance(action, Action):
            actor.require_permission(action)
            action_name = action.value
        else:
            action_name = str(action)

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        entry_id = f"AUDIT-{uuid4().hex[:12]}"

        raw_payload = {
            "entry_id": entry_id,
            "timestamp": ts,
            "actor_id": actor.user_id,
            "actor_roles": [r.value for r in actor.roles],
            "action": action_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "previous_value": previous_value,
            "new_value": new_value,
            "reason": reason,
            "previous_hash": self._last_hash,
        }

        entry_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=ts,
            actor_id=actor.user_id,
            actor_roles=[r.value for r in actor.roles],
            action=action_name,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            previous_hash=self._last_hash,
            entry_hash=entry_hash,
        )

        self.entries.append(entry)
        self._last_hash = entry_hash
        return entry

    def query(
        self,
        entity_id: Optional[str] = None,
        field_name: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> List[AuditEntry]:
        results = self.entries
        if entity_id is not None:
            results = [e for e in results if e.entity_id == entity_id]
        if field_name is not None:
            results = [e for e in results if e.field_name == field_name]
        if actor_id is not None:
            results = [e for e in results if e.actor_id == actor_id]
        return results

    def verify_integrity(self) -> bool:
        expected_prev = "0" * 64
        for entry in self.entries:
            if entry.previous_hash != expected_prev:
                return False
            raw_payload = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp,
                "actor_id": entry.actor_id,
                "actor_roles": entry.actor_roles,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "field_name": entry.field_name,
                "previous_value": entry.previous_value,
                "new_value": entry.new_value,
                "reason": entry.reason,
                "previous_hash": entry.previous_hash,
            }
            computed = hashlib.sha256(
                json.dumps(raw_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            if computed != entry.entry_hash:
                return False
            expected_prev = entry.entry_hash
        return True


# ============================================================================
# API FastAPI para Verificação de Perfis e Auditoria (REQ-GOV-001, REQ-GOV-003)
# ============================================================================

class FieldCorrectionRequest(BaseModel):
    entity_id: str
    field_name: str
    previous_value: Any
    new_value: Any
    reason: str = Field(min_length=5)


class AdjudicationRequest(BaseModel):
    conflict_id: str
    selected_option: str
    rationale: str = Field(min_length=10)


def create_governance_router(ledger: AuditTrailLedger) -> APIRouter:
    router = APIRouter(prefix="/api/governance", tags=["Governança e RBAC"])

    def parse_user(x_user_id: Optional[str], x_user_roles: Optional[str]) -> UserPrincipal:
        if not x_user_id or not x_user_roles:
            raise HTTPException(status_code=401, detail="Autenticação e perfil obrigatórios.")
        roles = [r.strip() for r in x_user_roles.split(",") if r.strip()]
        return UserPrincipal.create(x_user_id, *roles)

    @router.post("/fields/correct")
    def correct_field(
        body: FieldCorrectionRequest,
        x_user_id: Optional[str] = Header(None),
        x_user_roles: Optional[str] = Header(None),
    ):
        actor = parse_user(x_user_id, x_user_roles)
        try:
            entry = ledger.record_change(
                actor=actor,
                action=Action.CORRECT_FIELD,
                entity_type="FIELD",
                entity_id=body.entity_id,
                field_name=body.field_name,
                previous_value=body.previous_value,
                new_value=body.new_value,
                reason=body.reason,
            )
            return {"status": "SUCCESS", "audit_entry": entry.to_dict()}
        except PermissionDeniedError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @router.post("/conflicts/adjudicate")
    def adjudicate_conflict(
        body: AdjudicationRequest,
        x_user_id: Optional[str] = Header(None),
        x_user_roles: Optional[str] = Header(None),
    ):
        actor = parse_user(x_user_id, x_user_roles)
        try:
            entry = ledger.record_change(
                actor=actor,
                action=Action.ADJUDICATE_CONFLICT,
                entity_type="CONFLICT",
                entity_id=body.conflict_id,
                field_name="resolution",
                previous_value="EM_CONFLITO",
                new_value=body.selected_option,
                reason=body.rationale,
            )
            return {"status": "SUCCESS", "audit_entry": entry.to_dict()}
        except PermissionDeniedError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @router.get("/audit")
    def get_audit_trail(
        entity_id: Optional[str] = None,
        field_name: Optional[str] = None,
        x_user_id: Optional[str] = Header(None),
        x_user_roles: Optional[str] = Header(None),
    ):
        actor = parse_user(x_user_id, x_user_roles)
        actor.require_permission(Action.READ_ANALYSIS)
        entries = ledger.query(entity_id=entity_id, field_name=field_name)
        return {
            "total": len(entries),
            "integrity_verified": ledger.verify_integrity(),
            "entries": [e.to_dict() for e in entries],
        }

    return router

