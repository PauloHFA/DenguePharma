# DenguePharma

**Versão 0.27.0:** fluxo de seleção e triagem PRISMA-ScR interativo (REQ-SEL-004), com verificação de igualdade contábil estrita (`identificados = duplicados_removidos + registros_triados` e `registros_triados = incluidos + excluidos`), categorização padronizada de exclusões por motivo pré-definido, API REST no backend (`/api/public/prisma-flow`) e visualizador interativo em blocos no Dashboard do frontend (`PrismaFlowView`), totalizando **37 requisitos formais verificados no SDD**.

**Versão 0.26.0:** modelo de meta-regressão por efeitos aleatórios (DerSimonian-Laird ponderado), salvaguardas metodológicas de compatibilidade de contextos (bloqueio estrito de fusão in vitro e humano, ou profilaxia e tratamento - REQ-ANA-002) e proibição de ranqueamento de eficácia / certeza GRADE automática (REQ-ANA-009 / RC-07), com ciclo reprodutível de ingestão multi-fonte (OpenDengue, SINAN/DATASUS e bioatividades ChEMBL), totalizando **36 requisitos formais verificados no SDD**.

**Versão 0.25.0:** benchmark empírico de extração por IA frente à referência adjudicada (Eixo D - REQ-ANA-006 e REQ-ANA-007), com cálculo de Precisão, Recall e F1 por campo/estrato, regras congeladas para sinônimos/números e intervalos de confiança de 95% via Cluster Bootstrap por família de estudo (1000 réplicas), totalizando 34 requisitos SDD formalmente verificados, com API REST no backend (`/api/public/extraction-benchmark`) e visualizador interativo integrado no Dashboard do frontend (`ExtractionBenchmarkView`).

**Versão 0.24.0:** análise de sobrevivência Kaplan–Meier de relato (Eixo B), monitoramento de retratações científicas com expurgo automático da síntese (REQ-ANA-010) e ingestão de microdados OpenDengue/SINAN (REQ-ING-008), com visualização interativa em degraus no frontend e 32 requisitos SDD verificados.

**Versão 0.23.0:** [expansão multidisciplinar e salvaguardas avançadas](docs/ETAPA_MELHORIAS_ESTRUTURAIS.md), integrando CI/CD multisserviço no GitHub Actions, interoperabilidade ChEMBL no backend, análise de Carga Global de Doença (Eixo C - GBD/DATASUS) e identificação de Desertos de Pesquisa no frontend, visualizador molecular 2D/3D interativo do PubChem e parecer consultivo por IA (Shadow Screening) para apoio à adjudicação humana com salvaguardas RC-01 a RC-07.

**Versão 0.22.0:** [concordância inter-avaliadores na triagem duplo-cega](docs/ETAPA_CONCORDANCIA_REVISAO.md), com cálculo determinístico de concordância observada ($P_o$), Kappa de Cohen ($\kappa$) e AC1 de Gwet imune ao paradoxo de prevalência, matriz de contingência 3x3 e visualização protegida na curadoria.

**Versão 0.21.0:** [inspeção de alterações em resultados clínicos](docs/ETAPA_ALTERACOES_RESULTADOS.md), com comparação estrutural entre versões de rascunhos e correções, preservação de ausência/null/zero e hashes de integridade sem expor trechos literais privados. As novas etapas seguem a [política de commits](docs/VERSIONAMENTO.md).

**Versão 0.20.0:** [mapa de cobertura da extração por desfecho](docs/ETAPA_COBERTURA_EXTRACAO.md), com resultados revisados, pendências, conflitos e exportação privada rastreável. As novas etapas seguem a [política de commits](docs/VERSIONAMENTO.md).

**Versão 0.19.0:** [integridade documental](docs/ETAPA_INTEGRIDADE_DOCUMENTAL.md), com alerta humano, prévia de impacto e suspensão da evidência corrente. Regularizar um documento exige nova revisão; publicações históricas permanecem imutáveis.

**Versão 0.18.0:** [curadoria com atualização independente](docs/ETAPA_ATUALIZACAO_CURADORIA.md). No teste local de troca de filtro, as requisições públicas caíram de 29 para zero, mantendo as consultas privadas atualizadas.

**Versão 0.17.0:** [fila pessoal de revisão](docs/ETAPA_FILA_PESSOAL.md), com tarefas da própria conta, revisões atuais e reavaliações. No piloto clínico, são 20 tarefas iniciais por revisor no estado atual e 40 avaliações independentes globais faltantes.

**Versão 0.16.0:** [resumo auditável da seleção](docs/ETAPA_FLUXO_SELECAO.md), motivos humanos de exclusão e exportação privada. Os totais não reconstruídos permanecem ausentes; o piloto não é apresentado como revisão concluída.

**Versão 0.15.0:** [dossiê documental na triagem](docs/ETAPA_DOSSIE_TRIAGEM.md), com documentos, versões e fontes do estudo selecionado na curadoria protegida. A revisão e as conclusões clínicas continuam humanas.

**Pesquisa reproduzível:** [relatórios HTML e notebooks executados](docs/resultados/pesquisa-reprodutivel/README.md), separados por piloto, com [instruções de reprodução e limites](docs/ETAPA_NOTEBOOK_PESQUISA.md). As execuções ainda não contêm resultados clínicos revisados.

**Etapa 0.14.0:** [cobertura bibliográfica por PMID](docs/ETAPA_REFERENCIAS_PUBLICACOES.md), com referências por código da fonte, candidatos e PMIDs a conferir. Não coleta artigos nem confirma vínculos clínicos automaticamente.

**Etapa 0.13.0:** [auditoria de relato dos registros](docs/ETAPA_AUDITORIA_RELATO.md), com disponibilidade de resultados, precisão das datas, intervalos de calendário e rastreabilidade. É a introdução descritiva do eixo B, sem Kaplan–Meier ou análise da sobrevida dos pacientes.

**Etapa 0.12.0:** [patrocinadores declarados nos registros](docs/ETAPA_PATROCINADORES.md), com dados reais, proveniência, ausências/conflitos, CSVs, PNG e relatório Quarto. O panorama descreve os registros coletados; não avalia eficácia ou risco de viés.

**Etapa 0.11.0:** [comparação de execuções publicadas](docs/ETAPA_COMPARACAO_EXECUCOES.md), com compatibilidade de escopo, mudanças documentais, denominadores e exportações reproduzíveis. As comparações reais confirmaram preservação dos pilotos entre as versões 0.6 e 0.8.

**Etapa 0.10.0:** [identidade dos estudos](docs/ETAPA_IDENTIDADE_ESTUDOS.md), com conferência de vínculos, prévia do impacto e correção auditável. Ambiguidades não escolhem automaticamente um estudo, e desfazer um vínculo exige nova revisão das bases afetadas.

**Etapa 0.9.0:** [backup e restauração da curadoria](docs/ETAPA_BACKUP_CURADORIA.md), com cópia consistente, hashes, validação de fontes/auditoria e recuperação isolada dos dois pilotos. A revisão científica permanece pendente.

**Etapa 0.8.0:** [prévia da revisão independente](docs/ETAPA_PREVIA_REVISAO.md), com conferência do lote sem gravar votos, confirmação explícita e recusa de prévias desatualizadas. A revisão científica do piloto continua pendente.

**Etapa 0.7.0:** [coleta completa controlada](docs/ETAPA_COLETA_COMPLETA.md), com estratégia congelada, retomada conservadora e exportação pelo PostgreSQL somente de leitura. A execução real depende da seleção e calibração humanas do piloto.

Estudo de ciência de dados sobre evidências farmacológicas relacionadas à dengue, em migração gradual para Python.

**Etapa 0.6.0:** [calibração e síntese clínica por campos](docs/ETAPA_CALIBRACAO_SINTESE.md), com decisões vinculadas à seleção vigente, justificativas humanas e bloqueios na API. O piloto real continua pendente de revisão; nenhuma conclusão foi gerada automaticamente.

**Etapa 0.5.0:** [extração clínica e revisão por campos](docs/ETAPA_EXTRACAO_CLINICA.md), com prévia sem gravação, referências às fontes e decisões independentes. O piloto real ainda depende da triagem humana; não foram gerados resultados clínicos automaticamente.

**Etapa 0.4.0:** [apoio à revisão independente](docs/ETAPA_REVISAO_INDEPENDENTE.md), com pacote privado do piloto, importação de triagem validada em lote, painel de pendências e localizadores literais. O material está preparado para dois revisores; não houve aprovação científica automática.

**Continuidade 0.3.0:** o dashboard tem a aba **Resultados gerais**, diagnóstico de calibração e triagem por campos. Os [resultados descritivos obtidos](docs/RESULTADOS_GERAIS_PESQUISA.md) e os [arquivos exportados](docs/resultados/README.md) estão documentados. O piloto mantém zero resultados clínicos revisados; sinais de metadados não aprovam nem excluem estudos automaticamente.

**Atualização de 28/10/2026:** a prioridade é a [síntese clínica de benefício, alívio de sintomas e segurança](docs/IMPLEMENTACAO_SINTESE_CLINICA.md), regida pela [emenda do protocolo](spec/clinical/EMENDA_CLINICA.md). Foram implementados seleção/revisão protegidas, resultados por estudo, ICs, tabelas, fichas e gráficos. O novo piloto de 20 registros ainda aguarda revisão humana; não há conclusão de eficácia publicada. Carga de doença e avaliação de IA ficam para depois.

O escopo vigente é a **[especificação Analytics](spec/README.md)**, derivada do novo PDF e implementada por etapas. A primeira entrega Python usa FastAPI, Streamlit, Quarto e Parquet/DuckDB em paralelo a Java/React. Panorama coletado e evidências revisadas permanecem separados. O experimento de IA volta ao objetivo completo do projeto, mas ainda não foi implementado e não é necessário para executar esta fundação.

Para executar a nova aplicação, consulte **[analytics/README.md](analytics/README.md)**. Dashboard: `http://127.0.0.1:8501`; API: `http://127.0.0.1:18081`. Os coletores duráveis e a autenticação continuam no legado; a nova curadoria clínica usa área privada própria. Os requisitos v2/v3 abaixo são históricos.

Uso exclusivo para pesquisa e consulta de evidências. A plataforma não realiza diagnóstico, prescrição, cálculo de dose, ranking de medicamentos ou avaliação automática de eficácia.

## Funcionalidades

- Protocolos versionados, importação com checkpoint, identidade documental e normalização de substâncias.
- Triagem independente, revisão humana com suporte documental e controle de publicação de campos críticos.
- Catálogo, comparação contextualizada e relatórios PDF/CSV/JSON com snapshots.
- Pipeline durável com PostgreSQL, RabbitMQ, MinIO e workers Python.
- Análises descritivas de dados revisados: distribuições, mapas de lacunas, completude e rastreabilidade estrutural.
- Tabelas e gráficos na aplicação, execução por comando e pacote ZIP com CSV/JSON/HTML/PNG, versões e hashes.

Os mapas revisados contam cada estudo uma vez, preservam conflitos e valores ausentes e separam os contextos experimentais. O panorama distingue documentos, registros de ensaios e estudos. Campos científicos ainda não revisados não são preenchidos a partir de resumos não aprovados. Um resultado vazio informa “sem dados”.

## Estrutura

| Diretório | Conteúdo |
| --- | --- |
| `backend/` | Java 21, Spring Boot, API REST, autorização, curadoria, snapshots e Flyway |
| `frontend/` | React/TypeScript, triagem, revisão, catálogo, relatórios e análises |
| `workers/` | Python, regras documentais, pandas/Matplotlib, execução de jobs e CLI |
| `infra/minio/` | Imagem MinIO compilada de fonte oficial fixada |
| `docs/` | Requisitos vigentes, auditoria histórica e registros de implementação |

## Executar a aplicação legada localmente

Pré-requisitos: JDK 21, Maven, Node/npm, Python 3.12 e Docker Desktop com engine Linux.

Crie `.env` a partir de `.env.example` e configure senhas de banco, RabbitMQ e MinIO, `JWT_SECRET` com pelo menos 32 caracteres e credenciais do primeiro administrador. Não versione esse arquivo.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\scripts\configure-pipeline.ps1
docker compose up -d --build postgres rabbitmq minio
```

O script preserva um `PIPELINE_TOKEN` já configurado e gera uma credencial interna quando ela estiver vazia. Não exibe o segredo. A primeira compilação do MinIO pode levar alguns minutos.

Carregue o ambiente e inicie o backend; Flyway aplica as migrations, incluindo V9:

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim()) } }
mvn -f backend/pom.xml spring-boot:run
```

Em outros terminais:

```powershell
docker compose --profile pipeline up -d --build worker
npm install --prefix frontend
npm run dev --prefix frontend
```

Interface: `http://localhost:5173`. API: `http://localhost:8080`. O PostgreSQL local usa a porta 5434 no exemplo. O worker em Docker acessa o backend pelo host; `PIPELINE_BACKEND_URL` permite mudar esse endereço.

## Ciência de dados e dashboards

A página inicial abre sem login. Resultados aparecem após a publicação explícita de uma execução; a curadoria permanece protegida. Séries temporais, perfil dos ensaios, países, intervenções, completude e vínculos são calculados por scripts reproduzíveis.

Consulte **[Etapa 4: coleta piloto, análise, revisão e publicação](docs/IMPLEMENTACAO_ETAPA_4.md)** para executar os comandos. O piloto tem até 25 registros por fonte e gera uma planilha pendente de revisão; a coleta completa por CLI exige essa validação. O notebook de exploração está em `notebooks/01_exploracao_corpus.ipynb`.

## Análises de evidências revisadas (compatibilidade v2)

1. Registre um protocolo, importe fontes e realize a triagem.
2. Revise e publique campos com suporte documental. A extração por regras cobre apenas alguns padrões; demais campos podem permanecer pendentes.
3. Em **Relatórios → Análises descritivas**, selecione os filtros e solicite a execução com perfil PESQUISADOR/ADMINISTRADOR.
4. Consulte o estado, tabelas, gráficos e pacote ZIP. LEITOR pode consultar e baixar análises existentes.

O snapshot congela os dados aprovados na solicitação. Atualizações e retratações posteriores afetam novas análises, preservando as antigas. Substância, desenho, fase e categoria de desfecho só aparecem quando aprovados campo a campo. Dados demonstrativos ficam fora das análises científicas.

### Reproduzir por comando

Baixe `dataset.json` de uma análise e execute:

```powershell
workers\.venv\Scripts\python.exe -m pip install -r workers/requirements.lock
workers\.venv\Scripts\python.exe -m pip install --no-deps -e workers
workers\.venv\Scripts\python.exe -m denguepharma_workers.analysis --input dataset.json --output resultados
```

Se necessário, crie antes o ambiente com `python -m venv workers/.venv`. Os scripts não precisam de credenciais para analisar esse arquivo local.

O pacote contém dados estruturados sem texto integral, tabelas CSV, resumo JSON, relatório HTML, gráficos PNG e manifesto de reprodução. Extraia o ZIP para abrir o HTML com suas imagens. A análise não transforma falta de registros em prova de ausência de evidência na literatura.

## Testes

```powershell
workers\.venv\Scripts\python.exe -m pytest workers -q
npm test --prefix frontend -- --run
npm run build --prefix frontend
mvn -B -f backend/pom.xml test
```

Para incluir o teste completo com PostgreSQL, RabbitMQ, MinIO, servidor HTTP e processo Python reais:

```powershell
docker compose build minio
$env:PIPELINE_INTEGRATION = 'true'
$env:PIPELINE_PYTHON = (Resolve-Path workers/.venv/Scripts/python.exe).Path
mvn -B -f backend/pom.xml test
```

Os testes de integração usam recursos isolados. Sem a variável de habilitação, o teste completo opcional é ignorado.

## Compatibilidade e histórico

Os endpoints `/api/experiment/split`, `/allocate`, `/sessions` e `/metrics` foram retirados do MVP e retornam `410 Gone`. Registros experimentais antigos não são apagados. As hipóteses de IA H1/H2/H3 não são requisitos obrigatórios das versões 2 e 3; o experimento fica para uma etapa posterior.

- [Especificação Analytics](spec/README.md) — fonte vigente, derivada do novo PDF.
- [Requisitos v3](docs/REQUISITOS_V3.md) — escopo anterior, preservado como histórico.
- [Requisitos v2](docs/REQUISITOS_V2.md) — escopo anterior, preservado para histórico e compatibilidade.
- [Etapa 3: análises descritivas](docs/IMPLEMENTACAO_ETAPA_3.md) — contratos, uso, reprodução e limites.
- [Etapa 2: pipeline](docs/IMPLEMENTACAO_ETAPA_2.md) — configuração de filas, armazenamento e worker.
- [Etapa 1](docs/IMPLEMENTACAO_ETAPA_1.md) e [auditoria](docs/AUDITORIA_REQUISITOS.md) — registros históricos de achados e correções.
- `DenguePharma_Proposta_Formal.pdf` — proposta original preservada.

A implementação das análises v2 não equivale a homologação de toda a plataforma. Pendências gerais de operação e curadoria permanecem descritas nos documentos, incluindo recuperação de backup, testes de carga e acessibilidade completa.

## Registro final das alterações

Consulte o **[registro consolidado das etapas 1 a 4](docs/ALTERACOES_CONSOLIDADAS.md)** para todas as alterações de escopo, curadoria, coleta, processamento, APIs, banco, análises, dashboards e reprodução. Ele reúne os resultados finais dos testes, os limites operacionais e as pendências.

A [validação do piloto real](docs/TESTE_CIENCIA_DADOS.md) registra 50 documentos coletados, 19 tabelas CSV e oito gráficos. O panorama está disponível sem login; a revisão humana do piloto e a coleta completa continuam pendentes.

### Migração Python — primeiro marco

A [etapa de migração Analytics](docs/MIGRACAO_ANALYTICS.md) registra a estrutura nova, as diferenças em relação ao PDF, a leitura somente de leitura, os marts e a validação. Java/React e dados históricos permanecem disponíveis até a paridade dos fluxos substitutos. A primeira entrega não conclui os eixos B, C e D nem a avaliação científica do corpus.
