import { useEffect, useState } from "react";

interface GraphNode {
  id: string;
  label: string;
  type: "SUBSTANCE" | "TARGET" | "OUTCOME" | "STUDY";
  group: string;
  details: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  evidenceLevel: string;
}

interface EvidenceGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    axis: string;
    title: string;
    notice: string;
    nodeCount: number;
    edgeCount: number;
  };
}

const FALLBACK_GRAPH: EvidenceGraphData = {
  nodes: [
    { id: "tgt-ns5-rdrp", label: "NS5 (RdRp)", type: "TARGET", group: "VIRAL_NAO_ESTRUTURAL", details: "RNA polimerase viral" },
    { id: "tgt-ns3-prot", label: "NS3 (Protease)", type: "TARGET", group: "VIRAL_NAO_ESTRUTURAL", details: "Serino protease clivagem poliproteica" },
    { id: "tgt-protein-e", label: "Proteína E", type: "TARGET", group: "VIRAL_ESTRUTURAL", details: "Ligação ao receptor e fusão" },
    { id: "sub-balapiravir", label: "Balapiravir", type: "SUBSTANCE", group: "ANTIVIRAL_DIRETO", details: "Análogo de nucleosídeo RdRp" },
    { id: "sub-sofosbuvir", label: "Sofosbuvir", type: "SUBSTANCE", group: "ANTIVIRAL_DIRETO", details: "Inibidor de RdRp reposicionado" },
    { id: "sub-ivermectina", label: "Ivermectina", type: "SUBSTANCE", group: "MODULADOR", details: "Inibidor de importina e helicase" },
    { id: "sub-cloroquina", label: "Cloroquina", type: "SUBSTANCE", group: "MODULADOR", details: "Bloqueador de fusão endossomal" },
    { id: "out-clearance", label: "Depuração Viral", type: "OUTCOME", group: "VIROLOGICO", details: "Redução de carga viral" },
    { id: "out-febre", label: "Duração da Febre", type: "OUTCOME", group: "CLINICO", details: "Alívio térmico" },
    { id: "out-grave", label: "Dengue Grave", type: "OUTCOME", group: "GRAVE", details: "Progressão para complicações" },
  ],
  edges: [
    { source: "sub-balapiravir", target: "tgt-ns5-rdrp", relation: "INIBE", evidenceLevel: "ENSAIO_CLINICO" },
    { source: "sub-sofosbuvir", target: "tgt-ns5-rdrp", relation: "INIBE", evidenceLevel: "IN_VITRO" },
    { source: "sub-ivermectina", target: "tgt-ns3-prot", relation: "MODULA", evidenceLevel: "IN_VITRO" },
    { source: "sub-cloroquina", target: "tgt-protein-e", relation: "MODULA_FUSAO", evidenceLevel: "ENSAIO_CLINICO" },
    { source: "tgt-ns5-rdrp", target: "out-clearance", relation: "IMPACTA", evidenceLevel: "MECANISTICO" },
    { source: "tgt-protein-e", target: "out-grave", relation: "IMPACTA", evidenceLevel: "MECANISTICO" },
  ],
  metadata: {
    axis: "E",
    title: "Topologia em Grafo de Rede de Evidências (Eixo E)",
    notice: "Frequência e proximidade em rede não configuram eficácia clínica (Regras RC-01 e RC-04).",
    nodeCount: 10,
    edgeCount: 6,
  },
};

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  SUBSTANCE: { bg: "#dbeafe", border: "#2563eb", text: "#1e40af" },
  TARGET: { bg: "#f3e8ff", border: "#9333ea", text: "#6b21a8" },
  OUTCOME: { bg: "#dcfce7", border: "#16a34a", text: "#166534" },
  STUDY: { bg: "#ffedd5", border: "#ea580c", text: "#9a3412" },
};

export function EvidenceGraphPage() {
  const [data, setData] = useState<EvidenceGraphData>(FALLBACK_GRAPH);
  const [selectedType, setSelectedType] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    fetch("/api/public/evidence-graph")
      .then((res) => (res.ok ? res.json() : null))
      .then((json) => {
        if (json && json.nodes && json.nodes.length > 0) {
          setData(json);
        }
      })
      .catch(() => {
        // Usa dados locais se a rota pública ainda não responder
      });
  }, []);

  const filteredNodes = selectedType
    ? data.nodes.filter((n) => n.type === selectedType)
    : data.nodes;

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const visibleEdges = data.edges.filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  // Calcula coordenadas dos nós em 3 colunas hierárquicas
  const columnMap: Record<string, number> = {
    SUBSTANCE: 80,
    TARGET: 340,
    OUTCOME: 600,
    STUDY: 860,
  };

  const nodesByType: Record<string, GraphNode[]> = {
    SUBSTANCE: filteredNodes.filter((n) => n.type === "SUBSTANCE"),
    TARGET: filteredNodes.filter((n) => n.type === "TARGET"),
    OUTCOME: filteredNodes.filter((n) => n.type === "OUTCOME"),
    STUDY: filteredNodes.filter((n) => n.type === "STUDY"),
  };

  const nodePositions = new Map<string, { x: number; y: number }>();
  Object.entries(nodesByType).forEach(([type, nodesList]) => {
    const x = columnMap[type] ?? 400;
    const spacing = 520 / Math.max(nodesList.length, 1);
    nodesList.forEach((n, idx) => {
      nodePositions.set(n.id, { x, y: 50 + idx * spacing });
    });
  });

  return (
    <section aria-labelledby="graph-heading">
      <h1 id="graph-heading">Grafo de Rede de Evidências Farmacológicas (Eixo E)</h1>
      <p>
        Topologia de conexões entre fármacos candidatos, alvos moleculares (virais e hospedeiro),
        desfechos clínicos de interesse e estudos documentados.
      </p>

      <div className="filter-bar" style={{ display: "flex", gap: "1.5rem", alignItems: "center" }}>
        <label>
          Filtrar Tipo de Nó:{" "}
          <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
            <option value="">Todos os nós</option>
            <option value="SUBSTANCE">Substâncias / Fármacos</option>
            <option value="TARGET">Alvos Moleculares</option>
            <option value="OUTCOME">Desfechos Clínicos</option>
            <option value="STUDY">Estudos / Ensaios</option>
          </select>
        </label>
        <span className="muted">
          Total visível: {filteredNodes.length} nós | {visibleEdges.length} conexões
        </span>
      </div>

      <div style={{ display: "flex", gap: "1rem", margin: "1rem 0" }}>
        {Object.entries(TYPE_COLORS).map(([type, colors]) => (
          <span
            key={type}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              background: colors.bg,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              padding: "0.2rem 0.6rem",
              borderRadius: "4px",
              fontSize: "0.85rem",
              fontWeight: 500,
            }}
          >
            ● {type === "SUBSTANCE" ? "Fármacos" : type === "TARGET" ? "Alvos Moleculares" : type === "OUTCOME" ? "Desfechos" : "Estudos"}
          </span>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "1.5rem", marginTop: "1rem" }}>
        <div style={{ background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", overflow: "hidden", minHeight: "560px", position: "relative" }}>
          <svg width="100%" height="560" viewBox="0 0 960 560" style={{ display: "block" }}>
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
              </marker>
            </defs>

            {/* Linhas de conexão (Arestas) */}
            {visibleEdges.map((e, idx) => {
              const from = nodePositions.get(e.source);
              const to = nodePositions.get(e.target);
              if (!from || !to) return null;
              const isSelected = selectedNode && (selectedNode.id === e.source || selectedNode.id === e.target);
              return (
                <line
                  key={`${e.source}-${e.target}-${idx}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={isSelected ? "#2563eb" : "#cbd5e1"}
                  strokeWidth={isSelected ? 2.5 : 1.2}
                  strokeDasharray={e.evidenceLevel === "IN_VITRO" ? "4,4" : undefined}
                  markerEnd="url(#arrow)"
                />
              );
            })}

            {/* Nós interativos */}
            {filteredNodes.map((n) => {
              const pos = nodePositions.get(n.id) ?? { x: 50, y: 50 };
              const colors = TYPE_COLORS[n.type] ?? { bg: "#f1f5f9", border: "#64748b", text: "#334155" };
              const isSelected = selectedNode?.id === n.id;
              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelectedNode(n)}
                >
                  <circle
                    r={isSelected ? 16 : 12}
                    fill={colors.bg}
                    stroke={isSelected ? "#1e40af" : colors.border}
                    strokeWidth={isSelected ? 3 : 1.8}
                  />
                  <text
                    x={18}
                    y={4}
                    fontSize={11}
                    fontWeight={isSelected ? 700 : 500}
                    fill={colors.text}
                  >
                    {n.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <aside className="card" style={{ padding: "1.2rem", height: "fit-content" }}>
          {selectedNode ? (
            <div>
              <span
                style={{
                  display: "inline-block",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  padding: "0.15rem 0.5rem",
                  borderRadius: "4px",
                  background: TYPE_COLORS[selectedNode.type]?.bg,
                  color: TYPE_COLORS[selectedNode.type]?.text,
                  border: `1px solid ${TYPE_COLORS[selectedNode.type]?.border}`,
                  marginBottom: "0.5rem",
                }}
              >
                {selectedNode.type}
              </span>
              <h3 style={{ margin: "0.2rem 0 0.6rem 0" }}>{selectedNode.label}</h3>
              <p style={{ fontSize: "0.95rem" }}>{selectedNode.details}</p>

              <div style={{ marginTop: "1rem", borderTop: "1px solid #e2e8f0", paddingTop: "0.8rem" }}>
                <strong>Vínculos e Relações Diretas:</strong>
                <ul style={{ paddingLeft: "1.2rem", marginTop: "0.4rem", fontSize: "0.9rem" }}>
                  {data.edges
                    .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                    .map((e, i) => (
                      <li key={i} style={{ marginBottom: "0.3rem" }}>
                        <code>{e.relation}</code> ({e.evidenceLevel}) &rarr;{" "}
                        {e.source === selectedNode.id ? e.target : e.source}
                      </li>
                    ))}
                </ul>
              </div>

              <button
                type="button"
                style={{ marginTop: "1rem", width: "100%", padding: "0.4rem" }}
                onClick={() => setSelectedNode(null)}
              >
                Limpar Seleção
              </button>
            </div>
          ) : (
            <div>
              <h3>Inspeção do Grafo</h3>
              <p className="muted" style={{ fontSize: "0.9rem" }}>
                Clique em qualquer nó do grafo para inspecionar seus detalhes biológicos,
                estudos associados, nível de evidência e conexões mecanísticas.
              </p>
              <div style={{ marginTop: "1rem", background: "#f1f5f9", padding: "0.8rem", borderRadius: "6px", fontSize: "0.85rem" }}>
                <strong>Pilares de Relação:</strong>
                <p style={{ margin: "0.3rem 0" }}>1. <strong>Fármacos &rarr; Alvos:</strong> Inibição enzimática ou modulação de fusão.</p>
                <p style={{ margin: "0.3rem 0" }}>2. <strong>Alvos &rarr; Desfechos:</strong> Hipótese mecanística antiviral.</p>
                <p style={{ margin: "0.3rem 0" }}>3. <strong>Estudos &rarr; Evidências:</strong> Medição clínica documentada.</p>
              </div>
            </div>
          )}
        </aside>
      </div>

      <p className="notice" style={{ marginTop: "1.5rem" }}>
        {data.metadata.notice}
      </p>
    </section>
  );
}

