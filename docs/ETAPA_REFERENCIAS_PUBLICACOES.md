# Publicações indicadas — cobertura por PMID, versão 0.14.0

Entrega de 28/10/2026. A aplicação passou a auditar as referências declaradas pelos registros e procurar coincidências por PMID entre as publicações já coletadas. Não busca artigos, confirma vínculos clínicos ou altera a curadoria automaticamente.

Método: [registry-publication-reference-audit-1](../spec/reporting/PROTOCOLO_REFERENCIAS.md). Foram usados os mesmos JSONs congelados da etapa 0.12.0, preservando versões, hashes e as análises posteriores.

## Resultados reais

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Registros de ensaios | 10 | 25 |
| Documentos de publicações no corpus | 10 | 25 |
| Registros com referência `RESULT` | 0/10 | 2/25 |
| PMIDs distintos em `RESULT` | 0 | 28 |
| PMIDs distintos em `DERIVED` | 14 | 19 |
| PMIDs distintos em `BACKGROUND` | 57 | 23 |
| PMIDs citados encontrados por PMID nas publicações do corpus | 0 | 0 |
| PMIDs distintos ainda sem coincidência no corpus, união dos tipos | 71 | 69 |

No piloto clínico há seis referências `BACKGROUND` sem PMID utilizável, conservadas como ocorrências com estado de ausência. Os 16 apontamentos `DERIVED` correspondem a 14 PMIDs distintos, distribuídos por cinco registros. No operacional há sobreposição de um PMID entre códigos; por isso os totais por tipo não devem ser somados como publicações únicas.

Os registros clínicos continuam indicando resultados em 6/10 casos, conforme a auditoria anterior, mesmo sem referência tipificada como `RESULT`. **Indicador de resultados no registro, tipo de referência, artigo presente no corpus e vínculo clínico conferido são informações distintas.** Ausência de `RESULT` não demonstra ausência de publicação de resultados.

Os números descrevem os snapshots de conveniência. Eles não medem cobertura da literatura completa, relevância clínica, elegibilidade, eficácia ou segurança. Os pilotos podem se sobrepor e não devem ser somados como estudos independentes. Não é obrigatório recuperar ou incluir todas as referências: muitas podem ser de contexto ou inelegíveis para pacientes com dengue estabelecida.

Artefatos compartilháveis: [resumos, CSVs, gráfico e manifestos](resultados/referencias-0.14/README.md).

## Unidades e critérios

Registros são consolidados por NCT válido ou ID documental. Os códigos `RESULT`, `DERIVED`, `BACKGROUND` e quaisquer outros informados são mantidos separadamente, sem reclassificação por interpretação do artigo.

A coincidência bibliográfica usa apenas PMID no campo próprio. São aceitas strings numéricas positivas, normalizando espaços e zeros à esquerda. Isso valida formato; não verifica externamente a existência do identificador. Não há busca por DOI, título ou semelhança textual. Uma publicação pode estar no corpus com outro identificador e não ser localizada por este método; documentos sem PMID utilizável são contabilizados.

Cada relação válida é registro × código de referência × PMID. Ocorrências repetidas são consolidadas preservando documentos, versões, hashes e índices da referência na lista original. Documentos diferentes com o mesmo PMID contam um identificador para cobertura. Referências sem PMID utilizável mantêm suas ocorrências, sem deduplicação por texto e sem URL fabricada.

Indicadores e denominadores:

- Proporção de registros com referências: registros com o código / todos os registros consolidados.
- Cobertura por PMID: PMIDs coincidentes / PMIDs de formato válido distintos daquele código.
- Entradas sem PMID utilizável: contagem separada das ocorrências ausentes ou inválidas.
- Lista de lacunas: união de PMIDs citados que não coincidiram, mantendo registros e códigos associados.

Denominador zero produz `null`. No piloto clínico, a cobertura por PMID de `RESULT` é não calculável, pois não há IDs dessa categoria; não foi apresentada como 0% ou 100%. Já zero coincidências em 14 PMIDs `DERIVED` é um resultado observado do corpus filtrado.

`CANDIDATO_NO_CORPUS` significa apenas coincidência de PMID. Não comprova identidade clínica, população, desfecho, relevância ou suporte semântico. `NAO_RECUPERADO_NO_CORPUS` significa que o identificador não foi localizado entre as publicações disponíveis, sem afirmar inexistência do artigo ou ausência de evidência na literatura.

Todos os vínculos produzidos pelo módulo têm `automatically_confirmed=false`. Identidade legada compartilhada e `hasResults=true` não confirmam vínculos nem geram referências `RESULT`. As relações de identidade humana e a revisão científica continuam em seus fluxos próprios.

## Implementação e reprodução

Três tabelas públicas foram acrescentadas, totalizando **39 tabelas** por execução nova:

- `publication_reference_links`: referências, estados, candidatos, observações e proveniência.
- `publication_reference_coverage`: contagens e denominadores por código da fonte.
- `publication_reference_missing`: PMIDs para consulta, com códigos e registros associados.

As 36 tabelas anteriores preservaram seus hashes lógicos nas execuções reais. Os textos integrais, resumos, citações livres, contatos e identidades de revisores não são exportados por esse módulo. Os CSVs incluem somente os campos necessários e links PubMed construídos para IDs utilizáveis. Nenhuma fila de coleta é criada.

No [dashboard](http://127.0.0.1:8501), abrir **Qualidade e reprodução → Publicações indicadas — cobertura por PMID**. Os painéis antigos de vínculos por identidade compartilhada permanecem identificados como legados, sem substituir a conferência clínica.

As tabelas, o gráfico PNG e a seção Quarto usam a mesma entrada congelada. Para reproduzir o piloto clínico:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --input analytics/data/snapshots/sponsors-0.12/clinical-20.json --expected-hash fb8d1a58ed83ac29dd5391cb4184402e5d46523d7d0bef8db74d0751d8ee4f00
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data report --run RUN_ID --quarto analytics/.tools/bin/quarto.cmd
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data publish --run RUN_ID
```

| Corpus | Execução publicada |
| --- | --- |
| Piloto clínico | `7a1897915598231a92e7b969185fc13d33e23d88e245d5c015bab26b13984424` |
| Piloto operacional | `7f3b1e541a1c8a2c1a5cc5ab245ae84de7995870b13dabb50aa64f541a83ac90` |

Execuções antigas sem essas tabelas mostram indisponibilidade, sem inventar dados. Os artefatos e relatórios anteriores foram preservados.

## Verificação e continuidade

Foram aprovados **117 testes**, incluindo oito novos casos de cobertura/duplicidade, categorias sobrepostas, identificadores ausentes/inválidos, privacidade, não inferência clínica, equivalência CLI/API/Parquet/PNG/Quarto, compatibilidade da interface e preservação dos conjuntos anteriores. Evidência: `analytics/target/publication-refs-junit.xml`. A execução real está em `analytics/target/publication-refs-real-results.json`.

A matriz contém 96 requisitos: 66 do PDF, 17 MIG e 13 CLN. MIG-017 cobre esta auditoria; vínculos clínicos conferidos, discrepâncias registro/publicação, censura e Kaplan–Meier continuam pendentes. O eixo B permanece parcial.

A curadoria original não recebeu eventos novos: permanecem **40 votos iniciais pendentes e zero resultados clínicos revisados** no piloto clínico. A lista de referências ajuda a conferir o material e calibrar a pesquisa, mas não substitui a seleção humana ou autoriza a inclusão automática de artigos.

A matriz registra **29 requisitos com evidência automatizada** nesta execução; os demais requisitos futuros não foram declarados concluídos. A conferência em Chrome validou o painel público, o aviso sobre ausência do código RESULT, os 71 PMIDs não localizados no piloto clínico, a ausência de confirmação automática e os downloads de PNG/CSV/Quarto. O hash do PNG coincidiu com o arquivo exportado, sem erros JavaScript. Evidência: `analytics/target/publication-refs-browser-results.json`.
