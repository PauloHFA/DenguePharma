import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

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
          purpose: null,
          design: null,
          serotype: null,
          phase: null,
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
    const snap = await api<Record<string, unknown>>(session, `/api/reports/${id}/export?format=json`);
    setPreviewJson(JSON.stringify(snap, null, 2));
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
          placeholder="Filtrar substância (opcional)"
          value={substanceFilter}
          onChange={(e) => setSubstanceFilter(e.target.value)}
        />
        <select value={contextFilter} onChange={(e) => setContextFilter(e.target.value)} aria-label="Contexto">
          <option value="">Todos os contextos</option>
          <option value="HUMANO">HUMANO</option>
          <option value="ANIMAL">ANIMAL</option>
          <option value="IN_VITRO">IN_VITRO</option>
          <option value="IN_SILICO">IN_SILICO</option>
        </select>
        <button type="button" onClick={generateReport}>Gerar Snapshot de Relatório</button>
      </div>

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
                <a href={`/api/reports/${r.id}/export?format=csv`} target="_blank" rel="noreferrer">CSV</a>{" "}
                <a href={`/api/reports/${r.id}/export?format=pdf`} target="_blank" rel="noreferrer">PDF</a>
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
