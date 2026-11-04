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
    r"(?i)(ignore\s+(all\s+)?(previous|prior)\s+instructions|ignore\s+(as\s+)?instru[çc][õo]es|ignore.*publique|system\s+override|altere\s+o\s+status|force\s+publish|<script\b|drop\s+table|rm\s+-rf|curl\s+http|exec\(|eval\()"
)
FRACTION_PATTERN = re.compile(r"(\d+)\s*(?:/|de|of)\s*(\d+)")
PERCENT_PATTERN = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%")
INCOMPATIBLE_COUNT_UNITS = {"mg", "mg/kg", "ml", "ug/ml", "ng/ml", "mmhg", "g/dl"}


@dataclass(frozen=True)
class TableQualityMetrics:
    ocr_confidence: float = 1.0
    is_misaligned: bool = False
    cell_column_ambiguous: bool = False
    header_overlap: bool = False


def validate_table_reading_quality(
    metrics: TableQualityMetrics | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """SE a leitura de tabela ou OCR tiver baixa qualidade ou relação célula-coluna incerta,
    ENTÃO o sistema deve bloquear a extração numérica e sinalizar (REQ-EXT-007 / ACC-EXT-007 / T6).
    """
    if metrics is None:
        return {
            "allows_numeric_extraction": True,
            "is_blocked": False,
            "alerts": [],
            "status": "QUALIDADE_ADEQUADA",
        }

    if isinstance(metrics, Mapping):
        ocr_conf = float(metrics.get("ocr_confidence", 1.0))
        is_misaligned = bool(metrics.get("is_misaligned", False))
        cell_ambiguous = bool(metrics.get("cell_column_ambiguous", False))
        header_overlap = bool(metrics.get("header_overlap", False))
    else:
        ocr_conf = metrics.ocr_confidence
        is_misaligned = metrics.is_misaligned
        cell_ambiguous = metrics.cell_column_ambiguous
        header_overlap = metrics.header_overlap

    alerts: list[str] = []
    if is_misaligned:
        alerts.append("Tabela com colunas desalinhadas (ACC-EXT-007 / T6)")
    if cell_ambiguous:
        alerts.append("Relação célula-coluna incerta ou ambígua")
    if header_overlap:
        alerts.append("Sobreposição de cabeçalho detectada na estrutura tabular")
    if ocr_conf < 0.70:
        alerts.append(f"Baixa confiança de OCR ({ocr_conf:.2f} < 0.70)")

    is_blocked = len(alerts) > 0
    return {
        "allows_numeric_extraction": not is_blocked,
        "is_blocked": is_blocked,
        "alerts": alerts,
        "status": "BLOQUEADO_OCR_TABELA_INCERTA" if is_blocked else "QUALIDADE_ADEQUADA",
        "notice": (
            "Alerta de leitura: extração numérica bloqueada devido a desalinhamento de tabela ou baixa qualidade de OCR (REQ-EXT-007 / T6)."
            if is_blocked
            else None
        ),
    }


@dataclass(frozen=True)
class ExtractionRunAuditRecord:
    run_id: str
    document_version_id: str
    provider: str
    model: str
    model_version: str
    parameters: dict[str, Any]
    prompt_hash: str
    execution_time_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    status: str = "COMPLETED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_audited_extraction_run(
    run_id: str,
    document_version_id: str,
    provider: str,
    model: str,
    model_version: str,
    parameters: Mapping[str, Any],
    prompt_hash: str,
    execution_time_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    status: str = "COMPLETED",
) -> ExtractionRunAuditRecord:
    """Registra em cada ExtractionRun provedor, modelo, versão, parâmetros, hash do prompt,
    tempo, tokens e custo, garantindo que todos os campos estejam preenchidos (REQ-EXT-008 / ACC-EXT-008).
    """
    required_strings = {
        "run_id": run_id,
        "document_version_id": document_version_id,
        "provider": provider,
        "model": model,
        "model_version": model_version,
        "prompt_hash": prompt_hash,
    }
    for name, val in required_strings.items():
        if not val or not str(val).strip():
            raise ValueError(f"Campo obrigatório '{name}' não pode ser nulo ou vazio no ExtractionRun (ACC-EXT-008)")

    if parameters is None:
        raise ValueError("Parâmetros do modelo são obrigatórios no ExtractionRun")

    if execution_time_ms is None or execution_time_ms < 0:
        raise ValueError("execution_time_ms deve ser informado e >= 0")

    if prompt_tokens is None or prompt_tokens < 0 or completion_tokens is None or completion_tokens < 0:
        raise ValueError("prompt_tokens e completion_tokens devem ser informados e >= 0")

    if cost_usd is None or cost_usd < 0:
        raise ValueError("cost_usd deve ser informado e >= 0")

    return ExtractionRunAuditRecord(
        run_id=run_id,
        document_version_id=document_version_id,
        provider=provider,
        model=model,
        model_version=model_version,
        parameters=dict(parameters),
        prompt_hash=prompt_hash,
        execution_time_ms=int(execution_time_ms),
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_tokens=int(prompt_tokens + completion_tokens),
        cost_usd=float(cost_usd),
        status=status,
    )

def sanitize_document_data_only(text: str | None) -> dict[str, Any]:
    """Trata o texto do documento estritamente como dado passivo (REQ-EXT-005 / ACC-EXT-005).

    Instruções embutidas (prompt injection) não podem alterar o fluxo, nem acionar ferramentas,
    nem forçar publicação automática.
    """
    if text is None:
        return {
            "sanitized_text": "",
            "contains_injection_attempt": False,
            "is_treated_as_data_only": True,
            "can_alter_flow": False,
            "can_trigger_tools": False,
        }

    raw = str(text)
    match = PROMPT_INJECTION_PATTERN.search(raw)
    if match:
        sanitized = PROMPT_INJECTION_PATTERN.sub("[INSTRUCAO_BLOQUEADA]", raw)
        return {
            "sanitized_text": sanitized,
            "contains_injection_attempt": True,
            "injection_matched": match.group(0),
            "is_treated_as_data_only": True,
            "can_alter_flow": False,
            "can_trigger_tools": False,
            "notice": "Instrução embutida neutralizada; texto tratado exclusivamente como dado passivo (REQ-EXT-005).",
        }

    return {
        "sanitized_text": raw,
        "contains_injection_attempt": False,
        "is_treated_as_data_only": True,
        "can_alter_flow": False,
        "can_trigger_tools": False,
    }


def validate_numeric_and_population_coherence(
    field_name: str,
    value: Any,
    denominator: int | float | None = None,
    n_randomized: int | float | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    """Valida coerência de números, unidades e populações (REQ-EXT-006 / ACC-EXT-006 / T5).

    Se n_analisado > n_randomizado, ou numerador > denominador, ou percentual fora de 0..100%,
    ou unidade incompatível, bloqueia compulsoriamente a extração.
    """
    val_str = str(value) if value is not None else ""
    errors: list[str] = []

    # 1. Se unidade incompatível para campos de contagem amostral
    if unit and any(u in unit.lower() for u in INCOMPATIBLE_COUNT_UNITS):
        if field_name in {"sample_size", "n_randomized", "n_analyzed", "events"}:
            errors.append(f"Unidade incoerente '{unit}' para campo populacional {field_name}")

    # 2. Fração X/Y com numerador maior que denominador
    frac_match = FRACTION_PATTERN.search(val_str)
    if frac_match:
        num = int(frac_match.group(1))
        den = int(frac_match.group(2))
        if den <= 0:
            errors.append(f"Denominador zero ou negativo ({num}/{den})")
        elif num > den:
            errors.append(f"Numerador maior que o denominador ({num}/{den})")

    # 3. Percentuais fora de 0..100%
    pct_matches = PERCENT_PATTERN.findall(val_str)
    for p in pct_matches:
        try:
            val_pct = float(p.replace(",", "."))
            if val_pct < 0.0 or val_pct > 100.0:
                errors.append(f"Percentual fora do intervalo 0..100% ({val_pct}%)")
        except ValueError:
            pass

    # 4. População analisada maior que randomizada (T5)
    numbers = extract_numbers_from_text(val_str)
    num_val = numbers[0] if numbers else None

    if field_name in {"n_analyzed", "sample_size"} and num_val is not None:
        effective_randomized = n_randomized or denominator
        if effective_randomized is not None and num_val > effective_randomized:
            errors.append(
                f"n analisado ({num_val}) maior que n randomizado ({effective_randomized}) - T5"
            )

    is_blocked = len(errors) > 0
    return {
        "field_name": field_name,
        "is_coherent": not is_blocked,
        "is_blocked": is_blocked,
        "reasons": errors,
        "status": "BLOQUEADO_INCOERENCIA_NUMERICA" if is_blocked else "COERENTE",
    }


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
    denominator: int | float | None = None,
    n_randomized: int | float | None = None,
    unit: str | None = None,
    table_metrics: TableQualityMetrics | Mapping[str, Any] | None = None,
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

    # Sanitização de prompt injection e texto passivo (REQ-EXT-005 / ACC-EXT-005 / T10)
    orig_str = str(original_value) if original_value is not None else ""
    injection_eval = sanitize_document_data_only(orig_str)
    if injection_eval["contains_injection_attempt"]:
        rejection_reasons.append("Instrução embutida/prompt injection neutralizada; fluxo e publicação inalterados (REQ-EXT-005 / T10)")
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

    # Validação de qualidade de leitura de tabela e OCR (REQ-EXT-007 / ACC-EXT-007 / T6)
    if table_metrics is not None:
        table_eval = validate_table_reading_quality(table_metrics)
        if table_eval["is_blocked"]:
            rejection_reasons.extend(table_eval["alerts"])
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

    # Validação de coerência numérica, denominadores e população (REQ-EXT-006 / ACC-EXT-006 / T5)
    coherence = validate_numeric_and_population_coherence(
        field_name=field_name,
        value=original_value,
        denominator=denominator,
        n_randomized=n_randomized,
        unit=unit,
    )
    if coherence["is_blocked"]:
        rejection_reasons.extend(coherence["reasons"])
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
            denominator=c.get("denominator"),
            n_randomized=c.get("n_randomized"),
            unit=c.get("unit"),
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
