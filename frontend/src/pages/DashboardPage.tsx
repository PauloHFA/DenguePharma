import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DiseaseBurdenView } from "../components/DiseaseBurdenView";

type Row = Record<string, unknown>;
type Run = { id: string; published_at: string; protocol_code: string; cutoff_date: string };
type RecordRow = { document_id: string; title: string; document_type: string; sources: string[]; context: string; publication_year: number | null; start_year: number | null; substances: string[]; countries: string[]; identifiers: string[]; screening_states: string[] };
type Summary = {
  protocol?: { maxRecordsPerSource?: number; eligibility?: { stage?: string } };
  notice: string; documentCount: number; rawDocumentCount: number; publicationCount: number; trialCount: number; studyCount: number;
  temporal: Row[]; distributions: Row[]; completeness: Row[]; enrollment: Row[]; sourceRuns: Row[]; warnings: string[];
  scientificFieldAvailability?: Row[];
  temporalFlags?: Row[];
  linkCoverage: { numerator: number; denominator: number; proportion: number | null }; links: Row[]; linkCandidates: Row[];
  changes: { status: string; comparable?: boolean; new: string[]; changed: string[]; notObserved: string[] };
  reviewed: { notice: string; contextCounts: Row[]; distributions: Row[]; completeness: Row[]; gaps: Row[]; traceability: Row[] };
};
const base = "/api/public/analyses";
async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });
  if (!response.ok) throw new Error(`Não foi possível carregar os resultados (${response.status}).`);
  return response.json() as Promise<T>;
}
const display = (value: unknown): string => value === null || value === undefined ? "Sem dados" : typeof value === "object" ? JSON.stringify(value) : String(value);
function identifierUrl(value: string): string | undefined {
  if (/^PMID:\d+$/.test(value)) return `https://pubmed.ncbi.nlm.nih.gov/${value.slice(5)}/`;
  if (/^NCT:NCT\d{8}$/.test(value)) return `https://clinicaltrials.gov/study/${value.slice(4)}`;
  if (/^PMCID:PMC\d+$/.test(value)) return `https://pmc.ncbi.nlm.nih.gov/articles/${value.slice(6)}/`;
  if (value.startsWith("DOI:")) return `https://doi.org/${encodeURIComponent(value.slice(4))}`;
  return undefined;
}
function Table({ title, rows, columns, search = "" }: { title: string; rows: Row[]; columns: string[]; search?: string }) {
  const filtered = rows.filter(row => JSON.stringify(row).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [search, rows]);
  const size = 30;
  return <section className="dashboard-table"><h3>{title}</h3>{!filtered.length ? <p className="empty">Sem dados para esta seleção.</p> : <>
    <div className="table-scroll"><table><thead><tr>{columns.map(c => <th key={c} scope="col">{c}</th>)}</tr></thead>
      <tbody>{filtered.slice(page * size, (page + 1) * size).map((r, i) => <tr key={i}>{columns.map(c => <td key={c}>{c === "identifiers" && Array.isArray(r[c]) ? (r[c] as string[]).map(value => identifierUrl(value) ? <p key={value}><a href={identifierUrl(value)} target="_blank" rel="noreferrer">{value}</a></p> : <p key={value}>{value}</p>) : display(r[c])}</td>)}</tr>)}</tbody></table></div>
    <div className="actions"><button disabled={page === 0} onClick={() => setPage(p => p - 1)}>Anterior</button><span>{page + 1} / {Math.ceil(filtered.length / size)} · {filtered.length} linhas</span><button disabled={(page + 1) * size >= filtered.length} onClick={() => setPage(p => p + 1)}>Próxima</button></div>
  </>}</section>;
}

export function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]), [id, setId] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null), [records, setRecords] = useState<RecordRow[]>([]), [figures, setFigures] = useState<string[]>([]);
  const [error, setError] = useState(""), [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("panorama"), [search, setSearch] = useState("");
  const [source, setSource] = useState(""), [context, setContext] = useState(""), [recordYear, setRecordYear] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    get<Run[]>(base, abort.signal).then(result => { setRuns(result); setId(result[0]?.id ?? ""); }).catch(e => { if (e.name !== "AbortError") setError(e.message); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, []);
  useEffect(() => {
    setSummary(null); setRecords([]); setFigures([]); setSearch(""); setSource(""); setContext(""); setRecordYear("");
    if (!id) return;
    const abort = new AbortController(); setLoading(true); setError("");
    Promise.all([
      get<Summary>(`${base}/${id}/artifacts?name=summary.json`, abort.signal),
      get<RecordRow[]>(`${base}/${id}/artifacts?name=records.json`, abort.signal),
      get<{ artifacts: { name: string }[] }>(`${base}/${id}`, abort.signal),
    ]).then(([s, r, details]) => { setSummary(s); setRecords(r); setFigures(details.artifacts.map(a => a.name).filter(n => n.endsWith(".png"))); })
      .catch(e => { if (e.name !== "AbortError") setError(e.message); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [id]);
  const filteredRecords = useMemo(() => records.filter(r => (!source || r.sources.includes(source)) && (!context || r.context === context)
    && (!recordYear || String(r.document_type === "PUBLICACAO" ? r.publication_year : r.start_year) === recordYear)
    && (!search || JSON.stringify(r).toLocaleLowerCase().includes(search.toLocaleLowerCase()))), [records, source, context, recordYear, search]);
  const current = runs.find(r => r.id === id);
  const artifact = (name: string) => `${base}/${id}/artifacts?name=${encodeURIComponent(name)}`;
  return <div className="dashboard">
    <header className="dashboard-header"><Link to="/" className="brand">DenguePharma <small>Observatório de evidências</small></Link><Link to="/protocolos">Área de curadoria</Link></header>
    <main>
      <p className="eyebrow">CIÊNCIA DE DADOS · DENGUE</p><h1>Panorama da pesquisa farmacológica</h1>
      <p>Explore publicações, ensaios registrados e evidências revisadas sobre medicamentos e compostos.</p>
      {error && <p role="alert" className="error">{error}</p>}
      {loading && <p role="status">Carregando análises…</p>}
      {!loading && !error && !runs.length && <div className="empty"><h2>Nenhuma análise publicada</h2><p>Os resultados aparecerão após a coleta, o processamento e a publicação de uma execução. A revisão científica do piloto será identificada separadamente.</p></div>}
      {!!runs.length && <label>Execução publicada <select aria-label="Execução publicada" value={id} onChange={e => setId(e.target.value)}>{runs.map(r => <option key={r.id} value={r.id}>{r.protocol_code} · corte {r.cutoff_date} · {new Date(r.published_at).toLocaleString("pt-BR")}</option>)}</select></label>}
      {summary && <>
        <p className="notice">{summary.notice}</p>
        {summary.protocol?.eligibility?.stage === "pilot" && <p className="notice"><strong>Coleta piloto: até {summary.protocol.maxRecordsPerSource} registros por fonte.</strong> Amostra de conveniência para validar a preparação dos dados. A revisão científica permanece pendente nos registros sem decisão consolidada.</p>}
        <p className="muted">Protocolo {current?.protocol_code} · Data de corte {current?.cutoff_date} · Resultados congelados desta execução.</p>
        <div className="metrics">{[["Documentos após deduplicação", summary.documentCount], ["Publicações", summary.publicationCount], ["Registros de ensaios", summary.trialCount], ["Estudos com campos revisados", summary.studyCount]].map(([label, value]) => <article key={label}><strong>{value}</strong><span>{label}</span></article>)}</div>
        <nav aria-label="Análises" className="dashboard-tabs">{[["panorama", "Corpus e evolução"], ["ensaios", "Ensaios e intervenções"], ["evidencias", "Evidências revisadas"], ["qualidade", "Qualidade e integração"], ["carga", "Carga Global (Eixo C)"]].map(([value, label]) => <button key={value} aria-pressed={tab === value} onClick={() => { setTab(value); setSearch(""); }}>{label}</button>)}</nav>
        <label>Buscar nas tabelas desta aba <input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Substância, país, categoria…" /></label>
        {tab === "panorama" && <>
          <h2>Corpus coletado</h2><p>A elegibilidade pode estar pendente. Ano de publicação e ano de início de ensaio representam eventos distintos.</p>
          <Table title="Distribuição temporal" rows={summary.temporal} columns={["field", "category", "count", "denominator", "unit"]} search={search} />
          {!!summary.temporalFlags?.length && <p className="notice">{summary.temporalFlags.length} registros têm ano bibliográfico posterior ao corte da busca. Os valores foram preservados para conferência na fonte; ano da edição e data usada pela busca podem diferir.</p>}
          <fieldset><legend>Filtros da tabela de documentos</legend>
            <label>Fonte <select aria-label="Fonte" value={source} onChange={e => setSource(e.target.value)}><option value="">Todas</option>{[...new Set(records.flatMap(r => r.sources))].sort().map(v => <option key={v}>{v}</option>)}</select></label>
            <label>Contexto revisado <select aria-label="Contexto revisado" value={context} onChange={e => setContext(e.target.value)}><option value="">Todos</option>{[...new Set(records.map(r => r.context))].sort().map(v => <option key={v}>{v}</option>)}</select></label>
            <label>Ano do evento <input type="number" value={recordYear} onChange={e => setRecordYear(e.target.value)} /></label>
          </fieldset>
          <Table title="Documentos e referências" rows={filteredRecords as unknown as Row[]} columns={["title", "document_type", "sources", "publication_year", "start_year", "context", "screening_states", "identifiers"]} />
        </>}
        {tab === "ensaios" && <>
          <h2>Ensaios e intervenções registradas</h2><p>Intervenções e países podem se sobrepor. Nomes recebem normalização lexical; a frequência representa disponibilidade no corpus.</p>
          <Table title="Distribuições dos ensaios" rows={summary.distributions.filter(r => r.unit === "registro_ensaio")} columns={["field", "category", "count", "denominator", "proportion", "overlapping"]} search={search} />
          <Table title="Participantes informados por registro — sem somatório" rows={summary.enrollment} columns={["field", "available", "denominator", "missing", "median", "q1", "q3", "min", "max"]} search={search} />
        </>}
        {tab === "evidencias" && <>
          <h2>Mapa de evidências revisadas</h2><p>{summary.reviewed.notice}</p>
          {!summary.studyCount && <p className="empty">Sem estudos com campos científicos revisados neste snapshot. O panorama coletado continua disponível nas outras abas.</p>}
          <Table title="Distribuições por contexto" rows={summary.reviewed.distributions} columns={["context", "field", "category", "status", "count", "denominator"]} search={search} />
          <Table title="Cobertura por substância e categoria de desfecho" rows={summary.reviewed.gaps} columns={["layer", "context", "substance", "category", "count", "denominator"]} search={search} />
          <Table title="Completude dos campos revisados" rows={summary.reviewed.completeness} columns={["context", "field", "present", "applicable", "proportion", "states"]} search={search} />
          <Table title="População, comparador, limitações e demais campos científicos" rows={summary.scientificFieldAvailability ?? []} columns={["context", "field", "present", "applicable", "proportion", "states"]} search={search} />
        </>}
        {tab === "qualidade" && <>
          <h2>Qualidade documental e integração</h2><p>Preenchimento e rastreabilidade não constituem avaliação de risco de viés.</p>
          <p>Registros de ensaios com publicação vinculada e confirmada: <strong>{summary.linkCoverage.numerator}/{summary.linkCoverage.denominator || "sem dados"}</strong>. Referências candidatas permanecem pendentes de revisão.</p>
          <Table title="Coletas e cobertura" rows={summary.sourceRuns} columns={["source", "status", "records_seen", "total_returned", "query", "executed_at"]} search={search} />
          <Table title="Disponibilidade dos metadados" rows={summary.completeness} columns={["source", "field", "present", "applicable", "missing", "conflicts", "proportion"]} search={search} />
          <Table title="Vínculos confirmados" rows={summary.links} columns={["trial_document_id", "publication_document_id", "study_id", "status"]} search={search} />
          <Table title="Vínculos candidatos para revisão" rows={summary.linkCandidates} columns={["trial_document_id", "publication_document_id", "identifier", "status"]} search={search} />
          <Table title="Rastreabilidade dos campos revisados" rows={summary.reviewed.traceability} columns={["metric", "numerator", "denominator", "proportion"]} search={search} />
          <h3>Atualização entre snapshots</h3>{summary.changes.status === "NO_BASELINE" ? <p>Sem execução anterior selecionada para comparação.</p> : <p>Novos: {summary.changes.new.length}; alterados: {summary.changes.changed.length}; não observados: {summary.changes.notObserved.length}. {summary.changes.comparable ? "Mesmo protocolo." : "Protocolos diferentes: a cobertura pode ter mudado."}</p>}
          <ul>{summary.warnings.map(w => <li key={w}>{w}</li>)}</ul>
        </>}
        {tab === "carga" && <DiseaseBurdenView />}
        <section><h2>Gráficos da execução completa</h2><div className="dashboard-figures">{figures.filter(name => tab === "evidencias" ? name.includes("reviewed_") : !name.includes("reviewed_") && (tab === "panorama" ? name.includes("temporal") : tab === "qualidade" ? name.includes("completeness") : !name.includes("temporal") && !name.includes("completeness"))).map(name => <figure key={name}><img src={artifact(name)} alt={name.replace("figures/", "").replace(".png", "")} loading="lazy" /><figcaption><a href={artifact(name)} download>Baixar PNG</a></figcaption></figure>)}</div></section>
        <section><h2>Dados e reprodução</h2><div className="actions">{[["bundle.zip", "Pacote completo"], ["documents.csv", "Documentos CSV"], ["summary.json", "Resumo JSON"], ["manifest.json", "Manifesto"], ["pilot_review.csv", "Planilha de revisão do piloto"]].map(([name, label]) => <a key={name} href={artifact(name)} download>{label}</a>)}</div></section>
      </>}
    </main><footer className="notice">Pesquisa e consulta de evidências. Os resultados descrevem o corpus coletado e não constituem recomendação terapêutica.</footer>
  </div>;
}
