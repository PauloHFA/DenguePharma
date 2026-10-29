import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";
import { absenceStatuses, criticalFields, type ReviewDecision } from "../review-contract";

interface ExtractedFieldRow {
  id: string;
  study_id: string;
  study_title: string;
  field_name: string;
  original_value: string | null;
  normalized_value: string | null;
  absence_status: string;
  review_status: string;
  published: boolean;
  evidence_text: string | null;
  section: string | null;
  page: number | null;
  locator: string | null;
  document_text: string;
  document_origin: string;
  document_version_no: number;
  model_provider: string;
  model_version: string;
}

export function ReviewPage() {
  const { session } = useAuth();
  const [fields, setFields] = useState<ExtractedFieldRow[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [editing, setEditing] = useState<Record<string, { correctedValue: string; correctedAbsenceStatus: string; correctedQuotedText: string; reason: string }>>({});
  const canAdjudicate = Boolean(session?.roles.some((role) => ["ADJUDICADOR", "ADMINISTRADOR"].includes(role)));
  const canReview = Boolean(canAdjudicate || session?.roles.includes("REVISOR"));
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

  async function submitReview(fieldId: string, decision: ReviewDecision) {
    if (!session) return;
    setError(null);
    setMessage(null);
    const edit = editing[fieldId];
    const field = fields.find((f) => f.id === fieldId)!;
    if (decision === "CORRIGIR" && !edit?.reason.trim()) {
      setError("Informe o motivo da correção.");
      return;
    }
    try {
      await api(session, `/api/extractions/fields/${fieldId}/review`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          correctedValue: edit?.correctedValue !== undefined && edit.correctedValue !== "" ? edit.correctedValue : null,
          correctedAbsenceStatus: edit?.correctedAbsenceStatus || null,
          correctedQuotedText: edit?.correctedQuotedText ?? field.evidence_text,
          reason: edit?.reason || null,
          adjudication: canAdjudicate,
          publishAfterApproval: decision !== "REJEITAR" && (!criticalFields.has(field.field_name) || canAdjudicate)
            && !["INCERTO", "NAO_EXTRAIDO"].includes(decision === "CORRIGIR" ? edit?.correctedAbsenceStatus ?? field.absence_status : field.absence_status),
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
        Confira o valor com o trecho e a versão documental. Correções de valores presentes exigem um trecho literal
        da fonte e justificativa. Campos críticos seguem para aprovação do adjudicador.
      </p>

      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}

      <div className="filter-bar">
        <label>
          Filtrar status:{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Todos</option>
            <option value="RASCUNHO_IA">Rascunho de extração</option>
            <option value="EM_REVISAO">Em revisão</option>
            <option value="APROVADO">Aprovado</option>
            <option value="REJEITADO">Rejeitado</option>
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
              correctedQuotedText: f.evidence_text ?? "",
              reason: "",
            };
            return (
              <tr key={f.id}>
                <td>
                  <strong>{f.field_name}</strong>
                  <div className="muted">{f.study_title} ({f.model_provider}/{f.model_version})</div>
                </td>
                <td>{f.normalized_value ?? f.original_value ?? <em>(vazio)</em>}</td>
                <td><code>{f.absence_status}</code></td>
                <td>
                  <p>{f.document_origin} — versão {f.document_version_no}</p>
                  {f.evidence_text ? (
                    <>
                      <blockquote>{f.evidence_text}</blockquote>
                      <small className="muted">{f.section} {f.page != null ? `— página ${f.page}` : ""} — {f.locator}</small>
                    </>
                  ) : (
                    <em>Sem trecho de suporte verificado</em>
                  )}
                  {f.document_text && <details><summary>Texto disponível da fonte</summary><p style={{ whiteSpace: "pre-wrap" }}>{f.document_text}</p></details>}
                </td>
                <td>{f.review_status} {f.published ? "(Publicado)" : ""}</td>
                <td>
                  <input
                    aria-label={`Valor corrigido de ${f.field_name}`}
                    placeholder="Valor corrigido (opcional)"
                    value={edit.correctedValue}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, correctedValue: e.target.value } })}
                  />
                  <select
                    aria-label={`Estado de ausência de ${f.field_name}`}
                    value={edit.correctedAbsenceStatus}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, correctedAbsenceStatus: e.target.value } })}
                  >
                    {absenceStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
                  </select>
                  <textarea
                    aria-label={`Trecho de suporte corrigido de ${f.field_name}`}
                    placeholder="Copie o trecho literal da fonte que sustenta o valor corrigido"
                    value={edit.correctedQuotedText}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, correctedQuotedText: e.target.value } })}
                  />
                  <input
                    aria-label={`Motivo da correção de ${f.field_name}`}
                    placeholder="Motivo da aprovação/correção"
                    value={edit.reason}
                    onChange={(e) => setEditing({ ...editing, [f.id]: { ...edit, reason: e.target.value } })}
                  />
                  <div>
                    <button type="button" disabled={!canReview} onClick={() => submitReview(f.id, "ACEITAR")}>{criticalFields.has(f.field_name) && !canAdjudicate ? "Enviar para adjudicação" : "Aprovar"}</button>
                    <button type="button" disabled={!canReview || f.review_status === "APROVADO"} onClick={() => submitReview(f.id, "CORRIGIR")}>Corrigir</button>
                    <button type="button" disabled={!canReview} onClick={() => submitReview(f.id, "REJEITAR")}>Rejeitar</button>
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

