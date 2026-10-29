import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth/AuthContext";
import { ReviewPage } from "./pages/ReviewPage";
import { ComparatorPage } from "./pages/ComparatorPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ScreeningPage } from "./pages/ScreeningPage";
import { api } from "./api";
import type { Role } from "./auth/roles";

function session(roles: Role[] = ["ADJUDICADOR"]) {
  const value = { token: "token-test", email: "curador@test.org", roles };
  sessionStorage.setItem("dp.session", JSON.stringify(value));
  return value;
}

const field = {
  id: "f1", study_id: "s1", study_title: "Ensaio", field_name: "result", original_value: "20/25",
  normalized_value: "20/25", absence_status: "PRESENTE", review_status: "RASCUNHO_IA", published: false,
  evidence_text: "Virus cleared in 20/25 patients.", section: "Results", locator: "sent-2", page: 2,
  document_text: "Virus cleared in 20/25 patients.", document_origin: "PUBMED", document_version_no: 3,
  model_provider: "test", model_version: "1",
};

afterEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("contratos e fluxos de curadoria", () => {
  it("mostra o trecho real e envia as decisões aceitas pelo backend", async () => {
    session();
    const fetchMock = vi.fn(async (_path: string, init?: RequestInit) =>
      new Response(JSON.stringify(init?.method === "POST" ? { reviewStatus: "APROVADO" } : [field]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><ReviewPage /></AuthProvider>);
    expect(await screen.findByText(field.evidence_text, { selector: "blockquote" })).toBeInTheDocument();
    expect(screen.getByText(/versão 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Aprovar" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/extractions/fields/f1/review", expect.objectContaining({ method: "POST" })));
    const request = fetchMock.mock.calls.find(([, init]) => init?.method === "POST")![1]!;
    expect(JSON.parse(request.body as string)).toMatchObject({ decision: "ACEITAR", adjudication: true, publishAfterApproval: true });
  });

  it("exige motivo real para correção e envia trecho e enum em português", async () => {
    session();
    const fetchMock = vi.fn(async (_path: string, init?: RequestInit) =>
      new Response(JSON.stringify(init?.method === "POST" ? {} : [field]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><ReviewPage /></AuthProvider>);
    await screen.findByText("result", { selector: "strong" });
    await userEvent.click(screen.getByRole("button", { name: "Corrigir" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Informe o motivo");
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    await userEvent.type(screen.getByLabelText("Motivo da correção de result"), "Conferido na fonte");
    await userEvent.click(screen.getByRole("button", { name: "Corrigir" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
    expect(JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === "POST")![1]!.body as string))
      .toMatchObject({ decision: "CORRIGIR", correctedAbsenceStatus: "PRESENTE", correctedQuotedText: field.evidence_text, reason: "Conferido na fonte" });
  });

  it("encaminha campo crítico do revisor para adjudicação sem publicar", async () => {
    session(["REVISOR"]);
    const fetchMock = vi.fn(async (_path: string, init?: RequestInit) => new Response(JSON.stringify(init?.method === "POST" ? {} : [field])));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><ReviewPage /></AuthProvider>);
    await userEvent.click(await screen.findByRole("button", { name: "Enviar para adjudicação" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true));
    expect(JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === "POST")![1]!.body as string))
      .toMatchObject({ decision: "ACEITAR", adjudication: false, publishAfterApproval: false });
  });

  it("exibe a mensagem de incompatibilidade retornada pela API", async () => {
    session(["LEITOR"]);
    vi.stubGlobal("fetch", vi.fn(async (_path: string, init?: RequestInit) => new Response(JSON.stringify(init?.method === "POST"
      ? { studies: [], compatibleForDirectSynthesis: false, rankingPolicy: "Sem ranking", incompatibilities: [{ rule: "RC-01", code: "CONTEXTO_INCOMPATIVEL", message: "Contextos humano e animal são incompatíveis" }] }
      : [{ id: "a", title: "A" }, { id: "b", title: "B" }]))));
    render(<AuthProvider><ComparatorPage /></AuthProvider>);
    await userEvent.click(await screen.findByRole("button", { name: /Comparar Estudos Selecionados \(2\)/ }));
    expect(await screen.findByText(/Contextos humano e animal são incompatíveis/)).toBeInTheDocument();
  });

  it("baixa PDF com Bearer token e nome de arquivo", async () => {
    session(["LEITOR"]);
    const createUrl = vi.fn(() => "blob:report");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: vi.fn() }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("relatorio-r1.pdf");
    });
    const fetchMock = vi.fn(async (path: string) => path.includes("/export")
      ? new Response("%PDF-1.4", { headers: { "Content-Type": "application/pdf" } })
      : new Response(JSON.stringify([{ id: "r1", created_at: "2026-10-27", filters: "{}", study_count: 1 }])));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><ReportsPage /></AuthProvider>);
    await userEvent.click(await screen.findByRole("button", { name: "PDF" }));
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith("/api/reports/r1/export?format=pdf", { headers: { Authorization: "Bearer token-test" } });
    expect(createUrl).toHaveBeenCalledOnce();
  });

  it("preserva contexto pré-clínico, mostra resumo e exige justificativa para excluir", async () => {
    session(["REVISOR"]);
    const study = { id: "s1", title: "Modelo celular", context: "IN_VITRO", purpose: "PROFILAXIA", screening_status: "AGUARDANDO_TEXTO_COMPLETO", abstract_text: "Experimento em células", full_text: null };
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => new Response(JSON.stringify(
      init?.method === "POST" ? {} : path === "/api/screening/studies" ? [study] : path.endsWith("flowchart") ? null : [])));
    vi.stubGlobal("fetch", fetchMock);
    render(<AuthProvider><ScreeningPage /></AuthProvider>);
    expect(await screen.findByText("Experimento em células")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Excluir (TEXTO_COMPLETO)" }));
    expect(screen.getByRole("alert")).toHaveTextContent("justificativa");
    await userEvent.click(screen.getByRole("button", { name: "Incluir (TEXTO_COMPLETO)" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true));
    expect(JSON.parse(fetchMock.mock.calls.find(([, init]) => init?.method === "POST")![1]!.body as string))
      .toMatchObject({ context: "IN_VITRO", purpose: "PROFILAXIA", decision: "INCLUIR" });
  });

  it("aceita resposta vazia HTTP 200 e preserva detalhe de validação", async () => {
    const auth = session();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 200 })));
    await expect(api(auth, "/api/ops/reassessments/a/resolve", { method: "POST" })).resolves.toBeUndefined();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Trecho documental obrigatório" }), { status: 422 })));
    await expect(api(auth, "/api/extractions/fields/a/review")).rejects.toThrow("Trecho documental obrigatório");
  });
});
