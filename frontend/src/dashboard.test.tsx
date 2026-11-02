import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";

afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); });
function open() { return render(<MemoryRouter initialEntries={["/"]}><AuthProvider><App /></AuthProvider></MemoryRouter>); }

it("abre dashboard sem login e mostra estado vazio", async () => {
  const fetcher = vi.fn(async () => new Response("[]")); vi.stubGlobal("fetch", fetcher);
  open();
  expect(screen.getByRole("heading", { name: "Panorama da pesquisa farmacológica" })).toBeInTheDocument();
  expect(await screen.findByText("Nenhuma análise publicada")).toBeInTheDocument();
  expect(screen.queryByLabelText("Senha")).not.toBeInTheDocument();
  expect(fetcher).toHaveBeenCalledWith("/api/public/analyses", expect.objectContaining({ signal: expect.any(AbortSignal) }));
});

it("mostra resultados publicados, filtra documentos e distingue ausencia de revisao", async () => {
  const summary = { notice: "Panorama coletado", documentCount: 2, rawDocumentCount: 2, publicationCount: 1, trialCount: 1, studyCount: 0,
    temporal: [], distributions: [], completeness: [], enrollment: [], sourceRuns: [], warnings: [], links: [], linkCandidates: [],
    linkCoverage: { numerator: 0, denominator: 1, proportion: 0 }, changes: { status: "NO_BASELINE", new: [], changed: [], notObserved: [] },
    reviewed: { notice: "Revisão obrigatória", contextCounts: [], distributions: [], completeness: [], gaps: [], traceability: [] } };
  const records = [{ document_id: "p", title: "Artigo A", document_type: "PUBLICACAO", sources: ["PUBMED"], context: "NAO_CLASSIFICADO", publication_year: 2020, start_year: null, substances: [], countries: [], identifiers: ["PMID:1"], screening_states: ["PENDENTE"] },
    { document_id: "t", title: "Ensaio B", document_type: "REGISTRO_ENSAIO", sources: ["CLINICALTRIALS"], context: "NAO_CLASSIFICADO", publication_year: null, start_year: 2021, substances: ["composto"], countries: ["Brazil"], identifiers: ["NCT:2"], screening_states: ["PENDENTE"] }];
  vi.stubGlobal("fetch", vi.fn(async (path: string) => new Response(JSON.stringify(path.endsWith("summary.json") ? summary : path.endsWith("records.json") ? records : path === "/api/public/analyses" ? [{ id: "a", protocol_code: "PILOTO", cutoff_date: "2026-10-27", published_at: "2026-10-27T12:00:00Z" }] : { artifacts: [] }))));
  open();
  expect(await screen.findByText("Artigo A")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "PMID:1" })).toHaveAttribute("href", "https://pubmed.ncbi.nlm.nih.gov/1/");
  await userEvent.selectOptions(screen.getByLabelText("Fonte"), "PUBMED");
  await waitFor(() => expect(screen.queryByText("Ensaio B")).not.toBeInTheDocument());
  expect(screen.getByText("Artigo A")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Evidências revisadas" }));
  expect(screen.getByText(/Sem estudos com campos científicos revisados/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Pacote completo" })).toHaveAttribute("href", "/api/public/analyses/a/artifacts?name=bundle.zip");

  await userEvent.click(screen.getByRole("button", { name: "Carga Global (Eixo C)" }));
  expect(screen.getByRole("heading", { name: /Eixo C — Carga Global de Doença/ })).toBeInTheDocument();
  expect(screen.getByText(/Deserto de pesquisa clínica: altíssima mortalidade/)).toBeInTheDocument();
});

it("exibe falha de carregamento sem simular dados", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 503 })));
  open(); expect(await screen.findByRole("alert")).toHaveTextContent("503");
  expect(screen.queryByText("Nenhuma análise publicada")).not.toBeInTheDocument();
});
