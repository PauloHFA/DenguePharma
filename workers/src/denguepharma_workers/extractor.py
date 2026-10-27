"""Pipeline de extração assistida por IA, validação determinística e métricas (Seções 10 e 15 do PDF).

Implementa:
- Extração baseada em regras de metadados estruturados + adaptador de modelo de linguagem.
- Sanitização de instruções maliciosas no documento ou resposta do modelo (Cenário T10).
- Exigência de trecho literal de suporte (EvidenceSpan) e abstenção explícita quando insuficiente (Cenário T4).
- Validação determinística de números, unidades e denominadores (Cenário T5).
- Cálculo de Precisão, Recall e F1 excluindo verdadeiros negativos de ausência (Seção 15).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

ABSENCE_STATUSES = {
    "PRESENTE",
    "NAO_INFORMADO",
    "NAO_APLICAVEL",
    "NAO_EXTRAIDO",
    "INCERTO",
    "NAO_HOUVE_EVENTO",
}

PROMPT_INJECTION_RE = re.compile(
    r"(?i)(ignore\s+(all\s+)?(previous|prior)\s+instructions|system\s+override|<script\b|drop\s+table|rm\s+-rf|curl\s+http|exec\()"
)
FRACTION_RE = re.compile(r"(\d+)\s*(?:/|de|of)\s*(\d+)")
PERCENT_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%")
MEDIAN_TO_MEAN_RE = re.compile(
    r"(?i)(mediana.*convertid[ao].*m[eé]dia|median\s+converted\s+to\s+mean)"
)


@dataclass(frozen=True)
class CandidateField:
    field_name: str
    original_value: str | None = None
    normalized_value: str | None = None
    absence_status: str = "PRESENTE"
    section: str | None = None
    page: int | None = None
    locator: str | None = None
    quoted_text: str | None = None
    denominator: int | None = None


@dataclass(frozen=True)
class ValidatedField:
    field_name: str
    original_value: str | None
    normalized_value: str | None
    absence_status: str
    section: str | None
    page: int | None
    locator: str | None
    quoted_text: str | None
    review_status: str = "RASCUNHO_IA"
    published: bool = False
    warnings: list[str] = field(default_factory=list)


def sanitize_data_only(text: str | None, field_name: str, warnings: list[str]) -> str | None:
    """Trata o texto como dado puro; instruções maliciosas não executam ações (Cenário T10)."""
    if text is None:
        return None
    if PROMPT_INJECTION_RE.search(text):
        warnings.append(f"{field_name}: instrucao maliciosa/script neutralizada (T10)")
        return PROMPT_INJECTION_RE.sub("[INSTRUCAO_BLOQUEADA]", text).strip()
    return text.strip()


def has_literal_support(document_text: str, quoted_text: str | None) -> bool:
    """Verifica se o trecho citado consta literalmente no documento (normalizando apenas espaços)."""
    if not document_text or not quoted_text:
        return False
    clean_quote = quoted_text.strip()
    if len(clean_quote) < 5:
        return False
    norm_doc = re.sub(r"\s+", " ", document_text).lower()
    norm_quote = re.sub(r"\s+", " ", clean_quote).lower()
    return norm_quote in norm_doc


def validate_numerics_and_units(
    field_name: str,
    orig: str | None,
    norm: str | None,
    denominator: int | None = None,
) -> str | None:
    """Valida determinísticamente números, frações, denominadores e unidades (Cenário T5)."""
    text = norm if (norm and norm.strip()) else orig
    if not text or not text.strip():
        return "valor vazio para campo PRESENTE"
    if "[INSTRUCAO_BLOQUEADA]" in text:
        return "conteudo bloqueado por seguranca (T10)"
    if MEDIAN_TO_MEAN_RE.search(text):
        return "proibido converter mediana em media por inferencia (Secao 08)"

    frac = FRACTION_RE.search(text)
    if frac:
        num = int(frac.group(1))
        den = int(frac.group(2))
        if den <= 0:
            return f"denominador zero ou negativo ({num}/{den})"
        if num > den:
            return f"numerador maior que denominador ({num}/{den})"

    for pct in PERCENT_RE.finditer(text):
        val = float(pct.group(1).replace(",", "."))
        if val < 0.0 or val > 100.0:
            return f"percentual fora de 0..100% ({val}%)"

    if field_name in {"sample_size", "n_analyzed"}:
        digits = re.sub(r"[^0-9-]", "", text)
        if not digits:
            return "tamanho amostral nao numerico"
        n_val = int(digits)
        if n_val <= 0:
            return "tamanho amostral deve ser positivo"
        if denominator is not None and n_val > denominator:
            return f"amostra analisada ({n_val}) maior que denominador randomizado ({denominator})"

    return None


def validate_and_abstain(document_text: str, candidates: list[CandidateField]) -> list[ValidatedField]:
    """Valida cada campo extraído contra o texto-fonte, aplicando abstenção (T4), checagem numérica (T5) e sanitização (T10)."""
    out: list[ValidatedField] = []
    for c in candidates:
        if not c.field_name or not c.field_name.strip():
            raise ValueError("field_name obrigatorio no schema de extracao")
        if c.absence_status not in ABSENCE_STATUSES:
            raise ValueError(f"absence_status invalido: {c.absence_status}")

        warnings: list[str] = []
        orig = sanitize_data_only(c.original_value, c.field_name, warnings)
        norm = sanitize_data_only(c.normalized_value, c.field_name, warnings)
        quote = sanitize_data_only(c.quoted_text, c.field_name, warnings)
        status = c.absence_status

        if status == "PRESENTE":
            if not has_literal_support(document_text, quote) or not c.locator or not c.locator.strip():
                status = "INCERTO"
                norm = None
                warnings.append(f"{c.field_name}: sem trecho de suporte literal na fonte (abstencao T4)")

        if status == "PRESENTE":
            problem = validate_numerics_and_units(c.field_name, orig, norm, c.denominator)
            if problem:
                status = "INCERTO"
                norm = None
                warnings.append(f"{c.field_name}: bloqueado por validacao numerica/unidade ({problem})")

        out.append(
            ValidatedField(
                field_name=c.field_name,
                original_value=orig,
                normalized_value=norm,
                absence_status=status,
                section=c.section if status == "PRESENTE" else None,
                page=c.page if status == "PRESENTE" else None,
                locator=c.locator if status == "PRESENTE" else None,
                quoted_text=quote if status == "PRESENTE" else None,
                review_status="RASCUNHO_IA",
                published=False,
                warnings=warnings,
            )
        )
    return out


def extract_from_structured_metadata(metadata: dict[str, Any]) -> list[CandidateField]:
    """Extração determinística inicial baseada em metadados estruturados (Condição B da Seção 14)."""
    abstract = str(metadata.get("abstract") or "")
    fields: list[CandidateField] = []

    serotype_match = re.search(r"\b(DENV-[1-4](?:/[1-4])?)\b", abstract)
    if serotype_match:
        fields.append(
            CandidateField(
                field_name="serotype",
                original_value=serotype_match.group(1),
                normalized_value=serotype_match.group(1),
                absence_status="PRESENTE",
                section="Abstract",
                locator="regex:serotype",
                quoted_text=serotype_match.group(0),
            )
        )
    else:
        fields.append(CandidateField(field_name="serotype", absence_status="NAO_INFORMADO"))

    sample_match = re.search(r"randomized\s+(\d+)\s+(?:adult\s+)?patients", abstract, re.IGNORECASE)
    if sample_match:
        fields.append(
            CandidateField(
                field_name="sample_size",
                original_value=sample_match.group(1),
                normalized_value=sample_match.group(1),
                absence_status="PRESENTE",
                section="Abstract",
                locator="regex:sample_size",
                quoted_text=sample_match.group(0),
            )
        )
    else:
        fields.append(CandidateField(field_name="sample_size", absence_status="NAO_INFORMADO"))

    return fields


def compute_extraction_metrics(
    predictions: list[tuple[str, str | None]],
    references: list[tuple[str, str | None]],
) -> dict[str, float]:
    """Calcula Precisão, Recall e F1 excluindo verdadeiros negativos de ausência (Seção 15 do PDF).

    Cada item é (absence_status, normalized_value).
    Quando ambos esperado e predito são ausentes (status != 'PRESENTE'), o par é contabilizado em
    `correct_absences`, mas excluído de precisão/recall de extração para não inflar o resultado.
    """
    if len(predictions) != len(references):
        raise ValueError("predictions e references devem ter o mesmo tamanho")

    tp = 0
    extracted_count = 0
    expected_count = 0
    correct_absences = 0
    total_absences = 0

    for (pred_status, pred_val), (ref_status, ref_val) in zip(predictions, references):
        pred_present = pred_status == "PRESENTE" and pred_val is not None
        ref_present = ref_status == "PRESENTE" and ref_val is not None

        if not ref_present:
            total_absences += 1
            if not pred_present and pred_status == ref_status:
                correct_absences += 1

        if not pred_present and not ref_present:
            continue

        if pred_present:
            extracted_count += 1
        if ref_present:
            expected_count += 1
        if pred_present and ref_present and pred_val.strip().lower() == ref_val.strip().lower():
            tp += 1

    precision = tp / extracted_count if extracted_count > 0 else 0.0
    recall = tp / expected_count if expected_count > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    absence_accuracy = correct_absences / total_absences if total_absences > 0 else 1.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "absence_accuracy": round(absence_accuracy, 4),
    }


class BudgetExceededError(RuntimeError):
    """Lançada quando o custo acumulado da execução ultrapassa o teto de orçamento (Seções 13 e 17)."""


class BudgetGuard:
    """Controla o teto de orçamento por execução de extração assistida por IA."""

    def __init__(self, max_cost_usd: float) -> None:
        if max_cost_usd <= 0:
            raise ValueError("max_cost_usd deve ser positivo")
        self.max_cost_usd = max_cost_usd
        self.spent_usd = 0.0

    def record_call(self, call_cost_usd: float) -> float:
        if call_cost_usd < 0:
            raise ValueError("call_cost_usd nao pode ser negativo")
        if self.spent_usd + call_cost_usd > self.max_cost_usd:
            raise BudgetExceededError(
                f"teto de orcamento excedido ({self.spent_usd + call_cost_usd:.4f} > {self.max_cost_usd:.4f} USD)"
            )
        self.spent_usd += call_cost_usd
        return round(self.spent_usd, 6)


def run_ablation_h3(
    document_text: str,
    candidates: list[CandidateField],
    require_span_and_abstention: bool,
) -> list[ValidatedField]:
    """Ablação offline H3 (Seção 14): compara extração automática com e sem exigência de trecho/abstenção.

    Nenhuma saída da ablação é publicada sem revisão (`published=False` em ambas as condições).
    """
    if require_span_and_abstention:
        return validate_and_abstain(document_text, candidates)

    out: list[ValidatedField] = []
    for c in candidates:
        warnings: list[str] = ["H3_ABLATION: sem exigencia de trecho literal"]
        orig = sanitize_data_only(c.original_value, c.field_name, warnings)
        norm = sanitize_data_only(c.normalized_value, c.field_name, warnings)
        quote = sanitize_data_only(c.quoted_text, c.field_name, warnings)
        out.append(
            ValidatedField(
                field_name=c.field_name,
                original_value=orig,
                normalized_value=norm,
                absence_status=c.absence_status,
                section=c.section,
                page=c.page,
                locator=c.locator,
                quoted_text=quote,
                review_status="ABLACAO_OFFLINE_H3",
                published=False,
                warnings=warnings,
            )
        )
    return out


