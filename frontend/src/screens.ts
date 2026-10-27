import type { Role } from "./auth/roles";

export interface ScreenDef {
  path: string;
  title: string;
  description: string;
  emptyMessage: string;
  /** Papéis com acesso; vazio = qualquer usuário autenticado. */
  roles: readonly Role[];
}

// Telas mínimas da seção 11 do PDF.
export const SCREENS: readonly ScreenDef[] = [
  {
    path: "protocolos",
    title: "Protocolos",
    description: "Fontes, estratégia, elegibilidade e data de corte. Toda execução referencia a versão do protocolo.",
    emptyMessage: "Nenhum protocolo registrado.",
    roles: ["PESQUISADOR", "ADMINISTRADOR"],
  },
  {
    path: "importacoes",
    title: "Importações",
    description: "Coletas do PubMed e do ClinicalTrials.gov com checkpoint.",
    emptyMessage: "Nenhuma importação executada. Atualização pendente até a primeira coleta.",
    roles: ["PESQUISADOR", "ADMINISTRADOR"],
  },
  {
    path: "triagem",
    title: "Triagem",
    description: "Triagem independente por dois revisores e adjudicação das divergências.",
    emptyMessage: "Nenhum registro aguardando triagem.",
    roles: ["REVISOR", "ADJUDICADOR", "PESQUISADOR"],
  },
  {
    path: "revisao",
    title: "Revisão de extração",
    description: "Sugestões lado a lado com o trecho de origem. Revisão humana é obrigatória para publicar.",
    emptyMessage: "Nenhuma extração aguardando revisão.",
    roles: ["REVISOR", "ADJUDICADOR"],
  },
  {
    path: "catalogo",
    title: "Catálogo",
    description: "Evidência publicada por substância, finalidade, desenho, sorotipo e fase. Os filtros não ocultam limitações.",
    emptyMessage: "Nenhuma evidência publicada. O texto integral pode estar indisponível por licença.",
    roles: [],
  },
  {
    path: "comparador",
    title: "Comparador",
    description: "Comparação por desfecho e tempo, com incompatibilidades visíveis. Não há ranking clínico automático.",
    emptyMessage: "Selecione evidências publicadas para comparar.",
    roles: [],
  },
  {
    path: "relatorios",
    title: "Relatórios",
    description: "Exportação em PDF, CSV e JSON com fontes, filtros, data, versões, limitações e status de revisão.",
    emptyMessage: "Nenhum relatório gerado.",
    roles: [],
  },
  {
    path: "painel",
    title: "Painel operacional",
    description: "Monitoramento de processamento, falhas, retentativas e reprocessamento autorizado.",
    emptyMessage: "Nenhum job registrado.",
    roles: ["ADMINISTRADOR"],
  },
];

