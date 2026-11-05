"""
Módulo M02: Conformidade de Governança, Sanitização do Pacote Público, Avisos e Congelamento de Protocolo
(REQ-GOV-004, REQ-GOV-005, REQ-GOV-006).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple


class GovernanceComplianceError(ValueError):
    """Erro base de conformidade regulatória e de governança."""
    pass


class SecretLeakError(GovernanceComplianceError):
    """Lançado quando segredos, senhas ou chaves de API são detectados no pacote público (REQ-GOV-004)."""
    pass


class PIILeakError(GovernanceComplianceError):
    """Lançado quando dados pessoais identificáveis (PII) são detectados no pacote público (REQ-GOV-004)."""
    pass


class UnlicensedContentLeakError(GovernanceComplianceError):
    """Lançado quando texto integral sem licença aberta é detectado no pacote público (REQ-GOV-004)."""
    pass


class MissingClinicalNoticeError(GovernanceComplianceError):
    """Lançado quando aviso obrigatório de pesquisa/não-recomendação individual está ausente (REQ-GOV-005)."""
    pass


class UnfrozenProtocolExecutionError(GovernanceComplianceError):
    """Lançado quando o teste final é iniciado sem protocolo congelado previamente por commit (REQ-GOV-006)."""
    pass


def sha256_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ============================================================================
# REQ-GOV-004: Sanitização e Varredura do Pacote Público (ACC-GOV-004 / T9)
# ============================================================================

OPEN_LICENSES = {"CC-BY", "CC-BY-4.0", "CC-BY-SA", "CC0", "OPEN_ACCESS", "PUBLIC_DOMAIN"}

SECRET_KEY_PATTERNS = [
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"password", re.I),
    re.compile(r"private[_-]?token", re.I),
    re.compile(r"auth[_-]?token", re.I),
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),               # AWS Key
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),            # OpenAI / LLM key
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),           # GitHub token
    re.compile(r"postgres://[^:]+:[^@]+@"),        # Database URI with password
    re.compile(r"fixture-secret", re.I),
]

PII_KEY_PATTERNS = [
    re.compile(r"patient[_-]?email", re.I),
    re.compile(r"investigator[_-]?phone", re.I),
    re.compile(r"subject[_-]?cpf", re.I),
    re.compile(r"patient[_-]?name", re.I),
]

PII_VALUE_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),  # Email
    re.compile(r"\+55\s?\(?[1-9]{2}\)?\s?[9]?[0-9]{4}-?[0-9]{4}"),       # Phone
]


@dataclass
class ComplianceScanResult:
    is_clean: bool
    total_elements_scanned: int
    secret_findings: List[str] = field(default_factory=list)
    pii_findings: List[str] = field(default_factory=list)
    unlicensed_findings: List[str] = field(default_factory=list)


def scan_public_package(package_data: Any) -> ComplianceScanResult:
    """
    Varre recursivamente o pacote público verificando a ausência total de chaves secretas,
    dados pessoais identificáveis (PII) e textos sem licença aberta (ACC-GOV-004 / T9).
    """
    secret_findings = []
    pii_findings = []
    unlicensed_findings = []
    element_count = 0

    def _traverse(node: Any, current_path: str = "root"):
        nonlocal element_count
        element_count += 1

        if isinstance(node, dict):
            for k, v in node.items():
                path = f"{current_path}.{k}"
                # Checa chave por padrões de segredo
                if any(p.search(k) for p in SECRET_KEY_PATTERNS):
                    secret_findings.append(f"Chave proibida de segredo encontrada: {path}")
                # Checa chave por padrões de PII
                if any(p.search(k) for p in PII_KEY_PATTERNS):
                    pii_findings.append(f"Chave de dado pessoal encontrada: {path}")

                # Checa licença restritiva
                if k.lower() in ("license", "licenca"):
                    if str(v).upper() not in OPEN_LICENSES:
                        # Se houver texto integral associado
                        if "full_text" in node or "fulltext" in node or "text" in node:
                            unlicensed_findings.append(
                                f"Texto sem licença aberta encontrado em {path}: licença='{v}'"
                            )

                _traverse(v, path)

        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _traverse(item, f"{current_path}[{idx}]")

        elif isinstance(node, str):
            # Checa valores por segredos literais
            for p in SECRET_VALUE_PATTERNS:
                if p.search(node):
                    secret_findings.append(f"Padrão de credencial/segredo encontrado em {current_path}")
                    break
            # Checa marcador de texto privado
            if "PRIVATE_FULLTEXT" in node or "PRIVATE_KEY" in node:
                secret_findings.append(f"Marcador de conteúdo privado exposto em {current_path}")

    _traverse(package_data)

    if secret_findings:
        raise SecretLeakError(f"REQ-GOV-004: Segredos detectados no pacote público: {secret_findings}")
    if pii_findings:
        raise PIILeakError(f"REQ-GOV-004: Dados pessoais detectados no pacote público: {pii_findings}")
    if unlicensed_findings:
        raise UnlicensedContentLeakError(f"REQ-GOV-004: Texto sem licença aberta no pacote público: {unlicensed_findings}")

    return ComplianceScanResult(
        is_clean=True,
        total_elements_scanned=element_count,
    )


class PublicPackageSanitizer:
    """Sanitiza documentos e métricas para publicação segura no pacote público."""

    @staticmethod
    def sanitize(raw_documents: List[Dict[str, Any]], aggregated_metrics: Dict[str, Any]) -> Dict[str, Any]:
        sanitized_docs = []
        for doc in raw_documents:
            lic = str(doc.get("license", "CLOSED")).upper().strip()
            # Mantém estritamente identificadores públicos e hashes
            item = {
                "document_id": doc.get("document_id") or doc.get("documentId"),
                "document_type": doc.get("document_type") or doc.get("documentType"),
                "identifiers": doc.get("identifiers", []),
                "content_hash": doc.get("content_hash") or doc.get("contentHash"),
                "license": lic,
                "title": doc.get("title", ""),
            }
            # Só armazena texto integral se a licença for aberta
            if lic in OPEN_LICENSES and "full_text" in doc:
                item["full_text"] = doc["full_text"]
            sanitized_docs.append(item)

        package = {
            "schema_version": "public-package-v1",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "identifiers_count": len(sanitized_docs),
            "documents": sanitized_docs,
            "metrics": aggregated_metrics,
        }
        # Validação pós-sanitização garante conformidade absoluta
        scan_public_package(package)
        return package


# ============================================================================
# REQ-GOV-005: Aviso de Uso em Pesquisa e Ausência de Recomendação Clínica (ACC-GOV-005)
# ============================================================================

MANDATORY_NOTICE_TEXT = (
    "Uso estrito em pesquisa farmacológica e acadêmica. As informações catalogadas "
    "não constituem prescrição médica nem recomendação clínica individual. "
    "A frequência de relatos e o panorama analítico não medem eficácia isolada."
)


class EvidenceNoticeValidator:
    """Valida a exibição obrigatória do aviso de uso em pesquisa em telas e relatórios (REQ-GOV-005)."""

    @staticmethod
    def validate_view_notice(view_data: Dict[str, Any] | str) -> bool:
        if isinstance(view_data, str):
            text = view_data.lower()
        elif isinstance(view_data, dict):
            # Busca em campos como notice, disclaimer, footer ou texto consolidado
            text = (
                str(view_data.get("notice", "")) + " " +
                str(view_data.get("research_disclaimer", "")) + " " +
                str(view_data.get("disclaimer", ""))
            ).lower()
        else:
            raise ValueError("view_data deve ser um dicionário de tela ou texto renderizado.")

        has_research = any(w in text for w in ("uso em pesquisa", "pesquisa farmacológica", "pesquisa acadêmica"))
        has_no_individual_rec = any(w in text for w in ("sem recomendação individual", "ausência de recomendação individual", "não constituem prescrição médica", "não é recomendação"))

        if not has_research or not has_no_individual_rec:
            raise MissingClinicalNoticeError(
                "REQ-GOV-005: Aviso obrigatório ausente. A interface e os relatórios "
                "devem exibir o aviso de uso em pesquisa e a ausência de recomendação individual."
            )
        return True

    @staticmethod
    def attach_notice(view_model: Dict[str, Any]) -> Dict[str, Any]:
        """Anexa o aviso padronizado a qualquer tela de evidência."""
        updated = dict(view_model)
        updated["research_notice"] = {
            "text": MANDATORY_NOTICE_TEXT,
            "is_visible": True,
            "badge": "USO_EM_PESQUISA_SEM_RECOMENDACAO_INDIVIDUAL",
        }
        return updated


# ============================================================================
# REQ-GOV-006: Congelamento de Protocolo e Plano Estatístico (ACC-GOV-006)
# ============================================================================

@dataclass
class FrozenProtocolSnapshot:
    protocol_id: str
    version: str
    commit_hash: str
    frozen_at: str
    protocol_spec: Dict[str, Any]
    statistical_plan: Dict[str, Any]
    status: Literal["FROZEN", "SUPERSEDED"]
    snapshot_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProtocolFreezeManager:
    """Gerencia o registro e congelamento prévio de protocolo e plano estatístico (REQ-GOV-006)."""

    @classmethod
    def freeze(
        cls,
        protocol_spec: Dict[str, Any],
        statistical_plan: Dict[str, Any],
        commit_hash: str,
        frozen_at: str,
        version: str = "1.0.0",
    ) -> FrozenProtocolSnapshot:
        if not re.fullmatch(r"[a-f0-9]{7,40}", commit_hash):
            raise ValueError("Commit hash do repositório deve ser válido (7 a 40 hex chars).")
        if not protocol_spec or not statistical_plan:
            raise ValueError("Protocolo e plano estatístico são mandatórios para o congelamento.")

        payload = {
            "version": version,
            "commit_hash": commit_hash,
            "frozen_at": frozen_at,
            "protocol_spec": protocol_spec,
            "statistical_plan": statistical_plan,
        }
        snap_hash = sha256_digest(canonical_json_bytes(payload))
        prot_id = f"PROT-FROZEN-{snap_hash[:12]}"

        return FrozenProtocolSnapshot(
            protocol_id=prot_id,
            version=version,
            commit_hash=commit_hash,
            frozen_at=frozen_at,
            protocol_spec=protocol_spec,
            statistical_plan=statistical_plan,
            status="FROZEN",
            snapshot_hash=snap_hash,
        )

    @classmethod
    def verify_precondition_for_final_test(
        cls,
        frozen_protocol: FrozenProtocolSnapshot,
        test_start_timestamp: str,
    ) -> bool:
        """
        ACC-GOV-006: Dado o teste final, quando iniciado, então existe um commit
        do plano com data anterior ao início do teste.
        """
        if frozen_protocol.status != "FROZEN":
            raise UnfrozenProtocolExecutionError(
                f"REQ-GOV-006: Protocolo {frozen_protocol.protocol_id} não está no estado FROZEN (status={frozen_protocol.status})."
            )

        # Checagem de integridade bit-a-bit do snapshot
        payload = {
            "version": frozen_protocol.version,
            "commit_hash": frozen_protocol.commit_hash,
            "frozen_at": frozen_protocol.frozen_at,
            "protocol_spec": frozen_protocol.protocol_spec,
            "statistical_plan": frozen_protocol.statistical_plan,
        }
        recomputed = sha256_digest(canonical_json_bytes(payload))
        if recomputed != frozen_protocol.snapshot_hash:
            raise UnfrozenProtocolExecutionError(
                f"REQ-GOV-006: Adulteração detectada no protocolo congelado. Esperado {frozen_protocol.snapshot_hash}, obtido {recomputed}."
            )

        # Checagem temporal estrita: congelamento DEVE anteceder o início do teste final
        t_frozen = datetime.fromisoformat(frozen_protocol.frozen_at.replace("Z", "+00:00"))
        t_test = datetime.fromisoformat(test_start_timestamp.replace("Z", "+00:00"))

        if t_frozen >= t_test:
            raise UnfrozenProtocolExecutionError(
                f"REQ-GOV-006: Violação temporal: protocolo congelado em {frozen_protocol.frozen_at}, "
                f"mas o teste final iniciou em {test_start_timestamp}. O congelamento deve ter data anterior."
            )

        return True
