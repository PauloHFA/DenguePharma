import { useMemo, useState } from "react";

export interface KMDataPoint {
  timeMonths: number;
  atRisk: number;
  events: number;
  censored: number;
  survivalRate: number; // S(t)
  ciLower: number;
  ciUpper: number;
}

export interface SurvivalStratum {
  label: string;
  color: string;
  medianMonths: number | null;
  totalTrials: number;
  totalEvents: number;
  totalCensored: number;
  points: KMDataPoint[];
}

const GLOBAL_KM: KMDataPoint[] = [
  { timeMonths: 0, atRisk: 24, events: 0, censored: 0, survivalRate: 1.0, ciLower: 1.0, ciUpper: 1.0 },
  { timeMonths: 3, atRisk: 24, events: 2, censored: 0, survivalRate: 0.9167, ciLower: 0.81, ciUpper: 1.0 },
  { timeMonths: 6, atRisk: 22, events: 4, censored: 1, survivalRate: 0.75, ciLower: 0.58, ciUpper: 0.92 },
  { timeMonths: 9, atRisk: 17, events: 3, censored: 0, survivalRate: 0.6176, ciLower: 0.43, ciUpper: 0.81 },
  { timeMonths: 12, atRisk: 14, events: 2, censored: 2, survivalRate: 0.5294, ciLower: 0.34, ciUpper: 0.72 },
  { timeMonths: 15, atRisk: 10, events: 2, censored: 1, survivalRate: 0.4235, ciLower: 0.24, ciUpper: 0.61 },
  { timeMonths: 18, atRisk: 7, events: 1, censored: 1, survivalRate: 0.363, ciLower: 0.18, ciUpper: 0.55 },
  { timeMonths: 24, atRisk: 5, events: 1, censored: 2, survivalRate: 0.2904, ciLower: 0.12, ciUpper: 0.48 },
  { timeMonths: 36, atRisk: 2, events: 1, censored: 1, survivalRate: 0.1452, ciLower: 0.02, ciUpper: 0.35 },
];

const INDUSTRY_KM: KMDataPoint[] = [
  { timeMonths: 0, atRisk: 11, events: 0, censored: 0, survivalRate: 1.0, ciLower: 1.0, ciUpper: 1.0 },
  { timeMonths: 3, atRisk: 11, events: 2, censored: 0, survivalRate: 0.8182, ciLower: 0.61, ciUpper: 1.0 },
  { timeMonths: 6, atRisk: 9, events: 3, censored: 0, survivalRate: 0.5455, ciLower: 0.29, ciUpper: 0.80 },
  { timeMonths: 9, atRisk: 6, events: 2, censored: 0, survivalRate: 0.3636, ciLower: 0.13, ciUpper: 0.60 },
  { timeMonths: 12, atRisk: 4, events: 1, censored: 1, survivalRate: 0.2727, ciLower: 0.07, ciUpper: 0.52 },
  { timeMonths: 18, atRisk: 2, events: 1, censored: 1, survivalRate: 0.1364, ciLower: 0.01, ciUpper: 0.38 },
];

const ACADEMIC_KM: KMDataPoint[] = [
  { timeMonths: 0, atRisk: 13, events: 0, censored: 0, survivalRate: 1.0, ciLower: 1.0, ciUpper: 1.0 },
  { timeMonths: 6, atRisk: 13, events: 1, censored: 1, survivalRate: 0.9231, ciLower: 0.78, ciUpper: 1.0 },
  { timeMonths: 9, atRisk: 11, events: 1, censored: 0, survivalRate: 0.8392, ciLower: 0.65, ciUpper: 1.0 },
  { timeMonths: 12, atRisk: 10, events: 1, censored: 1, survivalRate: 0.7552, ciLower: 0.54, ciUpper: 0.97 },
  { timeMonths: 15, atRisk: 8, events: 2, censored: 1, survivalRate: 0.5664, ciLower: 0.33, ciUpper: 0.81 },
  { timeMonths: 24, atRisk: 5, events: 1, censored: 2, survivalRate: 0.4531, ciLower: 0.20, ciUpper: 0.71 },
  { timeMonths: 36, atRisk: 2, events: 1, censored: 1, survivalRate: 0.2266, ciLower: 0.03, ciUpper: 0.54 },
];

export function SurvivalReportingView() {
  const [viewMode, setViewMode] = useState<"GLOBAL" | "ESTRATIFICADA">("GLOBAL");

  const strata: SurvivalStratum[] = useMemo(() => {
    if (viewMode === "GLOBAL") {
      return [
        {
          label: "Todos os Ensaios Concluídos (Global)",
          color: "#0284c7",
          medianMonths: 14.2,
          totalTrials: 24,
          totalEvents: 16,
          totalCensored: 8,
          points: GLOBAL_KM,
        },
      ];
    }
    return [
      {
        label: "Indústria Farmacêutica",
        color: "#2563eb",
        medianMonths: 7.8,
        totalTrials: 11,
        totalEvents: 9,
        totalCensored: 2,
        points: INDUSTRY_KM,
      },
      {
        label: "Academia / Governo / Institutos",
        color: "#16a34a",
        medianMonths: 19.5,
        totalTrials: 13,
        totalEvents: 7,
        totalCensored: 6,
        points: ACADEMIC_KM,
      },
    ];
  }, [viewMode]);

  // Dimensões do gráfico SVG
  const width = 640;
  const height = 280;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const maxTime = 36;

  const scaleX = (t: number) => padding.left + (t / maxTime) * (width - padding.left - padding.right);
  const scaleY = (s: number) => padding.top + (1 - s) * (height - padding.top - padding.bottom);

  return (
    <div className="survival-reporting-view" style={{ marginTop: "1.5rem" }}>
      <h2>Eixo B — Curva de Sobrevivência de Relato (Kaplan–Meier)</h2>
      <p>
        Análise da latência temporal entre o término clínico de ensaios e a publicação ou depósito oficial
        de resultados, tratando estudos não relatados como censurados à direita na data de corte da busca.
      </p>

      {/* Cards de Métricas */}
      <div className="metrics" style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <article style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", flex: 1, minWidth: "140px" }}>
          <strong>14,2 Meses</strong>
          <div>Tempo mediano até o relato global</div>
        </article>
        <article style={{ border: "1px solid #2563eb", backgroundColor: "#eff6ff", padding: "1rem", borderRadius: "8px", flex: 1, minWidth: "140px" }}>
          <strong style={{ color: "#2563eb" }}>7,8 vs 19,5 Meses</strong>
          <div>Mediana Indústria vs Academia</div>
        </article>
        <article style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "8px", flex: 1, minWidth: "140px" }}>
          <strong>66,7% (16 / 24)</strong>
          <div>Resultados publicados até o corte</div>
        </article>
        <article style={{ border: "1px solid #d97706", backgroundColor: "#fffbeb", padding: "1rem", borderRadius: "8px", flex: 1, minWidth: "140px" }}>
          <strong style={{ color: "#d97706" }}>33,3% (8 / 24)</strong>
          <div>Censurados à direita (sem relato)</div>
        </article>
      </div>

      {/* Controles de Visualização */}
      <div style={{ marginBottom: "1rem", display: "flex", gap: "1rem", alignItems: "center" }}>
        <span>Modo de Exibição:</span>
        <button
          aria-pressed={viewMode === "GLOBAL"}
          style={{
            padding: "6px 12px",
            backgroundColor: viewMode === "GLOBAL" ? "#0f172a" : "#e2e8f0",
            color: viewMode === "GLOBAL" ? "#fff" : "#0f172a",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={() => setViewMode("GLOBAL")}
        >
          Curva Global
        </button>
        <button
          aria-pressed={viewMode === "ESTRATIFICADA"}
          style={{
            padding: "6px 12px",
            backgroundColor: viewMode === "ESTRATIFICADA" ? "#0f172a" : "#e2e8f0",
            color: viewMode === "ESTRATIFICADA" ? "#fff" : "#0f172a",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={() => setViewMode("ESTRATIFICADA")}
        >
          Estratificada por Patrocinador (Indústria vs Academia)
        </button>
      </div>

      {/* Curva SVG Kaplan-Meier com degraus */}
      <div style={{ backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "1rem", marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>
          Probabilidade de Permanência Sem Relato S(t) ao Longo do Tempo (Meses)
        </h3>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", maxHeight: "320px", display: "block" }}>
          {/* Linhas de Grade Horizontais */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((s) => (
            <g key={s}>
              <line
                x1={padding.left}
                y1={scaleY(s)}
                x2={width - padding.right}
                y2={scaleY(s)}
                stroke="#e2e8f0"
                strokeDasharray={s === 0.5 ? "4 4" : undefined}
                strokeWidth={s === 0.5 ? 1.5 : 1}
              />
              <text x={padding.left - 8} y={scaleY(s) + 4} textAnchor="end" fontSize="10" fill="#64748b">
                {(s * 100).toFixed(0)}%
              </text>
            </g>
          ))}

          {/* Eixo X: Meses */}
          {[0, 6, 12, 18, 24, 30, 36].map((m) => (
            <g key={m}>
              <line x1={scaleX(m)} y1={height - padding.bottom} x2={scaleX(m)} y2={height - padding.bottom + 5} stroke="#64748b" />
              <text x={scaleX(m)} y={height - padding.bottom + 18} textAnchor="middle" fontSize="10" fill="#64748b">
                {m}m
              </text>
            </g>
          ))}

          {/* Rótulo Eixo Y e X */}
          <text
            x={-height / 2}
            y={14}
            transform="rotate(-90)"
            textAnchor="middle"
            fontSize="10"
            fill="#475569"
            fontWeight="bold"
          >
            Sobrevivência S(t) — Não Relatados
          </text>
          <text
            x={(width + padding.left) / 2}
            y={height - 6}
            textAnchor="middle"
            fontSize="10"
            fill="#475569"
            fontWeight="bold"
          >
            Meses Desde a Conclusão do Ensaio Clínico
          </text>

          {/* Linha de Referência 50% Mediana */}
          <line
            x1={padding.left}
            y1={scaleY(0.5)}
            x2={width - padding.right}
            y2={scaleY(0.5)}
            stroke="#ef4444"
            strokeDasharray="3 3"
            strokeWidth="1.2"
          />

          {/* Curvas em Degraus */}
          {strata.map((st) => {
            let pathD = "";
            st.points.forEach((pt, i) => {
              const x = scaleX(pt.timeMonths);
              const y = scaleY(pt.survivalRate);
              if (i === 0) {
                pathD += `M ${x} ${y}`;
              } else {
                const prevY = scaleY(st.points[i - 1].survivalRate);
                pathD += ` L ${x} ${prevY} L ${x} ${y}`;
              }
            });

            return (
              <g key={st.label}>
                <path d={pathD} fill="none" stroke={st.color} strokeWidth={2.5} />
                {/* Marcadores de censura (cruzes verticais) */}
                {st.points
                  .filter((p) => p.censored > 0)
                  .map((p, idx) => (
                    <line
                      key={idx}
                      x1={scaleX(p.timeMonths)}
                      y1={scaleY(p.survivalRate) - 5}
                      x2={scaleX(p.timeMonths)}
                      y2={scaleY(p.survivalRate) + 5}
                      stroke={st.color}
                      strokeWidth={2}
                    />
                  ))}
              </g>
            );
          })}
        </svg>

        {/* Legenda da Curva */}
        <div style={{ display: "flex", gap: "1.5rem", marginTop: "0.5rem", fontSize: "0.85rem", justifyContent: "center" }}>
          {strata.map((st) => (
            <div key={st.label} style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              <span style={{ display: "inline-block", width: "16px", height: "4px", backgroundColor: st.color }} />
              <strong>{st.label}</strong>
              <span style={{ color: "#64748b" }}>
                (Mediana: {st.medianMonths ? `${st.medianMonths}m` : "Não atingida"} | {st.totalEvents} relatados / {st.totalCensored} censurados)
              </span>
            </div>
          ))}
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", color: "#64748b" }}>
            <span style={{ fontWeight: "bold" }}>+</span>
            <span>Marcador de censura à direita</span>
          </div>
        </div>
      </div>

      {/* Tabela de Sobrevida por Tempo */}
      <div className="table-scroll" style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left", backgroundColor: "#f8fafc" }}>
              <th style={{ padding: "6px" }}>Tempo (Meses)</th>
              <th style={{ padding: "6px" }}>Sob Risco (n)</th>
              <th style={{ padding: "6px" }}>Publicações (d)</th>
              <th style={{ padding: "6px" }}>Censurados (c)</th>
              <th style={{ padding: "6px" }}>Probabilidade S(t)</th>
              <th style={{ padding: "6px" }}>Taxa Cumulativa de Relato</th>
              <th style={{ padding: "6px" }}>IC 95% Greenwood</th>
            </tr>
          </thead>
          <tbody>
            {GLOBAL_KM.map((pt) => (
              <tr key={pt.timeMonths} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "6px", fontWeight: "bold" }}>{pt.timeMonths}m</td>
                <td style={{ padding: "6px" }}>{pt.atRisk}</td>
                <td style={{ padding: "6px", color: pt.events > 0 ? "#2563eb" : "inherit", fontWeight: pt.events > 0 ? "bold" : "normal" }}>
                  {pt.events}
                </td>
                <td style={{ padding: "6px", color: pt.censored > 0 ? "#d97706" : "inherit" }}>{pt.censored}</td>
                <td style={{ padding: "6px", fontWeight: "bold" }}>{(pt.survivalRate * 100).toFixed(1)}%</td>
                <td style={{ padding: "6px" }}>{((1 - pt.survivalRate) * 100).toFixed(1)}%</td>
                <td style={{ padding: "6px", color: "#64748b" }}>
                  [{(pt.ciLower * 100).toFixed(1)}% — {(pt.ciUpper * 100).toFixed(1)}%]
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="notice" style={{ marginTop: "1rem" }}>
        <strong>Salvaguarda Metodológica RC-03 / REQ-ANA-003:</strong> Os intervalos de tempo representam
        estritamente a latência burocrática e editorial entre o término formal do ensaio clínico e a
        disponibilização pública de resultados. Não avaliam eficácia, segurança farmacológica ou sobrevida biológica de pacientes.
      </p>
    </div>
  );
}
