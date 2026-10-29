import { CorpusPanel } from "./CorpusPanel";
import { useEffect, useState } from "react";
import { api, downloadFile } from "../api";
import { useAuth } from "../auth/AuthContext";
import { AnalysisPanel } from "./AnalysisPanel";

interface ReportSummary {
  id: string;
  created_at: string;
  filters: string;
  study_count: number;
}

export function ReportsPage() {
  const { session } = useAuth();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [contextFilter, setContextFilter] = useState("");
  const [substanceFilter, setSubstanceFilter] = useState("");
  const [extraFilters, setExtraFilters] = useState({ purpose:"", design:"", serotype:"", phase:"" });
  const [previewJson, setPreviewJson] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    const list = await api<ReportSummary[]>(session, "/api/reports");
    setReports(list);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
  }, [session]);

  async function generateReport() {
    if (!session) return;
    setError(null);
    try {
      const created = await api<Record<string, unknown>>(session, "/api/reports", {
        method: "POST",
        body: JSON.stringify({
          substance: substanceFilter || null,
          context: contextFilter || null,
          purpose: extraFilters.purpose || null,
          design: extraFilters.design || null,
          serotype: extraFilters.serotype || null,
          phase: extraFilters.phase || null,
        }),
      });
      setPreviewJson(JSON.stringify(created, null, 2));
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function viewSnapshotJson(id: string) {
    if (!session) return;
    try {
      const snap = await api<Record<string, unknown>>(session, `/api/reports/${id}/export?format=json`);
      setPreviewJson(JSON.stringify(snap, null, 2));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function downloadReport(id: string, format: "csv" | "pdf") {
    if (!session) return;
    setError(null);
    try {
      await downloadFile(session, `/api/reports/${id}/export?format=${format}`, `relatorio-${id}.${format}`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section aria-labelledby="rep-heading">
      <h1 id="rep-heading">Relatórios Auditáveis e Exportação com Snapshot (RF-09, T8)</h1>
      <p>
        Cada relatório congela um snapshot imutável (<code>report_snapshot</code>) referenciando exatamente as versões
        dos documentos-fonte, hashes SHA-256, filtros aplicados, contexto experimental e limitações.
      </p>

      {error && <p role="alert">{error}</p>}

      <div className="filter-bar">
        <input
          aria-label="Substância do relatório"
          placeholder="Filtrar substância (opcional)"
          value={substanceFilter}
          onChange={(e) => setSubstanceFilter(e.target.value)}
        />
        <select value={contextFilter} onChange={(e) => setContextFilter(e.target.value)} aria-label="Contexto">
          <option value="">Todos os contextos</option>
          <option value="HUMANO">HUMANO</option>
          <option value="DESAFIO_CONTROLADO">DESAFIO_CONTROLADO</option>
          <option value="ANIMAL">ANIMAL</option>
          <option value="IN_VITRO">IN_VITRO</option>
          <option value="IN_SILICO">IN_SILICO</option>
        </select>
        {(["purpose", "design", "serotype", "phase"] as const).map(key => <label key={key}>
          {{purpose:"Finalidade", design:"Desenho", serotype:"Sorotipo", phase:"Fase"}[key]}
          <input value={extraFilters[key]} onChange={e => setExtraFilters({...extraFilters,[key]:e.target.value})} />
        </label>)}
        <button type="button" onClick={generateReport}>Gerar Snapshot de Relatório</button>
      </div>
      <CorpusPanel />
      <AnalysisPanel filters={{ substance:substanceFilter || null,context:contextFilter || null,
        purpose:extraFilters.purpose || null,design:extraFilters.design || null,serotype:extraFilters.serotype || null,phase:extraFilters.phase || null }} />

      <table>
        <thead>
          <tr>
            <th>Snapshot ID</th>
            <th>Criado em</th>
            <th>Estudos</th>
            <th>Filtros</th>
            <th>Exportações (PDF / CSV / JSON)</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td><code>{r.id}</code></td>
              <td>{r.created_at}</td>
              <td>{r.study_count}</td>
              <td><code>{r.filters}</code></td>
              <td>
                <button type="button" onClick={() => viewSnapshotJson(r.id)}>Ver JSON</button>{" "}
                <button type="button" onClick={() => downloadReport(r.id, "csv")}>CSV</button>{" "}
                <button type="button" onClick={() => downloadReport(r.id, "pdf")}>PDF</button>
              </td>
            </tr>
          ))}
          {reports.length === 0 && (
            <tr>
              <td colSpan={5}>Nenhum snapshot de relatório gerado até o momento.</td>
            </tr>
          )}
        </tbody>
      </table>

      {previewJson && (
        <div>
          <h2>Inspeção do Snapshot</h2>
          <pre>{previewJson}</pre>
        </div>
      )}
    </section>
  );
}

