# Exportações — piloto clínico de 20 documentos

**Nova consolidação:** [pesquisa reproduzível](pesquisa-reprodutivel/README.md), com HTMLs, notebooks executados e manifestos separados por piloto (20 e 50 documentos). Nenhuma das execuções contém resultados clínicos revisados.

Data de referência: 28/10/2026. Software 0.3.0; regras `metadata-calibration-1`.

Execução: `ad0c3d88b792684e14f3b5cc40f60e36deeccb7aac63f97bc01fbbb057b33361`.

Hash da entrada clínica congelada: `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb`.

Os arquivos abaixo são cópias dos artefatos públicos da execução, com metadados estruturados e sem resumos privados, textos integrais, senhas ou tokens:

- [Documentos, fontes e sinais](calibration_documents.csv): 20 documentos deduplicados, identificadores, endereços das fontes e proveniência dos sinais.
- [Sinais por fonte e no conjunto](calibration_signals.csv): numeradores, denominadores e indicação de sobreposição.
- [Tipos declarados de intervenção](calibration_intervention_types.csv): cada registro conta uma vez por tipo; não confundir todos os tipos com fármacos.
- [Execuções das buscas](calibration_searches.csv): consultas e totais informados na coleta original, com os documentos da respectiva fonte presentes no conjunto.
- [Gráfico dos sinais](calibration-signals.png): diagnóstico descritivo, sem decisão automática de exclusão.

Campos com sufixo `_json` preservam listas, referências e relações dentro das células CSV. A exportação usa a mesma neutralização de fórmulas da API pública. Os termos dos sinais correspondem a títulos/metadados; não comprovam elegibilidade, suporte semântico ou eficácia.

Consulte o [relatório de resultados gerais](../RESULTADOS_GERAIS_PESQUISA.md) e a [documentação da calibração](../CONTINUIDADE_CALIBRACAO.md). Os resultados clínicos continuam pendentes de revisão humana. Os totais de buscas não devem ser somados como estudos únicos ou elegíveis.

## Atualizações comparadas em 28/10/2026 — versão 0.11.0

Os [artefatos das comparações](atualizacoes-0.11/README.md) registram a preservação dos pilotos entre as publicações 0.6.0 e 0.8.0, com denominadores e hashes. Não representam nova coleta ou nova conclusão clínica; os arquivos científicos históricos desta pasta permanecem preservados.

## Patrocinadores — atualização de 28/10/2026

Os [resultados descritivos de patrocinadores](patrocinadores-0.12/README.md) disponibilizam CSVs, resumos, gráficos PNG e manifestos para os pilotos de 20 e 50 documentos, separadamente. Foram usadas as mesmas versões documentais, sem nova coleta ou conclusão de eficácia.

## Relato dos registros — atualização de 28/10/2026

Os [resultados de auditoria de datas](relato-0.13/README.md) disponibilizam registros, flags, tabelas cruzadas, intervalos, gráfico e manifesto. São dias de calendário entre campos declarados nos registros, sem censura, Kaplan–Meier ou interpretação como sobrevida de pacientes.

## Referências por PMID — atualização de 28/10/2026

Os [resultados de cobertura bibliográfica](referencias-0.14/README.md) disponibilizam referências por tipo da fonte, candidatos, PMIDs não localizados, gráfico e manifesto. Esses identificadores não são artigos automaticamente incluídos e não comprovam vínculo clínico ou ausência de publicação.
