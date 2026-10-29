# Extração clínica por campos e revisão dos resultados

Data: 28/10/2026. Software **0.5.0**. Continuidade do [plano atual](PLANO_ATUAL_SINTESE_CLINICA.md) e da [preparação da revisão independente](ETAPA_REVISAO_INDEPENDENTE.md).

## Objetivo e situação científica

Permitir registrar resultados clínicos por campos, conferir cálculos sem salvar, vincular trechos exatos e conduzir revisão/adjudicação sem preencher JSON no fluxo principal. As ações avançadas por contrato continuam disponíveis.

**Esta entrega é de software.** O piloto real continua com 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados. Nenhum estudo foi incluído ou extraído automaticamente. A extração só é habilitada para estudos incluídos pela seleção independente atual; enquanto isso, a interface apresenta bloqueio explícito.

## O que foi implementado

- Formulário de resultado por estudo, intervenção, comparador, população, gravidade, fase, início da intervenção, população de análise, desfecho, unidade e período.
- Identidade da comparação e dos braços, participantes analisados/randomizados, eventos ou médias/desvios padrão, conforme o método escolhido.
- Registro da estimativa publicada ou cálculo individual RR/MD nos casos já autorizados pelo protocolo, sem combinação estatística.
- Estados explícitos de ausência para números não preenchidos. Campo vazio permanece nulo e não vira zero; zero informado permanece zero.
- Cuidados de suporte, limitações, instrumento metodológico, domínios e justificativas, sem avaliação automática de risco de viés.
- Referências literais por campo, selecionando versão, trecho e ocorrência explicitamente. O usuário não precisa digitar hashes no formulário.
- Prévia somente de leitura usando a mesma validação do salvamento e os mesmos cálculos existentes.
- Consulta de rascunhos e formulários próprios para revisão independente e adjudicação, com permissões derivadas na API e conferidas novamente em cada ação.
- Revalidação da classificação consolidada: um resultado incompatível com a intervenção/população/contexto atualmente permitidos deixa de compor os resultados atuais.

O protocolo científico e os contratos de entrada analítica permanecem preservados. Não houve nova coleta nem alteração do corte temporal, dos desfechos ou dos métodos estatísticos aprovados.

## Uso na interface

1. Abrir `http://127.0.0.1:8501/`, autenticar na curadoria e selecionar o espaço clínico correto.
2. Concluir a seleção por duas revisões independentes e adjudicar conflitos quando necessário. O formulário não permite pular essa etapa.
3. Em **Extração clínica por campos**, escolher o estudo incluído. Classificações consolidadas aparecem identificadas como tal; números e informações específicas do resultado começam vazios.
4. Em **Trechos de suporte deste rascunho**, selecionar uma versão pertencente aos documentos vinculados ao estudo. Consultar a fonte permitida, copiar o trecho com seus espaços e selecionar a ocorrência conferida.
5. Adicionar referências para cada campo necessário. O sistema constrói o localizador com versão, hash, posições e texto literal; não interpreta se o trecho sustenta semanticamente o resultado.
6. Escolher como registrar o efeito, preencher os campos, cuidados de suporte, limitações e avaliação metodológica.
7. Usar **Conferir rascunho sem salvar** para verificar a estrutura, o cálculo individual e a disponibilidade de suporte literal.
8. Usar **Salvar rascunho para revisão independente** somente após conferir os dados. O salvamento não aprova nem publica evidência.
9. Outra pessoa deve abrir **Revisão e adjudicação dos resultados**, conferir o rascunho e registrar uma decisão com justificativa. A adjudicação exige identidade distinta do autor e dos revisores anteriores, com papel autorizado.
10. Após aprovação, gerar e publicar nova execução explicitamente, conforme o [guia de operação](IMPLEMENTACAO_SINTESE_CLINICA.md). A tela não publica resultados automaticamente.

Os trechos em preparação ficam na sessão privada, separados por workspace e estudo. Só passam a integrar a auditoria quando o rascunho é salvo. Logout limpa esses dados de sessão. Não há cache global de fontes ou trechos. Não use a sessão como armazenamento permanente de uma extração ainda não salva.

## Preenchimento numérico e ausências

Contagens aceitam apenas inteiros, sem separador de milhar. Medidas contínuas e estimativas aceitam ponto ou vírgula decimal, mas não ambos no mesmo valor. NaN e infinitos são rejeitados. Um erro de preenchimento pode ser corrigido e reenviado sem gravar o resultado inválido.

Os modos disponíveis são:

| Modo | Comportamento |
|---|---|
| `REPORTED` | Preserva RR, OR, HR ou diferença de médias publicados, com os limites e o nível de confiança informados |
| `RR` | Usa eventos e denominadores de braços paralelos randomizados independentes, conforme o método existente |
| `MD` | Usa médias, desvios padrão e denominadores compatíveis, conforme o método existente |

Uma prévia com cálculo não representa evidência de benefício. Suporte literal completo significa apenas que as referências exigidas passaram pelas verificações estruturais/literais implementadas; a interpretação exige revisão humana. Células zero, dados insuficientes ou desenhos incompatíveis continuam sujeitos às regras metodológicas existentes, sem correção automática de continuidade, conversão de medianas ou inferência de valores.

Os estados `NAO_EXTRAIDO`, `NAO_INFORMADO`, `NAO_APLICAVEL`, `INCERTO` e `NAO_HOUVE_EVENTO` são selecionados pelo curador para campos ausentes. Marcar um estado não cria um valor numérico. Eventos zero observados devem ser digitados explicitamente como `0`.

## Revisão, correções e mudanças de classificação

Decisões começam sem opção escolhida. Autor não pode revisar seu próprio resultado. Um adjudicador que atuar também como revisor intermediário não poderá adjudicar aquele resultado; as verificações permanecem na API, independentemente da interface.

Resultados já decididos exigem confirmação de reavaliação na interface para registrar outra revisão ou adjudicação. Cada decisão mantém o histórico. Resultados substituídos ou com base incompatível são identificados, e seus botões de revisão ficam bloqueados.

Correções podem referenciar rascunho anterior e precisam de motivo. A identidade do estudo/comparação/desfecho/tempo deve ser preservada conforme o contrato; outra combinação representa outro resultado. Um rascunho de correção não retira automaticamente um resultado aprovado. A substituição continua dependendo de revisão e adjudicação.

A validação compartilhada verifica também a classificação atual da seleção. Por exemplo: se a triagem consolidada deixar de incluir a intervenção de um resultado antigo, esse resultado passa a incompatível e não entra na próxima síntese congelada. Snapshots históricos continuam imutáveis e consultáveis; nenhuma publicação anterior é reescrita silenciosamente.

## Estados de acompanhamento

O fluxo identifica rascunhos aguardando revisão, aguardando adjudicação, rejeitados, aprovados, substituídos, em conflito, com reavaliação pendente ou com base desatualizada. Esses estados são operacionais; não correspondem às categorias clínicas de benefício, dano ou inconclusão.

## API e validação

Novos endpoints protegidos:

- `GET /api/clinical/{workspace}/extraction`: estudos incluídos, rascunhos, estado atual, cálculos e permissões de ação para a identidade autenticada.
- `POST /api/clinical/{workspace}/results/preview`: valida o resultado e calcula a prévia, sem eventos ou publicação.

Salvar, revisar e adjudicar continuam usando os eventos existentes `RESULT_DRAFTED`, `RESULT_REVIEWED` e `RESULT_ADJUDICATED`. A validação do resultado foi centralizada e é reutilizada pela prévia, salvamento, revisão e seleção dos resultados atuais.

**45 testes aprovados**, incluindo PostgreSQL e Quarto reais. Oito novos cenários cobrem ausências/zero/decimais, prévia sem gravação, ciclo de aprovação com identidades distintas, mudança de classificação, permissões, bloqueio sem inclusão, preenchimento de formulário com correção de erro e decisões explícitas pelos formulários de revisão/adjudicação. Casos com votos e resultados são sintéticos, em diretórios temporários; não constituem resultados reais da pesquisa.

A matriz contém 87 requisitos. REQ-CLN-009 acompanha esta entrega de software; REQ-CLN-006, que exige revisão e síntese científicas reais, continua pendente.

Verificação com login real no Chrome: piloto de 20 registros selecionado, 40 votos pendentes, extração bloqueada por ausência de estudos incluídos, nenhum botão de salvamento de resultado disponível nesse estado, pacote de revisão conferido por hash e logout concluído sem erros JavaScript. Nenhuma decisão foi enviada ao corpus real. Registros operacionais ficam em `analytics/target/extraction-browser-results.json` e `analytics/target/extraction-dashboard.png`, ignorados pelo Git.

Execução publicada com software 0.5.0: `19fb639335fdebac1cea0a3675814212238b9c467d5eb40e6d007095b7565eb4`. A entrada clínica conserva o hash `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb`, a auditoria permanece sem votos e as 29 tabelas têm os mesmos hashes lógicos da execução anterior. Os testes de extração completa demonstram o fluxo de software em dados sintéticos, sem afirmar que o corpus real já passou pela seleção ou revisão.
