"""Testes para geração do Grafo de Evidências estritamente a partir de campos aprovados (REQ-ANA-008)."""
from __future__ import annotations

import pytest

from denguepharma_analytics.analyses.evidence_graph import build_evidence_network


@pytest.mark.requirement("REQ-ANA-008")
def test_draft_fields_do_not_generate_graph_edges():
    """Valida o critério de aceitação ACC-ANA-008:

    Dado um campo em rascunho (RASCUNHO, RASCUNHO_IA, EM_REVISAO),
    quando o grafo for construído, então ele NÃO gera aresta.
    Apenas registros com status 'APROVADO' geram arestas na rede.
    """
    records = [
        # Registro 1: Rascunho da IA (não aprovado)
        {
            "study_id": "NCT01230001",
            "substance": "Ivermectina",
            "outcome": "Clareamento Viral",
            "comparator": "Placebo",
            "review_status": "RASCUNHO_IA",
        },
        # Registro 2: Em revisão clínica (não adjudicado)
        {
            "study_id": "NCT01230002",
            "substance": "Cloroquina",
            "outcome": "Duração da Febre",
            "comparator": "Cuidado Padrão",
            "review_status": "EM_REVISAO",
        },
        # Registro 3: Formalmente APROVADO pela adjudicação
        {
            "study_id": "NCT01230003",
            "substance": "Celgosivir",
            "outcome": "Redução de Carga Viral",
            "comparator": "Placebo",
            "review_status": "APROVADO",
        },
        # Registro 4: Rejeitado
        {
            "study_id": "NCT01230004",
            "substance": "Balapiravir",
            "outcome": "Progressão Grave",
            "comparator": "Placebo",
            "review_status": "REJEITADO",
        },
    ]

    # Constrói o grafo com a lista mista
    graph = build_evidence_network(records, enabled=True)

    assert graph["enabled"] is True
    assert graph["drafts_ignored_count"] == 3  # RASCUNHO_IA, EM_REVISAO, REJEITADO

    # Apenas o estudo aprovado (Celgosivir) deve gerar arestas
    edges = graph["edges"]
    assert len(edges) == 3  # substância->estudo, estudo->desfecho, estudo->comparador

    # Nenhuma aresta pode pertencer aos estudos em rascunho
    for edge in edges:
        assert edge["study_id"] == "NCT01230003"
        assert edge["evidence_status"] == "APROVADO"
        assert "ivermectina" not in edge["source"] and "ivermectina" not in edge["target"]
        assert "cloroquina" not in edge["source"] and "cloroquina" not in edge["target"]
        assert "balapiravir" not in edge["source"] and "balapiravir" not in edge["target"]

    # Se passarmos APENAS rascunhos, o grafo NÃO deve ter nenhuma aresta
    only_drafts = [
        {
            "study_id": "NCT99999999",
            "substance": "Droga X",
            "outcome": "Mortalidade",
            "comparator": "Placebo",
            "review_status": "RASCUNHO",
        }
    ]
    empty_edges_graph = build_evidence_network(only_drafts, enabled=True)
    assert len(empty_edges_graph["edges"]) == 0
    assert empty_edges_graph["total_edges"] == 0
    assert empty_edges_graph["drafts_ignored_count"] == 1


@pytest.mark.requirement("REQ-ANA-008")
def test_disabled_graph_generates_no_edges():
    """Valida comportamento quando o grafo estiver desabilitado."""
    records = [
        {
            "study_id": "NCT01230003",
            "substance": "Celgosivir",
            "outcome": "Redução de Carga Viral",
            "comparator": "Placebo",
            "review_status": "APROVADO",
        }
    ]
    graph = build_evidence_network(records, enabled=False)
    assert graph["enabled"] is False
    assert len(graph["nodes"]) == 0
    assert len(graph["edges"]) == 0
