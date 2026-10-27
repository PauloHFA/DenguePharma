import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

interface CatalogItem {
  id: string;
  title: string;
  context: string;
  purpose: string;
  design: string;
  phase: string;
  substance_published_name: string | null;
}

interface CompareResponse {
  studies: Array<{
    id: string;
    title: string;
    context: string;
    purpose: string;
    design: string;
    phase: string;
    substance_name: string | null;
    outcome_summary: string | null;
    outcome_category: string | null;
    outcome_time_frame: string | null;
    effect_summary: string | null;
    limitations: string;
  }>;
  compatibleForDirectSynthesis: boolean;
  incompatibilities: Array<{ rule: string; detail: string }>;
  rankingPolicy: string;
}

export function ComparatorPage() {
  const { session } = useAuth();
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    api<CatalogItem[]>(session, "/api/catalog")
      .then((list) => {
        setCatalog(list);
        if (list.length >= 2) {
          setSelected([list[0].id, list[1].id]);
        }
      })
      .catch((e) => setError((e as Error).message));
  }, [session]);

  async function runComparison() {
    if (!session) return;
    setError(null);
    try {
      const res = await api<CompareResponse>(session, "/api/catalog/compare", {
        method: "POST",
        body: JSON.stringify({ studyIds: selected }),
      });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function toggleStudy(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <section aria-labelledby="cmp-heading">
      <h1 id="cmp-heading">Comparador Metodológico por Desfecho e Janela Temporal (RF-08)</h1>
      <p>
        Compara estudos por desfecho e janela temporal com contexto explícito, apontando incompatibilidades
        metodológicas (RC-01, RC-03) e vedando qualquer ranking clínico universal (RC-04).
      </p>

      {error && <p role="alert">{error}</p>}

      <div>
        <h2>Selecione ao menos 2 estudos do catálogo vigente</h2>
        <ul>
          {catalog.map((st) => (
            <li key={st.id}>
              <label>
                <input
                  type="checkbox"
                  checked={selected.includes(st.id)}
                  onChange={() => toggleStudy(st.id)}
                />{" "}
                {st.title} (<code>{st.context}</code> / <code>{st.purpose}</code>)
              </label>
            </li>
          ))}
        </ul>
        <button type="button" onClick={runComparison} disabled={selected.length < 2}>
          Comparar Estudos Selecionados ({selected.length})
        </button>
      </div>

      {result && (
        <article className="card">
          <div className="notice">
            <p><strong>Política RC-04:</strong> {result.rankingPolicy}</p>
            <p>
              <strong>Compatível para síntese direta:</strong>{" "}
              {result.compatibleForDirectSynthesis ? "Sim" : "Não — veja incompatibilidades abaixo"}
            </p>
          </div>

          {result.incompatibilities.length > 0 && (
            <div role="note" className="warning">
              <strong>Incompatibilidades Metodológicas Detectadas (RF-08 / RC-01):</strong>
              <ul>
                {result.incompatibilities.map((inc, i) => (
                  <li key={i}>
                    <code>{inc.rule}</code>: {inc.detail}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <table>
            <thead>
              <tr>
                <th>Estudo</th>
                <th>Substância</th>
                <th>Contexto</th>
                <th>Finalidade</th>
                <th>Desenho / Fase</th>
                <th>Desfecho & Janela</th>
                <th>Efeito</th>
                <th>Limitações</th>
              </tr>
            </thead>
            <tbody>
              {result.studies.map((s) => (
                <tr key={s.id}>
                  <td>{s.title}</td>
                  <td>{s.substance_name ?? "N/I"}</td>
                  <td><code>{s.context}</code></td>
                  <td><code>{s.purpose}</code></td>
                  <td>{s.design} ({s.phase})</td>
                  <td>{s.outcome_summary} ({s.outcome_category} / {s.outcome_time_frame})</td>
                  <td>{s.effect_summary}</td>
                  <td>{s.limitations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      )}
    </section>
  );
}

