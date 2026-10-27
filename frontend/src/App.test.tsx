import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function mockApi(roles: string[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/auth/login") return new Response(JSON.stringify({ token: "t" }), { status: 200 });
      return new Response(JSON.stringify({ email: "u@x.org", roles }), { status: 200 });
    }),
  );
}

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

describe("acesso", () => {
  it("redireciona para o login sem sessão", () => {
    renderAt("/catalogo");
    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("login inválido mostra erro em texto", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 401 })));
    renderAt("/login");
    await userEvent.type(screen.getByLabelText("E-mail"), "a@b.org");
    await userEvent.type(screen.getByLabelText("Senha"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos");
  });

  it("leitor vê só telas permitidas e não acessa o painel", async () => {
    mockApi(["LEITOR"]);
    renderAt("/login");
    await userEvent.type(screen.getByLabelText("E-mail"), "u@x.org");
    await userEvent.type(screen.getByLabelText("Senha"), "senha");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: "Catálogo" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(nav).toHaveTextContent("Catálogo");
    expect(nav).not.toHaveTextContent("Painel operacional");
    expect(nav).not.toHaveTextContent("Revisão de extração");
  });

  it("tela restrita exibe acesso limitado a quem não tem papel", async () => {
    mockApi(["LEITOR"]);
    sessionStorage.setItem("dp.session", JSON.stringify({ token: "t", email: "u@x.org", roles: ["LEITOR"] }));
    renderAt("/painel");
    expect(await screen.findByRole("alert")).toHaveTextContent("Acesso limitado");
  });

  it("pesquisador vê protocolos e importações com estado vazio", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("[]", { status: 200 })));
    sessionStorage.setItem("dp.session", JSON.stringify({ token: "t", email: "p@x.org", roles: ["PESQUISADOR"] }));
    const first = renderAt("/protocolos");
    expect(await screen.findByText(/Nenhum protocolo registrado/)).toBeInTheDocument();
    first.unmount();

    renderAt("/importacoes");
    expect(await screen.findByText(/Nenhuma importação executada/)).toBeInTheDocument();
  });

  it("protocolo registrado oferece congelar; rascunho oferece registrar", async () => {
    const protocols = [
      { id: "1", code: "A", version: 1, title: "T", question: "Q", sources: ["PUBMED"], cutoffDate: "2026-10-26", status: "DRAFT" },
      { id: "2", code: "B", version: 1, title: "T", question: "Q", sources: ["PUBMED"], cutoffDate: "2026-10-26", status: "REGISTERED" },
    ];
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(protocols), { status: 200 })));
    sessionStorage.setItem("dp.session", JSON.stringify({ token: "t", email: "p@x.org", roles: ["PESQUISADOR"] }));
    renderAt("/protocolos");
    expect(await screen.findByRole("button", { name: "Registrar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Congelar" })).toBeInTheDocument();
  });
});

