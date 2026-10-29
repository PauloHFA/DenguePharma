# Relato dos registros — auditoria de datas, versão 0.13.0

Entrega de 28/10/2026. Foi iniciada a parte descritiva do eixo B: disponibilidade declarada de resultados, precisão das datas e intervalos de calendário entre campos do registro. Não foi implementada análise de sobrevivência ou de evolução dos pacientes.

Método congelado: [registry-reporting-audit-1](../spec/reporting/PROTOCOLO_DATAS_REGISTROS.md). A pergunta clínica sobre benefício, sintomas e segurança permanece prioritária e depende da revisão humana.

## Resultados reais

Foram reutilizados exatamente os JSONs congelados da etapa 0.12.0. Não houve nova coleta ou consulta às APIs externas.

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos no corpus | 20 | 50 |
| Registros consolidados de ensaios | 10 | 25 |
| Status declarado `COMPLETED` | 8/10 | 17/25 |
| Indicador `hasResults=true` | 6/10 | 6/25 |
| Pares de datas calculáveis pelo protocolo | 5 | 3 |
| Mediana dos pares calculáveis | 709 dias | 1.288 dias |
| Mínimo–máximo | 469–1.288 dias | 368–2.090 dias |
| Primeiro–terceiro quartil | 709–725 dias | 828–1.689 dias |

Os intervalos vão da data declarada de conclusão primária à data declarada do primeiro depósito de resultados no registro. **Não são tempos de recuperação, tratamento ou sobrevida dos pacientes.** A mediana descreve somente os pares calculáveis; não estima o atraso de todos os registros ou daqueles sem resultados.

No piloto clínico, um dos seis registros com resultados tem a data de depósito tipificada como `ESTIMATED`. O indicador continua verdadeiro, e a data fica preservada, mas esse par não entra no intervalo definido. Os demais registros sem par calculável não recebem zero nem são tratados automaticamente como censurados.

Os pilotos têm protocolos e composições distintos, podem se sobrepor e não devem ser somados ou comparados como mudança longitudinal. Os registros ainda podem conter vacinas, prevenção e outras intervenções inelegíveis para pacientes com dengue estabelecida. Essas estatísticas não avaliam eficácia, qualidade metodológica ou cumprimento legal de prazos de relato.

Artefatos: [CSVs, JSONs, PNGs e manifestos](resultados/relato-0.13/README.md).

## Critérios e estados preservados

O intervalo é calculado somente com status `COMPLETED`, indicador explicitamente verdadeiro, ausência de conflitos, corte diário válido e datas diárias `ACTUAL` de conclusão primária, primeiro depósito e última atualização até o corte. O depósito não pode anteceder a conclusão primária para esse intervalo específico.

Datas parciais permanecem com precisão `MES` ou `ANO`, sem preenchimento de dia. Datas inválidas, estimadas, desconhecidas ou posteriores ao corte ficam identificadas. Uma diferença válida de zero dias é preservada como zero; campo ausente permanece ausente. `hasResults=false`, informação ausente e conflito são categorias separadas.

Observações e referências são preservadas por documento e versão. Valores divergentes entre representações do mesmo NCT geram conflito, sem escolha automática da versão mais recente. Datas e indicadores discordantes ficam para conferência, sem corrigir automaticamente a fonte.

As flags indicam impedimentos para o cálculo definido, não necessariamente erro do registro. Um depósito anterior à conclusão, por exemplo, pode refletir relato parcial. Um status `UNKNOWN` não é declarado como ensaio encerrado ou não encerrado: apenas não atende ao critério de status `COMPLETED`.

A disponibilidade e o status são os da versão armazenada; não há reconstrução histórica de todos os registros no corte. O corte limita os pares do intervalo. Depósito no registro e publicação vinculada são eventos distintos; este módulo não confirma publicações nem lê resultados clínicos para concluir benefício ou dano.

## Implementação e reprodução

Quatro tabelas públicas foram acrescentadas, totalizando **36 tabelas** por execução nova:

- `reporting_registry`: datas, tipos, precisões, estados, flags, intervalo e proveniência.
- `reporting_availability`: frequências e denominadores dos indicadores e precisões.
- `reporting_results_by_status`: tabela cruzada com as quatro categorias de resultado, preservando células zero.
- `reporting_intervals`: n de pares observados, mínimo, máximo, mediana e quartis, sem censura.

O agrupamento de registros por NCT/ID documental foi compartilhado com a análise de patrocinadores, mantendo seus resultados. Os resumos e cruzamentos usam pandas. O gráfico Matplotlib mostra mediana e intervalo interquartil, sem intervalo de confiança ou efeito combinado. Os 32 conjuntos de tabelas da etapa anterior preservaram seus hashes lógicos nas execuções reais.

Executar na raiz do repositório, sobre uma entrada congelada:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --input analytics/data/snapshots/sponsors-0.12/clinical-20.json --expected-hash fb8d1a58ed83ac29dd5391cb4184402e5d46523d7d0bef8db74d0751d8ee4f00
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data report --run RUN_ID --quarto analytics/.tools/bin/quarto.cmd
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data publish --run RUN_ID
```

Novas execuções publicadas:

| Corpus | Run |
| --- | --- |
| Metadados do piloto clínico | `6c72e99616e81bddb006effb674e38b4a973cc3da8c0c6dee64c551f8b5769c2` |
| Metadados do piloto operacional | `61be88f39fb9750c8ac966cc8cca22569e7905571f94dbe321572ff4fdc95d26` |

O relatório Quarto incorpora as tabelas e o PNG em seção separada dos efeitos clínicos. O [dashboard](http://127.0.0.1:8501) disponibiliza o painel em **Ensaios → Relato de resultados — auditoria de datas**. Execuções antigas sem essas tabelas mostram uma mensagem de indisponibilidade; conjuntos vazios não geram estatísticas artificiais.

## Limites e próximos requisitos

O eixo B continua parcial. Não foram implementados Kaplan–Meier, censura, modelos associados, vínculos de publicação conferidos ou análise de discrepâncias registro/publicação. **REQ-ANA-003 permanece planejado**, pois seu aceite exige a análise de sobrevivência validada. MIG-016 cobre somente esta auditoria descritiva.

Os workspaces clínicos não receberam novos eventos, e nenhuma aprovação foi transferida. O piloto clínico original mantém **40 votos iniciais pendentes e zero resultados clínicos revisados**. Para responder sobre medicamentos, ainda é necessário concluir a [revisão independente](ETAPA_PREVIA_REVISAO.md), calibrar a busca e revisar os resultados elegíveis.

## Verificação da entrega

A evidência consolidada contém **109 cenários aprovados**, incluindo os oito testes novos de auditoria de datas e as verificações reais de PostgreSQL/Quarto. Na execução completa, 108 testes passaram e uma asserção antiga ainda exigia eixo B inteiramente planejado. Ela foi atualizada para o estado parcial com Kaplan–Meier pendente; os nove casos afetados foram executados novamente e passaram. Os registros originais foram preservados, e a evidência consolidada está em `analytics/target/reporting-verified-junit.xml`.

A matriz contém **95 requisitos, 28 com evidência automatizada nesta execução**. A validação cobre precisão diária/parcial, tipos estimados, corte, cronologia, zero válido, ausência versus falso, conflitos sem escolha por data, células zero, conjunto vazio, equivalência CLI/API/Parquet/PNG/Quarto, interface e preservação das tabelas anteriores. As verificações com dados reais estão em `analytics/target/reporting-real-results.json`.

O teste no Chrome validou o painel público, os 10 registros, os 8 status COMPLETED, os 5 pares calculáveis e a mediana de 709 dias. Confirmou também que o registro com depósito ESTIMATED mantém o indicador positivo sem receber intervalo, que Kaplan–Meier continua pendente e que PNG, CSV e Quarto estão disponíveis com integridade. Não houve erro JavaScript ou conclusão clínica. Evidência: `analytics/target/reporting-browser-results.json`.
