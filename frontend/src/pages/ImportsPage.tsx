import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api";

interface Run {
  id: string;
  protocol_id: string;
  protocol_code: string;
  protocol_version: number;
  source: string;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  records_seen: number;
  records_created: number;
  records_updated: number;
  records_unchanged: number;
  total_returned: number | null;
  last_error: string | null;
  executed_at: string;
}

interface Protocol {
  id: string;
  code: string;
  version: number;
  status: string;
  sources: string[];
}

const STATUS_LABEL: Record<Run["status"], string> = {
  RUNNING: "Em andamento",
  COMPLETED: "Concluída",
  FAILED: "Falhou (retomável)",
};

export function ImportsPage() {
  const { session } = useAuth();
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [protocolId, setProtocolId] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) return;
    try {
      setRuns(await api<Run[]>(session, "/api/imports"));
      const all = await api<Protocol[]>(session, "/api/protocols");
      setProtocols(all.filter((p) => p.status !== "DRAFT"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar.");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  // Atualiza enquanto houver importação em andamento.
  useEffect(() => {
    if (!runs?.some((r) => r.status === "RUNNING")) return;
    const t = setInterval(() => void load(), 3000);
    return () => clearInterval(t);
  }, [runs, load]);

  async function start() {
    if (!session) return;
    try {
      await api(session, "/api/imports", { method: "POST", body: JSON.stringify({ protocolId, source }) });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao iniciar.");
    }
  }

  async function resume(id: string) {
    if (!session) return;
    try {
      await api(session, `/api/imports/${id}/resume`, { method: "POST" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao retomar.");
    }
  }

  const selected = protocols.find((p) => p.id === protocolId);

  return (
    <section aria-labelledby="t">
      <h1 id="t">Importações</h1>
      <p>Coletas do PubMed e do ClinicalTrials.gov com checkpoint. Repetir a coleta não duplica estudos.</p>
      {error && <p role="alert" className="error">Erro: {error}</p>}

      <div className="stack">
        <label htmlFor="i-protocol">Protocolo registrado</label>
        <select id="i-protocol" value={protocolId} onChange={(e) => { setProtocolId(e.target.value); setSource(""); }}>
          <option value="">Selecione…</option>
          {protocols.map((p) => (
            <option key={p.id} value={p.id}>{p.code} v{p.version}</option>
          ))}
        </select>
        <label htmlFor="i-source">Fonte</label>
        <select id="i-source" value={source} onChange={(e) => setSource(e.target.value)} disabled={!selected}>
          <option value="">Selecione…</option>
          {selected?.sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button type="button" disabled={!protocolId || !source} onClick={start}>Iniciar importação</button>
      </div>

      {runs === null ? (
        <p role="status">Carregando…</p>
      ) : runs.length === 0 ? (
        <div className="empty" role="status">
          <strong>Estado vazio:</strong> Nenhuma importação executada. Atualização pendente até a primeira coleta.
        </div>
      ) : (
        <table>
          <caption>Importações</caption>
          <thead>
            <tr><th>Início</th><th>Protocolo</th><th>Fonte</th><th>Status</th><th>Vistos</th><th>Novos</th><th>Atualizados</th><th>Sem mudança</th><th>Ações</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{new Date(r.executed_at).toLocaleString("pt-BR")}</td>
                <td>{r.protocol_code} v{r.protocol_version}</td>
                <td>{r.source}</td>
                <td>
                  {STATUS_LABEL[r.status]}
                  {r.last_error && <div className="error">{r.last_error}</div>}
                </td>
                <td>{r.records_seen}{r.total_returned != null ? ` / ${r.total_returned}` : ""}</td>
                <td>{r.records_created}</td>
                <td>{r.records_updated}</td>
                <td>{r.records_unchanged}</td>
                <td>{r.status === "FAILED" && <button type="button" onClick={() => resume(r.id)}>Retomar</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

