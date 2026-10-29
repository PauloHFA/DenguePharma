# Síntese clínica — implementação e operação

**Atualização 0.10.0:** a [identidade dos estudos](ETAPA_IDENTIDADE_ESTUDOS.md) recebeu prévia e confirmação por campos. Vínculos divergentes exigem conferência humana, e correções não reativam revisões antigas. Os agrupamentos dos pilotos reais permaneceram iguais.

**Atualização 0.9.0:** o [backup da curadoria](ETAPA_BACKUP_CURADORIA.md) preserva snapshot, protocolo, fontes e auditoria, com restauração em diretório separado. É uma entrega operacional; os resultados publicados da versão 0.8.0 e a pendência de revisão humana continuam preservados.

**Atualização 0.8.0:** a [prévia da revisão independente](ETAPA_PREVIA_REVISAO.md) permite conferir a planilha sem criar votos. A interface exige confirmação explícita e envia recibo ligado ao estado atual; mudanças de base exigem nova conferência.

**Atualização 0.7.0:** a [coleta completa controlada](ETAPA_COLETA_COMPLETA.md) acrescenta plano congelado, retomada conservadora e exportação PostgreSQL somente de leitura. A execução real continua condicionada à seleção e calibração humanas; nenhuma aprovação é transportada automaticamente ao corpus ampliado.

Data: 28/10/2026. Versão Python: 0.2.0. Especificação prioritária: [emenda clínica](../spec/clinical/EMENDA_CLINICA.md). Java/React, dados e execuções anteriores foram preservados.

O [plano atual do estudo](PLANO_ATUAL_SINTESE_CLINICA.md) consolida objetivo, metodologia, sequência de execução e critérios de aceite. Este guia descreve a implementação e a operação dessa entrega.

**Atualização 0.6.0:** a [calibração e síntese por campos](ETAPA_CALIBRACAO_SINTESE.md) acrescenta decisões metodológicas e conclusões com seleção/calibração vigentes e vínculo `selection_hash`. Os formulários substituem o JSON no fluxo principal dessas decisões; a execução científica real continua pendente.

**Atualização 0.5.0:** a [extração clínica por campos](ETAPA_EXTRACAO_CLINICA.md) acrescenta prévia sem gravação, suporte por ocorrência e formulários de revisão/adjudicação. A seleção independente permanece requisito para extrair, e o corpus real continua sem resultados clínicos aprovados.

**Atualização 0.4.0:** a [revisão independente do piloto](ETAPA_REVISAO_INDEPENDENTE.md) acrescenta pacote privado, importação CSV, painel de pendências e auxílio a localizadores. Foram preparados os materiais para as revisões humanas; o corpus real continua sem votos ou resultados clínicos aprovados.

**Atualização 0.3.0:** a [continuidade de calibração](CONTINUIDADE_CALIBRACAO.md) acrescenta triagem por campos, quatro tabelas de metadados e a aba Resultados gerais. As seções abaixo registram a entrega 0.2.0; a triagem já não exige preencher JSON, e as demais ações avançadas mantêm essa opção.

## Entrega

- Espaço clínico privado, separado por hash de entrada + protocolo, SQLite transacional, eventos e fontes sem atualização/exclusão e cadeia de hashes. Nenhuma escrita analítica no PostgreSQL legado.
- Triagem por dois revisores, adjudicação independente, classificações clínicas, vínculos documentais explícitos e invalidação por mudança de fonte. Votos alheios não são expostos antes da decisão independente.
- Rascunhos por braço/comparação/população/desfecho/tempo, revisão por outra pessoa e adjudicação por terceiro. Bloqueios de autorrevisão, números incompatíveis, versão incorreta, suporte literal inventado e duplicação divergente.
- RR log-Wald e diferença de médias com IC de Welch; estimativas publicadas preservadas. Zero eventos, falta de média/SD, braços dependentes e outros desenhos não recebem cálculo indevido. Sem pooling ou ranking.
- Julgamentos humanos justificados e associados ao conjunto de resultados, distinção entre pendência e inconclusão, ausência de estudo somente após decisão explícita e seleção completa.
- Seis tabelas clínicas em Parquet/DuckDB: seleção, resultados, síntese, referências, conflitos e ausências. CSVs e gráficos PNG individuais na API pública; relatório Quarto com tabelas e figuras incorporadas. Fichas e mapa de categorias no Streamlit, sem estimativa combinada.
- Curadoria protegida no Streamlit e na FastAPI, reutilizando a identidade verificada pelo backend legado. Dashboard público sem login. Não há senha/token em manifesto nem cache global de curadoria.
- Ponte Python para a coleta durável existente, com busca clínica congelada, corte e checkpoint; somente piloto de até 20 registros. Não substitui a migração operacional completa.

As tabelas clínicas são um contrato adicional ao snapshot v3. Os snapshots anteriores não foram alterados; execuções antigas continuam consultáveis. A API retorna indisponibilidade para tabelas que ainda não existiam naquela execução, em vez de quebrar a consulta.

## Comandos

Executar na raiz do repositório, com o ambiente Python 3.12 de `analytics` e infraestrutura legada ativa. As credenciais são lidas do `.env`, sem serem impressas.

```powershell
analytics/.venv/Scripts/python.exe -m pip install -r analytics/requirements.lock
analytics/.venv/Scripts/python.exe -m pip install --no-deps -e analytics

# Nova coleta clínica para calibração; repetir a mesma pasta retoma o checkpoint.
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-collect-pilot --protocol spec/clinical/protocolo.json --cutoff 2026-10-28 --output analytics/data/calibration/clinical-001

# Congelar entrada/protocolo e recuperar as versões originais exatas para revisão privada.
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-init --input analytics/data/calibration/clinical-001/dataset.json --protocol spec/clinical/protocolo.json
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-enrich --workspace <workspace_id>

# Após decisões humanas, gerar outra execução imutável, conferir e publicar explicitamente.
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-freeze --workspace <workspace_id>
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli verify --run <run_id>
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli report --run <run_id> --quarto analytics/.tools/bin/quarto.cmd
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli publish --run <run_id>
```

`clinical-freeze` usa os mesmos cálculos e exportadores usados pela API/dashboard; não aceita conclusões por argumento nem gera aprovação. Novas decisões resultam em novo snapshot/run. Publicar diagnóstico com zero resultados é permitido, desde que identificado como tal; não transforma metadados em evidência clínica.

O checkpoint da coleta guarda IDs de protocolo, importações e análise. Falhas dos jobs são tratadas no processamento legado. Em falha de rede entre criação e recebimento da resposta, verificar o protocolo/filas antes de repetir uma criação ambígua. Não há promessa de transação distribuída entre o arquivo de checkpoint e a API. O coletor não inicia coleta integral nem amplia o limite após uma aprovação presumida.

## Curadoria

Abra `http://127.0.0.1:8501`, expanda “Curadoria clínica — acesso protegido” e use uma conta existente. Pesquisador/revisor pode registrar triagem e extração; adjudicação exige administrador/adjudicador com identidade distinta. São necessárias **três pessoas/contas independentes** para autor, revisão e adjudicação de resultados. Não contorne a independência criando aprovações automáticas.

A primeira interface usa formulário JSON orientado por contrato, lista de estudos/fontes e visualização privada das pendências. Exemplos em [clinical-actions.json](../analytics/examples/clinical-actions.json); contratos consultáveis no próprio formulário e em `GET /api/clinical/contracts`. Essa interface é funcional para pesquisa, mas ainda não é um formulário clínico especializado com campos individuais.

Fluxo: consultar fila/hash da base → abrir versão permitida → registrar duas triagens → adjudicar divergência → conferir identidade/vínculos → extrair resultado e localizadores → revisão independente → adjudicação → avaliar instrumento metodológico → justificar síntese → congelar/publicar nova execução. Os identificadores e offsets retornados pela API são os que devem constar dos dados de revisão.

`absence_states` preserva estados informados pelo curador; campo nulo não é convertido em zero. A fonte privada exibe representação textual normalizada e seu hash. Seus offsets identificam essa representação, e não a paginação do PDF. O hash original também acompanha a referência pública. Presença literal não comprova suporte semântico: o revisor precisa conferir a interpretação, o subgrupo, a unidade e o período de avaliação.

## API

Público: `/api/public/analyses/{run}/tables/clinical_results`, demais tabelas clínicas e `/artifacts?name=clinical_results.csv` ou nome PNG informado no manifesto.

Protegido com Bearer: `POST /api/clinical/login`, `GET /api/clinical/workspaces`, `/contracts`, `/{workspace}/state`, `/{workspace}/sources/{version}` e `POST /{workspace}/actions/{kind}`. A API valida identidade em `/api/auth/me` do legado; `ANALYTICS_AUTH_URL` pode configurar seu endereço. Indisponibilidade da autenticação bloqueia curadoria, sem afetar leitura pública. Não existe endpoint público de aprovação ou publicação.

Corpos e decisões estão nos modelos em `analytics/src/denguepharma_analytics/clinical/models.py`. Eventos: `SCREENED`, `SCREEN_ADJUDICATED`, `DOCUMENT_LINKED`, `RESULT_DRAFTED`, `RESULT_REVIEWED`, `RESULT_ADJUDICATED`, `SYNTHESIS_CONCLUDED`, `CALIBRATION_APPROVED`, `ABSENCE_CONCLUDED`. A adjudicação de triagem exige o `votes_hash` atual mostrado apenas ao adjudicador no conflito.

## Dados reais e pendências

O piloto operacional de 50 documentos continua preservado e com suas versões conferidas. Foi criado um **novo piloto clínico de 20 documentos**, 10 PubMed + 10 ClinicalTrials.gov, corte 28/10/2026. A seleção é de conveniência, com elegibilidade pendente, e pode conter estudos inelegíveis. A coleta não garante acesso a todos os textos completos.

Protocolo de coleta: `c59fc9c6-32e4-4988-965e-5483692c1137`; análise legada: `b9b1098a-de42-487a-bb68-a45ffb4dded4`; hash do snapshot: `c1605cb455f0789735ab8566721333cb19a3d3c1924da06ef13c77d96205bf7b`. Espaço privado: `98043ff1652d98455adf3a115125cff18b89967a6c90f15545d87cb880f33e0e`.

**Nenhum desses conjuntos já constitui a síntese clínica.** Faltam definir/conferir referências sentinela, obter textos por canais permitidos, executar triagem e extração independentes, adjudicar, aplicar avaliação metodológica, calibrar a busca, coletar o corpus final e registrar as conclusões. Sem essas atividades, o sistema mostra zero resultados clínicos revisados. Não foi necessário contratar IA ou API paga.

Requisitos de software CLN-001 a CLN-005 têm testes executáveis; CLN-006 permanece planejado por depender da execução científica humana. Carga de doença e experimento de IA foram adiados, e meta-análise permanece fora do escopo.

## Validação executada

- **24 testes aprovados**, incluindo PostgreSQL e Quarto reais, cálculos conhecidos, seleção independente, conflitos, duplicação, literalidade, fontes alteradas, observacionais/subgrupos, conclusões, permissões e equivalência CLI/exportador.
- Verificador SDD: 84 requisitos, 17 com evidência automatizada nesta execução (12 MIG + 5 CLN); nenhum requisito científico futuro foi marcado como concluído.
- Coleta real do piloto de 20 registros pelos jobs existentes, armazenamento de fontes no legado e conferência das 20 versões originais por hash. O piloto anterior de 50 versões também foi conferido.
- Login real validado contra a autenticação existente, sem imprimir token; fila privada com 20 pendências e zero resultados aprovados.
- Navegador Chrome: dashboard aberto com contagens 20/10/10/0, aba clínica sem resultados fictícios, CSV e Quarto disponíveis, curadoria sem token recusada com 401, arquivo privado indisponível e nenhum erro JavaScript. Capturas desktop/mobile e relatório operacional ficam em `analytics/target/`, ignorado pelo Git.

Execução clínica publicada do novo piloto: `2665dc99d26e8a4b765664bed913e894b0fda613dd431ce2adbfd83eb90ad5d2`; entrada clínica congelada: `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb`. Diagnóstico clínico preservando os 50 documentos: `043def5a6c675f808a52d3069367457619508ca9a1306627bac2f56cd10726fc`. Cada execução contém 25 tabelas tipadas; resultados e síntese clínica permanecem vazios por falta de revisão.

**Atualização 0.11.0:** o [comparador de execuções publicadas](ETAPA_COMPARACAO_EXECUCOES.md) acrescenta acompanhamento de mudanças documentais e de tabelas. Os resultados reais confirmam preservação dos pilotos entre as versões 0.6.0 e 0.8.0, sem nova coleta ou revisão clínica.

**Atualização 0.12.0:** o [panorama dos patrocinadores declarados](ETAPA_PATROCINADORES.md) descreve registros coletados e não avaliados para elegibilidade. Os resultados são separados da síntese clínica e não atribuem risco de viés ou benefício a medicamentos. O workspace clínico original permanece pendente de revisão.

**Atualização 0.13.0:** a [auditoria de datas dos registros](ETAPA_AUDITORIA_RELATO.md) analisa relato administrativo de resultados, sem sobrevida de pacientes, censura ou Kaplan–Meier. É separada da síntese de benefício/segurança e não cria votos ou aprovações clínicas.

**Atualização 0.14.0:** a [auditoria de referências por PMID](ETAPA_REFERENCIAS_PUBLICACOES.md) produz candidatos e lacunas bibliográficas, sem confirmar vínculo clínico ou coletar artigos automaticamente. O estado da revisão científica permanece inalterado.

**Atualização 0.16.0:** o [resumo privado da seleção](ETAPA_FLUXO_SELECAO.md) acrescenta motivos principais humanos após exclusão resolvida, preservando votos e justificativas anteriores. O fluxo completo PRISMA continua pendente; não foram criadas decisões científicas nesta entrega.

**Atualização 0.17.0:** a [fila pessoal](ETAPA_FILA_PESSOAL.md) apresenta tarefas e revisões da própria conta, separadas dos votos globais. Mantém as validações de dois revisores e adjudicação independente; a navegação não registra decisões automaticamente.

**Atualização 0.18.0:** a [curadoria independente do dashboard público](ETAPA_ATUALIZACAO_CURADORIA.md) reduz reconstruções durante as interações privadas. As consultas de curadoria continuam atuais, sem cache de votos ou tokens. Não houve alteração nos resultados científicos publicados.

**Atualização 0.19.0:** o [fluxo de integridade documental](ETAPA_INTEGRIDADE_DOCUMENTAL.md) suspende a evidência corrente após alerta humano confirmado e preserva o histórico. Regularização exige novas revisões. A detecção automática e a atualização automática de relatórios históricos não foram implementadas nesta etapa.
