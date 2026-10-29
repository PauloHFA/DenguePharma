import { useEffect, useState } from "react";
import { api, downloadFile, readFile } from "../api";
import { useAuth } from "../auth/AuthContext";

type Row = Record<string, unknown>;
type Filters = { substance: string | null; context: string | null; purpose: string | null; design: string | null; phase: string | null; serotype: string | null };
interface Run { dictionary_version?: string; id: string; created_at: string; status: string; study_count: number; input_hash: string; last_error?: string; artifacts?: {name: string}[] }
interface Summary {
  status: string; notice: string; studyCount: number; documentCount: number; reassessmentPendingCount: number;
  contextCounts: Row[]; distributions: Row[]; completeness: Row[]; traceability: Row[]; gaps: Row[];
}
const percent = (value: unknown) => value == null ? "Sem dados" : `${(Number(value) * 100).toFixed(1)}%`;

function ResultTable({ title, rows, columns }: { title: string; rows: Row[]; columns: [string, string][] }) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(rows.length / 100));
  const selectedPage = Math.min(page, totalPages - 1);
  return <section><h4>{title}</h4><div style={{overflowX:"auto"}}><table>
    <caption>{title}</caption><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead>
    <tbody>{rows.slice(selectedPage * 100, (selectedPage + 1) * 100).map((row, index) => <tr key={index}>{columns.map(([key]) => <td key={key}>
      {key === "proportion" ? percent(row[key]) : row[key] == null ? "—" : typeof row[key] === "object" ? JSON.stringify(row[key]) : String(row[key])}
    </td>)}</tr>)}{rows.length === 0 && <tr><td colSpan={columns.length}>Sem dados.</td></tr>}</tbody>
  </table></div>{totalPages > 1 && <div><button type="button" disabled={selectedPage === 0} onClick={() => setPage(selectedPage - 1)}>Página anterior</button>
    <span> Página {selectedPage + 1} de {totalPages} </span><button type="button" disabled={selectedPage + 1 === totalPages} onClick={() => setPage(selectedPage + 1)}>Próxima página</button></div>}</section>;
}

function FigurePreview({ run, name }: { run: string; name: string }) {
  const { session } = useAuth();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!session || !name) return;
    let active = true, created = "";
    setUrl(""); setError("");
    readFile(session, `/api/analyses/${run}/artifacts?name=${encodeURIComponent(name)}`).then(blob => {
      if (active) { created = URL.createObjectURL(blob); setUrl(created); }
    }).catch(e => { if (active) setError((e as Error).message); });
    return () => { active=false; if (created) URL.revokeObjectURL(created); };
  }, [session, run, name]);
  return <figure>{error && <p role="alert">{error}</p>}{url && <img src={url} alt={`Gráfico descritivo: ${name}`} style={{maxWidth:"100%"}} />}<figcaption>{name}</figcaption></figure>;
}

export function AnalysisPanel({ filters }: { filters: Filters }) {
  const { session } = useAuth();
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [figure, setFigure] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const canCreate = session?.roles.some(role => ["PESQUISADOR", "ADMINISTRADOR"].includes(role));
  useEffect(() => {
    if (!session) return;
    let active=true;
    const load=() => api<Run[]>(session, "/api/analyses").then(data => { if (active) setRuns(data.filter(r => r.dictionary_version !== "corpus-v3.0")); }).catch(e => { if (active) setError((e as Error).message); });
    void load(); const timer=setInterval(() => void load(),5000);
    return () => { active=false; clearInterval(timer); };
  }, [session]);
  useEffect(() => {
    if (!session || !selected) return;
    const current = runs.find(run => run.id === selected.id);
    if (current && current.status !== selected.status) void inspect(selected.id);
  }, [runs]);
  async function inspect(id: string) {
    if (!session) return;
    setSummary(null); setFigure(""); setError("");
    try {
      const run=await api<Run>(session, `/api/analyses/${id}`); setSelected(run);
      if (run.status === "COMPLETED") {
        const result=await api<Summary>(session, `/api/analyses/${id}/artifacts?name=summary.json`); setSummary(result);
        setFigure(run.artifacts?.find(a => a.name.endsWith(".png"))?.name ?? "");
      }
    } catch (e) { setError((e as Error).message); }
  }
  async function create() {
    if (!session) return;
    setCreating(true); setError("");
    try {
      const run=await api<Run>(session,"/api/analyses", {method:"POST",body:JSON.stringify(filters)});
      setRuns(await api<Run[]>(session,"/api/analyses")); await inspect(run.id);
    } catch(e) { setError((e as Error).message); } finally { setCreating(false); }
  }
  async function download(id: string, name: string) {
    if (!session) return;
    try { await downloadFile(session,`/api/analyses/${id}/artifacts?name=${encodeURIComponent(name)}`, `analise-${id}-${name.split("/").pop()}`); }
    catch(e) { setError((e as Error).message); }
  }
  return <section aria-labelledby="analyses-heading"><h2 id="analyses-heading">Análises descritivas de evidências revisadas</h2>
    <p>Os filtros acima selecionam valores aprovados individualmente. Cada análise congela sua entrada; campos pendentes e conflitos permanecem explícitos. Uma célula vazia não demonstra ausência de evidência na literatura.</p>
    {canCreate && <button type="button" disabled={creating} onClick={create}>{creating ? "Solicitando análise…" : "Gerar análise descritiva"}</button>}
    {error && <p role="alert">{error}</p>}
    <table><caption>Análises solicitadas</caption><thead><tr><th>Data</th><th>Estado</th><th>Estudos</th><th>Entrada</th><th>Ações</th></tr></thead><tbody>
      {runs.map(run => <tr key={run.id}><td>{run.created_at}</td><td>{run.status}{run.last_error && ` — ${run.last_error}`}</td><td>{run.study_count}</td><td><code>{run.input_hash}</code></td><td>
        <button type="button" onClick={() => inspect(run.id)}>Consultar análise</button>
        <button type="button" onClick={() => download(run.id,"dataset.json")}>Baixar entrada JSON</button>
        {run.status === "COMPLETED" && <button type="button" onClick={() => download(run.id,"bundle.zip")}>Baixar pacote ZIP</button>}
      </td></tr>)}{runs.length === 0 && <tr><td colSpan={5}>Nenhuma análise solicitada.</td></tr>}</tbody></table>
    {selected && !summary && <p role="status">Estado da análise selecionada: {selected.status}. A execução depende do worker ativo.</p>}
    {summary && selected && <article><h3>Resultado descritivo</h3><p>{summary.notice}</p>
      {summary.status === "NO_DATA" ? <p role="status">Sem dados para os filtros selecionados.</p> : <p>{summary.studyCount} estudos; {summary.documentCount} documentos referenciados; {summary.reassessmentPendingCount} estudos com reavaliação pendente.</p>}
      <ResultTable title="Cobertura por contexto" rows={summary.contextCounts} columns={[["context","Contexto"],["layer","Camada"],["count","Estudos"],["denominator","Total do corpus"],["proportion","Proporção"]]} />
      <ResultTable title="Distribuições por contexto" rows={summary.distributions} columns={[["context","Contexto"],["field","Campo"],["category","Categoria"],["status","Estado"],["count","Estudos"],["denominator","Denominador"],["proportion","Proporção"]]} />
      <ResultTable title="Completude dos campos" rows={summary.completeness} columns={[["context","Contexto"],["field","Campo"],["present","Presentes"],["applicable","Aplicáveis"],["proportion","Completude"],["states","Estados de ausência e revisão"]]} />
      <ResultTable title="Rastreabilidade estrutural" rows={summary.traceability} columns={[["metric","Indicador"],["numerator","Numerador"],["denominator","Denominador"],["proportion","Proporção"]]} />
      <ResultTable title="Mapas de lacunas do corpus" rows={summary.gaps} columns={[["map","Mapa"],["context","Contexto"],["substance","Substância"],["category","Categoria"],["count","Estudos"],["denominator","Denominador"]]} />
      {figure && <><label>Gráfico<select value={figure} onChange={e => setFigure(e.target.value)}>{selected.artifacts?.filter(a => a.name.endsWith(".png")).map(a => <option key={a.name}>{a.name}</option>)}</select></label><FigurePreview run={selected.id} name={figure}/></>}
      <div><h4>Arquivos da análise</h4>{selected.artifacts?.map(a => <button type="button" key={a.name} onClick={() => download(selected.id,a.name)}>{a.name}</button>)}</div>
    </article>}
  </section>;
}
