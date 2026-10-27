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
    id: number;
    event_id: string;
    aggregate_type: string;
    event_type: string;
    attempts: number;
    created_at: string;
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
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!session) return;
    const data = await api<OpsSummary>(session, "/api/ops/summary");
    setSummary(data);
  }

  useEffect(() => {
    load().catch((e) => setError((e as Error).message));
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

  return (
    <section aria-labelledby="ops-heading">
      <h1 id="ops-heading">Painel Operacional: Filas, Reavaliação e Pacote de Reprodução (RF-10, RF-11, RF-12)</h1>
      {error && <p role="alert">{error}</p>}

      <div>
        <button type="button" onClick={exportReproductionPackage}>
          Exportar Pacote de Reprodução Respeitando Licenças (RF-12 / T9)
        </button>
      </div>

      {reproPkg && (
        <div>
          <h2>Pacote de Reprodução (T9 / RNF-03)</h2>
          <pre>{reproPkg}</pre>
        </div>
      )}

      {summary && (
        <>
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
