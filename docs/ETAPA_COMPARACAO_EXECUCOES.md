# Comparação entre execuções publicadas — versão 0.11.0

Entrega de 28/10/2026. Foi implementada a análise de mudanças entre snapshots publicados, acessível por comando, API e dashboard. A análise diferencia alterações dos dados de origem de alterações no processamento e não infere mudança de efeito clínico.

## Métodos e unidades

A unidade documental é o **ID persistido do documento de origem**, contado uma vez em cada execução. Não é uma contagem de estudos únicos, ensaios elegíveis ou participantes. Documentos distintos sobre o mesmo estudo continuam sendo documentos distintos nessa comparação. Não há correspondência aproximada entre IDs.

O comparador exige o mesmo contrato de entrada, dicionário, protocolo/versão/corte/limite, filtros congelados, fontes/consultas e protocolo clínico, quando presente. Diferenças nesses elementos recusam a comparação com `INCOMPATIBLE_COMPARISON`; não são exibidas contagens como se as buscas fossem equivalentes. Os pilotos clínico e operacional não podem ser comparados como atualizações do mesmo corpus.

São comparadas as execuções completas; filtros visuais de outras tabelas do dashboard não são aplicados silenciosamente.

| Categoria | Critério | Denominador da proporção |
| --- | --- | --- |
| `NOVO` | ID presente apenas na execução atual | Documentos atuais |
| `NAO_OBSERVADO` | ID presente apenas na referência | Documentos da referência |
| `CONTEUDO_ALTERADO` | Mudança do hash do conteúdo da fonte | IDs compartilhados |
| `REFERENCIA_ALTERADA` | Mudança de versão, fonte, tipo, licença ou acesso, sem mudança do hash | IDs compartilhados |
| `REPRESENTACAO_ALTERADA` | Mudança de título, metadados ou vínculos na representação, sem as mudanças anteriores | IDs compartilhados |
| `DATA_RECUPERACAO_ALTERADA` | Apenas a data de recuperação mudou | IDs compartilhados |
| `INALTERADO` | Nenhuma dessas diferenças | IDs compartilhados |

Cada ID recebe uma categoria pela prioridade acima; campos alterados também são listados. As proporções têm denominadores distintos e não devem ser somadas. Denominador zero produz `null`, sem métricas artificiais de 100%.

Não observado não significa retratação, exclusão ou ausência na literatura. Mudança de hash não comprova alteração de benefício ou dano. Mudança de data não comprova nova coleta. A comparação tampouco certifica que todo conteúdo científico dos documentos foi examinado.

Para as tabelas públicas, são comparados número de linhas, schema e hash lógico. Uma coluna nova em uma tabela vazia é mudança de schema; não é novo resultado clínico. Tabelas privadas `silver_*`, resumos, textos integrais, votos e credenciais não são exportados. Nas diferenças documentais, são expostos somente os títulos e as referências permitidas, além dos nomes dos campos alterados.

## Dashboard e API

No [dashboard](http://127.0.0.1:8501), selecionar a execução atual, abrir **Qualidade e reprodução → Atualizações entre execuções**, selecionar a referência e clicar em **Comparar execuções publicadas**. A seleção inicial fica em branco. A interface apresenta barras, contagens/denominadores, documentos alterados, mudanças das tabelas e downloads.

- `GET /api/public/comparisons?baseline=RUN_ANTERIOR&current=RUN_ATUAL`.
- `GET /api/public/comparisons/artifacts?baseline=RUN_ANTERIOR&current=RUN_ATUAL&name=NOME`.
- Artefatos permitidos: `comparison.json`, `document_changes.csv`, `table_changes.csv` e `manifest.json`.

A API só permite comparar execuções publicadas e verifica a integridade dos artefatos e entradas. Não publica análises nem altera snapshots. Os CSVs protegem células que possam ser interpretadas como fórmulas.

## Comando e reprodução

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data compare --baseline RUN_ANTERIOR --current RUN_ATUAL
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data compare --baseline RUN_ANTERIOR --current RUN_ATUAL --output analytics/data/comparisons/NOVA_PASTA
```

Sem `--output`, o comando imprime JSON. Com a opção, cria os quatro artefatos em uma pasta completa, sem sobrescrever conteúdo diferente. Uma repetição idêntica verifica e reutiliza a pasta existente. O manifesto registra hashes dos artefatos, IDs/hashes das entradas e manifestos das duas execuções, versão do comparador, versão do software e hash do código.

A API calcula a comparação com a versão instalada do comparador. Uma atualização do software pode gerar outro `comparison_id` para o mesmo par de execuções. Para preservar uma reprodução, conservar os artefatos exportados e conferir seus hashes contra o manifesto da mesma comparação.

## Resultado obtido com os pilotos reais

Foram comparadas as publicações da versão 0.6.0 com as da versão 0.8.0, separadamente para cada piloto:

| Corpus | Documentos de origem | Novos | Não observados | Alterados | Tabelas públicas inalteradas |
| --- | --- | --- | --- | --- | --- |
| Piloto clínico | 20 | 0 | 0 | 0 | 24 de 24 |
| Piloto operacional | 50 | 0 | 0 | 0 | 24 de 24 |

Em ambos os casos, a entrada congelada é a mesma. Os resultados confirmam preservação dos dados entre essas versões de software; não demonstram ampliação da pesquisa, novos estudos ou novo benefício clínico. Os dois pilotos não devem ser somados como estudos independentes.

Comparações geradas:

- Piloto clínico: `772a3a15932911a604941f152d74fea4adc93a6f30d5e24b3019b3b429c9ea43`.
- Piloto operacional: `b2cfaf3b97a22e106c658f4cf99d1ef5a3dc60d22460daafe8f426e223677b82`.

Os artefatos compartilháveis estão em [resultados das atualizações](resultados/atualizacoes-0.11/README.md). A evidência operacional privada está em `analytics/target/published-comparison-real-results.json`. As execuções originais, seus relatórios e a curadoria foram preservados.

O piloto clínico permanece com **20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados**. A [revisão independente](ETAPA_PREVIA_REVISAO.md) e a calibração continuam necessárias para avançar na síntese clínica e na coleta completa.

## Validação da entrega 0.11.0

A suíte completa teve **93 testes aprovados**, incluindo oito cenários novos de comparação e as verificações reais de PostgreSQL e Quarto. Foram conferidos resultados conhecidos, denominadores, conjunto vazio, incompatibilidade de escopo, publicação/integridade, proteção dos textos privados, CSV seguro, diferenças de schema sem novos dados, equivalência CLI/API, exportação imutável e interface.

Evidência: `analytics/target/published-comparison-junit.xml`. A matriz contém **93 requisitos, 26 com evidência automatizada nesta execução**. A aprovação desses testes não conclui a pesquisa clínica nem os requisitos futuros do PDF.

O painel foi validado no Chrome com acesso público: exigiu escolha explícita da referência, apresentou os 20 documentos e as 24 tabelas inalteradas e disponibilizou o JSON com SHA-256 idêntico ao exportado pelo comando. A API recusou a comparação entre os protocolos dos dois pilotos. Não houve erro JavaScript nem alteração de decisões científicas. Evidência: `analytics/target/published-comparison-browser-results.json`.
