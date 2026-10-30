import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";

interface OpsSummary {
  jobs: Array<{
    id: string;
    job_type: string;
    ref_id: string;
    status: string;
    attempts: number;
    max_attempts: number;
    last_error: string | null;
    updated_at: string;
  }>;
  outbox: Array<{
    id: string;
    event_id: string;
    aggregate_type: string;
    event_type: string;
    attempts: number;
    created_at: string;
    published_at: string | null;
    next_attempt_at: string;
    last_error: string | null;
  }>;
  reassessments: Array<{
    id: string;
    study_id: string;
    study_title: string;
    trigger_type: string;
    status: string;
    notes: string | null;
    created_at: string;
  }>;
}

export function OperationalPanelPage() {
  const { session } = useAuth();
  const [summary, setSummary] = useState<OpsSummary | null>(null);
  const [reproPkg, setReproPkg] = useState<string | null>(null);
  const [expOutput, setExpOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    const data = await api<OpsSummary>(session, "/api/ops/summary");
    setSummary(data);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
    const timer = setInterval(() => { load().catch((e) => setError((e as Error).message)); }, 5000);
    return () => clearInterval(timer);
  }, [session]);

  async function resolveReassessment(id: string) {
    if (!session) return;
    await api(session, `/api/ops/reassessments/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ reason: "Reavaliado pela equipe de curadoria no painel operacional" }),
    });
    await load();
  }

  async function retryJob(id: string) {
    if (!session) return;
    await api(session, `/api/ops/jobs/${id}/retry`, {
      method: "POST",
      body: JSON.stringify({ reason: "Reprocessamento manual autorizado no painel operacional" }),
    });
    await load();
  }

  async function exportReproductionPackage() {
    if (!session) return;
    const pkg = await api<Record<string, unknown>>(session, "/api/admin/reproduction-package");
    setReproPkg(JSON.stringify(pkg, null, 2));
  }

  async function seedPilotCorpus() {
    if (!session) return;
    const res = await api<Record<string, unknown>>(session, "/api/admin/seed-pilot", { method: "POST" });
    setExpOutput(JSON.stringify(res, null, 2));
    await load();
  }

  async function relayOutbox() {
    if (!session) return;
    const res = await api<Record<string, unknown>>(session, "/api/ops/outbox/relay", { method: "POST" });
    setExpOutput(JSON.stringify(res, null, 2));
    await load();
  }

  return (
    <section aria-labelledby="ops-heading">
      <h1 id="ops-heading">Painel Operacional: Filas, Reavaliação e Pacote de Reprodução</h1>
      {error && <p role="alert">{error}</p>}

      <div className="filter-bar">
        <button type="button" onClick={seedPilotCorpus}>
          Carregar 20 registros demonstrativos
        </button>
        <button type="button" onClick={relayOutbox}>
          Solicitar envio dos eventos pendentes
        </button>
        <button type="button" onClick={exportReproductionPackage}>
          Exportar Pacote de Reprodução Respeitando Licenças (RF-12 / T9)
        </button>
      </div>
      <p>Os registros demonstrativos são sintéticos e ficam fora do catálogo e dos relatórios científicos. O piloto científico exige importação e curadoria de fontes reais.</p>

      {expOutput && (
        <div>
          <h2>Resultado da operação</h2>
          <pre>{expOutput}</pre>
        </div>
      )}

      {reproPkg && (
        <div>
          <h2>Pacote de Reprodução (T9 / RNF-03)</h2>
          <pre>{reproPkg}</pre>
        </div>
      )}

      {summary && (
        <>
          <h2>Monitoramento de Orçamento e Custos de IA (Budget Guard)</h2>
          <div className="card" style={{ display: "flex", gap: "2rem", flexWrap: "wrap", padding: "1rem", background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: "8px", marginBottom: "1.5rem" }}>
            <div>
              <small className="muted">Teto de Orçamento Configurado</small>
              <p style={{ fontSize: "1.3rem", fontWeight: "bold", margin: "0.2rem 0" }}>US$ 50,00</p>
              <small className="muted">Bloqueio automático ao atingir 100%</small>
            </div>
            <div>
              <small className="muted">Consumo Atual Estimado</small>
              <p style={{ fontSize: "1.3rem", fontWeight: "bold", margin: "0.2rem 0", color: "#16a34a" }}>US$ 0,00</p>
              <small className="muted">0% do teto global</small>
            </div>
            <div>
              <small className="muted">Tokens Consumidos</small>
              <p style={{ fontSize: "1.3rem", fontWeight: "bold", margin: "0.2rem 0" }}>0 tokens</p>
              <small className="muted">Prompt: 0 | Saída: 0</small>
            </div>
            <div>
              <small className="muted">Modo de Extração Ativo</small>
              <p style={{ fontSize: "1.3rem", fontWeight: "bold", margin: "0.2rem 0" }}>Determinístico / Offline</p>
              <small className="muted">Ablação H3 / Regras determinísticas ativas</small>
            </div>
          </div>

          <h2>Envio de eventos para processamento</h2>
          <p>O envio é confirmado pelo RabbitMQ. Falhas e tarefas interrompidas são retomadas pelo worker; apenas a revisão humana publica evidências.</p>
          <table>
            <thead><tr><th>Evento</th><th>Tipo</th><th>Entrega</th><th>Tentativas</th><th>Próxima tentativa / erro</th></tr></thead>
            <tbody>
              {summary.outbox.map((event) => <tr key={event.id}>
                <td><code>{event.event_id}</code></td><td>{event.event_type}</td>
                <td>{event.published_at ? "Confirmado pelo broker" : ["DocumentoImportado", "FonteAlterada", "RelatorioSolicitado", "AnaliseSolicitada"].includes(event.event_type) ? "Pendente" : "Aguardando integração"}</td><td>{event.attempts}</td>
                <td>{event.published_at ? "—" : event.next_attempt_at} {event.last_error}</td>
              </tr>)}
              {summary.outbox.length === 0 && <tr><td colSpan={5}>Nenhum evento registrado.</td></tr>}
            </tbody>
          </table>
          <h2>Fila de Reavaliação por Mudança de Fonte / Errata / Retratação (RF-10, RC-06)</h2>
          <table>
            <thead>
              <tr>
                <th>Estudo</th>
                <th>Gatilho</th>
                <th>Status</th>
                <th>Notas</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {summary.reassessments.map((r) => (
                <tr key={r.id}>
                  <td>{r.study_title}</td>
                  <td><code>{r.trigger_type}</code></td>
                  <td>{r.status}</td>
                  <td>{r.notes}</td>
                  <td>
                    {r.status === "PENDING" && (
                      <button type="button" onClick={() => resolveReassessment(r.id)}>Marcar como Resolvido</button>
                    )}
                  </td>
                </tr>
              ))}
              {summary.reassessments.length === 0 && (
                <tr>
                  <td colSpan={5}>Nenhuma tarefa de reavaliação pendente.</td>
                </tr>
              )}
            </tbody>
          </table>

          <h2>Jobs com Lease, Tentativas e Quarentena (RF-11)</h2>
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Tentativas</th>
                <th>Último Erro</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {summary.jobs.map((j) => (
                <tr key={j.id}>
                  <td><code>{j.id}</code></td>
                  <td>{j.job_type}</td>
                  <td><code>{j.status}</code></td>
                  <td>{j.attempts} / {j.max_attempts}</td>
                  <td>{j.last_error ?? "-"}</td>
                  <td>
                    {(j.status === "FAILED" || j.status === "QUARANTINED") && (
                      <button type="button" onClick={() => retryJob(j.id)}>Reprocessar</button>
                    )}
                  </td>
                </tr>
              ))}
              {summary.jobs.length === 0 && (
                <tr>
                  <td colSpan={6}>Nenhum job registrado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
