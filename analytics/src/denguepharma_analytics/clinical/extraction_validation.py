"""Validação determinística de extração por IA, suporte literal e salvaguardas anti-alucinação.

Implementa os requisitos formais:
- REQ-EXT-001: Guarda document_version_id, localização (seção/página/offset) e trecho de suporte literal.
- REQ-EXT-002: Valida saída contra o esquema e bloqueia publicação se falhar.
- REQ-EXT-003: Verifica de forma determinística que o trecho citado existe no documento e que o número extraído consta no trecho.
- REQ-EXT-004: Se o modelo não produzir trecho localizável, registra como 'INCERTO' e impede publicação (abstenção T4).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


VALID_ABSENCE_STATUSES = {
    "PRESENTE",
    "NAO_INFORMADO",
    "NAO_APLICAVEL",
    "NAO_EXTRAIDO",
    "INCERTO",
    "NAO_HOUVE_EVENTO",
}

CRITICAL_EXTRACTION_FIELDS = {
    "sample_size",
    "n_randomized",
    "n_analyzed",
    "events",
    "serotype",
    "intervention",
    "comparator",
    "outcome",
    "follow_up_days",
}

NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?![\w.])")
PROMPT_INJECTION_PATTERN = re.compile(
    r"(?i)(ignore\s+(all\s+)?(previous|prior)\s+instructions|system\s+override|<script\b|drop\s+table|rm\s+-rf|curl\s+http|exec\()"
)


@dataclass(frozen=True)
class EvidenceSpan:
    document_version_id: str
    section: str | None = None
    page: int | None = None
    locator: str | None = None
    start_char: int | None = None
    end_char: int | None = None
    quoted_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractedFieldRecord:
    field_name: str
    original_value: Any
    normalized_value: Any
    absence_status: str
    evidence_span: EvidenceSpan | None
    is_valid: bool
    published: bool
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_literal_quote_exists(document_text: str, quote: str | None) -> bool:
    """Verifica de forma determinística se a citação existe no documento (REQ-EXT-003)."""
    if not document_text or not quote:
        return False
    norm_doc = normalize_whitespace(document_text).lower()
    norm_quote = normalize_whitespace(quote).lower()
    return len(norm_quote) >= 3 and norm_quote in norm_doc


def extract_numbers_from_text(text: str | None) -> list[float]:
    """Extrai todos os números reais/inteiros de um texto."""
    if not text:
        return []
    matches = NUMBER_PATTERN.findall(text)
    numbers: list[float] = []
    for m in matches:
        try:
            numbers.append(float(m.replace(",", ".")))
        except ValueError:
            continue
    return numbers


def validate_extracted_field(
    field_name: str,
    original_value: Any,
    document_text: str,
    document_version_id: str,
    quoted_text: str | None = None,
    locator: str | None = None,
    section: str | None = None,
    page: int | None = None,
    absence_status: str = "PRESENTE",
) -> ExtractedFieldRecord:
    """Valida um campo extraído aplicando estritamente as regras REQ-EXT-001 a REQ-EXT-004."""
    rejection_reasons: list[str] = []

    # 1. Validação de Schema (REQ-EXT-002)
    if not field_name or not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name é obrigatório e deve ser string não-vazia")

    if absence_status not in VALID_ABSENCE_STATUSES:
        rejection_reasons.append(f"absence_status inválido: {absence_status}")
        return ExtractedFieldRecord(
            field_name=field_name,
            original_value=original_value,
            normalized_value=None,
            absence_status="INCERTO",
            evidence_span=None,
            is_valid=False,
            published=False,
            rejection_reasons=rejection_reasons,
        )

    # Sanitização de prompt injection (REQ-EXT-005)
    orig_str = str(original_value) if original_value is not None else ""
    if PROMPT_INJECTION_PATTERN.search(orig_str):
        rejection_reasons.append("Instrução maliciosa bloqueada por segurança (T10)")
        return ExtractedFieldRecord(
            field_name=field_name,
            original_value="[INSTRUCAO_BLOQUEADA]",
            normalized_value=None,
            absence_status="INCERTO",
            evidence_span=None,
            is_valid=False,
            published=False,
            rejection_reasons=rejection_reasons,
        )

    # Se status for ausência legítima declarada
    if absence_status in {"NAO_INFORMADO", "NAO_APLICAVEL", "NAO_HOUVE_EVENTO"}:
        span = None
        if quoted_text and locator:
            span = EvidenceSpan(
                document_version_id=document_version_id,
                section=section,
                page=page,
                locator=locator,
                quoted_text=quoted_text,
            )
        return ExtractedFieldRecord(
            field_name=field_name,
            original_value=None,
            normalized_value=None,
            absence_status=absence_status,
            evidence_span=span,
            is_valid=True,
            published=False,  # Requer adjudicação humana para publicar
            rejection_reasons=[],
        )

    # 2. Exigência de Trecho de Suporte Localizável (REQ-EXT-004 - Abstenção T4)
    if not quoted_text or not quoted_text.strip() or not locator or not locator.strip():
        rejection_reasons.append("Sem trecho de suporte localizável na fonte; registrado como INCERTO (T4)")
        return ExtractedFieldRecord(
            field_name=field_name,
            original_value=original_value,
            normalized_value=None,  # Proibido inventar número
            absence_status="INCERTO",
            evidence_span=None,
            is_valid=False,
            published=False,
            rejection_reasons=rejection_reasons,
        )

    # 3. Verificação Determinística de Presença no Texto (REQ-EXT-003)
    if not check_literal_quote_exists(document_text, quoted_text):
        rejection_reasons.append("Trecho citado inexistente no documento original (ACC-EXT-003)")
        return ExtractedFieldRecord(
            field_name=field_name,
            original_value=original_value,
            normalized_value=None,
            absence_status="INCERTO",
            evidence_span=None,
            is_valid=False,
            published=False,
            rejection_reasons=rejection_reasons,
        )

    # 4. Verificação de Coerência Numérica: Número Extraído deve Constar no Trecho (REQ-EXT-003)
    value_numbers = extract_numbers_from_text(orig_str)
    quote_numbers = extract_numbers_from_text(quoted_text)

    if value_numbers:
        # Pelo menos o número principal extraído deve constar no trecho citado
        for vn in value_numbers:
            if not any(abs(vn - qn) < 1e-6 for qn in quote_numbers):
                rejection_reasons.append(
                    f"Número extraído ({vn}) não consta no trecho de suporte literal (REQ-EXT-003)"
                )
                return ExtractedFieldRecord(
                    field_name=field_name,
                    original_value=original_value,
                    normalized_value=None,
                    absence_status="INCERTO",
                    evidence_span=None,
                    is_valid=False,
                    published=False,
                    rejection_reasons=rejection_reasons,
                )

    # 5. Rastreabilidade Completa (REQ-EXT-001)
    span = EvidenceSpan(
        document_version_id=document_version_id,
        section=section or "Corpus",
        page=page,
        locator=locator,
        quoted_text=quoted_text.strip(),
    )

    return ExtractedFieldRecord(
        field_name=field_name,
        original_value=original_value,
        normalized_value=original_value,
        absence_status="PRESENTE",
        evidence_span=span,
        is_valid=True,
        published=False,  # Fica como rascunho validado aguardando adjudicação
        rejection_reasons=[],
    )


def validate_extraction_batch(
    document_text: str,
    document_version_id: str,
    candidate_fields: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Processa lote de extração aplicando checagens determinísticas completas."""
    results: list[ExtractedFieldRecord] = []
    for c in candidate_fields:
        res = validate_extracted_field(
            field_name=c["field_name"],
            original_value=c.get("original_value"),
            document_text=document_text,
            document_version_id=document_version_id,
            quoted_text=c.get("quoted_text"),
            locator=c.get("locator"),
            section=c.get("section"),
            page=c.get("page"),
            absence_status=c.get("absence_status", "PRESENTE"),
        )
        results.append(res)

    valid_count = sum(1 for r in results if r.is_valid and r.absence_status == "PRESENTE")
    uncertain_count = sum(1 for r in results if r.absence_status == "INCERTO")
    missing_count = sum(1 for r in results if r.absence_status in {"NAO_INFORMADO", "NAO_APLICAVEL"})

    return {
        "document_version_id": document_version_id,
        "total_fields": len(results),
        "valid_drafts_count": valid_count,
        "uncertain_abstained_count": uncertain_count,
        "missing_status_count": missing_count,
        "all_uncertain_unpublishable": all(
            not r.published for r in results if r.absence_status == "INCERTO"
        ),
        "fields": [r.to_dict() for r in results],
    }
