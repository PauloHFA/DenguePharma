import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api";

interface Protocol {
  id: string;
  code: string;
  version: number;
  title: string;
  question: string;
  sources: string[];
  cutoffDate: string;
  status: "DRAFT" | "REGISTERED" | "FROZEN";
}

const STATUS_LABEL: Record<Protocol["status"], string> = {
  DRAFT: "Rascunho",
  REGISTERED: "Registrado",
  FROZEN: "Congelado",
};

export function ProtocolsPage() {
  const { session } = useAuth();
  const [items, setItems] = useState<Protocol[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!session) return;
    try {
      setItems(await api<Protocol[]>(session, "/api/protocols"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar.");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(path: string, body?: unknown) {
    if (!session) return;
    try {
      await api(session, path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na operação.");
    }
  }

  return (
    <section aria-labelledby="t">
      <h1 id="t">Protocolos</h1>
      <p>Fontes, estratégia, elegibilidade e data de corte. Toda execução referencia a versão do protocolo.</p>
      {error && <p role="alert" className="error">Erro: {error}</p>}

      <NewProtocolForm onCreated={load} />

      {items === null ? (
        <p role="status">Carregando…</p>
      ) : items.length === 0 ? (
        <div className="empty" role="status"><strong>Estado vazio:</strong> Nenhum protocolo registrado.</div>
      ) : (
        <table>
          <caption>Versões de protocolo</caption>
          <thead>
            <tr><th>Código</th><th>Versão</th><th>Título</th><th>Fontes</th><th>Corte</th><th>Status</th><th>Ações</th></tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id}>
                <td>{p.code}</td>
                <td>v{p.version}</td>
                <td>{p.title}</td>
                <td>{p.sources.join(", ")}</td>
                <td>{p.cutoffDate}</td>
                <td>{STATUS_LABEL[p.status]}</td>
                <td className="actions">
                  {p.status === "DRAFT" && (
                    <button type="button" onClick={() => act(`/api/protocols/${p.id}/register`)}>Registrar</button>
                  )}
                  {p.status === "REGISTERED" && (
                    <button type="button" onClick={() => act(`/api/protocols/${p.id}/freeze`)}>Congelar</button>
                  )}
                  <button type="button" onClick={() => act(`/api/protocols/${p.id}/new-version`, { reason: "nova versão" })}>
                    Nova versão
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function NewProtocolForm({ onCreated }: { onCreated: () => Promise<void> }) {
  const { session } = useAuth();
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("");
  const [pubmed, setPubmed] = useState("");
  const [condition, setCondition] = useState("dengue");
  const [cutoff, setCutoff] = useState("");
  const [include, setInclude] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!session) return;
    const sources = [pubmed ? "PUBMED" : null, condition ? "CLINICALTRIALS" : null].filter(Boolean);
    try {
      await api(session, "/api/protocols", {
        method: "POST",
        body: JSON.stringify({
          code, title, question, sources,
          strategy: { pubmed: { query: pubmed }, clinicaltrials: { condition } },
          eligibility: { include },
          cutoffDate: cutoff,
        }),
      });
      setCode(""); setTitle(""); setQuestion(""); setPubmed(""); setInclude("");
      setError(null);
      await onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao criar.");
    }
  }

  return (
    <details>
      <summary>Novo protocolo</summary>
      <form onSubmit={submit} className="stack">
        <label htmlFor="p-code">Código</label>
        <input id="p-code" required value={code} onChange={(e) => setCode(e.target.value)} />
        <label htmlFor="p-title">Título</label>
        <input id="p-title" required value={title} onChange={(e) => setTitle(e.target.value)} />
        <label htmlFor="p-question">Pergunta de pesquisa</label>
        <textarea id="p-question" required value={question} onChange={(e) => setQuestion(e.target.value)} />
        <label htmlFor="p-pubmed">Estratégia PubMed (deixe vazio para não usar a fonte)</label>
        <textarea id="p-pubmed" value={pubmed} onChange={(e) => setPubmed(e.target.value)} />
        <label htmlFor="p-ct">Condição no ClinicalTrials.gov (vazio para não usar a fonte)</label>
        <input id="p-ct" value={condition} onChange={(e) => setCondition(e.target.value)} />
        <label htmlFor="p-include">Critério de inclusão</label>
        <textarea id="p-include" required value={include} onChange={(e) => setInclude(e.target.value)} />
        <label htmlFor="p-cutoff">Data de corte</label>
        <input id="p-cutoff" type="date" required value={cutoff} onChange={(e) => setCutoff(e.target.value)} />
        {error && <p role="alert" className="error">Erro: {error}</p>}
        <button type="submit">Criar rascunho</button>
      </form>
    </details>
  );
}
