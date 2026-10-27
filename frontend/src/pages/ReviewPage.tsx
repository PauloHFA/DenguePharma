import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

interface ExtractedFieldRow {
  id: string;
  study_id: string;
  study_title: string;
  field_name: string;
  raw_value: string | null;
  normalized_value: string | null;
  absence_status: string;
  review_status: string;
  published: boolean;
  quote: string | null;
  char_start: number | null;
  char_end: number | null;
  model_provider: string;
  model_version: string;
}

export function ReviewPage() {
  const { session } = useAuth();
  const [fields, setFields] = useState<ExtractedFieldRow[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [editing, setEditing] = useState<Record<string, { correctedValue: string; correctedAbsenceStatus: string; reason: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    const list = await api<ExtractedFieldRow[]>(session, "/api/extractions/fields");
    setFields(list);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
  }, [session]);

  async function submitReview(fieldId: string, decision: "APPROVED" | "CORRECTED" | "REJECTED") {
    if (!session) return;
    setError(null);
    setMessage(null);
    const edit = editing[fieldId];
    try {
      await api(session, `/api/extractions/fields/${fieldId}/review`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          correctedValue: edit?.correctedValue !== undefined && edit.correctedValue !== "" ? edit.correctedValue : null,
          correctedAbsenceStatus: edit?.correctedAbsenceStatus || null,
          reason: edit?.reason || "Revisão humana concluída com conferência do trecho fonte",
          adjudication: session.roles.includes("ADJUDICADOR") || session.roles.includes("ADMINISTRADOR"),
          publishAfterApproval: true,
        }),
      });
      setMessage(`Revisão registrada (${decision}) para o campo ${fieldId}.`);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const filtered = statusFilter ? fields.filter((f) => f.review_status === statusFilter) : fields;

  return (
    <section aria-labelledby="rev-heading">
      <h1 id="rev-heading">Revisão Lado a Lado de Extração (RF-05, RF-06)</h1>
      <p>
        Todo campo extraído apresenta o trecho literal de evidência com posição de caracteres (<code>char_start..char_end</code>)
        e diferencia <em>não relatado</em>, <em>não aplicável</em>, <em>incerto</em> e <em>conflitante entre fontes</em>.
      </p>

      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}

      <div className="filter-bar">
        <label>
          Filtrar status:{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Todos</option>
            <option value="PENDING">PENDING</option>
            <option value="APPROVED">APPROVED</option>
            <option value="CORRECTED">CORRECTED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
        </label>
      </div>

      <table>
        <thead>
          <tr>
            <th>Estudo / Campo</th>
            <th>Valor Extraído</th>
            <th>Status de Ausência</th>
            <th>Trecho Literal & Span</th>
            <th>Status de Revisão</th>
            <th>Correção / Justificativa (RF-06)</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((f) => {
            const edit = editing[f.id] ?? {
              correctedValue: f.normalized_value ?? "",
              correctedAbsenceStatus: f.absence_status,
              reason: "",
            };
            return (
              <tr key={f.id}>
                <td>
                  <strong>{f.field_name}</strong>
                  <div className="muted">{f.study_title} ({f.model_provider}/{f.model_version})</div>
                </td>
                <td>{f.normalized_value ?? <em>(vazio)</em>}</td>
                <td><code>{f.absence_status}</code></td>
                <td>
                  {f.quote ? (
                    <>
                      <blockquote>"{f.quote}"</blockquote>
                      <small className="muted">Span: [{f.char_start}..{f.char_end}]</small>
                    </>
                  ) : (
                    <em>Sem trecho (ausência explícita)</em>
                  )}
                </td>
                <td>{f.review_status} {f.published ? "(Publicado)" : ""}</td>
                <td>
                  <input
                    placeholder="Valor corrigido (opcional)"
                    value={edit.correctedValue}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, correctedValue: e.target.value } })}
                  />
                  <select
                    value={edit.correctedAbsenceStatus}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, correctedAbsenceStatus: e.target.value } })}
                  >
                    <option value="PRESENT">PRESENT</option>
                    <option value="NOT_REPORTED">NOT_REPORTED</option>
                    <option value="NOT_APPLICABLE">NOT_APPLICABLE</option>
                    <option value="UNCERTAIN">UNCERTAIN</option>
                    <option value="CONFLICTING">CONFLICTING</option>
                  </select>
                  <input
                    placeholder="Motivo da aprovação/correção"
                    value={edit.reason}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, reason: e.target.value } })}
                  />
                  <div>
                    <button type="button" onClick={() => submitReview(f.id, "APPROVED")}>Aprovar</button>
                    <button type="button" onClick={() => submitReview(f.id, "CORRECTED")}>Corrigir</button>
                    <button type="button" onClick={() => submitReview(f.id, "REJECTED")}>Rejeitar</button>
                  </div>
                </td>
              </tr>
            );
          })}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={6}>Nenhum campo extraído encontrado para o filtro selecionado.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

