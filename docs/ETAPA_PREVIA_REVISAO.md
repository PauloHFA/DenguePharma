# Conferência da revisão independente — versão 0.8.0

Entrega de 28/10/2026. Esta etapa facilita conferir as decisões da própria planilha antes de registrá-las. Não executa triagem científica automaticamente e não remove a exigência de revisores independentes.

## Fluxo na aplicação

1. Abrir o [dashboard local](http://127.0.0.1:8501) e entrar em **Curadoria clínica — acesso protegido** com sua conta.
2. Em **Preparar e acompanhar a revisão do piloto**, baixar o pacote de revisão independente. Cada revisor deve preencher somente sua própria planilha, consultando fontes permitidas.
3. Selecionar o CSV UTF-8 preenchido e clicar em **Conferir prévia sem gravar decisões**.
4. Conferir as contagens de decisões novas, alterações, decisões idênticas e linhas em branco. A tabela mostra estudo, operação e os campos enviados pelo próprio revisor.
5. Confirmar a conferência e a autoria independente; clicar em **Confirmar e importar minhas decisões**.

A prévia não registra votos, não gera IDs de eventos e não altera snapshots. Um erro em qualquer linha recusa o lote. A confirmação continua necessária para a gravação, que permanece atômica e auditável.

Alterar a planilha ou a sessão remove a prévia na interface. Se outra decisão, fonte ou vínculo mudar a base entre a conferência e o envio, a API recusa o recibo antigo com `STALE_REVIEW_PREVIEW`. Confira novamente antes de tentar importar. A confirmação não reserva vagas de revisor; os limites e a independência são revalidados na importação.

## Contrato e compatibilidade

- Novo `POST /api/clinical/{workspace}/screening/preview`, autenticado, com corpo `text/csv`.
- Resposta: `preview=true`, `content_hash`, `receipt`, `would_import`, `would_create`, `would_update`, `unchanged`, `skipped` e `changes`.
- Confirmação pela interface: `POST /api/clinical/{workspace}/screening/import?expected_preview=RECIBO`, com os mesmos bytes de CSV e a mesma identidade autenticada.

O recibo é um hash de conferência que vincula workspace, input, arquivo, identidade, papéis, seleção/fontes atuais e cabeça da auditoria. Não substitui autenticação nem é aprovação científica. O recibo é recalculado na mesma transação da importação, antes de gravar qualquer decisão.

O endpoint antigo de importação continua aceitando chamadas sem `expected_preview` para compatibilidade com clientes existentes; elas continuam sujeitas às validações anteriores. O fluxo principal da interface exige a prévia e envia o recibo. Não se afirma que a prévia seja obrigatória para todos os clientes da API.

As duas operações compartilham a validação de triagem, incluindo bases antigas, classificação, limites de revisores e permissões. Na prévia não há chamada ao mecanismo de anexação de eventos nem `INSERT` temporário. Um terceiro revisor não pode usar a prévia para contornar a adjudicação. O resultado não apresenta votos, justificativas ou identidades de outros revisores.

## Limites preservados

O formato e os limites do CSV permanecem os mesmos: até 1 MiB, até 100 decisões por lote, cabeçalho do pacote sem alterações, hashes originais e campos humanos completos. Linhas inteiramente em branco são ignoradas; linhas parcialmente preenchidas são recusadas. Reenvios idênticos não duplicam votos.

O lote não adjudica conflitos, não aprova calibração e não publica evidência. Alterações de votos podem invalidar seleção e calibração anteriores, conforme o protocolo. A [coleta completa](ETAPA_COLETA_COMPLETA.md) continua condicionada à seleção e calibração vigentes.

## Situação da pesquisa

O piloto clínico real continua com **20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados**. Nenhum voto real foi preenchido durante esta implementação. Os cenários de importação e confirmação são sintéticos; a validação do ambiente real deve apenas consultar o piloto e conferir bloqueios.

REQ-CLN-012 registra esta entrega de software. REQ-CLN-006 permanece pendente da execução científica humana. O próximo passo científico é dois revisores preencherem suas decisões independentes, resolverem as divergências com adjudicação e documentarem a calibração antes de ampliar a coleta.

As contagens do [panorama anterior](RESULTADOS_GERAIS_PESQUISA.md) continuam descritivas. Esta melhoria não produz novas conclusões sobre benefício, alívio de sintomas ou segurança de medicamentos.

## Verificação da entrega

A suíte completa teve **69 testes aprovados**, incluindo os oito cenários novos de prévia, testes de permissões, validação dos formulários, PostgreSQL somente de leitura e relatórios Quarto reais. A evidência está em `analytics/target/review-preview-junit.xml`. A matriz contém **90 requisitos, dos quais 23 têm evidência automatizada nesta execução**; os requisitos futuros do PDF continuam planejados.

Os cenários novos conferem ausência de chamadas ao anexador de eventos e de alteração na sequência de IDs, reprodução da prévia, criação/alteração/reenvio, recusa de lotes inválidos e de terceiro revisor, vínculo do recibo a arquivo/ator/papéis/auditoria/fontes, autorização e confirmação explícita no formulário.

Os dois pilotos foram reprocessados na versão 0.8.0, com relatórios HTML e publicação local. As 29 tabelas de cada piloto preservaram os hashes lógicos da versão anterior, e os hashes dos inputs e a auditoria científica vazia permaneceram iguais.

| Corpus | Execução publicada localmente |
| --- | --- |
| Piloto clínico de 20 documentos | `19d81d238efa1134b188a06e7cffe45dc2e7166af1f8de9b8ffbef146d7685ed` |
| Piloto operacional de 50 documentos | `4b63e26758d5f1cc4bf7c38505ad90a9c1b8d900c7939565ce5024169c3c5da5` |

Os pilotos não devem ser somados como estudos únicos. Reprocessamento de software não equivale a nova coleta ou a novo resultado científico.

No navegador Chrome, com autenticação real, foram conferidos os indicadores 20/10/10/0, as 40 revisões pendentes e o envio de uma planilha em branco. A API recusou o lote com `REVIEW_CSV_NO_COMPLETED_DECISIONS`; o botão de confirmação permaneceu ausente, nenhuma importação foi enviada e login/logout funcionaram sem erros JavaScript. A verificação aguardou a conclusão do upload antes de acionar a prévia. Evidência: `analytics/target/review-preview-browser-results.json`.
