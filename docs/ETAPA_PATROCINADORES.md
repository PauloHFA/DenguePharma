# Panorama dos patrocinadores declarados — versão 0.12.0

Entrega de 28/10/2026. A análise descritiva passou a incluir o patrocinador responsável declarado nos registros coletados do ClinicalTrials.gov. Foram acrescentadas tabelas, gráfico PNG, apresentação no dashboard e seção no relatório Quarto. Não há avaliação de eficácia ou de risco de viés por patrocinador.

## Resultado com os dados reais

Os mesmos documentos e versões já coletados foram consultados no PostgreSQL somente de leitura. Não houve busca nova nas APIs ou ampliação da coleta.

| Categoria declarada pelo registro | Piloto clínico: 10 registros de ensaios | Piloto operacional: 25 registros de ensaios |
| --- | --- | --- |
| `INDUSTRY` | 4/10 — 40% | 8/25 — 32% |
| `OTHER` | 4/10 — 40% | 11/25 — 44% |
| `NIH` | 2/10 — 20% | 3/25 — 12% |
| `FED` | 0/10 — 0% | 2/25 — 8% |
| `OTHER_GOV` | 0/10 — 0% | 1/25 — 4% |

Nome e categoria estavam disponíveis em **10/10** registros do piloto clínico e **25/25** do operacional, sem conflitos nesses campos. Isso significa disponibilidade nesses snapshots, não qualidade metodológica, confirmação do financiamento ou aprovação dos estudos.

Os códigos acima são os valores declarados pela fonte. Não foram inferidos pela instituição, pelo país ou pela intervenção. Categorias com contagem zero na tabela-resumo indicam que nenhum dos registros comparados as declarou; não representam ausência de patrocínio na literatura.

O piloto clínico possui 20 documentos no total, dos quais 10 são registros de ensaios. O operacional possui 50 documentos, dos quais 25 são registros. **Os pilotos são amostras separadas, podem se sobrepor e não devem ser somados como estudos independentes.** Seus registros ainda podem conter vacinas, prevenção ou outras intervenções inelegíveis para a pergunta sobre pacientes com dengue estabelecida.

Artefatos compartilháveis: [tabelas, resumo, gráfico e manifesto](resultados/patrocinadores-0.12/README.md).

## Método e denominadores

A análise considera somente documentos do tipo `REGISTRO_ENSAIO`. Publicações não entram como patrocinadores ausentes. A unidade é o registro consolidado por NCT válido; quando ele está ausente ou inválido, mantém-se a identidade persistida do documento. Isso não garante identidade clínica única entre registros distintos.

- O mesmo NCT é contado uma vez, preservando todas as referências documentais.
- Nomes recebem apenas normalização de espaços e caixa. Não há resolução de identidade institucional, fusão de homônimos ou normalização por inferência.
- Valores originais com espaços normalizados e observações por documento são preservados para conferência.
- Nome e categoria são analisados separadamente como `PRESENTE`, `NAO_INFORMADO` ou `CONFLITO`.
- Valores não ausentes divergentes geram conflito; não se escolhe a versão mais recente.
- Se houver valor informado em uma representação e ausência em outra, o valor disponível pode representar o registro, preservando a ausência na observação documental. Ausência não é uma segunda categoria de patrocinador.
- A distribuição de cada campo usa todos os registros consolidados, incluindo categorias explícitas de ausência e conflito.
- A completude usa registros com um valor não conflitante divididos pelos registros consolidados, com numerador e denominador.
- Denominador zero produz proporção `null`; não há métricas artificiais de 100%.

As agregações usam pandas. Metadados com tipos incompatíveis e identidades documentais contraditórias são recusados, sem preenchimento automático. Não são calculados intervalos de confiança populacionais para esse piloto de conveniência, testes de associação, rankings de tratamentos ou medidas de risco de viés a partir desses campos.

## Fontes, dados e reprodução

O adaptador somente de leitura passou a preservar `sponsorCollaboratorsModule.leadSponsor.name` e `.class`. Contatos, responsável individual pelo envio, descrições e dados de investigadores não são copiados por esse módulo. Colaboradores e financiamento efetivo não são analisados nesta entrega.

Os snapshots novos mantêm as versões e hashes canônicos dos documentos originais, além de licenças, fontes e identificadores. Eles contêm metadados; `studies` e `scientificFields` permanecem vazios, sem bloco de aprovações clínicas transferidas. A curadoria dos workspaces anteriores não foi modificada.

Novas tabelas públicas em Parquet/DuckDB:

- `corpus_sponsor_trials`: unidade consolidada, valores, estados, observações e referências.
- `corpus_sponsor_distributions`: frequências, denominadores e proporções por campo.
- `corpus_sponsor_completeness`: disponibilidade, ausência e conflitos.

As execuções novas possuem **32 tabelas**. As execuções e relatórios anteriores são preservados. Um snapshot antigo que não contenha patrocinadores continua sem essa informação; a preparação nunca consulta o banco silenciosamente para preencher campos ausentes.

Para exportar metadados de importações concluídas e identificadas:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli snapshot-collection --protocol PROTOCOL_ID --run-id PUBMED_RUN_ID --run-id CLINICALTRIALS_RUN_ID --output analytics/data/snapshots/NOVO_ARQUIVO.json --env-file .env
```

O comando não inicia coleta, não publica e recusa um arquivo de destino existente. Depois de congelar a entrada:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --input analytics/data/snapshots/NOVO_ARQUIVO.json --expected-hash HASH_RETORNADO
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data report --run RUN_ID --quarto analytics/.tools/bin/quarto.cmd
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data publish --run RUN_ID
```

Repetir a preparação da mesma entrada/configuração reproduz as tabelas e verifica o resultado existente. A exportação de outro snapshot pode gerar novo ID e data de execução; isso não significa nova coleta. Todos os dados analíticos são reconstruídos a partir do JSON congelado.

Execuções publicadas localmente:

| Corpus | Run |
| --- | --- |
| Metadados do piloto clínico de 20 documentos | `057a93cead43265598f1c97c446ac0740f06fe2654b66ee75b0f970a37b10f7f` |
| Metadados do piloto operacional de 50 documentos | `9c5e342e4627b94a793b04ad2838d77a8e5a400a8b36d909fe136b79f079b741` |

Os resultados anteriores de comparações de snapshots continuam sendo artefatos históricos. Não se deve comparar uma execução clínica com aprovações vinculadas ao protocolo com uma exportação somente de metadados como se ambas tivessem o mesmo escopo de curadoria.

## Onde consultar

No [dashboard local](http://127.0.0.1:8501), abrir **Ensaios → Patrocinadores declarados nos registros**. O painel informa a unidade, disponibiliza estados e observações documentais e oferece CSVs. O PNG também é exportável pelos artefatos da execução e está incorporado na seção própria do relatório Quarto, separado dos gráficos de efeitos clínicos.

Execuções anteriores sem essas tabelas mostram uma mensagem de indisponibilidade, sem erro e sem inventar valores. Os dashboards e esses metadados publicados são abertos; a curadoria permanece protegida.

## Situação científica

Esta entrega descreve a composição documental do corpus. Patrocinador responsável declarado não equivale necessariamente ao financiador efetivo. Frequência por categoria não demonstra benefício, dano ou risco de viés, e a disponibilidade do campo não substitui avaliação metodológica.

O workspace clínico original continua com **20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados**. Não houve preenchimento de votos, transferência de aprovações ou conclusão sobre medicamentos. Patrocinadores por estudo clínico incluído/revisado, os demais itens do eixo A e a execução científica CLN-006 continuam pendentes.

## Validação da entrega

A suíte completa teve **101 testes aprovados**, com PostgreSQL e Quarto reais. Os oito cenários novos verificam contagens e proporções conhecidas, consolidação por NCT, grafias originais, ausências e conflitos por documento, identificadores inválidos, conjunto vazio, whitelist de privacidade, equivalência CLI/API/Parquet/PNG/HTML, compatibilidade com execuções antigas e preservação das outras 29 tabelas ao acrescentar somente esses metadados.

A matriz contém **94 requisitos, 27 com evidência automatizada nesta execução**. Evidência: `analytics/target/sponsors-junit.xml`. A execução real está registrada em `analytics/target/sponsors-real-results.json`.

A conferência no Chrome validou o painel público de patrocinadores, os 10 registros e a distribuição INDUSTRY 4 / NIH 2 / OTHER 4. O PNG disponibilizado pela API teve hash idêntico ao arquivo compartilhado, e CSV e relatório Quarto foram acessados com sucesso. Não houve erro JavaScript ou resultado clínico gerado. Evidência: `analytics/target/sponsors-browser-results.json`.
