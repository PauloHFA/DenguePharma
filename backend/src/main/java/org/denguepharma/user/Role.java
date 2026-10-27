package org.denguepharma.user;

/** Papéis de acesso definidos na seção 11 da proposta. */
public enum Role {
    LEITOR,        // consulta evidência publicada
    REVISOR,       // tria e corrige, sem alterar fonte bruta
    ADJUDICADOR,   // resolve divergências e aprova campos críticos
    PESQUISADOR,   // define protocolos e executa avaliação
    ADMINISTRADOR  // gerencia acesso e operação
}

