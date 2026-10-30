# Etapa 0.22.0 — Concordância Inter-Avaliadores na Triagem Duplo-Cega

## 1. Contexto Metodológico
Na revisão sistemática e triagem metodológica (PRISMA-ScR), a seleção de estudos por dois revisores independentes e cegados exige a avaliação periódica do grau de alinhamento e calibração das decisões humanas.

Esta etapa disponibiliza o módulo [`denguepharma_analytics.clinical.agreement`](../analytics/src/denguepharma_analytics/clinical/agreement.py), endpoint protegido com `Cache-Control: no-store` e visualização no Streamlit.

## 2. Métricas Implementadas
1. **Concordância Observada ($P_o$)**: Proporção direta de concordância entre os revisores na diagonal da matriz de contingência ($N_{concordantes} / N_{total}$).
2. **Kappa de Cohen ($\kappa$)**: Coeficiente clássico que desconta a concordância esperada pelo acaso ($P_e$):
   $$\kappa = \frac{P_o - P_e}{1 - P_e}$$
3. **AC1 de Gwet**: Coeficiente de concordância inter-avaliadores robusto e imune ao *paradoxo de prevalência* (Feinstein & Cicchetti, 1990), onde distribuições altamente desbalanceadas (ex.: alta taxa de exclusão natural na triagem) produzem valores de $\kappa$ artificialmente baixos mesmo com $P_o > 90\%$.
4. **Matriz de Contingência 3x3**: Detalhamento estrito dos pares (`INCLUIR`, `EXCLUIR`, `INCERTO`) entre Revisor 1 e Revisor 2.

## 3. Salvaguardas Metodológicas
- **Preservação de Ausências**: Votos não pareados (onde apenas um revisor votou ou votos inválidos) são contabilizados separadamente em `excluded_unpaired` e não geram inferências artificiais.
- **Não Resolução Automática**: Métricas descritivas não substituem a adjudicação humana de conflitos e não alteram o status da seleção.
- **Proteção de Dados**: Consultas privadas exigem perfil `PESQUISADOR` ou `ADMINISTRADOR`.

## 4. Verificação e Evidências
- 6 testes unitários em `analytics/tests/test_agreement.py` cobrindo concordância perfeita, concordância ao acaso, teste de estresse contra o paradoxo de prevalência, matrizes incompletas e piloto realista.
- 1 teste de integração na API em `analytics/tests/test_review_workflow.py` validando autenticação, `Cache-Control: no-store` e payload JSON.
- 173 testes da suíte de analytics íntegros e compatíveis com a matriz de requisitos `REQ-CLN-008`.
