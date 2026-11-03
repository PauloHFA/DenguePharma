"""Construção e projeção do Grafo de Evidências Clínicas (Eixo E - REQ-ANA-008).

Regras formais:
- ONDE o grafo estiver habilitado, o sistema deve gerar arestas substância-estudo-desfecho-comparador
  apenas a partir de campos aprovados.
- Critério de aceitação ACC-ANA-008: Dado um campo em rascunho (RASCUNHO, RASCUNHO_IA, EM_REVISAO),
  quando o grafo for construído, então ele NÃO gera aresta.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    type: str  # 'SUBSTANCE', 'STUDY', 'OUTCOME', 'COMPARATOR'
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str  # 'AVALIA', 'MENSURA', 'COMPARADO_COM'
    evidence_status: str  # estritamente 'APROVADO'
    study_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_evidence_network(
    candidate_records: Sequence[Mapping[str, Any]],
    enabled: bool = True,
) -> dict[str, Any]:
    """Constrói o Grafo de Evidências garantindo que apenas campos aprovados gerem arestas (REQ-ANA-008)."""
    if not enabled:
        return {
            "enabled": False,
            "nodes": [],
            "edges": [],
            "total_nodes": 0,
            "total_edges": 0,
            "notice": "Grafo de evidências desabilitado na configuração.",
        }

    nodes_map: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    drafts_ignored_count = 0

    for rec in candidate_records:
        status = str(rec.get("review_status", rec.get("status", "RASCUNHO"))).strip().upper()

        # REQ-ANA-008 / ACC-ANA-008: Campos em rascunho NÃO geram aresta
        if status != "APROVADO":
            drafts_ignored_count += 1
            continue

        study_id = str(rec["study_id"]).strip()
        substance = str(rec["substance"]).strip()
        outcome = str(rec["outcome"]).strip()
        comparator = str(rec.get("comparator", "PLACEBO")).strip()

        sub_node_id = f"sub-{substance.lower().replace(' ', '-')}"
        std_node_id = f"std-{study_id.lower().replace(' ', '-')}"
        out_node_id = f"out-{outcome.lower().replace(' ', '-')}"
        cmp_node_id = f"cmp-{comparator.lower().replace(' ', '-')}"

        # Adiciona nós ao grafo
        if sub_node_id not in nodes_map:
            nodes_map[sub_node_id] = GraphNode(
                id=sub_node_id,
                label=substance,
                type="SUBSTANCE",
                metadata={"title": f"Fármaco / Substância: {substance}"},
            )

        if std_node_id not in nodes_map:
            nodes_map[std_node_id] = GraphNode(
                id=std_node_id,
                label=study_id,
                type="STUDY",
                metadata={"title": f"Estudo Clínico: {study_id}"},
            )

        if out_node_id not in nodes_map:
            nodes_map[out_node_id] = GraphNode(
                id=out_node_id,
                label=outcome,
                type="OUTCOME",
                metadata={"title": f"Desfecho Clínico: {outcome}"},
            )

        if cmp_node_id not in nodes_map:
            nodes_map[cmp_node_id] = GraphNode(
                id=cmp_node_id,
                label=comparator,
                type="COMPARATOR",
                metadata={"title": f"Comparador: {comparator}"},
            )

        # Gera arestas do quadrilátero substância-estudo-desfecho-comparador
        edges.append(
            GraphEdge(
                source=sub_node_id,
                target=std_node_id,
                relation="AVALIA",
                evidence_status="APROVADO",
                study_id=study_id,
            )
        )
        edges.append(
            GraphEdge(
                source=std_node_id,
                target=out_node_id,
                relation="MENSURA",
                evidence_status="APROVADO",
                study_id=study_id,
            )
        )
        edges.append(
            GraphEdge(
                source=std_node_id,
                target=cmp_node_id,
                relation="COMPARADO_COM",
                evidence_status="APROVADO",
                study_id=study_id,
            )
        )

    return {
        "enabled": True,
        "nodes": [n.to_dict() for n in nodes_map.values()],
        "edges": [e.to_dict() for e in edges],
        "total_nodes": len(nodes_map),
        "total_edges": len(edges),
        "drafts_ignored_count": drafts_ignored_count,
        "safeguard_verified": all(e.evidence_status == "APROVADO" for e in edges),
        "notice": "Apenas campos formalmente aprovados geram arestas na rede (REQ-ANA-008).",
    }

