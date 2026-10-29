# DenguePharma Analytics — fundação Python

**Versão 0.20.0:** [cobertura da extração por desfecho](../docs/ETAPA_COBERTURA_EXTRACAO.md), mapa privado por estudo incluído e desfecho, com resultados canônicos e conflitos. Exporta CSV/JSON/manifesto sem votos ou textos. Não calcula eficácia ou porcentagem genérica de completude.

**Versão 0.19.0:** [retratações e correções documentais](../docs/ETAPA_INTEGRIDADE_DOCUMENTAL.md), registradas por humano autorizado com prévia e confirmação. No dashboard: **Curadoria clínica → Integridade documental — retratações e correções**. O alerta não atualiza automaticamente execuções públicas históricas.

**Versão 0.18.0:** [atualização independente da curadoria](../docs/ETAPA_ATUALIZACAO_CURADORIA.md), com fragmento Streamlit e atualização no escopo permitido. Trocar filtros privados deixa de reconstruir os dashboards públicos; não há cache de votos ou tokens.

**Versão 0.17.0:** [fila pessoal de revisão](../docs/ETAPA_FILA_PESSOAL.md), com progresso por conta, filtros de tarefas e atualização após envio humano. No dashboard: **Curadoria clínica → Triagem por campos → Mostrar na minha fila**. Nenhum voto é atribuído automaticamente.

**Versão 0.16.0:** [fluxo da seleção e motivos de exclusão](../docs/ETAPA_FLUXO_SELECAO.md), com contagens privadas, motivos principais confirmados por humano e exportação JSON agregada. No dashboard: **Curadoria clínica → Fluxo da seleção e motivos de exclusão**. Não gera PRISMA completo ou decisões automáticas.

**Versão 0.15.0:** [dossiê documental na triagem](../docs/ETAPA_DOSSIE_TRIAGEM.md), consulta privada por estudo com controle de acesso, hashes e verificação da base atual. No formulário de triagem: **Documentos do estudo selecionado — leitura para triagem**. Os relatórios públicos anteriores permanecem na versão 0.14.0.

**Consolidação científica sobre 0.14.0:** [notebook executável e relatórios HTML](../docs/ETAPA_NOTEBOOK_PESQUISA.md), consultando as mesmas 34 tabelas públicas. Executor: `analytics/scripts/reproduce-notebook.py`; não exige nova coleta nem altera a curadoria.

**Versão 0.14.0:** [auditoria de referências](../docs/ETAPA_REFERENCIAS_PUBLICACOES.md), três tabelas adicionais (39 no total), PNG e seção Quarto. No dashboard: **Qualidade e reprodução → Publicações indicadas — cobertura por PMID**.

**Versão 0.13.0:** [auditoria de datas e relato](../docs/ETAPA_AUDITORIA_RELATO.md), quatro tabelas adicionais (36 no total), gráfico e Quarto, usando os mesmos JSONs congelados. No dashboard: **Ensaios → Relato de resultados — auditoria de datas**.

**Versão 0.12.0:** [panorama dos patrocinadores](../docs/ETAPA_PATROCINADORES.md), três tabelas adicionais (32 no total), gráfico exportável e leitura das mesmas versões documentais por `snapshot-collection`. No dashboard: **Ensaios → Patrocinadores declarados nos registros**.

**Versão 0.11.0:** [comparador de execuções](../docs/ETAPA_COMPARACAO_EXECUCOES.md) por CLI/API e painel **Qualidade e reprodução → Atualizações entre execuções**. Distingue mudanças dos dados, das referências e das tabelas, sem inferir efeitos clínicos.

**Versão 0.10.0:** [conferência da identidade documental](../docs/ETAPA_IDENTIDADE_ESTUDOS.md), com consulta privada, alteração por adjudicador/administrador e confirmação vinculada ao estado atual. O fluxo não funde estudos automaticamente nem transfere votos entre grupos.

**Versão 0.9.0:** [backup privado e restauração isolada](../docs/ETAPA_BACKUP_CURADORIA.md) por `clinical-backup` e `clinical-restore`, sem sobrescrever workspaces ou publicar cópias. O pacote cobre somente a curadoria clínica.

**Versão 0.8.0:** [prévia da revisão independente](../docs/ETAPA_PREVIA_REVISAO.md), com validação sem anexar eventos, contagens de novas decisões/alterações e confirmação vinculada ao estado atual. O formato do CSV continua compatível.

**Versão 0.7.0:** [coleta completa controlada](../docs/ETAPA_COLETA_COMPLETA.md), com plano privado, retomada por IDs, snapshot imutável e leitura PostgreSQL sem o limite HTTP de 8 MiB. A execução real aguarda a calibração humana do piloto.

**Versão 0.6.0:** [calibração e síntese](../docs/ETAPA_CALIBRACAO_SINTESE.md), com formulários para decisões metodológicas, conclusões por desfecho e ausência no corpus. Chamadas de aprovação devem incluir `selection_hash`; o novo formulário envia o vínculo automaticamente.

**Versão 0.5.0:** [extração clínica por campos](../docs/ETAPA_EXTRACAO_CLINICA.md), com resultados por braço/desfecho/tempo, referências literais, prévia sem gravação e formulários de revisão/adjudicação. A extração é habilitada somente após inclusão pela seleção independente.

**Versão 0.4.0:** [revisão independente do piloto](../docs/ETAPA_REVISAO_INDEPENDENTE.md), com pacote privado, planilha em branco, importação atômica autenticada, painel de pendências e localizadores literais. O pacote de 20 registros foi preparado; a revisão científica continua dependendo de pessoas distintas.

**Versão 0.3.0:** [resultados gerais e calibração](../docs/CONTINUIDADE_CALIBRACAO.md), com quatro tabelas adicionais, sinais de metadados rastreáveis, resumo Markdown, gráfico e triagem por campos. Veja os [resultados descritivos do piloto](../docs/RESULTADOS_GERAIS_PESQUISA.md). Elegibilidade e conclusões clínicas continuam exigindo revisão independente.

**Versão 0.2.0:** a [síntese clínica](../docs/IMPLEMENTACAO_SINTESE_CLINICA.md) acrescenta curadoria autenticada, resultados por braço/desfecho/tempo, gráficos individuais e conclusões humanas. Consulte essa documentação para os novos comandos e a situação do piloto clínico de 20 registros. As seções de fundação abaixo descrevem a entrega anterior; não representam o limite atual do software.

Primeiro marco da migração aprovada em 28/10/2026: FastAPI, Streamlit, Quarto e Parquet/DuckDB em paralelo ao legado. A especificação vigente está em [spec](../spec/README.md). Os eixos A, B, C e D são objetivos do projeto completo; somente o diagnóstico descritivo e a estrutura de dados estão implementados nesta entrega.

## Instalação

Na raiz do repositório, com Python 3.12:

```powershell
py -3.12 -m venv analytics/.venv
analytics\.venv\Scripts\python.exe -m pip install -r analytics/requirements.lock
analytics\.venv\Scripts\python.exe -m pip install --no-deps -e analytics
```

As dependências resolvidas estão fixadas no lockfile. O pacote novo funciona sem importar `denguepharma_workers`; esse pacote só entra nos testes de equivalência. A consulta pública funciona sem Java após a preparação. A curadoria clínica valida identidade no backend legado, e a coleta piloto reutiliza seus coletores duráveis.

## Preparar e publicar dados

Leitura direta de um snapshot existente no PostgreSQL legado:

```powershell
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --legacy-analysis 5dc0c29f-234e-4ec4-8f32-91459358b472 --env-file .env
```

O adaptador usa conexão e transação somente de leitura, com isolamento repetível; confere os bytes canônicos contra o hash persistido. Usa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`, sem gravar credenciais no manifesto. O `.env` não é alterado.

Alternativamente, use um JSON v3 exportado:

```powershell
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --input CAMINHO_DO_DATASET --expected-hash HASH_DA_ENTRADA
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data verify --run RUN_ID
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data publish --run RUN_ID
```

A preparação não publica automaticamente. Publicar permite consulta dos metadados e agregações; não aprova elegibilidade ou campos científicos. O JSON de entrada é um contrato analítico legado, não uma coleta bruta original ou certificado de revisão científica independente.

## Armazenamento e módulos

| Área | Responsabilidade |
| --- | --- |
| `sources` | Leitura de JSON/PostgreSQL com conferência de hash e origem |
| `identity` | Normalização de identificadores; regras conservadoras |
| `preparation` | Preparação documental, duplicidades, conflitos e entidades químicas |
| `analyses` | Diagnóstico dos registros e agregação separada dos campos revisados |
| `marts.py` | Schemas Arrow, prata e ouro; mart revisado vazio conserva os tipos |
| `storage.py` | Runs imutáveis, publicação, hashes e consultas DuckDB somente de leitura |
| `api.py` / `dashboard.py` | FastAPI pública e dashboard Streamlit |
| `reports` | Template e renderização Quarto sobre os mesmos dados |

`analytics/data/` é privado e ignorado pelo Git. Contém `bronze/<hash>/snapshot.json`, `runs/<run_id>/`, `publications/` e `reports/`. Cada run tem 19 tabelas Parquet, DuckDB, resumo, código-fonte analítico e manifesto. Bronze e tabelas prata não são disponibilizados pela API. Isso não é backup completo do banco legado.

Runs são identificados por entrada, código, dependências e configuração. Repetir a preparação verifica a integridade e reutiliza o resultado; não o sobrescreve. Comparações em diretórios independentes verificam conteúdo e hashes Parquet. O binário DuckDB e o HTML têm hashes de integridade; não se promete igualdade binária entre versões/plataformas diferentes.

## Relatório Quarto

Instale Quarto pela distribuição oficial. No Windows, há opção portátil com versão e SHA-256 fixados, sem alterar a instalação global:

```powershell
analytics\.venv\Scripts\python.exe analytics/tools/install_quarto.py
$env:QUARTO_BIN = (Resolve-Path analytics/.tools/bin/quarto.cmd).Path
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data report --run RUN_ID
```

O HTML fica em `analytics/data/reports/RUN_ID/report.html`, acompanhado do QMD preenchido e de seu manifesto. Os dados são convertidos em tabelas HTML escapadas; o documento não executa instruções vindas das fontes. A API só serve o HTML se o run tiver publicação explícita e seu hash conferir.

## Executar a aplicação nova

```powershell
.\analytics\scripts\start-local.ps1
```

- Dashboard: **http://127.0.0.1:8501/**.
- API: **http://127.0.0.1:18081/**.
- Documentação da API: **http://127.0.0.1:18081/docs**.
- Saúde: **http://127.0.0.1:18081/health**.

O script inicia os processos em segundo plano, sem janela visível, registra PIDs/logs em `analytics/target/runtime` e recusa portas já ocupadas, sem interromper processos. Aceita `-ApiPort` e `-DashboardPort`. Para executar no terminal, use:

```powershell
analytics\.venv\Scripts\python.exe -m denguepharma_analytics.cli --data-dir analytics/data serve --port 18081
$env:ANALYTICS_API_URL = 'http://127.0.0.1:18081'
analytics\.venv\Scripts\python.exe -m streamlit run analytics/src/denguepharma_analytics/dashboard.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

`ANALYTICS_DATA_DIR` define o armazenamento; `ANALYTICS_API_URL` define a API usada pelo dashboard. A página pública abre sem login. A área de curadoria continua na aplicação legada, com link configurável por `LEGACY_CURATOR_URL`.

## Contratos públicos

| Rota | Uso |
| --- | --- |
| `GET /api/capabilities` | Capacidades implementadas, parciais e planejadas |
| `GET /api/public/analyses` | Execuções explicitamente publicadas |
| `GET /api/public/analyses/{id}` | Manifesto público, schemas e hashes dos Parquet |
| `GET /api/public/analyses/{id}/summary` | Resumo sanitizado e contexto do protocolo |
| `GET /api/public/analyses/{id}/tables/{table}` | Linhas paginadas; `offset`, `limit` de 1 a 1.000, filtros `source`/`context` quando aplicáveis |
| `GET /api/public/analyses/{id}/artifacts?name=...` | CSV, Parquet ouro, manifesto, resumo ou relatório autorizado |

Não há SQL arbitrário, API de escrita, download da entrada bronze, download de tabelas prata ou consumo de fila. Metadados particulares, parâmetros com chaves e textos integrais ficam fora das respostas públicas. CSV neutraliza prefixos interpretáveis como fórmulas; o Parquet mantém dados tipados.

## Testes e rastreabilidade

```powershell
$env:QUARTO_BIN = (Resolve-Path analytics/.tools/bin/quarto.cmd).Path
$env:ANALYTICS_LIVE_POSTGRES = 'true'
analytics\.venv\Scripts\python.exe -m pytest analytics/tests -q --junitxml=analytics/target/junit.xml
analytics\.venv\Scripts\python.exe spec/check.py --junit analytics/target/junit.xml
```

O teste PostgreSQL real lê o snapshot e confirma que uma tentativa de escrita sem linhas afetadas é recusada pela transação somente de leitura. Não modifica registros. Sem a variável de habilitação, esse teste é ignorado; sem Quarto configurado, o teste de renderização também é ignorado. O CI instala Quarto e executa os testes de referência; o acesso à base local não é necessário no CI.

Os 12 requisitos MIG só são marcados como verificados com evidência JUnit. O portão `--release-all` continua bloqueado enquanto houver requisito obrigatório do PDF sem teste/verificação. A primeira entrega não é release científico completo.

## Próximas etapas

Migrar coleta/curadoria/autorização e completar o eixo A antes dos novos métodos. Depois: relato e sobrevivência (B), carga × pesquisa (C), experimento com referência adjudicada (D) e grafo opcional (E). O piloto metodológico de 20 registros, o plano estatístico, o provedor e orçamento de IA e a referência humana ainda não foram realizados.

Contratos consultados: [DuckDB Python](https://duckdb.org/docs/stable/clients/python/overview.html), [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) e [Quarto Python](https://quarto.org/docs/computations/python.html). Quarto portátil vem da [distribuição oficial 1.10.19](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.10.19), verificada pelo hash registrado em `tools/quarto.lock.json`.
