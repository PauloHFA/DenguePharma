import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

interface Protocol { id: string; code: string; version: number; status: string }
interface Run { id: string; dictionary_version: string; status: string; created_at: string; published: boolean }

export function CorpusPanel() {
  const { session } = useAuth();
  const [protocols, setProtocols] = useState<Protocol[]>([]), [protocol, setProtocol] = useState("");
  const [runs, setRuns] = useState<Run[]>([]), [previous, setPrevious] = useState("");
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const allowed = session?.roles.some(r => ["PESQUISADOR", "ADMINISTRADOR"].includes(r));
  useEffect(() => {
    if (!session || !allowed) return;
    let active = true;
    api<Protocol[]>(session, "/api/protocols").then(rows => { if (active) setProtocols(rows.filter(p => p.status !== "DRAFT")); }).catch(e => { if (active) setError(e.message); });
    const load = () => api<Run[]>(session, "/api/analyses").then(rows => { if (active) setRuns(rows.filter(r => r.dictionary_version === "corpus-v3.0")); }).catch(e => { if (active) setError(e.message); });
    void load(); const timer = setInterval(() => void load(), 5000);
    return () => { active = false; clearInterval(timer); };
  }, [session, allowed]);
  if (!session || !allowed) return null;
  async function create() {
    if (!session) return; setBusy(true); setError("");
    try { await api(session, "/api/analyses/corpus", { method: "POST", body: JSON.stringify({ protocolId: protocol, previousAnalysisId: previous || null }) }); setRuns((await api<Run[]>(session, "/api/analyses")).filter(r => r.dictionary_version === "corpus-v3.0")); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function publish(id: string) {
    if (!session) return; setBusy(true); setError("");
    try { await api(session, `/api/analyses/${id}/publish`, { method: "POST", body: "{}" }); setRuns(rows => rows.map(r => r.id === id ? { ...r, published: true } : r)); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <section><h2>Panorama do corpus coletado</h2><p>Gera análises dos metadados deste protocolo e um mapa separado dos campos revisados. A publicação disponibiliza os artefatos no dashboard aberto.</p>
    {error && <p role="alert">{error}</p>}
    <label>Protocolo registrado <select value={protocol} onChange={e => setProtocol(e.target.value)}><option value="">Selecione</option>{protocols.map(p => <option key={p.id} value={p.id}>{p.code} v{p.version}</option>)}</select></label>
    <label>Comparar com execução anterior <select value={previous} onChange={e => setPrevious(e.target.value)}><option value="">Sem comparação</option>{runs.map(r => <option key={r.id} value={r.id}>{r.id} · {r.created_at}</option>)}</select></label>
    <button disabled={!protocol || busy} onClick={() => void create()}>Gerar panorama do corpus</button>
    {!runs.length ? <p>Nenhum panorama solicitado.</p> : <table><thead><tr><th>Execução</th><th>Estado</th><th>Publicação</th></tr></thead><tbody>{runs.map(r => <tr key={r.id}><td>{r.id}</td><td>{r.status}</td><td>{r.published ? <a href="/">Ver dashboard</a> : <button disabled={busy || r.status !== "COMPLETED"} onClick={() => void publish(r.id)}>Publicar no dashboard</button>}</td></tr>)}</tbody></table>}
  </section>;
}
