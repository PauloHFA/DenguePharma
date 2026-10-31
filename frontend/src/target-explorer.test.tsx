import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TargetExplorerPage } from "./pages/TargetExplorerPage";

describe("TargetExplorerPage", () => {
  it("renderiza alvos virais principais e detalhes do NS5", () => {
    render(<TargetExplorerPage />);
    expect(screen.getByRole("heading", { name: /Explorador de Alvos Biológicos/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /NS5 \(Polimerase RdRp & Metiltransferase\)/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Balapiravir/)[0]).toBeInTheDocument();
    expect(screen.getByText(/PDB 5ZQK/)).toBeInTheDocument();
  });

  it("permite selecionar outro alvo e visualizar seus inibidores", async () => {
    render(<TargetExplorerPage />);
    const ns3Button = screen.getByRole("button", { name: /NS3 \(Serino Protease & RNA Helicase\)/ });
    await userEvent.click(ns3Button);
    expect(screen.getByRole("heading", { name: /NS3 \(Serino Protease & RNA Helicase\)/ })).toBeInTheDocument();
    expect(screen.getAllByText(/Ivermectina/)[0]).toBeInTheDocument();
    expect(screen.getByText(/PDB 2FOM/)).toBeInTheDocument();
  });

  it("filtra alvos por categoria", async () => {
    render(<TargetExplorerPage />);
    const select = screen.getByLabelText(/Categoria de Alvo/);
    await userEvent.selectOptions(select, "HOSPEDEIRO");
    expect(screen.queryByRole("button", { name: /NS5/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Alvos Celulares do Hospedeiro/ })).toBeInTheDocument();
  });
});
