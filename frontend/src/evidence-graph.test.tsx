import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EvidenceGraphPage } from "./pages/EvidenceGraphPage";

describe("EvidenceGraphPage (Eixo E)", () => {
  it("renderiza o grafo de rede e suas legendas de cores", () => {
    render(<EvidenceGraphPage />);
    expect(screen.getByRole("heading", { name: /Grafo de Rede de Evidências/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Fármacos/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Alvos Moleculares/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Desfechos/).length).toBeGreaterThan(0);
    expect(screen.getByText("Balapiravir")).toBeInTheDocument();
    expect(screen.getByText("NS5 (RdRp)")).toBeInTheDocument();
  });

  it("permite selecionar um nó e visualizar seus detalhes e conexões", async () => {
    render(<EvidenceGraphPage />);
    const nodeText = screen.getByText("Balapiravir");
    await userEvent.click(nodeText);
    expect(screen.getByRole("heading", { level: 3, name: "Balapiravir" })).toBeInTheDocument();
    expect(screen.getByText(/Análogo de nucleosídeo RdRp/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Limpar Seleção/ })).toBeInTheDocument();
  });

  it("permite filtrar nós por tipo", async () => {
    render(<EvidenceGraphPage />);
    const select = screen.getByLabelText(/Filtrar Tipo de Nó/);
    await userEvent.selectOptions(select, "TARGET");
    expect(screen.queryByText("Balapiravir")).not.toBeInTheDocument();
    expect(screen.getByText("NS5 (RdRp)")).toBeInTheDocument();
  });
});
