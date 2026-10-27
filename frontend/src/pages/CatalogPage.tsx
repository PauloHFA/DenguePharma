import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

interface CatalogStudy {
  id: string;
  title: string;
  purpose: string;
  context: string;
  design: string;
  phase: string;
  serotype: string | null;
  countries: string | null;
  sample_size: number | null;
  comparator_label: string | null;
  outcome_summary: string | null;
  outcome_category: string | null;
  outcome_time_frame: string | null;
  effect_summary: string | null;
  adverse_events_status: string;
  limitations: string;
  risk_of_bias_tool: string | null;
  risk_of_bias_level: string | null;
  regulatory_status: string;
  regulatory_authority: string | null;
  regulatory_jurisdiction: string | null;
  regulatory_indication: string | null;
  substance_published_name: string | null;
  substance_normalized_name: string | null;
  scientific_notices?: string[];
}

export function CatalogPage() {
  const { session } = useAuth();
  const [studies, setStudies] = useState<CatalogStudy[]>([]);
  const [substance, setSubstance] = useState("");
  const [purpose, setPurpose] = useState("");
  const [context, setContext] = useState("");
  const [design, setDesign] = useState("");
  const [serotype, setSerotype] = useState("");
  const [phase, setPhase] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    setError(null);
    const params = new URLSearchParams();
    if (substance) params.set("substance", substance);
    if (purpose) params.set("purpose", purpose);
    if (context) params.set("context", context);
    if (design) params.set("design", design);
    if (serotype) params.set("serotype", serotype);
    if (phase) params.set("phase", phase);
    const q = params.toString() ? `?${params.toString()}` : "";
    try {
      const list = await api<CatalogStudy[]>(session, `/api/catalog${q}`);
      setStudies(list);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
  }, [session]);

  return (
    <section aria-labelledby="cat-heading">
      <h1 id="cat-heading">Catálogo de Evidências Aprovadas (RF-07, RC-01 a RC-07)</h1>
      <p>
        Catálogo restrito a registros aprovados por revisão humana e não retratados. As limitações metodológicas,
        separação de contextos experimentais e avisos de eventos adversos nunca são ocultados.
      </p>

      {error && <p role="alert">{error}</p>}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
        className="filter-bar"
      >
        <input
          placeholder="Substância (nome ou sinônimo)"
          value={substance}
          onChange={(e) => setSubstance(e.target.value)}
        />
        <select value={context} onChange={(e) => setContext(e.target.value)} aria-label="Contexto experimental">
          <option value="">Todos os contextos</option>
          <option value="HUMANO">HUMANO</option>
          <option value="ANIMAL">ANIMAL</option>
          <option value="IN_VITRO">IN_VITRO</option>
          <option value="IN_SILICO">IN_SILICO</option>
        </select>
        <select value={purpose} onChange={(e) => setPurpose(e.target.value)} aria-label="Finalidade">
          <option value="">Todas as finalidades</option>
          <option value="TRATAMENTO">TRATAMENTO</option>
          <option value="PROFILAXIA">PROFILAXIA</option>
          <option value="DESAFIO_CONTROLADO">DESAFIO_CONTROLADO</option>
          <option value="MANEJO_SINTOMATICO">MANEJO_SINTOMATICO</option>
        </select>
        <select value={design} onChange={(e) => setDesign(e.target.value)} aria-label="Desenho">
          <option value="">Todos os desenhos</option>
          <option value="ENSAIO_RANDOMIZADO">ENSAIO_RANDOMIZADO</option>
          <option value="COORTE">COORTE</option>
          <option value="EXPERIMENTAL_IN_VITRO">EXPERIMENTAL_IN_VITRO</option>
        </select>
        <input placeholder="Sorotipo (ex.: DENV-1)" value={serotype} onChange={(e) => setSerotype(e.target.value)} />
        <input placeholder="Fase (ex.: FASE_2)" value={phase} onChange={(e) => setPhase(e.target.value)} />
        <button type="submit">Filtrar</button>
      </form>

      <div className="catalog-cards">
        {studies.map((st) => (
          <article key={st.id} className="card">
            <h2>{st.title}</h2>
            <p>
              <strong>Substância:</strong> {st.substance_published_name ?? "Não vinculada"} |{" "}
              <strong>Contexto:</strong> <code>{st.context}</code> |{" "}
              <strong>Finalidade:</strong> <code>{st.purpose}</code>
            </p>
            <p>
              <strong>Desenho:</strong> {st.design} | <strong>Fase:</strong> {st.phase} |{" "}
              <strong>Sorotipo:</strong> {st.serotype ?? "N/I"} | <strong>Amostra:</strong> {st.sample_size ?? "N/I"} |{" "}
              <strong>Comparador:</strong> {st.comparator_label ?? "N/I"}
            </p>
            <p>
              <strong>Desfecho ({st.outcome_category ?? "N/I"} - {st.outcome_time_frame ?? "N/I"}):</strong>{" "}
              {st.outcome_summary ?? "N/I"} — <em>{st.effect_summary ?? "N/I"}</em>
            </p>
            <p>
              <strong>Status Regulatório (RC-02):</strong> <code>{st.regulatory_status}</code>
              {st.regulatory_authority && (
                <span>
                  {" "}({st.regulatory_authority} / {st.regulatory_jurisdiction} — {st.regulatory_indication})
                </span>
              )}
            </p>
            <p>
              <strong>Risco de Viés (RC-05):</strong> {st.risk_of_bias_tool ?? "NAO_AVALIADO"} ({st.risk_of_bias_level ?? "INCERTO"})
            </p>
            <p className="warning">
              <strong>Limitações Obrigatórias (RF-07):</strong> {st.limitations}
            </p>
            {st.scientific_notices && st.scientific_notices.length > 0 && (
              <ul className="muted">
                {st.scientific_notices.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
        {studies.length === 0 && <p>Nenhum estudo aprovado encontrado para os filtros informados.</p>}
      </div>
    </section>
  );
}

