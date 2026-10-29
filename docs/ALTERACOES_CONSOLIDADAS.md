# Registro final das alterações — DenguePharma

## 31. Mapa de cobertura da extração — versão 0.20.0

O [painel privado de cobertura](ETAPA_COBERTURA_EXTRACAO.md) apresenta uma célula por identidade incluída e desfecho do protocolo, contando somente resultados canônicos revisados. Mantém conflitos visíveis e distingue falta de revisão de ausência de benefício ou aplicabilidade. Não soma participantes, efeitos ou publicações repetidas. A exportação autenticada inclui CSV, resumo e manifesto de hashes, sem votos ou textos de fontes.

Os pilotos permanecem sem inclusões resolvidas, com mapas vazios e 40 e 100 avaliações independentes faltantes. Nenhum voto ou resultado clínico foi criado, e os snapshots anteriores foram preservados. Por orientação do pesquisador, as próximas entregas passam a ser commitadas após validação; o checkpoint até 0.19.0 é `0d2739f`, com política registrada em [VERSIONAMENTO.md](VERSIONAMENTO.md).

Validação: 160 testes aprovados, com seis casos novos, PostgreSQL e Quarto reais. O login, o estado vazio e o download passaram no Chrome; o ZIP coincidiu com o módulo e seus hashes foram conferidos. A matriz continua com 96 requisitos e 29 com evidência automatizada.

## 30. Integridade documental — versão 0.19.0

Foi acrescentado o [fluxo protegido de alertas documentais](ETAPA_INTEGRIDADE_DOCUMENTAL.md), com [contrato](../spec/clinical/INTEGRIDADE_DOCUMENTAL.md). Adjudicadores/administradores registram reavaliação, retirada ou regularização com referência e justificativa, mediante prévia de impacto e confirmação vinculada à conta e ao estado atual. O alerta modifica a base do estudo e impede uso de aprovações antigas, sem remover fontes ou eventos.

Regularizar não reativa votos, resultados ou calibração anteriores. O bloqueio acompanha o documento após correção de identidade. Novos snapshots não podem misturar alertas ativos e resultados aprovados dos estudos afetados. Os metadados de integridade omitidos quando vazios preservam os hashes dos dois snapshots reais; os pilotos continuam sem alertas humanos e com 40 e 100 avaliações independentes faltantes, respectivamente.

O efeito é na curadoria e nas próximas execuções explícitas. Relatórios históricos não são apagados ou atualizados automaticamente. Não há detecção automática de retratações, nova API externa ou decisão clínica gerada nesta entrega. O escopo integral do requisito do PDF permanece planejado.

Validação: 154 testes aprovados, com dez cenários novos, PostgreSQL e Quarto reais; login, permissões, painel e saída conferidos no Chrome. Os hashes dos snapshots reais e a integridade das publicações 0.14.0 foram confirmados, sem novos eventos reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada.

## 29. Atualização independente da curadoria — versão 0.18.0

A [área privada passou a atualizar seu próprio fragmento](ETAPA_ATUALIZACAO_CURADORIA.md), sem reconstruir as tabelas públicas em cada interação. O auxiliar de atualização distingue execução completa e de fragmento, sendo usado nos fluxos de login/saída, importação, triagem, vínculo, motivo de exclusão e limpeza de trechos. Não foi acrescentado cache de dados clínicos nem flexibilizada a verificação de integridade.

Na medição local da mesma troca de filtro, as chamadas públicas caíram de 29 para zero, mantendo oito consultas privadas. O tempo observado passou de 9,043 s para 0,574 s; trata-se de uma observação por versão, sem garantia de latência. Autenticação real, saída da sessão e ausência de erro de página foram conferidas, sem enviar decisões. Os dois workspaces e as publicações anteriores permanecem preservados; o piloto clínico continua com 40 votos faltantes e sem resultados clínicos revisados.

Validação final: 144 testes aprovados, incluindo cinco casos novos e PostgreSQL/Quarto reais. O filtro público por fonte também foi conferido no Chrome e continua recarregando a tabela selecionada. A matriz mantém 96 requisitos e 29 com evidência automatizada, sem declarar concluída a pesquisa.

## 28. Fila pessoal de revisão — versão 0.17.0

O [guia da etapa](ETAPA_FILA_PESSOAL.md) documenta o progresso por conta e os filtros para pendências, revisões registradas, adjudicação autorizada e fila completa. Os estados distinguem voto atual, fonte que exige reavaliação e vagas já ocupadas. A classificação anterior não é transferida ou reativada. Depois de um envio humano bem-sucedido, o formulário atualiza a fila e apresenta a próxima pendência, sem copiar os campos do estudo anterior.

Os endpoints privados de progresso e estado retornam dados pessoais vinculados à autenticação, com `Cache-Control: no-store`; filtros e avisos são limpos ao sair. Não há reserva automática de vagas. Os pilotos mantêm 20 e 50 identidades e 40 e 100 avaliações globais faltantes, respectivamente. Para uma conta sem voto atual, havia 20 e 50 tarefas disponíveis na conferência. Não foram registrados votos reais ou resultados clínicos; relatórios históricos continuam preservados.

Validação: 139 testes aprovados, com oito cenários novos e PostgreSQL/Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada. Revisão registrada não foi tratada como seleção resolvida ou conclusão clínica.

No Chrome, foram conferidos autenticação real, 20 tarefas pessoais versus 40 avaliações globais, filtros de revisões registradas/pendentes e retirada dos controles após sair. Nenhuma decisão foi enviada e não houve erro de página.

## 27. Resumo da seleção e motivos humanos — versão 0.16.0

Foi acrescentado o [resumo auditável da seleção](ETAPA_FLUXO_SELECAO.md), com [contrato próprio](../spec/clinical/MOTIVOS_EXCLUSAO.md). O painel distingue documentos, identidades e estados; permite a adjudicadores/administradores documentar um motivo principal apenas após exclusão resolvida. Os votos e as justificativas originais não são substituídos. Alterações de fontes, identidade, votos ou adjudicação deixam a anotação anterior fora da contagem atual, preservando o histórico.

O JSON agregado autenticado inclui hashes e versão do dicionário, sem votos, justificativas livres ou textos. Os totais de identificação, duplicados removidos e registros triados da revisão completa permanecem nulos; o requisito PRISMA completo SEL-004 não foi promovido como concluído. Os pilotos mantêm 20 e 50 documentos e, respectivamente, 40 e 100 avaliações independentes faltantes. Nenhum voto, motivo real ou resultado clínico foi criado na validação. As publicações analíticas anteriores permanecem intactas.

Validação: 131 testes aprovados, com oito cenários novos e PostgreSQL/Quarto reais; login, painel, download e saída conferidos no Chrome. O arquivo baixado corresponde ao retorno do módulo. A matriz continua com 96 requisitos e 29 com evidência automatizada, sem declarar concluída a pesquisa clínica.

## 26. Dossiê documental na triagem — versão 0.15.0

O formulário passou a apresentar documentos, identificadores, representações textuais e hashes do estudo selecionado, com consulta autenticada e leitura explícita do texto normalizado. O [guia](ETAPA_DOSSIE_TRIAGEM.md) descreve o fluxo e os limites. A API não retorna votos ou sugestões de elegibilidade, recusa base desatualizada e confere a integridade das representações. Identidades ambíguas e fontes sem texto permanecem visíveis, sem preenchimento automático.

Os 20 documentos clínicos e os 50 operacionais foram conferidos sem criar decisões ou alterar identidades; suas 50 e 125 representações permanecem preservadas. Os testes têm 123 casos aprovados considerando a reexecução do caso cujo mock foi atualizado; a falha inicial foi mantida no histórico de evidências. A matriz continua com 96 requisitos e 29 com evidência. A clínica permanece sem resultados revisados, com 40 avaliações independentes pendentes no piloto clínico. As execuções públicas e os relatórios históricos não foram substituídos.

## 25. Notebook de pesquisa e relatórios reproduzíveis

Entrega de 28/10/2026: [guia](ETAPA_NOTEBOOK_PESQUISA.md) e [resultados](resultados/pesquisa-reprodutivel/README.md). O notebook 03 reúne panorama, patrocinadores, completude, datas de relato, referências e situação clínica a partir das mesmas tabelas públicas da versão 0.14.0. Foram gerados HTMLs com gráficos incorporados e notebooks executados, separados para os pilotos de 20 e 50 documentos, com manifestos de hashes e versões. As transformações permanecem nos módulos analíticos.

As duas execuções completaram sete células sem erros; no navegador, três imagens carregadas por relatório e nenhuma requisição externa. A repetição do piloto clínico preservou as saídas das sete células e os hashes lógicos das 34 tabelas públicas. O executor recusa diretórios de destino existentes e execuções não publicadas. Nenhuma decisão de revisão, coleta ou snapshot foi alterada. Não houve promoção dos eixos científicos como completos ou mudança da versão do pacote.

Os resultados continuam descritivos: nenhum resultado clínico revisado, com 40 avaliações independentes pendentes no piloto clínico. Não há ranking de medicamentos ou conclusão de eficácia. Datas bibliográficas posteriores ao corte continuam sinalizadas para conferência.

Consolidação em 27/10/2026, horário de São Paulo. Este documento reúne as alterações das etapas 1 a 4, o escopo vigente, os resultados da validação e as pendências. Os números dos testes e do piloto representam a execução registrada nessa data.

## 1. Evolução do escopo

| Documento/etapa | Decisão ou entrega |
| --- | --- |
| Proposta PDF original | Proposta de integração de evidências e avaliação de extração manual versus IA; preservada como documento histórico. |
| Auditoria inicial | Inventário das funcionalidades, lacunas e problemas encontrados antes das correções. |
| Etapa 1 | Correções de curadoria, publicação, triagem, comparador, downloads e isolamento das demonstrações. |
| Etapa 2 | Processamento real com Outbox/Inbox, RabbitMQ, workers Python, MinIO, leases e retentativas. |
| Requisitos v2 / etapa 3 | Análises descritivas reproduzíveis de campos revisados; IA experimental retirada do MVP obrigatório. |
| Requisitos v3 / etapa 4 | Ciência de dados como núcleo do projeto; panorama do corpus coletado, evidências revisadas em camada separada e dashboards abertos. |

O escopo vigente é o dos [Requisitos v3](REQUISITOS_V3.md). O experimento com IA fica para uma etapa posterior. Não são necessárias APIs pagas de IA nesta entrega. Revisão humana continua necessária para inclusão e publicação de campos científicos.

O projeto abrange medicamentos e compostos em contextos clínicos e pré-clínicos separados. Vacinação, controle vetorial e diagnóstico sem intervenção farmacológica devem ser excluídos na triagem. A busca ampla pode recuperá-los, por isso registros coletados não são automaticamente considerados elegíveis.

## 2. Curadoria e integridade científica

- Revisão alinhada aos campos e estados da API, com valor, trecho disponível, seção, página, localizador e versão documental.
- Correções de valores presentes exigem justificativa e suporte literal da versão documental. O backend verifica o texto disponível e preserva antes/depois na auditoria.
- Campos críticos exigem o papel apropriado para publicação. Alterações automáticas não sobrescrevem valores já aprovados.
- Triagem permite classificar contexto e finalidade, registrar ausência de resultados e motivos de exclusão, preservando decisões individuais e adjudicação.
- Catálogo e comparador excluem estudos demonstrativos, excluídos, retratados e absorvidos por fusão, conforme seus critérios de elegibilidade.
- Comparador apresenta incompatibilidades e não aceita IDs repetidos como estudos diferentes.
- Downloads protegidos usam autenticação; relatórios PDF têm quebra de linhas/paginação e CSV registra filtros.
- Licença desconhecida permanece `NAO_VERIFICADA`; acesso aberto não é convertido automaticamente em autorização de redistribuição.

A conferência literal de um trecho e a existência de um localizador não demonstram, por si, suporte semântico. Essa avaliação permanece na revisão científica.

## 3. Coleta, integração e processamento

| Fonte | Uso implementado e limite |
| --- | --- |
| PubMed | Coleta E-utilities com paginação/checkpoint; consultas acima da janela de resultados são divididas por períodos. Preserva metadados, indexação química e identificadores de registros disponíveis. |
| ClinicalTrials.gov | Coleta paginada da API v2 e preservação do registro estruturado. Metadados de ensaio não equivalem ao texto integral de uma publicação. |
| PubChem | Consulta para normalização no cadastro de substâncias; o snapshot usa aliases exatos associados a um CID não ambíguo. |
| Europe PMC / PMC | Coleta e enriquecimento de metadados; não representa obtenção universal de textos integrais. Namespace de DOI alinhado ao usado pelo PubMed. |
| LILACS / WHO ICTRP | Importação assistida de registros informados no protocolo; não declarar como conectores automáticos completos dessas bases. |

Cada versão encontrada passa a ser vinculada à execução de busca que a encontrou, inclusive quando o conteúdo não mudou. Coletas anteriores à nova tabela não recebem proveniência retroativa inventada.

O fluxo reutiliza `Outbox → RabbitMQ → worker Python → MinIO`, com confirmação de publicação, mensagens persistentes, Inbox, job por evento, lease renovável, retentativas e quarentena. Resultados de executores com lease vencido são rejeitados. A conclusão do job e o registro transacional do resultado são atômicos.

Documentos e artefatos têm hashes verificados no armazenamento. A credencial interna do worker atende apenas às rotas do pipeline. O extrator inicial é determinístico e cobre padrões limitados de sorotipo/tamanho amostral; não realiza extração científica completa de PDFs, OCR ou tabelas.

## 4. Dados e métodos de análise

A metodologia combina revisão de escopo, análise exploratória e mapeamento de evidências. O [PRISMA-ScR](https://www.prisma-statement.org/scoping) orienta o relato; estratégias, elegibilidade, corte, amostragem e transformações ficam no protocolo e nos artefatos.

### Camadas e unidades

- **Corpus coletado:** documentos e registros recuperados, com situação de triagem explícita. Permite analisar metadados antes da revisão científica.
- **Evidências revisadas:** estudos incluídos com campos aprovados/publicados, provenientes de revisão identificada.
- **Documentos, estudos e campos científicos:** exportados em conjuntos relacionados, preservando referências e múltiplos vínculos. Documento, registro de ensaio e estudo não são usados como unidades intercambiáveis.

Deduplicação documental usa identificadores exatos e preserva as referências das fontes. Correspondências ambíguas e referências bibliográficas geram candidatos à revisão; não confirmam automaticamente que dois registros pertencem ao mesmo estudo. Valores divergentes são mantidos como conflitos, sem escolher silenciosamente o mais recente.

### Análises entregues

| Análise | Regra de interpretação |
| --- | --- |
| Distribuição temporal | Separar ano de publicação e ano de início do ensaio. Anos bibliográficos posteriores ao corte são preservados e sinalizados para conferência. |
| Perfil dos ensaios | Distribuições de desenho, fase, recrutamento e disponibilidade de resultados no registro. |
| Intervenções | Limpeza lexical dos nomes e uso de identidade PubChem quando há correspondência exata não ambígua; indexação química do PubMed não vira intervenção automaticamente. |
| Participantes informados | Separar inscrição prevista, efetiva e tipo desconhecido; descrever disponibilidade, mediana, quartis e extremos, sem somar participantes entre documentos. |
| Países | Usar local de realização do ensaio; contar cada registro uma vez por país. Ensaios multinacionais podem produzir percentuais cuja soma excede 100%. |
| Mapas revisados | Distribuições e cruzamentos por substância, contexto, finalidade e categoria de desfecho, mantendo clínico e pré-clínico separados. |
| Disponibilidade de campos | Mostrar numerador/denominador, ausências, conflitos e pendências. “Não aplicável” explícito fica fora do denominador; denominador zero produz nulo/“sem dados”. |
| Integração e rastreabilidade | Separar vínculos confirmados/candidatos e presença de identificadores, versões e localizadores. Resultados no registro e publicação vinculada são indicadores distintos. |
| Atualizações | Comparar snapshots para identificar documentos novos, hashes alterados e itens não observados; ausência não demonstra retratação. |

Completude não é risco de viés; frequência não é eficácia ou aprovação regulatória. Não foram implementados meta-análise, ranking terapêutico, previsão de eficácia, preenchimento por inferência ou testes de significância exploratórios.

## 5. Interfaces e contratos

### Aplicação

- `/` e `/dashboard` abrem diretamente nos resultados publicados, sem exigir login.
- `/curadoria` encaminha ao fluxo protegido. Login permanece disponível para curadoria/administração.
- Abas públicas: corpus/evolução, ensaios/intervenções, evidências revisadas e qualidade/integração.
- Indicadores e figuras representam a execução selecionada. Busca e seletores filtram as tabelas identificadas; selecionar outra execução troca o conjunto completo.
- Identificadores documentais têm links para as fontes quando reconhecidos. Há download de dados, gráficos, manifesto e pacote completo.
- Layout móvel mantém tabelas com rolagem horizontal local. Rótulos acessíveis dos seletores foram ajustados e testados no navegador.
- Relatórios permite solicitar o panorama por protocolo, escolher execução anterior para comparação e publicar resultados concluídos.

### APIs

| Interface | Comportamento |
| --- | --- |
| `POST /api/analyses` | Mantém análises revisadas v2, com solicitação autenticada. |
| `POST /api/analyses/corpus` | Solicita corpus v3 com `protocolId` e `previousAnalysisId` opcional; pesquisador/administrador. |
| `GET /api/analyses` e `/{id}` | Consulta autenticada de execuções e estado. |
| `GET /api/analyses/{id}/artifacts?name=...` | Download autenticado dos artefatos disponíveis. |
| `POST /api/analyses/{id}/publish` | Publicação explícita de corpus v3 concluído; pesquisador/administrador; repetir não duplica. |
| `GET /api/public/analyses` e `/{id}` | Leitura anônima apenas de execuções publicadas. |
| `GET /api/public/analyses/{id}/artifacts?name=...` | Download público dos artefatos da execução publicada. |
| Rotas experimentais antigas | Comandos de particionamento/alocação/sessões/métricas retirados do MVP retornam `410 Gone`; histórico preservado. |

Concluir o processamento não publica a execução. Publicar o panorama não aprova a elegibilidade dos registros nem seus campos científicos. Operações de importação, revisão e administração continuam protegidas.

## 6. Persistência e reprodução

| Migration | Alteração |
| --- | --- |
| V6 | Identificação e isolamento dos estudos demonstrativos. |
| V7 | Estruturas do pipeline durável, arquivamento e controle de processamento. |
| V8 | Snapshots, execuções e artefatos de análise imutáveis. |
| V9 | Proveniência entre busca/versão documental e publicação explícita de análises. |

Snapshots anteriores não são reescritos. Entrada v3 usa `schemaVersion=3.0` e `dictionaryVersion=corpus-v3.0`; análises v2 permanecem executáveis. O evento `AnaliseSolicitada` e o job `ANALYZE_EVIDENCE` atendem aos dois formatos.

Os módulos Python compartilham preparação/agregação entre execução por comando e worker. O notebook importa essas funções. pandas e Matplotlib atendem às tabelas/gráficos; dependências estão fixadas no lockfile.

O pacote contém entrada congelada, documentos preparados, estudos, campos científicos aprovados, tabelas analíticas, relatório HTML, PNG, resumo, planilha de revisão e manifesto. Este registra hashes, versões e configuração. `reproduction_source.json` preserva os bytes dos módulos analíticos e da cartografia em base64.

Cartografia: Natural Earth v5.1.2, domínio público, resolução 1:110m. Países não representados nessa resolução continuam nas tabelas e são relacionados no resumo.

Os comandos `collect`, `analyze`, `download` e `publish`, a preparação do ambiente e o procedimento de reprodução estão descritos na [etapa 4](IMPLEMENTACAO_ETAPA_4.md). A coleta completa por CLI exige a planilha identificada do piloto correspondente; essa validação não substitui a triagem/adjudicação científica.

## 7. Validação e execução local final

| Verificação | Resultado registrado |
| --- | --- |
| Java | 57 testes aprovados, sem falhas, erros ou testes ignorados nos relatórios consolidados. |
| Python | 38 testes aprovados. |
| Frontend | 21 testes aprovados e build TypeScript/Vite concluído. |
| Pipeline real | PostgreSQL, servidor HTTP, RabbitMQ, MinIO e processo Python verificados em recursos isolados, para análises v2/v3. |
| Navegador | Acesso anônimo, abas, filtros, fontes, imagens, download e tela móvel verificados. |
| Reprodução do piloto | Resumo numérico e 19 tabelas CSV coincidiram entre o worker e a execução com o código congelado no pacote. |
| Armazenamento do piloto | SHA-256 dos 34 objetos no MinIO verificados. |

O piloto real recuperou **25 registros PubMed e 25 ClinicalTrials.gov**, com corte solicitado em 27/10/2026. O pacote final contém **33 arquivos, 19 tabelas CSV e oito gráficos PNG**. Há **zero estudos com campos científicos revisados** nessa execução.

Dois registros têm ano bibliográfico posterior ao corte e exigem conferência. Há registros potencialmente inelegíveis na busca ampla. Singapore permanece na tabela, com ausência de representação no mapa de baixa resolução explicitada.

Execução publicada: `5dc0c29f-234e-4ec4-8f32-91459358b472`; script `corpus-3.0.2`. Protocolo, hash da entrada, evidências de reprodução e arquivos locais estão registrados em [Validação de ciência de dados](TESTE_CIENCIA_DADOS.md).

Endereços da execução local: interface `http://127.0.0.1:5173/`, backend `http://127.0.0.1:18080`, PostgreSQL 5434, RabbitMQ 5673/15673 e MinIO 9000/9001. As portas foram ajustadas para coexistir com outros serviços locais; configurações permanecem no ambiente, sem registrar segredos neste documento.

## 8. Pendências e limites

1. Revisar os 50 registros do piloto, conferindo preparação, elegibilidade, variedade dos desenhos e divergências temporais; registrar responsável, data e justificativas.
2. Ajustar o protocolo conforme essa revisão e então executar/homologar a coleta completa.
3. Realizar triagem e publicação de campos científicos para preencher o mapa de evidências revisadas. População, comparador, resultados e limitações podem exigir leitura documental.
4. Completar, conforme as próximas etapas, obtenção permitida de textos integrais/OCR, integrações complementares brasileiras e atualização periódica com eventos das fontes.
5. Homologar operação ampliada: desempenho/carga, acessibilidade completa, implantação/TLS e restauração conjunta de banco e objetos.
6. Se retomado, elaborar protocolo próprio para o experimento com IA, referência anotada e medição de qualidade/tempo.

Limites atuais: snapshot de corpus até 8 MiB; pacote compactado/descompactado até 32 MiB e até 256 artefatos. Exceder limites provoca falha explícita, sem truncamento silencioso. Corpus maiores podem exigir particionamento ou ampliação desses limites após o piloto.

**Estado final:** núcleo de ciência de dados implementado e piloto operacional executado. Revisão humana e validação científica permanecem pendentes; a plataforma não declara descoberta de tratamento nem homologação integral de todos os requisitos históricos.

## 9. Documentos de referência

- [Plano atual da síntese clínica](PLANO_ATUAL_SINTESE_CLINICA.md): objetivo vigente, metodologia, sequência de execução e critérios de aceite.
- [Implementação da síntese clínica](IMPLEMENTACAO_SINTESE_CLINICA.md): entrega técnica, comandos, validação e pendências científicas.
- [Requisitos v3](REQUISITOS_V3.md): escopo histórico anterior à migração Analytics e à emenda clínica.
- [Etapa 4](IMPLEMENTACAO_ETAPA_4.md): contratos, comandos e operação das análises de corpus.
- [Validação de ciência de dados — registro operacional](TESTE_CIENCIA_DADOS.md): resultados e pendências do piloto.
- [Requisitos v2](REQUISITOS_V2.md) e [etapa 3](IMPLEMENTACAO_ETAPA_3.md): análises revisadas e compatibilidade.
- [Etapa 2](IMPLEMENTACAO_ETAPA_2.md) e [etapa 1](IMPLEMENTACAO_ETAPA_1.md): entregas técnicas anteriores.
- [Auditoria inicial](AUDITORIA_REQUISITOS.md): estado histórico anterior às correções.

## 10. Atualização de 28/10/2026 — migração Analytics

O novo PDF Analytics foi adotado como referência do projeto completo, com eixos A/B/C/D obrigatórios por etapas e E opcional. A migração escolhida passa a usar FastAPI, Streamlit e Quarto, mantendo o mesmo repositório e preservando o legado durante a transição. Os requisitos v3 descritos acima ficam históricos.

A **[primeira entrega da migração](MIGRACAO_ANALYTICS.md)** documenta a especificação SDD, os módulos Python, a leitura somente de leitura, os 19 conjuntos Parquet/DuckDB, a API pública e o dashboard novo em `http://127.0.0.1:8501/`. O [guia de execução](../analytics/README.md) contém instalação e comandos.

Foram preservados os 50 documentos e o hash de entrada; o panorama científico continua vazio por falta de campos revisados. A nova suíte teve 14 testes aprovados com PostgreSQL/Quarto reais. Os 12 requisitos MIG do primeiro marco foram verificados; isso não conclui os 66 requisitos do novo PDF. Java/React, curadoria e processamento legados continuam disponíveis, sem retirada antecipada.

## 11. Atualização de 28/10/2026 — benefício, alívio de sintomas e segurança

A [emenda clínica](../spec/clinical/EMENDA_CLINICA.md) passa a priorizar a pergunta sobre intervenções farmacológicas em adultos e crianças com dengue estabelecida. Mantém ensaios randomizados como camada principal de benefício e observacionais separados para segurança/contexto, sem meta-análise ou ranking. Carga de doença e experimento de IA foram adiados. Os PDFs, requisitos anteriores, Java/React e os 50 documentos originais foram preservados.

Foi acrescentado o pacote `clinical` em Python, com protocolo congelado, espaço privado transacional, auditoria por eventos/hash, duas triagens independentes, terceiro adjudicador, vínculos documentais explícitos, extração por braço/comparação/desfecho/tempo, suporte literal e revisão independente. Alterações de fontes invalidam revisões antigas. Dados aprovados divergentes geram conflito, sem preferência automática pelo mais recente. Rascunho de correção não remove resultado aprovado.

Foram implementados RR com IC log-Wald e diferença de médias com IC de Welch para casos compatíveis; estimativas publicadas conservam medida e nível do intervalo. Ausência não vira zero, medianas não viram médias, e não há efeito combinado. Avaliação metodológica exige instrumento/domínios quando marcada como realizada, sem GRADE automático. Conclusões dependem de justificativa humana sobre importância clínica, incerteza, consistência e limitações; ausência de resultado revisado não gera “inconclusivo” automaticamente.

As novas execuções têm seis tabelas clínicas adicionais, CSV/Parquet/DuckDB, fichas, mapa de categorias humanas e gráficos PNG por estudo, além do relatório Quarto HTML com figuras incorporadas. A FastAPI oferece consulta pública e curadoria protegida com papéis verificados na autenticação legada. O Streamlit continua aberto para leitura e oferece área protegida com formulário JSON por contrato. Versões publicadas anteriores permanecem acessíveis.

A busca clínica foi ampliada com termos de sintomas/analgésicos/antitérmicos. Um novo piloto de **20 registros reais (10 PubMed + 10 ClinicalTrials.gov)** foi coletado, com protocolo, corte e checkpoint registrados, separado do piloto operacional de 50 documentos. As 70 referências desses dois espaços foram conferidas contra as versões originais por hash, sem criar decisões científicas. Todos permanecem pendentes de revisão na síntese clínica. O piloto novo não foi transformado automaticamente em referência adjudicada nem em conclusão terapêutica.

O [guia completo da entrega](IMPLEMENTACAO_SINTESE_CLINICA.md) documenta comandos, endpoints, permissões, dados reais, testes e limitações. A matriz SDD agora contém 84 requisitos: 66 originais, 12 MIG e 6 CLN. A suíte cobre cálculos conhecidos, conflitos, duplicação, revisão independente, fontes obsoletas, pendência/ausência, permissões, downloads, CLI equivalente, gráficos e Quarto. A conclusão científica real continua pendente de calibração, textos permitidos, seleção, extração, avaliação metodológica e adjudicação por pesquisadores; isso está explicitado em REQ-CLN-006.

Validação final: **24 testes aprovados com PostgreSQL/Quarto reais**, cinco requisitos CLN de software verificados, autenticação real e teste no Chrome desktop/mobile. Dashboard em `http://127.0.0.1:8501/`, com novo piloto 20/10/10/0 e zero resultados clínicos aprovados. Execução clínica publicada: `2665dc99d26e8a4b765664bed913e894b0fda613dd431ce2adbfd83eb90ad5d2`. Não foi publicada conclusão de eficácia.

## 12. Consolidação do plano vigente em docs

O [plano atual da síntese clínica](PLANO_ATUAL_SINTESE_CLINICA.md) reúne a pergunta principal, população, exclusões, desfechos, métodos, produto científico, sequência de execução, situação da entrega e critérios de aceite. Distingue software implementado de revisão científica pendente e identifica a calibração do piloto de 20 registros como próximo marco. Não altera o protocolo nem declara novas análises ou conclusões clínicas executadas.

## 13. Continuidade — diagnóstico de calibração e resultados gerais

A versão 0.3.0 acrescenta quatro tabelas de calibração, sinais literais com proveniência, distinção dos tipos de intervenção declarados, gráfico exportável, resumo Markdown e seção própria no Quarto. O dashboard ganhou a aba Resultados gerais e a curadoria ganhou formulário de triagem por campos. Revisão independente, adjudicação e publicação explícita continuam obrigatórias; nenhum sinal gera decisão científica.

O piloto de 20 documentos foi reprocessado sem nova coleta e sem alterar o protocolo ou os snapshots antigos. Há 17 documentos com sinais para conferência, com sobreposição, 6/10 registros com resultados disponíveis e zero resultados clínicos revisados. Isso evidencia a necessidade de calibração, sem classificar os medicamentos como benéficos ou prejudiciais.

A [documentação da continuidade](CONTINUIDADE_CALIBRACAO.md), o [relatório de resultados gerais](RESULTADOS_GERAIS_PESQUISA.md) e os [CSVs exportados](resultados/README.md) registram métodos, números, fontes e limitações. Foram aprovados 30 testes com PostgreSQL/Quarto reais. A matriz contém 85 requisitos, incluindo CLN-007 para o diagnóstico; CLN-006, relativo à execução científica final, permanece pendente.

## 14. Apoio à revisão independente do piloto — versão 0.4.0

Foi preparado um pacote privado para os revisores do piloto de 20 registros, com planilha de decisão em branco, fontes/versões/hashes, protocolo, contratos e manifesto. Não contém votos, revisores ou textos integrais. A importação CSV exige autenticação, valida o lote inteiro em uma transação, rejeita bases antigas e reconhece reenvios idênticos sem duplicar eventos. As identidades dos revisores vêm da sessão; adjudicação e publicação continuam separadas.

O dashboard recebeu painel privado de pendências, identificação mais clara dos espaços e gerador de localizadores em texto normalizado, preservando Unicode e espaços. O pacote e o progresso também podem ser consultados por comando. Há 40 votos iniciais faltantes no piloto, sem aprovação automática de calibração, sem ampliação da coleta e sem novas conclusões clínicas.

O [guia da etapa](ETAPA_REVISAO_INDEPENDENTE.md) documenta arquivos, instruções para dois revisores e adjudicador, limites e endpoints. Foram aprovados **37 testes**, incluindo PostgreSQL/Quarto reais. A matriz contém 86 requisitos, com CLN-008 para o apoio operacional; CLN-006 continua pendente. Os snapshots, resultados publicados anteriores e o piloto de 50 documentos foram preservados.

## 15. Extração clínica e revisão por campos — versão 0.5.0

A curadoria recebeu formulário clínico por comparação, braço, população, desfecho e tempo, com números inicialmente vazios, estados de ausência, suporte literal por ocorrência e avaliação metodológica documentada. A prévia compartilha a validação e os cálculos do salvamento, sem gravar eventos. Foram acrescentados formulários de revisão e adjudicação com decisão explícita e permissões conferidas na API.

Resultados são revalidados contra a classificação atual da seleção. Uma intervenção removida da seleção, por exemplo, invalida a participação de seu resultado antigo na próxima síntese, sem alterar snapshots históricos. Correções, independência dos revisores, suporte documental e publicação explícita permanecem obrigatórios.

O [guia de extração](ETAPA_EXTRACAO_CLINICA.md) descreve campos, modos de efeito, referências, estados e limites. A suíte teve **45 testes aprovados**, com PostgreSQL/Quarto reais, e a matriz passou a 87 requisitos, incluindo CLN-009. No corpus real, a extração segue bloqueada por falta de seleção independente: 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados. Não houve coleta adicional ou aprovação científica automática.

## 16. Calibração e síntese clínica por campos — versão 0.6.0

Foram implementados formulários para referências sentinela e aprovação da calibração, conclusão clínica por grupo revisado e ausência de estudo elegível no corpus. As decisões exigem confirmação e justificativa humanas. Não há escolha automática de categoria, classificação por p-valor ou publicação automática.

A API passou a exigir `selection_hash` nas aprovações de calibração, conclusões e ausências. Conclusões dependem de seleção completa e calibração vigente; alterações invalidam o uso automático de decisões antigas. A verificação de ausência foi corrigida para não ignorar estudos incluídos em população mista. Snapshots e eventos anteriores permanecem preservados.

O [guia da etapa](ETAPA_CALIBRACAO_SINTESE.md) documenta procedimentos, mudança de contrato e limites metodológicos. Foram aprovados **53 testes**, incluindo PostgreSQL/Quarto reais. A matriz contém 88 requisitos, incluindo CLN-010; CLN-006 continua pendente de revisão científica real. O piloto mantém 20 registros, 40 votos iniciais faltantes e zero resultados clínicos revisados.

## 17. Coleta completa controlada — versão 0.7.0

Foi acrescentado um plano ligado à seleção e calibração vigentes, com estratégia, fontes e corte congelados. O runner persiste intenções antes das chamadas remotas, recupera operações por identificador, retoma importações falhadas e impede execução simultânea para a mesma configuração. Respostas perdidas não provocam repetição automática de POST.

O snapshot de metadados é exportado pelo PostgreSQL somente de leitura, preservando versões e hashes das importações, sem depender do limite HTTP de 8 MiB. Snapshot e manifesto são imutáveis e gravados atomicamente. Aprovações científicas, votos e textos integrais não são transferidos para o novo corpus.

O [guia da etapa](ETAPA_COLETA_COMPLETA.md) registra comandos, estados, recuperação, limites e pré-requisitos. A matriz passa a 89 requisitos, incluindo CLN-011. O piloto mantém 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados. A coleta completa real continua bloqueada; CLN-006 permanece pendente. Java/React e os resultados históricos foram preservados.

Validação da versão 0.7.0: **61 testes aprovados**, incluindo leitura PostgreSQL e relatórios Quarto reais. Os dois testes de banco foram repetidos após ligar o Docker, que estava indisponível no início. A matriz registra 22 requisitos com evidência automatizada. As 29 tabelas dos pilotos de 20 e 50 documentos preservaram os hashes lógicos; os snapshots novos documentam o reprocessamento, sem novos achados clínicos.

## 18. Conferência da revisão independente — versão 0.8.0

Foi acrescentada a prévia autenticada da importação CSV, com contagens de decisões novas, alterações, decisões idênticas e linhas em branco. A prévia usa a mesma validação da gravação, sem anexar eventos ou criar votos temporários. A interface apresenta os próprios campos enviados pelo revisor e exige confirmação explícita antes de importar.

Um recibo vincula arquivo, identidade, papéis, seleção/fontes e auditoria. Se a base mudar, a confirmação é recusada antes de gravar. Alterações de arquivo/sessão removem a prévia na interface. O endpoint antigo continua compatível; a prévia é obrigatória no fluxo principal da interface, sem substituir autenticação, independência, adjudicação ou calibração.

O [guia da entrega](ETAPA_PREVIA_REVISAO.md) descreve procedimentos, endpoints e limites. A matriz passa a 90 requisitos, incluindo CLN-012. O corpus real mantém 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados; nenhuma decisão foi produzida automaticamente.

Validação da versão 0.8.0: **69 testes aprovados**, com PostgreSQL e Quarto reais, e matriz com 23 requisitos apoiados por evidência automatizada. Os pilotos foram reprocessados sem modificar seus inputs ou as 29 tabelas lógicas. Os relatórios continuam descritivos, sem votos ou resultados clínicos novos.

O teste autenticado em navegador real também confirmou a recusa de planilha em branco, a ausência de confirmação antes de prévia válida e o logout, sem votos registrados ou erros JavaScript. A auditoria científica real permanece vazia.

## 19. Backup e restauração da curadoria — versão 0.9.0

Foi implementado o backup privado do workspace clínico por cópia consistente SQLite, com suporte a WAL, snapshot, protocolo, fontes e auditoria. O pacote registra hashes e tamanhos; a restauração exige o hash esperado, valida schema, integridade, fontes e cadeia de eventos, recusa arquivos perigosos e não substitui dados existentes. Arquivos e workspaces só aparecem no destino final após a gravação/validação completa.

Foram criadas e restauradas cópias dos pilotos reais de 20 e 50 documentos em diretório separado. Os snapshots e as fontes permaneceram equivalentes, os originais não foram alterados e nenhum evento científico foi acrescentado. As cópias não foram publicadas. O [guia operacional](ETAPA_BACKUP_CURADORIA.md) registra comandos, caminhos, hashes, limites e escopo privado.

A matriz passa a 91 requisitos, com MIG-013 para esta parte de M07. O backup integral do PostgreSQL/MinIO/filas e os demais critérios de migração continuam pendentes. Os relatórios analíticos publicados na versão 0.8.0 permanecem válidos. A pesquisa mantém 40 votos iniciais pendentes e zero resultados clínicos revisados no piloto de 20 registros.

Validação da versão 0.9.0: **77 testes aprovados**, incluindo oito cenários novos e verificações reais de PostgreSQL/Quarto. As restaurações dos dois pilotos reais preservaram snapshots, fontes e auditoria. A matriz registra 24 requisitos com evidência automatizada; M07 e a pesquisa não foram declarados concluídos.

## 20. Conferência da identidade dos estudos — versão 0.10.0

A curadoria recebeu tabela de vínculos documento–estudo, prévia do impacto e confirmação auditável por adjudicador/administrador. O recibo vincula a operação à identidade, à justificativa, aos papéis e à base atual; não há fusão automática por título ou substância. Correções podem devolver documentos a identidades originais conhecidas, sem apagar eventos ou criar IDs arbitrários.

Foi corrigida a escolha silenciosa do primeiro vínculo legado quando havia referências divergentes. Essas ambiguidades passam a bloquear inclusão e calibração até conferência humana. Eventos de identidade integram as bases dos estudos afetados; desfazer um vínculo não reativa votos, resultados ou calibrações antigos.

O [guia da etapa](ETAPA_IDENTIDADE_ESTUDOS.md) documenta interface, API, compatibilidade e limites. Foram aprovados **85 testes**, incluindo oito cenários novos e PostgreSQL/Quarto reais. A matriz passa a 92 requisitos, incluindo CLN-013. Nos pilotos reais não havia ambiguidades ou eventos de vínculo; seus agrupamentos e snapshots foram preservados, sem qualquer vínculo real confirmado nesta implementação.

O painel também foi validado em navegador real autenticado, com seleção explícita e confirmação indisponível antes da prévia, sem registrar vínculos ou votos. A consulta privada e a conferência dos backups anteriores preservaram os snapshots dos dois pilotos. A matriz registra 25 requisitos com evidência automatizada nesta execução.

## 21. Comparação entre execuções publicadas — versão 0.11.0

Foi implementado o acompanhamento de atualizações por CLI, API pública e dashboard. O comparador exige escopo compatível e distingue documentos novos, não observados, alterações de conteúdo/referência/representação e mudança da data de recuperação. Contagens possuem unidade e denominador explícitos; tabelas públicas têm mudanças de dados e schema separadas. Não se inferem retratação, exclusão ou efeito clínico.

As exportações JSON/CSV têm manifesto, hashes, proteção contra fórmulas e pasta imutável. A API verifica publicação e integridade; textos privados e tabelas silver não são exportados. O [guia da etapa](ETAPA_COMPARACAO_EXECUCOES.md) e os [artefatos compartilháveis](resultados/atualizacoes-0.11/README.md) registram métodos e resultados.

A comparação real entre as publicações 0.6.0 e 0.8.0 mostrou os mesmos 20 e 50 documentos em seus respectivos pilotos, zero documentos novos/alterados/não observados e 24 tabelas públicas inalteradas em cada caso. Os pilotos de protocolos diferentes não foram tratados como atualizações comparáveis. A curadoria permanece com 40 votos iniciais pendentes no piloto clínico; não houve novos achados de eficácia.

Validação da versão 0.11.0: **93 testes aprovados**, incluindo PostgreSQL/Quarto reais e oito cenários novos. A matriz registra 26 requisitos com evidência automatizada. Os JSONs, CSVs e manifestos dos dois resultados reais foram preservados em `docs/resultados/atualizacoes-0.11`, sem modificar entradas ou decisões científicas.

A conferência no navegador também passou: painel público, referência explícita, 20 documentos e 24 tabelas inalteradas, download com hash idêntico ao CLI e bloqueio de protocolos incompatíveis, sem erros JavaScript. Nenhum voto ou conclusão clínica foi criado.

## 22. Patrocinadores declarados nos registros — versão 0.12.0

Foi acrescentada uma análise descritiva por patrocinador responsável declarado no ClinicalTrials.gov, usando as mesmas versões documentais existentes no PostgreSQL somente de leitura. O módulo consolida registros por NCT válido, mantém documentos sem identificador separados, preserva observações e referências por documento e distingue presença, ausência e conflito. Não escolhe automaticamente valores divergentes por data e não infere identidade institucional, financiamento efetivo, risco de viés ou eficácia.

A aplicação passou a gerar 32 tabelas, incluindo três de patrocinadores, com gráfico PNG, seção no relatório Quarto e painel público em Ensaios. O novo comando `snapshot-collection` congela metadados de importações concluídas sem iniciar coleta nem transferir aprovações. Os workspaces clínicos originais e os snapshots anteriores permaneceram preservados.

No piloto clínico, os 10 registros declararam INDUSTRY em 4/10, OTHER em 4/10 e NIH em 2/10. No operacional, de 25 registros: OTHER 11/25, INDUSTRY 8/25, NIH 3/25, FED 2/25 e OTHER_GOV 1/25. Nome e categoria estavam disponíveis em todos os registros desses recortes. Os pilotos não foram somados e os resultados não foram apresentados como síntese de estudos elegíveis.

O [guia da etapa](ETAPA_PATROCINADORES.md) e os [artefatos compartilháveis](resultados/patrocinadores-0.12/README.md) registram métodos, contagens, denominadores, proveniência e limites. A matriz passa a 94 requisitos, incluindo MIG-015. O eixo A permanece parcial; a curadoria clínica mantém 40 votos iniciais pendentes e zero resultados clínicos revisados.

Validação da versão 0.12.0: **101 testes aprovados**, incluindo PostgreSQL/Quarto reais e oito cenários novos. A matriz registra 27 requisitos com evidência automatizada. As execuções têm 32 tabelas, e os gráficos, CSVs, resumos e manifestos estão preservados em `docs/resultados/patrocinadores-0.12`. O workspace clínico original não recebeu eventos científicos novos.

O teste em navegador real confirmou o painel público, as contagens 4/10 INDUSTRY, 2/10 NIH e 4/10 OTHER, o hash do PNG, o CSV e o relatório Quarto, sem erros JavaScript. A revisão clínica e os votos originais continuam pendentes.

## 23. Relato dos registros — auditoria de datas, versão 0.13.0

Foi iniciada a parte descritiva do eixo B, com disponibilidade declarada de resultados, precisão de datas, conflitos e intervalos de calendário entre conclusão primária e primeiro depósito. O [protocolo específico](../spec/reporting/PROTOCOLO_DATAS_REGISTROS.md) exige pares diários ACTUAL, status COMPLETED, indicador positivo e datas até o corte. Ausências, datas estimadas/parciais, conflitos e valores posteriores ao corte não são imputados. Indicador desconhecido não vira falso, e status UNKNOWN não é classificado como ensaio encerrado ou não encerrado.

Nos 10 registros do piloto clínico, 8 declaram COMPLETED e 6 indicam resultados; 5 pares são calculáveis, com mediana de 709 dias e intervalo de 469 a 1.288 dias. No piloto operacional, de 25 registros, 17 declaram COMPLETED, 6 indicam resultados e 3 pares são calculáveis, com mediana de 1.288 dias. Esses resumos condicionais não estimam o atraso dos demais registros, não representam tempo de recuperação dos pacientes e não são comparações entre os pilotos.

A aplicação passou a gerar 36 tabelas, com quatro novas de auditoria, gráfico PNG e seção Quarto separada dos efeitos clínicos. Os 32 conjuntos anteriores preservaram seus hashes lógicos. O [guia da etapa](ETAPA_AUDITORIA_RELATO.md) e os [artefatos exportados](resultados/relato-0.13/README.md) registram critérios, números e limitações.

A matriz passa a 95 requisitos, com MIG-016. O eixo B permanece parcial; Kaplan–Meier, censura, modelos, vínculos conferidos e discrepâncias não foram implementados, e ANA-003 continua planejado. O piloto clínico original mantém 40 votos iniciais pendentes e zero resultados clínicos revisados.

Validação da versão 0.13.0: evidência consolidada de **109 cenários aprovados**. A execução completa teve 108 aprovados e uma asserção de capacidade antiga; após atualizar o estado parcial do eixo B e conferir as flags de desconhecimento, nove testes foram repetidos com aprovação. A matriz registra 28 requisitos com evidência automatizada. Os logs individuais e a consolidação foram preservados.

O painel foi conferido em navegador real: 5 pares calculáveis, mediana de 709 dias, depósito ESTIMATED preservado e excluído do intervalo, PNG com hash verificado, CSV e Quarto disponíveis, sem erros JavaScript. A curadoria clínica e seus votos permaneceram intactos.

## 24. Cobertura bibliográfica por PMID — versão 0.14.0

Foi acrescentada a auditoria das referências declaradas pelos registros, mantendo RESULT, DERIVED, BACKGROUND e outros códigos separados. Coincidência por PMID gera somente candidato bibliográfico; não confirma identidade clínica, relevância ou suporte de resultados. Identificadores ausentes/inválidos e referências não localizadas permanecem rastreáveis, sem busca automática de artigos ou alterações de curadoria.

O piloto clínico tem 71 PMIDs citados sem coincidência no corpus: 57 BACKGROUND e 14 DERIVED, sem referência RESULT declarada. O indicador de resultados permanece verdadeiro em 6/10 registros, sem ser convertido em referência ou confirmação de artigo. No operacional, dois dos 25 registros declaram 28 PMIDs RESULT; a união dos tipos contém 69 PMIDs não localizados. Os pilotos e tipos sobrepostos não foram somados como estudos únicos.

As execuções novas possuem 39 tabelas, com três adicionais, PNG e seção Quarto. Os hashes lógicos das 36 tabelas anteriores foram preservados. O [guia da etapa](ETAPA_REFERENCIAS_PUBLICACOES.md), o [protocolo](../spec/reporting/PROTOCOLO_REFERENCIAS.md) e os [artefatos compartilháveis](resultados/referencias-0.14/README.md) registram métodos, denominadores, referências e limites.

Foram aprovados **117 testes**, incluindo oito novos cenários e PostgreSQL/Quarto reais. A matriz passa a 96 requisitos, incluindo MIG-017. Vínculos clínicos conferidos e discrepâncias continuam pendentes no eixo B. O piloto original permanece com 40 votos iniciais pendentes e zero resultados clínicos revisados.

O teste em navegador real confirmou o painel público, o aviso sobre RESULT, 71 PMIDs sem coincidência no piloto clínico, PNG com hash verificado e CSV/Quarto disponíveis. Não houve confirmação automática, erro JavaScript ou alteração clínica. A matriz registra 29 requisitos com evidência automatizada nesta execução.
