import io
import json
import pytest
from unittest.mock import MagicMock

from denguepharma_workers.extractor import BudgetGuard, BudgetExceededError
from denguepharma_workers.llm_adapter import (
    LLMExtractor,
    calculate_call_cost,
    estimate_tokens,
    parse_llm_json_response,
    MODEL_PRICING,
)


def test_calculate_call_cost_standard_models():
    # 1.000.000 prompt tokens + 1.000.000 completion tokens
    cost_mini = calculate_call_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost_mini == round(0.150 + 0.600, 6)

    cost_gemini = calculate_call_cost("gemini-1.5-flash", 1_000_000, 1_000_000)
    assert cost_gemini == round(0.075 + 0.300, 6)

    # 1.000 prompt tokens + 500 completion tokens no gpt-4o-mini
    # in: 1000 * 0.00000015 = 0.00015
    # out: 500 * 0.00000060 = 0.00030
    # total = 0.00045 USD
    assert calculate_call_cost("gpt-4o-mini", 1000, 500) == 0.00045


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") == max(1, len("hello world") // 4)


def test_parse_llm_json_response_with_markdown_fences():
    raw_markdown = """```json
    {
      "fields": [
        {
          "field_name": "substance",
          "original_value": "Chloroquine",
          "normalized_value": "chloroquine",
          "absence_status": "PRESENTE",
          "section": "Methods",
          "locator": "p.3",
          "quoted_text": "patients received chloroquine 500mg daily",
          "denominator": null
        }
      ]
    }
    ```"""
    candidates = parse_llm_json_response(raw_markdown)
    assert len(candidates) == 1
    assert candidates[0].field_name == "substance"
    assert candidates[0].normalized_value == "chloroquine"
    assert candidates[0].quoted_text == "patients received chloroquine 500mg daily"


def test_parse_llm_json_response_invalid_raises():
    with pytest.raises(ValueError, match="JSON válido"):
        parse_llm_json_response("Não é JSON válido de jeito nenhum")

    with pytest.raises(ValueError, match="lista em 'fields'"):
        parse_llm_json_response('{"status": "ok"}')


def test_llm_extractor_abstention_on_hallucination():
    """Cenário T4: Se a citação literal não existir no texto-fonte, força INCERTO."""
    doc_text = "This clinical study evaluated oral acetaminophen in adult dengue patients."
    
    # Modelo alucina citando trecho inexistente
    def mock_hallucinating_caller(sys_p, user_p):
        resp = {
            "fields": [
                {
                    "field_name": "substance",
                    "original_value": "Ivermectin",
                    "normalized_value": "ivermectin",
                    "absence_status": "PRESENTE",
                    "section": "Results",
                    "locator": "line 12",
                    "quoted_text": "ivermectin significantly reduced viral load",  # Inexistente no doc_text
                }
            ]
        }
        return json.dumps(resp), 150, 80, {"mock": True}

    extractor = LLMExtractor(
        provider="mock",
        model="gpt-4o-mini",
        custom_caller=mock_hallucinating_caller,
    )

    result = extractor.extract(document_id="DOC-99", document_text=doc_text)
    assert len(result.fields) == 1
    vf = result.fields[0]
    # Deve ser rebaixado para INCERTO e normalized_value nulo
    assert vf.absence_status == "INCERTO"
    assert vf.normalized_value is None
    assert vf.review_status == "RASCUNHO_IA"
    assert vf.published is False
    assert any("sem trecho de suporte literal" in w for w in vf.warnings)


def test_llm_extractor_literal_support_success():
    """Valida extração bem-sucedida quando trecho existe literalmente."""
    doc_text = "In a randomized trial, chloroquine was administered to 100 adult patients with acute dengue."
    
    def mock_faithful_caller(sys_p, user_p):
        resp = {
            "fields": [
                {
                    "field_name": "substance",
                    "original_value": "chloroquine",
                    "normalized_value": "chloroquine",
                    "absence_status": "PRESENTE",
                    "section": "Methods",
                    "locator": "para 1",
                    "quoted_text": "chloroquine was administered to 100 adult patients",
                }
            ]
        }
        return json.dumps(resp), 200, 100, {"mock": True}

    extractor = LLMExtractor(
        provider="mock",
        model="gpt-4o-mini",
        custom_caller=mock_faithful_caller,
    )

    result = extractor.extract(document_id="DOC-101", document_text=doc_text)
    assert len(result.fields) == 1
    vf = result.fields[0]
    assert vf.absence_status == "PRESENTE"
    assert vf.normalized_value == "chloroquine"
    assert vf.quoted_text == "chloroquine was administered to 100 adult patients"
    assert result.prompt_tokens == 200
    assert result.completion_tokens == 100
    assert result.call_cost_usd > 0
    assert len(result.idempotency_key) == 64


def test_llm_extractor_budget_guard_enforcement():
    """Verifica que o BudgetGuard bloqueia chamadas quando o custo acumulado estoura o teto."""
    doc_text = "Treatment with balapiravir in dengue infected individuals."
    
    # Teto extremamente baixo: 0.0001 USD
    guard = BudgetGuard(max_cost_usd=0.0001)

    def mock_costly_caller(sys_p, user_p):
        # 10.000 prompt + 5.000 completion = ~0.0045 USD no gpt-4o-mini
        resp = {"fields": []}
        return json.dumps(resp), 10_000, 5_000, {"mock": True}

    extractor = LLMExtractor(
        provider="mock",
        model="gpt-4o-mini",
        budget_guard=guard,
        custom_caller=mock_costly_caller,
    )

    with pytest.raises(BudgetExceededError, match="teto de orcamento excedido"):
        extractor.extract(document_id="DOC-BUDGET-1", document_text=doc_text)


def test_llm_extractor_openai_http_mocked():
    """Testa integração com contrato da API OpenAI via mock de urlopener."""
    doc_text = "Trial comparing prednisolone vs placebo in dengue shock syndrome."
    
    mock_response = MagicMock()
    openai_json = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "fields": [
                            {
                                "field_name": "substance",
                                "original_value": "prednisolone",
                                "normalized_value": "prednisolone",
                                "absence_status": "PRESENTE",
                                "section": "Abstract",
                                "locator": "line 1",
                                "quoted_text": "prednisolone vs placebo",
                            }
                        ]
                    })
                }
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165},
    }
    mock_response.read.return_value = json.dumps(openai_json).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    mock_opener = MagicMock(return_value=mock_response)

    extractor = LLMExtractor(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test-key",
        urlopener=mock_opener,
    )

    result = extractor.extract(document_id="DOC-OPENAI-1", document_text=doc_text)
    assert result.provider == "openai"
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 45
    assert len(result.fields) == 1
    assert result.fields[0].normalized_value == "prednisolone"
    assert result.fields[0].absence_status == "PRESENTE"


def test_llm_extractor_gemini_http_mocked():
    """Testa integração com contrato da API Google Gemini via mock de urlopener."""
    doc_text = "Study of lovastatin in adult patients with dengue."
    
    mock_response = MagicMock()
    gemini_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "fields": [
                                    {
                                        "field_name": "substance",
                                        "original_value": "lovastatin",
                                        "normalized_value": "lovastatin",
                                        "absence_status": "PRESENTE",
                                        "section": "Title",
                                        "locator": "title",
                                        "quoted_text": "lovastatin in adult patients",
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 95, "candidatesTokenCount": 38},
    }
    mock_response.read.return_value = json.dumps(gemini_json).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    mock_opener = MagicMock(return_value=mock_response)

    extractor = LLMExtractor(
        provider="gemini",
        model="gemini-1.5-flash",
        api_key="gemini-test-key",
        urlopener=mock_opener,
    )

    result = extractor.extract(document_id="DOC-GEMINI-1", document_text=doc_text)
    assert result.provider == "gemini"
    assert result.prompt_tokens == 95
    assert result.completion_tokens == 38
    assert len(result.fields) == 1
    assert result.fields[0].normalized_value == "lovastatin"
    assert result.fields[0].absence_status == "PRESENTE"
