# DenguePharma — Relatório de Auditoria Formal da Proposta e Código

**Data da Auditoria:** 29 de Outubro de 2026  
**Documentos de Referência:**
1. `DenguePharma_Proposta_Formal.pdf` (Versão 1.0, 26/10/2026)
2. `DenguePharma Analytics – Estudo de Data Science sobre Evidências Farmacológicas.pdf` (Versão 2.0, 28/10/2026; `spec/requirements.json`)
3. Código-fonte do repositório: `backend/`, `frontend/`, `workers/`, `analytics/`, `docker-compose.yml`

---

## 1. Parecer Executivo

O projeto DenguePharma possui maturidade técnica e rigor científico elevados na camada de integridade de dados (triggers de imutabilidade PostgreSQL, Outbox/Inbox transacional com concorrência por lease, triagem duplo-cega com PRISMA-ScR e catálogo com salvaguardas metodológicas RC-01 a RC-07).

Entretanto, uma auditoria exaustiva confrontando a proposta formal original (v1.0) e a especificação de engenharia v2.0 com a base de código revelou discrepâncias e lacunas que demandam remediação:
- **Lacuna Conceitual Biológica**: Inexistência de modelagem de alvos moleculares virais (NS5, NS3, proteínas estruturais) no backend e na interface (Target Explorer).
- **Interoperabilidade Química**: Conector ChEMBL ausente para bioatividades e alvos moleculares (`REQ-IDN-002`).
- **Segurança Web & Robustez**: Ausência de configuração de CORS no Spring Security e manipulador de exceções da API restrito apenas a `ResponseStatusException`.
- **Integridade Científica na Curadoria**: Permissão de aprovação de campos críticos sem exigência do papel `ROLE_ADJUDICADOR`, e criação de trecho textual sintético em caso de correção manual sem citação literal.
- **Divergência de Contrato Frontend/Backend**: Envio de ações em inglês (`APPROVED`/`CORRECTED`/`REJECTED`) na interface de revisão versus expectativa em português no backend (`ACEITAR`/`CORRIGIR`/`REJEITAR`).
- **Completude da Infraestrutura**: Ausência dos serviços `backend` e `frontend` no `docker-compose.yml`.

---

## 2. Matriz Detalhada de Auditoria Requisito a Requisito

| ID / Seção | Requisito Formal | Módulo / Camada | Status | Arquivo(s) de Código | Achados & Lacunas |
|---|---|---|---|---|---|
| **OE1 / QP1** | Identificação e catalogação de fármacos candidatos para reposicionamento contra dengue | Backend / DB / Worker | **PARCIALMENTE_IMPLEMENTADO** | `backend/.../catalog/CatalogService.java`, `workers/.../corpus.py` | Substâncias catalogadas e normalizadas via PubChem CID; faltam bioatividades ChEMBL e associação a alvos virais. |
| **OE2 / QP2** | Avaliação da consistência metodológica entre desenhos de estudo | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../catalog/CatalogService.java:261`, `frontend/.../ComparatorPage.tsx:44` | Aplicação estrita da Regra RC-01: bloqueia extrapolação in silico/in vitro/animal para clínica humana. |
| **OE3 / QP3** | Caracterização de desfechos de segurança e eventos adversos | Backend / DB / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../db/migration/V4.sql`, `frontend/.../CatalogPage.tsx:142` | Aplicação estrita da Regra RC-03: `adverse_events_status` distingue ausência de relato de comprovação de segurança. |
| **OE4 / QP4** | Comparação da extração por IA vs. curadoria humana (H1, H2, H3) | Worker / DB / Backend | **PARCIALMENTE_IMPLEMENTADO** | `workers/.../extractor.py:213`, `backend/.../ops/ExperimentAndPilotController.java` | Métricas de precisão, revocação e F1 implementadas no worker; endpoints crossover `/api/experiment/*` desativados com HTTP 410 GONE no MVP v2. |
| **OE5 / QP5** | Observatório interativo aberto com evidências farmacológicas | Frontend / Backend / Analytics | **TOTALMENTE_IMPLEMENTADO** | `frontend/.../DashboardPage.tsx`, `backend/.../analysis/PublicAnalysisController.java` | Dashboard público com 4 abas, links profundos (PMID, NCT, PMC, DOI), figuras PNG e pacote de download. |
| **OE6 / H3** | Estudo de ablação offline da exigência de trecho documental e abstenção | Worker | **TOTALMENTE_IMPLEMENTADO** | `workers/.../extractor.py:288`, `workers/tests/test_extractor.py:102` | Função `run_ablation_h3` executa extração com e sem restrição, garantindo `published=False`. |
| **RF-01** | Protocolo versionado com registro e congelamento | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../protocol/ProtocolService.java`, `frontend/.../ProtocolsPage.tsx` | Ciclo RASCUNHO -> REGISTRADO -> CONGELADO respeitado; gatilhos impedem alteração de protocolo congelado. |
| **RF-02** | Ingestão em lote multiautomatizada com checkpoints | Backend / Conectores | **TOTALMENTE_IMPLEMENTADO** | `backend/.../ingest/PubMedConnector.java`, `ClinicalTrialsConnector.java`, `ImportService.java` | Particionamento por data, controle de cota, paginação com cursor persistente no banco. |
| **RF-03** | Vinculação e desvinculação reversível estudo-documento | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../substance/StudyLinkService.java`, `frontend/.../ScreeningPage.tsx` | Propostas de vínculo, aprovação/rejeição e reversão completa com trilha de auditoria. |
| **RF-04** | Triagem duplo-cega com dois estágios e fluxo PRISMA-ScR | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../screening/ScreeningService.java`, `frontend/.../ScreeningPage.tsx` | Decisões independentes e cegas, adjudicação de conflitos e totalização PRISMA em tempo real. |
| **RF-05** | Pipeline estruturado de extração com IA | Backend / Worker | **PARCIALMENTE_IMPLEMENTADO** | `workers/.../pipeline.py`, `workers/.../extractor.py` | Pipeline determinístico (`rules-2`), sanitização de prompt injection e validações numéricas; falta adaptador de chamadas a LLM ativo. |
| **RF-06** | Revisão humana lado a lado com localizadores de trecho | Backend / Frontend | **PARCIALMENTE_IMPLEMENTADO** | `backend/.../extraction/ExtractionService.java`, `frontend/.../ReviewPage.tsx` | Visualização lado a lado; backend criava trecho artificial em correção; divergência nos códigos de status dos botões. |
| **RF-07** | Catálogo público com divulgação obrigatória de limitações | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../catalog/CatalogService.java:37`, `frontend/.../CatalogPage.tsx` | Status regulatório, risco de viés e avisos obrigatórios (RC-01..RC-07) em todos os registros. |
| **RF-08** | Comparador contextualizado sem pontuação ou ranking automático | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../catalog/CatalogService.java:214`, `frontend/.../ComparatorPage.tsx` | Enforça Regra RC-04: veda ranking universal ou pontuação automática de eficácia. |
| **RF-09** | Exportação de relatórios reproduzíveis em múltiplos formatos | Backend / Frontend | **TOTALMENTE_IMPLEMENTADO** | `backend/.../ops/ReportAndOpsService.java:446`, `frontend/.../ReportsPage.tsx` | Exportação de snapshots em PDF, CSV e JSON com hash SHA-256 e critérios documentados. |
| **RF-10** | Fila de reavaliação diante de alterações de versões da fonte | Backend / DB | **TOTALMENTE_IMPLEMENTADO** | `backend/.../db/migration/V4.sql`, `backend/.../ops/ReportAndOpsService.java:254` | Criação de tarefas de reavaliação preservando decisões históricas inalteradas. |
| **RF-11** | Arquitetura durável Outbox/Inbox com concorrência por lease | Backend / DB / Worker | **TOTALMENTE_IMPLEMENTADO** | `backend/.../pipeline/PipelineService.java`, `workers/.../runtime.py` | Processamento atômico no PostgreSQL com renovação de lease (`LeaseKeeper`) e DLQ RabbitMQ. |
| **RF-12** | Trilha completa de auditoria com imutabilidade | Backend / DB | **TOTALMENTE_IMPLEMENTADO** | `backend/.../audit/AuditService.java`, `backend/.../db/migration/V1.sql:35` | Trigger `forbid_mutation()` no PostgreSQL impede edição e exclusão de registros de auditoria. |
| **RNF-01** | Segurança, controle de acesso e higiene de segredos | Backend / Segurança | **PARCIALMENTE_IMPLEMENTADO** | `backend/.../security/SecurityConfig.java`, `ApiExceptionHandler.java` | Autenticação JWT e hashing BCrypt funcionais; falta configuração de CORS e captura ampla de erros. |
| **RNF-02** | Desempenho e latência de consulta (<2s) | Backend / DB | **TOTALMENTE_IMPLEMENTADO** | `backend/.../db/migration/V1.sql` | Índices cobrindo chaves de estudo, documento, substância, hashes e paginação. |
| **RNF-03** | Reprodutibilidade científica | Backend / Worker / Notebooks | **TOTALMENTE_IMPLEMENTADO** | `workers/.../idempotency.py`, `notebooks/`, `spec/check.py` | Chaves determinísticas de extração baseadas em hash de 5 componentes; notebooks auditáveis. |
| **RNF-04** | Conformidade regulatória (LGPD e Acesso Aberto) | Backend / Storage | **TOTALMENTE_IMPLEMENTADO** | `backend/.../ingest/EuropePmcConnector.java`, `ReportAndOpsService.java:369` | Respeito estrito às licenças; artigos sem licença aberta têm somente metadados exportados. |
| **RNF-05** | Resiliência, backoff exponencial e recuperação de falha | Backend / Conectores | **TOTALMENTE_IMPLEMENTADO** | `backend/.../ingest/PubMedConnector.java`, `ClinicalTrialsConnector.java` | Respeito a cabeçalhos Retry-After, backoff com jitter e checkpoints em banco. |
| **RNF-06** | Garantia de qualidade e abstenção mandatória | Backend / Worker | **TOTALMENTE_IMPLEMENTADO** | `workers/.../extractor.py:73`, `ExtractionService.java:436` | Abstenção compulsória (`INCERTO`) quando falta trecho literal em texto fonte (Cenário T4). |
| **RNF-07** | Usabilidade e interface centrada no usuário | Frontend | **TOTALMENTE_IMPLEMENTADO** | `frontend/src/pages/*.tsx` | 8 telas especializadas, navegação por papéis, formulários validados. |
| **RNF-08** | Interoperabilidade com vocabulários e bases científicas | Backend / Worker | **PARCIALMENTE_IMPLEMENTADO** | `backend/.../substance/PubChemClient.java` | PubChem PUG REST implementado; **falta conector ChEMBL**. |
| **Alvos** | Explorador de Alvos Biológicos (Target Explorer) | Backend / Frontend | **FALTANDO** | `backend/`, `frontend/` | Ausência de tela de alvos e entidades dedicadas a proteínas virais DENV (NS5, NS3, E). |
| **Orçamento** | Controle e Monitoramento de Orçamento de IA | Backend / Worker / Frontend | **PARCIALMENTE_IMPLEMENTADO** | `workers/.../extractor.py:268`, `backend/.../ops/` | `BudgetGuard` funcional no worker; falta widget de visualização de orçamento na interface. |
| **Infra** | Orquestração Completa em Contêineres | Infraestrutura | **PARCIALMENTE_IMPLEMENTADO** | `docker-compose.yml` | Postgres, RabbitMQ, MinIO e Worker configurados; **faltam serviços de backend e frontend**. |

---

## 3. Catálogo Priorizado de Gaps e Plano de Implementação

### 3.1 Prioridade Alta (Execução Imediata) — [TODOS OS 10 ITENS CONCLUÍDOS E VALIDADOS]
1. [CONCLUÍDO] **Segurança Web (CORS)**: Configurar CORS no `SecurityConfig.java` permitindo origens locais (`localhost:5173`, `localhost:3000`, `localhost:8501`). Validado em `SecurityCorsTest.java`. (Commit `b587245`)
2. [CONCLUÍDO] **Tratamento Robusto de Exceções**: Expandir `ApiExceptionHandler.java` para capturar `MethodArgumentNotValidException`, `AccessDeniedException` e `DataIntegrityViolationException`, retornando RFC 7807 `ProblemDetail`. Validado em `ApiExceptionHandlerTest.java`. (Commit `b587245`)
3. [CONCLUÍDO] **Integridade de Curadoria**: Exigir `ROLE_ADJUDICADOR` para campos críticos em `ExtractionService.java` e vedar trecho falso em correções humanas. Validado em `ExtractionCatalogReportOpsIntegrationTest.java`.
4. [CONCLUÍDO] **Alinhamento de Contrato de Revisão**: Atualizar `ReviewPage.tsx` para enviar `ACEITAR`, `CORRIGIR`, `REJEITAR`. Validado em `curation-flows.test.tsx`.
5. [CONCLUÍDO] **Explorador de Alvos Biológicos**: Criar página e rota do Target Explorer no frontend detalhando NS5 (MTase/RdRp), NS3 (Protease/Helicase), Proteínas Estruturais (E, prM, Capsídeo) e alvos do hospedeiro, com inibidores e serótipos DENV 1-4. Criado `TargetExplorerPage.tsx` e validado em `target-explorer.test.tsx`. (Commit `41ea16e`)
6. [CONCLUÍDO] **Visualização 2D de Estruturas Químicas**: Integrar imagens 2D do PubChem PUG REST nos cards do Catálogo (`CatalogPage.tsx` e `CatalogService.java`). (Commit `41ea16e`)
7. [CONCLUÍDO] **Monitor de Orçamento na Interface**: Incluir widget de monitoramento de orçamento no `OperationalPanelPage.tsx`. (Commit `41ea16e`)
8. [CONCLUÍDO] **Conector ChEMBL em Workers**: Implementar `chembl.py` em `denguepharma_workers` com testes automatizados em pytest (`test_chembl.py`, 5 testes aprovados). (Commit `6e0a2a9`)
9. [CONCLUÍDO] **Orquestração Completa no Docker Compose**: Adicionar contêineres e Dockerfiles de `backend` e `frontend` no `docker-compose.yml`. (Commit `69c55f4`)
10. [CONCLUÍDO] **Testabilidade do Backend sem Docker Ativo**: Ajustar `AbstractIntegrationTest.java` com verificação de `DockerClientFactory.isDockerAvailable()` e fallback de `Assumptions.assumeTrue`, permitindo execução limpa de testes unitários mesmo sem daemon ativo. (Commit `69c55f4`)

### 3.2 Prioridade Secundária (Fases Futuras)
- [CONCLUÍDO] **Visualização em Grafo de Rede para Topologia de Evidências (Eixo E)**: Endpoint `GET /api/public/evidence-graph` no Spring Boot (`EvidenceGraphController.java`), interface interativa SVG com nós tipados (Fármacos, Alvos, Desfechos, Estudos) e gaveta de detalhes (`EvidenceGraphPage.tsx`). Validado em testes unitários backend e frontend. (Commit `f0be291`)
- [CONCLUÍDO] **Ativação de Chamadas a Modelos LLM**: Adaptador `llm_adapter.py` em `denguepharma_workers` com suporte a OpenAI/Gemini/Mock, medição de tokens e custos em USD, chave de 5 componentes (`idempotency_key`), abstenção mandatória (T4/T5/T10) e controle compulsório de teto de gastos via `BudgetGuard`. Validado em 9 testes unitários dedicados em `test_llm_adapter.py` (total de 52 testes no módulo workers aprovados).
- **Geração de Relatórios Multipáginas**: Diagramação avançada em PDFBox/Quarto com bioatividades ChEMBL e mecanismos de ação de alvos.
- **Curadoria Manual Completa do Corpus**: Conclusão da triagem duplo-cega humana dos 120 documentos.
