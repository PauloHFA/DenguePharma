import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api";

interface Flowchart {
  identified: number;
  duplicatesRemoved: number;
  uniqueRecords: number;
  awaitingTitleAbstract: number;
  screened: number;
  excludedTitleAbstract: number;
  soughtForRetrieval: number;
  accessLimitedOrNotRetrieved: number;
  excludedFullText: number;
  complementaryPreClinical: number;
  includedCoreClinical: number;
  includedWithoutResults: number;
}

interface Proposal {
  id: string;
  primary_study_id: string;
  primary_title: string | null;
  candidate_study_id: string;
  candidate_title: string | null;
  shared_identifier: string;
  id_type: string;
  reason: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "UNDONE";
}

interface ScreeningStudy {
  id: string;
  title: string | null;
  context: string;
  purpose: string | null;
  screening_status: string;
  exclusion_category: string | null;
  final_exclusion_reason: string | null;
  access_status: string | null;
  abstract_text: string | null;
}

interface Substance {
  id: string;
  publishedName: string;
  normalizedName: string | null;
  productType: string | null;
  combination: boolean;
  aliases: { alias: string; external_source: string | null; external_id: string | null }[];
}

export function ScreeningPage() {
  const { session } = useAuth();
  const [flow, setFlow] = useState<Flowchart | null>(null);
  const [studies, setStudies] = useState<ScreeningStudy[] | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [substances, setSubstances] = useState<Substance[]>([]);
  const [subName, setSubName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const canAdjudicate = Boolean(
    session?.roles.includes("ADJUDICADOR") || session?.roles.includes("ADMINISTRADOR"),
  );

  const load = useCallback(async () => {
    if (!session) return;
    try {
      const [f, st, pr, sb] = await Promise.all([
        api<Flowchart>(session, "/api/screening/flowchart"),
        api<ScreeningStudy[]>(session, "/api/screening/studies"),
        api<Proposal[]>(session, "/api/study-links/proposals"),
        api<Substance[]>(session, "/api/substances"),
      ]);
      setFlow(f);
      setStudies(st);
      setProposals(pr);
      setSubstances(sb);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar triagem.");
    }
  }, [session]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(
    studyId: string,
    stage: "TITULO_RESUMO" | "TEXTO_COMPLETO",
    decision: "INCLUIR" | "EXCLUIR" | "INCERTO",
    adjudication: boolean,
  ) {
    if (!session) return;
    try {
      await api(session, "/api/screening/decisions", {
        method: "POST",
        body: JSON.stringify({
          studyId,
          stage,
          decision,
          exclusionCategory: decision === "EXCLUIR" ? "OUTRO" : null,
          exclusionReason: decision === "EXCLUIR" ? "Excluído na triagem" : null,
          context: "HUMANO",
          purpose: "TRATAMENTO",
          adjudication,
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao registrar decisão.");
    }
  }

  async function actProposal(id: string, action: "approve" | "reject" | "undo") {
    if (!session) return;
    try {
      await api(session, `/api/study-links/proposals/${id}/${action}`, {
        method: "POST",
        body: JSON.stringify({ reason: `Ação: ${action}` }),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na proposta de vínculo.");
    }
  }

  async function addSubstance(e: FormEvent) {
    e.preventDefault();
    if (!session || !subName.trim()) return;
    try {
      await api(session, "/api/substances", {
        method: "POST",
        body: JSON.stringify({
          publishedName: subName.trim(),
          productType: "SMALL_MOLECULE",
          combination: false,
          componentIds: [],
        }),
      });
      setSubName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao cadastrar substância.");
    }
  }

  async function normalizeSubstance(id: string) {
    if (!session) return;
    try {
      await api(session, `/api/substances/${id}/normalize`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao normalizar no PubChem.");
    }
  }

  return (
    <section aria-labelledby="t">
      <h1 id="t">Triagem</h1>
      <p>
        Triagem independente por dois revisores e adjudicação das divergências (RF-04), propostas de vínculo/fusão de
        estudos e normalização de substâncias via PubChem (RF-03).
      </p>
      {error && <p role="alert" className="error">Erro: {error}</p>}

      {flow && (
        <section aria-labelledby="prisma-heading">
          <h2 id="prisma-heading">Fluxograma de seleção (PRISMA-ScR)</h2>
          <table>
            <caption>Contagem por etapa de seleção</caption>
            <thead>
              <tr>
                <th>Identificados</th>
                <th>Duplicados absorvidos</th>
                <th>Triados</th>
                <th>Excluídos (título/resumo)</th>
                <th>Acesso limitado / somente resumo</th>
                <th>Excluídos (texto completo)</th>
                <th>Camada complementar (pré-clínico)</th>
                <th>Incluídos no núcleo clínico</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{flow.identified}</td>
                <td>{flow.duplicatesRemoved}</td>
                <td>{flow.screened}</td>
                <td>{flow.excludedTitleAbstract}</td>
                <td>{flow.accessLimitedOrNotRetrieved}</td>
                <td>{flow.excludedFullText}</td>
                <td>{flow.complementaryPreClinical}</td>
                <td>{flow.includedCoreClinical} (sem resultado: {flow.includedWithoutResults})</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      <section aria-labelledby="studies-heading">
        <h2 id="studies-heading">Registros em triagem</h2>
        {studies === null ? (
          <p role="status">Carregando…</p>
        ) : studies.length === 0 ? (
          <div className="empty" role="status">
            <strong>Estado vazio:</strong> Nenhum registro aguardando triagem.
          </div>
        ) : (
          <table>
            <caption>Fila de triagem independente e adjudicação</caption>
            <thead>
              <tr>
                <th>Título</th>
                <th>Contexto</th>
                <th>Acesso ao texto</th>
                <th>Status da triagem</th>
                <th>Decisão independente / Adjudicação</th>
              </tr>
            </thead>
            <tbody>
              {studies.map((s) => {
                const stage: "TITULO_RESUMO" | "TEXTO_COMPLETO" =
                  s.screening_status.includes("TEXTO_COMPLETO") ? "TEXTO_COMPLETO" : "TITULO_RESUMO";
                const needsAdjudication = s.screening_status.startsWith("DIVERGENCIA_");
                return (
                  <tr key={s.id}>
                    <td>{s.title ?? s.id}</td>
                    <td>{s.context}</td>
                    <td>{s.access_status ?? "SOMENTE_RESUMO"}</td>
                    <td>{s.screening_status}</td>
                    <td className="actions">
                      <button type="button" onClick={() => decide(s.id, stage, "INCLUIR", false)}>
                        Incluir ({stage})
                      </button>
                      <button type="button" onClick={() => decide(s.id, stage, "EXCLUIR", false)}>
                        Excluir ({stage})
                      </button>
                      {canAdjudicate && needsAdjudication && (
                        <>
                          <button type="button" onClick={() => decide(s.id, stage, "INCLUIR", true)}>
                            Adjudicar: Incluir
                          </button>
                          <button type="button" onClick={() => decide(s.id, stage, "EXCLUIR", true)}>
                            Adjudicar: Excluir
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="links-heading">
        <h2 id="links-heading">Propostas de vínculo / fusão de estudos (RF-03, T3)</h2>
        {proposals.length === 0 ? (
          <p className="muted">Nenhuma proposta de fusão ambígua pendente.</p>
        ) : (
          <table>
            <caption>Revisão de vínculos entre documentos e estudos</caption>
            <thead>
              <tr>
                <th>Estudo principal</th>
                <th>Estudo candidato</th>
                <th>Identificador compartilhado</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {proposals.map((p) => (
                <tr key={p.id}>
                  <td>{p.primary_title ?? p.primary_study_id}</td>
                  <td>{p.candidate_title ?? p.candidate_study_id}</td>
                  <td>{p.id_type}: {p.shared_identifier}</td>
                  <td>{p.status}</td>
                  <td className="actions">
                    {canAdjudicate && p.status === "PENDING" && (
                      <>
                        <button type="button" onClick={() => actProposal(p.id, "approve")}>Aprovar fusão</button>
                        <button type="button" onClick={() => actProposal(p.id, "reject")}>Rejeitar</button>
                      </>
                    )}
                    {canAdjudicate && p.status === "APPROVED" && (
                      <button type="button" onClick={() => actProposal(p.id, "undo")}>Desfazer fusão</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="sub-heading">
        <h2 id="sub-heading">Substâncias e normalização PubChem (RF-03)</h2>
        <form onSubmit={addSubstance} className="stack">
          <label htmlFor="sub-name">Nome publicado da substância</label>
          <input id="sub-name" required value={subName} onChange={(e) => setSubName(e.target.value)} />
          <button type="submit">Cadastrar substância</button>
        </form>
        {substances.length > 0 && (
          <table>
            <caption>Substâncias cadastradas</caption>
            <thead>
              <tr><th>Nome publicado</th><th>Nome normalizado (PubChem)</th><th>Tipo</th><th>Ações</th></tr>
            </thead>
            <tbody>
              {substances.map((s) => (
                <tr key={s.id}>
                  <td>{s.publishedName}</td>
                  <td>{s.normalizedName ?? "Não normalizada"}</td>
                  <td>{s.combination ? "Combinação" : (s.productType ?? "Monoterapia")}</td>
                  <td>
                    {!s.combination && (
                      <button type="button" onClick={() => normalizeSubstance(s.id)}>Normalizar (PubChem)</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}

