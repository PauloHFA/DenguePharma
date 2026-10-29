# Continuidade — calibração e resultados gerais

Data: 28/10/2026. Versão: **0.3.0**. Referência: [plano atual](PLANO_ATUAL_SINTESE_CLINICA.md).

## Entrega

O diagnóstico do corpus agora identifica sinais literais de metadados que precisam de conferência: menções a vacinas, desafio controlado, vetores, revisões, rastreio/diagnóstico e prevenção. Cada sinal guarda o documento de origem, o campo e o termo correspondente. As regras têm versão `metadata-calibration-1`.

Esses sinais **não classificam elegibilidade nem geram exclusões ou aprovações**. Um artigo de tratamento pode mencionar prevenção ou vacinas; isso não o exclui automaticamente. Documentos sem sinal também precisam de revisão humana. O diagnóstico usa títulos e metadados estruturados disponíveis, sem inferir campos científicos ausentes ou incorporar resumos privados aos arquivos públicos.

Foram acrescentadas quatro tabelas aos conjuntos Parquet/DuckDB:

| Tabela | Unidade e finalidade |
|---|---|
| `calibration_documents` | Documento deduplicado, referências, identificadores, endereço da fonte, intervenções declaradas, sinais e situação de revisão |
| `calibration_signals` | Documentos com cada sinal, por fonte e no conjunto, com numerador, denominador e sobreposição |
| `calibration_intervention_types` | Registros por tipo de intervenção declarado, contando cada registro uma vez por tipo |
| `calibration_searches` | Consulta, execução, total informado pela busca e documentos da respectiva fonte presentes no conjunto |

Tipos de intervenção permanecem separados: `DRUG`, `BIOLOGICAL`, `OTHER` e demais códigos declarados não são todos chamados de substâncias farmacológicas. `BIOLOGICAL` pode incluir vacinas. O tipo `DRUG` também não confirma tratamento de pacientes com dengue estabelecida.

O dashboard ganhou a aba **Resultados gerais**, com diagnóstico, tabelas, figura exportável, fontes e downloads. O relatório Quarto incorpora a calibração em seção própria, separada dos efeitos clínicos. O novo artefato `research_findings.md` apresenta resultados gerais da execução, sem texto integral ou conclusões automáticas de benefício.

A curadoria protegida ganhou **triagem por campos**: estudo, contexto, população, gravidade, fase, finalidade, desenho, presença de intervenção farmacológica, intervenções, decisão e justificativa. Os campos começam incertos ou recuperam somente o voto anterior do próprio revisor. Sinais de metadados e votos alheios não preenchem o formulário. A API continua exigindo revisores independentes, base atual e terceiro adjudicador para conflitos. As demais ações avançadas continuam disponíveis por JSON orientado por contrato.

## Como consultar

1. Abrir `http://127.0.0.1:8501/` e selecionar a execução mais recente do piloto clínico.
2. Consultar a aba **Resultados gerais** e as fontes dos documentos sinalizados.
3. Baixar o resumo Markdown, os CSVs ou o relatório HTML.
4. Para revisar, abrir a curadoria protegida, autenticar e usar **Triagem por campos — revisão humana**, depois de ler a fonte permitida.

As novas execuções têm **29 tabelas**. O preparo utiliza os mesmos comandos `clinical-freeze`, `verify`, `report` e `publish` já documentados no [guia operacional](IMPLEMENTACAO_SINTESE_CLINICA.md). Snapshots e execuções anteriores não foram alterados; versões antigas informam a indisponibilidade das tabelas novas.

API pública adicional: `/api/public/analyses/{run}/tables/calibration_documents`, demais tabelas de calibração e `/artifacts?name=research_findings.md`. Os PNGs continuam listados no manifesto. Fontes privadas e decisões de revisão permanecem protegidas.

## Dados e resultados obtidos

A entrega reprocessou os mesmos snapshots preservados, sem executar nova coleta ou alterar o protocolo científico. O conjunto principal continua sendo o piloto clínico de **20 documentos — 10 publicações PubMed e 10 registros ClinicalTrials.gov**. O piloto anterior de 50 documentos permanece separado; não somar os dois como estudos únicos.

No piloto clínico, os metadados indicam:

- 8/10 registros de ensaio intervencionais e 2/10 observacionais, sem inferir randomização apenas desses códigos.
- 8/10 registros concluídos, 1/10 ativo sem recrutamento e 1/10 encerrado antecipadamente.
- 6/10 registros com resultados disponíveis na fonte; isso não confirma benefício nem elegibilidade clínica.
- 3/10 publicações identificadas como revisão nos metadados.
- 17/20 documentos com pelo menos um sinal de conferência; categorias sobrepostas, sem exclusão automática.
- 6/20 com menção a vacina, 2/20 a desafio controlado, 3/20 a vetores, 3/20 a revisão, 1/20 a rastreio/diagnóstico e 10/20 a prevenção.
- Tipos de intervenção nos registros: `BIOLOGICAL` em 8/10, `DRUG` em 1/10 e `OTHER` em 2/10, com sobreposição.
- **Zero resultados clínicos revisados**, sem conclusão de benefício, dano ou inconclusão atribuída a medicamentos.

As buscas originais informaram 7.765 resultados no PubMed e 322 no ClinicalTrials.gov, mas o piloto reteve apenas 10 documentos por fonte. Esses números são históricos da execução registrada, não totais atuais verificados, estudos únicos ou estudos elegíveis. A fração recuperada não mede representatividade nem sensibilidade.

O achado metodológico é que a busca ampla e a amostragem por primeiros registros exigem calibração antes de uma comparação de tratamentos. Não se pode interpretar os 17 documentos sinalizados como 17 exclusões, nem os três sem sinal como três estudos elegíveis.

O [relatório de resultados gerais](RESULTADOS_GERAIS_PESQUISA.md) e os [arquivos exportados](resultados/README.md) documentam a execução e permitem conferir os números. REQ-CLN-006 permanece pendente: referências sentinela, leitura de textos permitidos, revisão independente, calibração e corpus clínico final ainda exigem execução científica.

## Validação

**30 testes aprovados**, com PostgreSQL e Quarto reais. Novos cenários cobrem contagem deduplicada, sobreposição de sinais, ausência de classificação automática, tipos de intervenção, privacidade, conjunto vazio, exportação pública, compatibilidade com execuções antigas e envio da triagem com hash atual. A equivalência CLI/exportador continua verificada.

A matriz passa a ter 85 requisitos: 66 originais, 12 MIG e 7 CLN. REQ-CLN-007 acompanha o diagnóstico de metadados; a verificação de software não representa aprovação da calibração científica. Nenhum voto ou julgamento clínico foi criado nesta entrega.

Verificação no Chrome desktop/mobile: aba Resultados gerais, contagens 20/10/10/0, 17 documentos sinalizados, CSV, Markdown e Quarto acessíveis; curadoria sem token responde 401. A execução histórica continua acessível e retorna 404 apenas para a tabela nova que ainda não possuía. Nenhum erro JavaScript observado. Registro operacional e capturas ficam em `analytics/target/calibration-browser-results.json` e `analytics/target/calibration-dashboard*.png`, ignorados pelo Git.
