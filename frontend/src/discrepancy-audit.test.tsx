import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DiscrepancyAuditView } from "./components/DiscrepancyAuditView";

describe("DiscrepancyAuditView (Eixo B - REQ-ANA-005 e REQ-ING-006)", () => {
  it("renderiza o cabeçalho, aviso de salvaguarda RC-01/RC-02 e cards de resumo", () => {
    render(<DiscrepancyAuditView />);

    expect(screen.getByTestId("discrepancy-audit-view")).toBeInTheDocument();
    expect(
      screen.getByText(/Auditoria de Discrepâncias Registro vs Publicação/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Salvaguardas Metodológicas RC-01, RC-02 e REQ-ANA-005/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Pares Auditados")).toBeInTheDocument();
    expect(screen.getByText("Discrepâncias Críticas")).toBeInTheDocument();
    expect(screen.getByText("Aguardando Adjudicação")).toBeInTheDocument();
  });

  it("exibe outcome switching como severidade CRÍTICA e roteia para AGUARDA_REVISAO_HUMANA", () => {
    render(<DiscrepancyAuditView />);

    expect(screen.getByText("OUTCOME_SWITCHING")).toBeInTheDocument();
    expect(screen.getByText("CRITICA")).toBeInTheDocument();
    expect(screen.getAllByText("AGUARDA_REVISAO_HUMANA").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("NCT01234567").length).toBeGreaterThanOrEqual(1);
  });

  it("permite filtrar por severidade", async () => {
    render(<DiscrepancyAuditView />);

    const select = screen.getByLabelText(/Severidade/i);
    await userEvent.selectOptions(select, "CRITICA");

    expect(screen.getByText("OUTCOME_SWITCHING")).toBeInTheDocument();
    expect(screen.queryByText("DATE_DISCREPANCY")).not.toBeInTheDocument();
  });

  it("permite alternar para o histórico de versões por hash e verificar integridade", async () => {
    render(<DiscrepancyAuditView />);

    const tabBtn = screen.getByRole("button", { name: /Histórico e Diff por Hash/i });
    await userEvent.click(tabBtn);

    expect(screen.getByText(/Rastreabilidade de Versões \(REQ-ING-006\)/i)).toBeInTheDocument();
    expect(screen.getAllByText(/v1 → v2/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("APROVADO_ORIGINAL").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/SIM \(Fila Aberta\)/i).length).toBeGreaterThanOrEqual(1);
  });
});
