# Atualização independente da curadoria — versão 0.18.0

Entrega de 28/10/2026. A curadoria passa a atualizar sua própria área sem reconstruir as tabelas públicas a cada interação. Essa alteração reduz a espera para filtrar a fila, consultar fontes e continuar a revisão humana. Não acrescenta análise científica ou decisão clínica.

## Problema observado e mudança

Até a versão 0.17.0, os controles privados provocavam a execução de toda a página Streamlit. Na medição local, uma troca de filtro pessoal repetiu 29 requisições à API pública, além das oito consultas privadas necessárias.

`clinical/ui.py` agora delimita a área de curadoria com `st.fragment`. Interações nessa área atualizam somente o fragmento. Login, saída da conta, importação confirmada de planilha, triagem salva, vínculo confirmado, motivo de exclusão e limpeza de trechos usam `clinical/refresh.py` para selecionar o escopo de atualização válido no contexto atual.

O auxiliar usa o escopo `fragment` durante uma execução isolada e o escopo `app` durante uma execução completa ou um formulário independente. Essa distinção evita solicitar uma atualização de fragmento em contexto não permitido pelo Streamlit. O comportamento foi conferido no código e na documentação do Streamlit instalado e fixado no lockfile, versão 1.66.1.

## Resultado observado no navegador

A mesma ação foi executada com autenticação real no piloto clínico: mudar **Minha revisão pendente** para **Minha revisão registrada**, aguardar o fim da atualização e sair sem registrar votos.

| Medida durante a troca do filtro | Antes, 0.17.0 | Depois, 0.18.0 |
| --- | --- | --- |
| Requisições à API pública | 29 | 0 |
| Requisições à API privada | 8 | 8 |
| Tempo observado | 9,043 s | 0,574 s |
| Decisões enviadas | 0 | 0 |
| Erros de página | 0 | 0 |

Os tempos são observações de uma execução local por versão, não uma garantia de latência ou um ensaio de carga. A redução de chamadas públicas demonstra que a ação privada deixou de reconstruir os dados públicos. As oito consultas privadas permaneceram, com informações atuais da conta e do workspace.

## Como usar

Abrir o [dashboard](http://127.0.0.1:8501/) e entrar em **Curadoria clínica — acesso protegido**. Não há configuração adicional. A [fila pessoal](ETAPA_FILA_PESSOAL.md), o [dossiê documental](ETAPA_DOSSIE_TRIAGEM.md), a importação e os formulários existentes permanecem disponíveis.

Os controles públicos e uma atualização completa da página continuam executando o dashboard e suas verificações. A área pública preserva o último resultado carregado enquanto a pessoa interage apenas com a curadoria; publicar uma execução continua sendo uma ação separada.

## Autorização, atualização e integridade

- Não foi introduzido cache de votos, tokens, fontes privadas ou respostas autenticadas.
- A identidade continua vindo da sessão e sendo validada pela API; os endpoints privados preservam suas permissões e respostas `no-store` existentes.
- A saída da sessão retira os controles e limpa o estado privado conforme o fluxo anterior.
- O ajuste não altera revisão independente, limites de dois votos, adjudicação ou validação de bases e recibos desatualizados.
- Uma atualização da interface não reenvia automaticamente um formulário confirmado.
- As verificações de publicação, hashes e downloads públicos continuam no backend. Não foram adicionadas exceções de integridade para obter o ganho de desempenho.

O fragmento é da sessão Streamlit; não há transferência de dados entre contas, agenda de atualização automática ou novo processamento de coleta.

## Verificação e evidências

Cinco casos novos cobrem os contextos de atualização, autenticação sucessiva de duas contas sintéticas, saída da conta e ausência de repetição de uma ação confirmada. Os testes dos formulários de triagem, importação, identidade, extração e seleção continuam fazendo parte da regressão.

A bateria completa passou: **144 testes**, incluindo PostgreSQL e Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada; MIG-006 e CLN-008 receberam os cenários adicionais. Um teste separado no Chrome confirmou que o filtro público por fonte continua consultando a tabela PUBMED e preservando os indicadores do corpus.

Evidências locais, fora do Git:

- `analytics/target/curation-performance-before.json` e `curation-performance-after.json`: medição da mesma troca de filtro nas duas versões.
- `analytics/target/curation-performance-browser.mjs`: execução no Chrome, com contagem das chamadas pelos logs da API.
- `analytics/target/curation-refresh-full-junit.xml`: regressão completa.
- `analytics/target/curation-refresh-real-results.json`: situação dos dois workspaces reais.
- `analytics/target/public-filter-refresh-browser-results.json`: continuidade do filtro público por fonte.

As medições não devem ser feitas em paralelo a outros acessos à API que contaminem a contagem do log. O script pressupõe serviços locais disponíveis e credenciais existentes, sem imprimir senhas ou tokens. A medição anterior exige a versão anterior do código; os arquivos registram o resultado observado antes desta alteração.

## Situação da pesquisa

Os pilotos preservam 20 e 50 documentos e, respectivamente, 40 e 100 votos independentes faltantes. Os eventos reais continuam vazios, sem aprovação de calibração ou resultados clínicos. As execuções publicadas e os [relatórios científicos 0.14.0](resultados/pesquisa-reprodutivel/README.md) foram preservados.

Esta etapa melhora a execução do trabalho de revisão. O próximo marco científico continua sendo a leitura e a decisão dos revisores independentes; o ganho de desempenho não constitui evidência sobre benefício ou dano de medicamentos.
