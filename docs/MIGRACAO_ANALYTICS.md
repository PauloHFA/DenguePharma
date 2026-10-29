# Migração Analytics — primeiro marco Python

Data: 28/10/2026, America/Sao_Paulo. Referência: novo PDF **DenguePharma Analytics — Estudo de Data Science sobre Evidências Farmacológicas para Dengue**, proposta 2.0, e plano de migração aprovado. Esta entrega é a fundação paralela; não representa conclusão dos eixos científicos do PDF.

## Decisões adotadas

- Mesmo repositório, com projeto novo em `analytics/` e especificação em `spec/`.
- FastAPI, Streamlit e Quarto substituem gradualmente Spring Boot/React; PostgreSQL, RabbitMQ e MinIO permanecem na arquitetura.
- A, B, C e D são objetivos obrigatórios por etapas; E é opcional.
- Java/React e suas tabelas, decisões e snapshots não foram removidos ou alterados pela migração.
- Nesta fase não há coleta externa nova, consumo de fila, escrita no PostgreSQL legado ou novo fluxo de curadoria. Esses serviços continuam no legado.

## Entregas realizadas

| Área | Entrega |
| --- | --- |
| SDD | Os 66 requisitos da seção 8 do PDF foram registrados com aceite, prioridade, forma de verificação, cenário, marco e referências. |
| Primeiro marco | Doze requisitos MIG delimitam os comportamentos entregues e seus testes. Os requisitos futuros continuam planejados. |
| Organização Python | Módulos separados de fontes, identidade, preparação, análises, marts, armazenamento, API, dashboard e relatórios. |
| Leitura | JSON v3 ou snapshot canônico via PostgreSQL, com hash verificado e transação somente de leitura. |
| Bronze | Entrada original preservada por hash; identificada como snapshot analítico legado, sem inventar uma resposta HTTP bruta retroativa. |
| Prata | Documentos, versões, identificadores, vínculos e campos aprovados, com schemas explícitos. |
| Ouro | Diagnósticos `corpus_*`, agregações revisadas e `mart_panorama` por estudo. O mart permanece vazio quando não há curadoria. |
| Persistência analítica | Dezenove tabelas Parquet, banco DuckDB derivado, manifesto e fontes analíticos; preparação idempotente e integridade conferida. |
| FastAPI | Consulta pública de execuções publicadas, schemas/hashes, resumo sanitizado, tabelas paginadas e downloads autorizados. Não oferece escrita. |
| Streamlit | Dashboard sem login, métricas, evolução temporal, tabelas, filtros de fonte/contexto e indicação dos eixos pendentes. |
| Quarto | HTML real, autocontido, com tabelas, denominadores, corte, proveniência e limitações, gerado sobre a mesma base analítica. |
| Reprodução | Testes de preparações independentes, hashes Parquet, igualdade com as regras legadas e verificação de entradas/artefatos alterados. |
| Notebook | `notebooks/02_analytics_marts.ipynb` consulta os mesmos marts em modo somente de leitura. |
| CI | Workflow separado para a fundação, lockfile Python, testes e validação da matriz SDD. |

As rotinas de identidade, preparação documental, diagnóstico e agregação revisada foram adaptadas do código Python anterior, com testes de equivalência. O runtime novo não importa o pacote de workers antigo nem chama a API Java.

## Validação executada

- **14 testes Analytics aprovados**, com PostgreSQL local real e Quarto configurados, sem testes ignorados nessa execução.
- Leitura real do snapshot `5dc0c29f-234e-4ec4-8f32-91459358b472` em `REPEATABLE READ READ ONLY`.
- Conferência de que uma tentativa de escrita com `WHERE false` é recusada pela conexão somente de leitura; nenhum registro é atualizado.
- Entrada preservada com hash `6cd0c7c07456e66a70ecbe3aa49de40c2e11977449177edde68f8af53fcf264e`.
- Equivalência da preparação e dos resultados do piloto real e de conjuntos pequenos conhecidos; a versão do módulo novo é identificada separadamente.
- Parquet com hashes iguais em preparações independentes e DuckDB com schemas preservados nas tabelas vazias.
- API bloqueando execuções não publicadas, arquivos privados, filtros inválidos e operações de escrita inexistentes.
- Testes de Streamlit com AppTest; Chrome real verificando acesso anônimo, métricas, filtro PubMed, abas, estados vazios, eixos planejados e layout móvel.
- Download do Quarto HTML pela API real, bloqueio do banco DuckDB privado e ausência de erros JavaScript de página.
- Doze requisitos MIG marcados como verificados por evidência JUnit; os 66 requisitos do PDF permanecem planejados nesta arquitetura. O portão de release completo permanece bloqueado.
- Pacote wheel local construído e inspecionado, incluindo o template Quarto e excluindo dados locais/segredos; dependências conferidas com `pip check`.

Há avisos de depreciação de bibliotecas nos testes, sem falhas: TestClient/HTTPX e uso interno de pandas pelo Streamlit. As versões verificadas estão fixadas no lockfile; esses avisos não foram confundidos com erros de contagem ou validação científica.

## Resultado com os dados existentes

| Indicador | Resultado |
| --- | --- |
| Documentos do piloto | 50 |
| Publicações | 25 |
| Registros de ensaios | 25 |
| Estudos com campos revisados | 0 |
| Tabelas Parquet | 19: cinco prata e 14 públicas/analíticas |
| Run Analytics publicado | `41934765a324a9fa59c58e02e11d7034e6afcfcf2e230872517e1b22a70a3433` |
| Quarto utilizado | 1.10.19, distribuição oficial portátil verificada por SHA-256 |

O piloto de 50 registros continua sendo material operacional/de desenvolvimento. Não foram aprovados campos fictícios nem construídos uma referência adjudicada ou um teste experimental a partir dele. Dois anos bibliográficos posteriores ao corte continuam sinalizados para conferência.

## Acesso e operação

- Novo dashboard: **http://127.0.0.1:8501/**.
- Nova API: **http://127.0.0.1:18081/**; documentação em `/docs`.
- Legado: interface `http://127.0.0.1:5173/`, backend `http://127.0.0.1:18080`.
- A área de curadoria segue protegida na aplicação legada, indicada no dashboard.

Instalação, preparação, publicação, relatório e comandos de inicialização estão em [analytics/README.md](../analytics/README.md). A [especificação](../spec/README.md) contém os requisitos, estados e critérios do marco.

Dados novos ficam em `analytics/data/`, ignorados pelo Git e separados de `target/`. Evidências locais de testes/navegador e logs ficam em `analytics/target/`; podem desaparecer se esse diretório for limpo. Essa exportação não substitui backup integral de PostgreSQL/MinIO.

## O que permanece para os próximos marcos

1. Migrar coleta, formulários científicos, triagem, adjudicação, autenticação e autorização para a nova arquitetura, com testes de paridade.
2. Completar o eixo A: patrocinador, IC e tendência, mantendo unidade de estudo e contextos distintos.
3. Construir o mart de relato e análise de sobrevivência/discrepâncias do eixo B.
4. Integrar carga de doença e definições geográficas/temporais do eixo C.
5. Definir referência, protocolo, revisores, provedor, orçamento e condições documentais para o eixo D.
6. Executar o piloto metodológico de 20 registros e o plano estatístico antes do teste final; os 50 registros anteriores não são teste independente.
7. Avaliar o grafo opcional e homologar restauração, carga e retirada do legado.

Os modelos estatísticos e de IA novos não foram simulados nem apresentados como prontos. O primeiro marco prepara os dados e a arquitetura para implementá-los de forma verificável.
