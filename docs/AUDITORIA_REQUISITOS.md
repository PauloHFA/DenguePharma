# Auditoria de requisitos do DenguePharma

Data: 27/10/2026. Referência: `DenguePharma_Proposta_Formal.pdf`, versão 1.0 de 26/10/2026, comparada ao código e aos testes do repositório.

Atualização: este documento preserva os achados iniciais. As correções realizadas posteriormente estão registradas em [Implementação — etapa 1](IMPLEMENTACAO_ETAPA_1.md).

A integração operacional posterior está documentada em [Implementação — etapa 2](IMPLEMENTACAO_ETAPA_2.md).

O escopo vigente passou a ser o dos [Requisitos v2](REQUISITOS_V2.md), implementado na [etapa 3](IMPLEMENTACAO_ETAPA_3.md). Os achados abaixo continuam como registro histórico da proposta v1; avaliação de IA não é requisito obrigatório do MVP atual.

## Parecer

**A aplicação ainda não implementa integralmente a proposta.** Existe uma base funcional relevante, com autenticação, protocolos versionados, importação, decisões de triagem, normalização química, validações de extração, catálogo e snapshots. Entretanto, o fluxo completo de extração assistida não está conectado, há erros de integração entre interface e API e existem violações das garantias de publicação e proveniência. O README superestima a conclusão do produto e da avaliação científica.

Este levantamento é uma inspeção estática acompanhada da execução das suítes existentes. Não foi realizada homologação visual em navegador, teste de carga, restauração de backup, consulta real às fontes científicas nem experimento com revisores. “Não localizado” significa que não foi encontrada implementação ou evidência no repositório; não exclui infraestrutura externa.

## Validação executada

| Verificação | Resultado |
| --- | --- |
| `mvn -B -q -f backend/pom.xml test` | 35 testes passaram; zero falhas, erros ou testes ignorados nos relatórios Surefire. PostgreSQL 16 via Testcontainers. |
| `workers/.venv/Scripts/python.exe -m pytest workers -q` | 9 testes passaram. |
| `npm test --prefix frontend -- --run` | 7 testes passaram. |
| `npm run build --prefix frontend` | TypeScript e Vite concluíram com sucesso. |

Esses resultados confirmam os cenários programados, mas não demonstram atendimento integral. O frontend usa respostas simuladas e testa principalmente acesso, estados vazios e renderização; não verifica os contratos reais dos botões de revisão, comparador e downloads. Os testes do backend usam dados preparados e agrupam vários critérios em um único teste.

## Matriz dos requisitos funcionais

“Parcial” indica que há implementação aproveitável, mas falta parte do aceite ou há defeito no fluxo.

| Requisito | Estado | Evidência e pendências |
| --- | --- | --- |
| RF-01 — Protocolo versionado | Implementado na API; interface parcial | `ProtocolService` cria, valida, registra, congela e deriva versões; `search_run` referencia a versão. A tela não permite editar rascunho/estratégia de uma nova versão e só cria protocolos para PubMed/ClinicalTrials. |
| RF-02 — Importação com checkpoint | Parcial | `ImportService`, `PubMedConnector` e `ClinicalTrialsConnector` implementam coleta, hash, paginação e retomada, com testes. Falta atualizar automaticamente nas rotinas semanal/mensal propostas. Identificadores usam namespaces diferentes entre conectores, prejudicando deduplicação entre fontes. |
| RF-03 — Substâncias e vínculos reversíveis | Parcial | PubChem, aliases, componentes de combinações e aprovação/reversão de fusões estão implementados e testados. Não foi localizada deduplicação aproximada por título/autoria/ano. A UI cadastra apenas monoterapia de pequena molécula. |
| RF-04 — Triagem independente e adjudicação | Parcial | API preserva decisões, exige dois votos para consolidar e calcula contagens PRISMA. A UI não exibe resumo/texto, fixa contexto e finalidade e não oferece inclusão sem resultados nem justificativa real de exclusão. |
| RF-05 — Extração com suporte e ausência | Parcial, com bloqueadores | Há validação de candidatos recebidos via API e funções Python. Não há execução de modelo, parser documental integrado ou consumidor que processe os jobs. Correções podem criar evidência artificial e campos críticos não têm aprovação especial obrigatória. |
| RF-06 — Revisão lado a lado auditada | Parcial, fluxo da UI quebrado | API registra decisões e auditoria. A UI envia enums incompatíveis e usa nomes de campos de evidência diferentes dos retornados pela API. |
| RF-07 — Catálogo e filtros | Parcial | Filtros, limitações, avisos científicos e exclusão de retratados existem. A seleção admite estudos incluídos na triagem sem campos publicados, e também estudos excluídos que tenham qualquer campo publicado. Falta mostrar fontes/trechos e acesso limitado na ficha da UI. |
| RF-08 — Comparação contextualizada | Parcial | API detecta diferenças de contexto, finalidade, categoria clínica/virológica, janela e desenho; não cria ranking. A UI perde as mensagens por incompatibilidade de contrato. A comparação não valida população, momento da intervenção, sorotipo, comparador ou identidade do desfecho. |
| RF-09 — PDF/CSV/JSON auditáveis | Parcial | Snapshots imutáveis e exportações existem. Downloads da UI não enviam Bearer token; PDF tem uma página fixa e trunca texto; CSV não inclui filtros e o status de revisão é fixo. |
| RF-10 — Mudanças e reavaliação | Parcial | Nova versão cria tarefa; retratação manual retira estudo do catálogo/comparador e mantém snapshots. Falta rotina periódica e detecção específica de errata/retratação das fontes; UI não evidencia atualização pendente no catálogo. |
| RF-11 — Monitorar e retentar | Parcial | Jobs, leases, quarentena, retry e painel existem. Relay cria jobs diretamente no banco; falta publicação RabbitMQ com confirmação, consumidor, execução automática e vínculo entre gravação da extração e lease vigente. |
| RF-12 — Administração e reprodução | Parcial | Há criação/listagem de usuários e pacote com protocolos, manifestos e campos publicados. Faltam edição/revogação de acesso, administração de dicionários/regras e interface administrativa. Pacote não reúne manual, schemas, configurações/dependências e todos os dados necessários à reprodução. |

## Problemas prioritários

### P0 — Proveniência, publicação e licenças

1. **Correção humana permite publicar sem trecho documental verdadeiro.** Em `backend/src/main/java/org/denguepharma/extraction/ExtractionService.java:276`, quando falta span, `CORRIGIR` cria um com texto `Corrigido pelo revisor: <motivo>` e localizador `curadoria`. Isso satisfaz a chave estrangeira sem sustentar o valor no documento. Quando já há span, o valor corrigido também não é revalidado contra ele. Aceite: exigir seleção/verificação de trecho da versão documental antes de publicar valor presente.

2. **Aprovação de campos críticos não exige adjudicador.** `CRITICAL_FIELDS` está declarado em `ExtractionService.java:34`, mas não é usado. Um REVISOR pode enviar `adjudication=false`, aceitar e publicar `result`, `population` ou outros campos críticos. Aceite: aplicar a política no backend, independentemente do payload/UI.

3. **Licença ausente é convertida em CC-BY.** `backend/src/main/java/org/denguepharma/ingest/EuropePmcConnector.java:87` usa CC-BY como fallback quando `isOpenAccess=Y`. O pacote considera CC-BY redistribuível. A condição de acesso não fornece uma licença específica. Aceite: manter licença desconhecida/restrita até verificação explícita; cobrir esse caso em T9.

4. **O piloto é sintético e já nasce publicado como aprovado.** `backend/src/main/java/org/denguepharma/ops/ExperimentAndPilotService.java:307` usa um array fixo, gera títulos/textos e insere campos `APROVADO/published=true` sem decisões individuais de revisão. Todos os estudos recebem amostra 120 e os mesmos países (`:392`), mesmo os pré-clínicos. Não é uma recuperação de 20 registros com corpus adjudicado. Aceite: identificar e isolar dados demonstrativos; construir piloto real por importação e revisão. Esta auditoria não verificou externamente os identificadores nem os resultados clínicos desse array.

5. **O catálogo não garante que os valores exibidos foram revisados.** `backend/src/main/java/org/denguepharma/catalog/CatalogService.java:56` usa inclusão na triagem **OU** existência de qualquer campo publicado. A primeira condição não exige revisão da extração, e a segunda pode recolocar um estudo excluído. PDF/CSV afirmam aprovação humana de forma fixa. Aceite: distinguir metadados, inclusão, rascunho e evidência aprovada por campo e usar o status verdadeiro nas exportações.

### P1 — Fluxos essenciais e integração

6. **Botões de revisão não funcionam com a API atual.** `frontend/src/pages/ReviewPage.tsx:40` envia `APPROVED/CORRECTED/REJECTED`; o backend aceita `ACEITAR/CORRIGIR/REJEITAR`. Filtros e estados de ausência também usam enums ingleses incompatíveis. O formulário ainda fornece motivo genérico se o revisor não escrever justificativa. Aceite: contrato compartilhado e teste de aprovação, correção e rejeição usando respostas reais da API.

7. **Fonte de evidência não aparece na revisão.** A UI usa `raw_value`, `quote`, `char_start` e `char_end`, enquanto `ExtractionService.java:200` retorna `original_value`, `evidence_text`, `section`, `page` e `locator`. A interface mostra “Sem trecho” mesmo para campos com evidência. A API também aceita qualquer localizador não vazio, sem validar posição. Aceite: exibir e validar o mesmo sistema de localização utilizado no documento.

8. **Downloads PDF/CSV perdem autenticação.** `frontend/src/pages/ReportsPage.tsx:103` usa links diretos. A aplicação usa Bearer token em `api.ts`, e o backend é stateless e exige autenticação. Navegação por link não acrescenta esse header. Aceite: baixar com requisição autenticada e salvar o Blob.

9. **Triagem pode reclassificar evidência incorretamente.** `frontend/src/pages/ScreeningPage.tsx` envia sempre `context: HUMANO` e `purpose: TRATAMENTO`, substituindo a classificação existente. Não renderiza `abstract_text`, não oferece texto integral, usa exclusão genérica e omite `withoutPostedResults`. Aceite: disponibilizar documento e escolhas reais, preservando classificações confirmadas.

10. **Pipeline assíncrono e IA não estão conectados.** `workers/src/denguepharma_workers` contém apenas funções de extração/validação, métricas e hash de idempotência. Não há consumidor RabbitMQ, cliente de modelo, recuperação semântica, leitura de PDF/tabelas/OCR ou persistência executada pelo worker. `ReportAndOpsService.java:395` marca eventos como publicados após criar jobs SQL; não envia ao broker. `ImportService.java:243` monta URI S3, mas não grava o objeto. Aceite: demonstrar importação → objeto persistido → evento confirmado → worker → rascunho → revisão → catálogo, inclusive após interrupção.

11. **Comparador oculta mensagens e pode declarar compatibilidade indevida.** `frontend/src/pages/ComparatorPage.tsx:119` lê `detail`; API retorna `message` e `code`. `CatalogService.compare` consulta qualquer estudo por ID, restringindo apenas retratados, sem exigir evidência pública ou excluir absorvidos. `detectIncompatibilities` ignora dimensões exigidas pela RC-04 e trata ausência de informações como se não houvesse divergência. Aceite: comparação limitada ao conjunto permitido, mensagens visíveis e compatibilidade indeterminada quando faltam dados essenciais.

12. **PDF corta conteúdo e CSV perde filtros.** `ReportAndOpsService.java:452` gera uma única página, sem quebra/paginação, e corta linhas acima de 105 caracteres. Relatórios com muitos estudos saem da área visível, e hashes/citações podem ser truncados. `exportCsv` não exporta os filtros do snapshot. Aceite: renderizar documento completo com paginação, fontes, filtros e status reais; verificar o PDF renderizado com múltiplos estudos.

13. **Identidade entre fontes não é uniforme.** PubMed usa fonte `DOI` para DOI e `PMC` para PMCID; Europe PMC usa `CROSSREF` para DOI e seu próprio namespace para PMCID. Como a unicidade/consulta inclui fonte e tipo, o mesmo DOI/PMCID pode não gerar vínculo entre conectores. Aceite: normalizar namespaces e testar o mesmo documento recuperado em fontes diferentes.

14. **Lease não protege a persistência da extração.** A conclusão do job verifica token, mas `submitExtraction` não recebe job/token. Um executor atrasado poderia inserir extração independentemente dessa verificação. `failJob` também não exige token vigente. Aceite: tornar atômicos a validação do lease e o commit do resultado, com teste de dois executores e lease vencido.

### P1 — Avaliação experimental ainda não atende à proposta

15. **F1 e fidelidade são inferidos do status de revisão.** `ExperimentAndPilotService.java:172` calcula acertos a partir de `APROVADO/REJEITADO`, sem comparar previsão original com referência independente adjudicada. Um erro corrigido e aprovado vira acerto; não há medida cega de suporte semântico. Sem dados, várias métricas retornam 1,0. O cálculo Python com pares previsão/referência existe, mas não está integrado a esse endpoint. Aceite: referência versionada, preservação da previsão original, métricas por campo/estrato e estado “sem dados”.

16. **Partição e alocação não são randomizadas nem congeladas de fato.** `ExperimentAndPilotService.java:70` distribui famílias por índice módulo 4; o estrato é apenas armazenado, não usado para estratificar. `:81` atualiza partições existentes, inclusive `TEST_FROZEN`. A alocação alterna revisores pela paridade (`:125`) e não restringe o experimento ao conjunto de teste. Aceite: desenho reproduzível com semente, estratos e congelamento efetivo, sem usar piloto/desenvolvimento como teste independente.

17. **Falta fluxo de coleta e análise experimental.** Sessões recebem segundos informados por API; não há cronômetro integrado na revisão nem formulários independentes para referência manual. Não foram encontrados intervalos de confiança, bootstrap por família, análise por condição/campo/estrato ou relatório de custos/erros. A ablação H3 é uma função Python, sem execução comparativa integrada documentada.

## Regras científicas

| Regra | Avaliação |
| --- | --- |
| RC-01 | Parcial: contextos modelados e avisos existentes; triagem sobrescreve classificação e comparabilidade é incompleta. |
| RC-02 | Parcial: constraint exige atributos regulatórios não nulos; falta fluxo de verificação documental e exposição da fonte regulatória. O README diz que o status é forçado para candidato, mas o banco rejeita a alteração inválida. |
| RC-03 | Parcial: avisos de segurança/desfecho substituto existem; faltam dados estruturados e verificação completa por braço/desfecho. |
| RC-04 | Parcial: não há ranking, mas a avaliação de comparabilidade e sua apresentação têm as falhas acima. |
| RC-05 | Parcial: constraint restringe RoB 2 a ensaio randomizado; risco é resumido por estudo, sem avaliação por resultado/revisores. |
| RC-06 | Parcial: retratação manual e histórico funcionam; falta detectar eventos das fontes e apresentar divergências entre documentos. |
| RC-07 | Restrição de escopo respeitada no código inspecionado: não foi localizado ranking, meta-análise ou GRADE automático. Mapa de lacunas e síntese narrativa não foram localizados como entregas completas. |

## Requisitos não funcionais

| Requisito | Estado | Pendência |
| --- | --- | --- |
| RNF-01 — Autenticação, perfis e auditoria | Parcial | JWT, BCrypt, perfis e trilha existem; autorização de campos críticos e filtragem do comparador precisam correção. |
| RNF-02 — TLS, segredos, backup e restauração | Não comprovado integralmente | Segredos por ambiente existem; não foram localizados TLS/deploy, procedimento de backup ou teste de recuperação conjunta banco/objetos. |
| RNF-03 — Licença e envio externo | Parcial | Pacote filtra licenças, mas conector presume CC-BY e não há política implementada de autorização de envio a modelo externo. |
| RNF-04 — Reprodutibilidade | Parcial | Migrations, hashes e snapshots imutáveis existem; objetos não são gravados e faltam configurações/dependências no pacote. Há `frontend/package-lock.json` versionado; não foi localizado lockfile Python. |
| RNF-05 — Quotas, cache e backoff | Parcial | Throttle, jitter e Retry-After em segundos existem; não foi localizado cache; Retry-After em data não é interpretado. |
| RNF-06 — p95 ≤ 2 s / 10 mil registros / 10 usuários | Não verificado | Não há evidência de teste de carga. Catálogo usa consultas adicionais por estudo e não oferece paginação. |
| RNF-07 — Acessibilidade e legibilidade | Parcial | Há HTML semântico, labels e alertas; vários controles têm apenas placeholder, sem nome acessível explícito. Não há evidência de validação completa por teclado/leitor de tela; PDF tem corte de conteúdo. |
| RNF-08 — Recuperação sem publicação parcial | Parcial | Transações, checkpoint e recuperação de importação existem; faltam worker real, cenários de falha ponta a ponta e integração de lease à gravação. |

O modelo relacional contém tabelas de braços, intervenções, desfechos e resultados, mas não foi localizado fluxo completo de API/UI para preenchê-las. A síntese atual usa principalmente campos resumidos em `study`, insuficientes para representar múltiplos braços, comparações, tempos e resultados com proveniência individual conforme a proposta.

## Entregas e cobertura dos cenários de aceite

| Entrega | Situação |
| --- | --- |
| E1 — Protocolo | Estrutura de software disponível; conteúdo metodológico completo e aprovado não comprovado. |
| E2 — Corpus e referência | Manifestos e vínculos disponíveis; semente sintética não comprova corpus recuperado e adjudicado. |
| E3 — MVP integrado | Parcial, bloqueado por revisão, downloads e ausência de pipeline real. |
| E4 — Qualidade e operação | Suítes passam; falha de worker real, broker e restauração não demonstradas. |
| E5 — Experimento | Estrutura parcial; métricas e desenho precisam correção antes da coleta. |
| E6 — Documentação científica | README disponível; manual de anotação, dicionário congelado, schemas distribuíveis e relatório científico não localizados. |

T1–T3 possuem testes de importação, mudança de versão e vínculos reversíveis. T4/T5/T10 possuem testes de funções e API, mas não de um modelo/documento real integrado; T5 não comprova conversões de unidades ou tabelas. T6 cobre retirada por retratação manual. T7 cobre idempotência e endpoints de jobs, sem reentrega real de broker/worker. T8 procura strings no PDF e não verifica paginação/legibilidade. T9 cobre licenças preparadas no teste, sem o fallback indevido do conector. Portanto, a existência de testes nomeados T1–T10 não equivale ao aceite completo desses cenários em operação.

## Ordem recomendada de conclusão

1. Corrigir proveniência, permissão de publicação crítica, licença desconhecida e isolamento dos dados demonstrativos.
2. Alinhar contratos da revisão/comparador; disponibilizar fontes na triagem; corrigir downloads autenticados e exportações completas.
3. Conectar armazenamento de objetos, broker, worker e extração, incluindo falhas, retentativas e concorrência.
4. Completar formulários/dicionários e o modelo de resultados; uniformizar identidade entre fontes e atualizações periódicas.
5. Implementar referência adjudicada, partição congelada, randomização, cronometragem e métricas válidas.
6. Executar homologação ponta a ponta, teste de carga, acessibilidade e restauração, produzindo evidências para o aceite.

Nenhuma alteração funcional foi realizada nesta auditoria. Foram adicionados este relatório e a exclusão da pasta temporária `.firecrawl/` no `.gitignore`.

## Registro final das alterações posteriores à auditoria

Esta auditoria permanece como retrato histórico do código inspecionado inicialmente. Suas tabelas não representam o estado final após as implementações.

O **[registro consolidado das etapas 1 a 4](ALTERACOES_CONSOLIDADAS.md)** reúne as correções, o pipeline real, as mudanças de escopo, os módulos de ciência de dados, as APIs, os dashboards sem login e a validação. Os [Requisitos v3](REQUISITOS_V3.md) são a referência vigente; a [etapa 4](IMPLEMENTACAO_ETAPA_4.md) contém os procedimentos de execução.

O [registro do piloto real](TESTE_CIENCIA_DADOS.md) documenta 50 registros coletados, os artefatos produzidos e a revisão científica ainda pendente. A validação operacional não equivale à homologação integral de todos os requisitos históricos desta auditoria.

## Migração Analytics — 28/10/2026

A referência vigente passa a ser a [especificação do novo PDF Analytics](../spec/README.md). A [primeira entrega da migração Python](MIGRACAO_ANALYTICS.md) é paralela, somente de leitura, e preserva o legado. Os problemas experimentais identificados nesta auditoria não foram reativados; o novo eixo D exige implementação e protocolo próprios.
