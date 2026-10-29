# DenguePharma — requisitos v3: ciência de dados e dashboards

Data: 27/10/2026. Substitui o escopo obrigatório v2 para a apresentação da aplicação; documentos anteriores e snapshots permanecem históricos.

## Perguntas e método

Pesquisa aplicada com revisão de escopo, análise exploratória e mapeamento de evidências. O [PRISMA-ScR](https://www.prisma-statement.org/scoping) orienta o relato, sem substituir o protocolo de execução.

1. Panorama: o que foi publicado e registrado sobre medicamentos e compostos relacionados à dengue?
2. Cobertura: quais substâncias, contextos, populações e desfechos estão representados nos estudos incluídos?
3. Qualidade documental: quais informações estão disponíveis, revisadas, integradas e rastreáveis?

Incluir medicamentos/compostos, profilaxia farmacológica, tratamento e manejo sintomático; excluir vacinação, controle vetorial e diagnóstico sem intervenção farmacológica na triagem. Manter humanos, desafio controlado, animais, in vitro e in silico separados. O corpus coletado pode conter itens inelegíveis, explicitamente pendentes; não classificá-los automaticamente como elegíveis. Não aplicar uma exclusão lexical indiscriminada de “vaccine”, que perderia documentos mistos.

IA experimental, meta-análise, ranking de tratamentos, previsão de eficácia e testes de significância exploratórios permanecem fora desta etapa. Completude não é avaliação de risco de viés. Frequência não é eficácia ou aprovação regulatória.

## Requisitos de execução

| ID | Comportamento |
| --- | --- |
| DS-01 | Protocolos versionados registram estratégias, elegibilidade, corte temporal, estágio piloto/completo e limite de registros. |
| DS-02 | PubMed e ClinicalTrials.gov são o núcleo; PubChem auxilia identidade química; Europe PMC/PMC e fontes complementares preservam seus limites técnicos e de licença. |
| DS-03 | Cada versão reencontrada pertence à execução de busca que a encontrou, mesmo sem novo documento. Coletas históricas anteriores à migração não recebem proveniência inventada. |
| DS-04 | Snapshot v3 separa documentos coletados de estudos e campos aprovados. Não exporta resumos, textos integrais, contatos ou credenciais. |
| DS-05 | Deduplicar documentos por identificadores exatos; preservar referências e conflitos. Não fundir estudos por semelhança textual ou por referência bibliográfica automática. |
| DS-06 | Representar múltiplas intervenções, países, classificações e vínculos por listas/relações. Cada registro conta uma vez por categoria; percentuais sobrepostos podem exceder 100%. |
| DS-07 | Separar ano de publicação/início de ensaio e inscrição prevista/efetiva. Não somar participantes. |
| DS-08 | Gerar distribuições, séries temporais, mapas, histogramas, disponibilidade por fonte, vínculos confirmados/candidatos e comparação de snapshots. |
| DS-09 | Usar valores revisados nos mapas científicos; metadados da fonte permanecem identificados como tal. Ausências/conflitos não recebem valores inferidos. |
| DS-10 | Estado “não aplicável” explícito não entra no denominador de completude. Denominador zero gera nulo/“sem dados”. |
| DS-11 | CLI e aplicação usam o mesmo despachante Python; notebook importa as rotinas e não duplica transformações. |
| DS-12 | Congelar entrada e registrar hashes, dependências, scripts, configuração, dicionário e referências. Produzir ZIP, CSV, JSON, HTML e PNG. |
| DS-13 | Publicação explícita, por pesquisador/administrador, somente após conclusão. Leitura dos artefatos publicados é pública; operações continuam autenticadas. |
| DS-14 | Aplicação abre no dashboard sem login; mantém acesso separado à curadoria. |
| DS-15 | Piloto de até 50 registros, distribuído entre as duas fontes, gera planilha pendente. Coleta completa por CLI exige revisão identificada do piloto correspondente. |

## Dicionário e interpretação

Entrada `schemaVersion=3.0`, `dictionaryVersion=corpus-v3.0`; snapshots v2 continuam executáveis. Documentos têm identidade própria, versões, hash, fonte e vínculos ao estudo. Publicação e registro do mesmo estudo não são documentos duplicados. Só vínculos confirmados entram na cobertura de integração.

Os nomes de intervenções recebem limpeza de espaços e caixa. Aliases exatos, associados a um único CID no cadastro normalizado via PubChem, podem resolver a identidade; ambiguidades permanecem explícitas. Indexação química do PubMed é preservada como indexação, sem promovê-la a intervenção estudada. Combinações não são divididas por inferência.

Disponibilidade de resultados no registro (`hasResults`) não equivale a publicação vinculada. Fase `NA` ou fase ausente em estudo explicitamente observacional não é considerada informação faltante aplicável. Campos sem revisão continuam pendentes.

Documentos coletados são a unidade do panorama; registros deduplicados são a unidade do perfil de ensaios; `study_id` é a unidade dos mapas revisados. O mapa geográfico usa país de realização, nunca afiliação de autor. Países sem correspondência cartográfica são relacionados no resumo, sem desaparecer das tabelas.

Comparações de snapshots identificam novos documentos, hashes alterados e documentos não observados. Ausência no snapshot posterior não demonstra retratação. A comparação registra se o protocolo é o mesmo; mudanças entre protocolos exigem interpretação da cobertura.

## Validação e limites

Testar contagens conhecidas, deduplicação, fusões, demonstrações/retratações, permissões, estados ausentes, conflitos, múltiplos países/intervenções, vínculos candidatos, hashes e execução por CLI/worker. Executar teste com PostgreSQL, RabbitMQ e MinIO reais e uma coleta piloto real.

O piloto inicial usa os primeiros registros retornados por fonte: amostra de conveniência para testar preparação, não estimativa representativa da literatura. Sua revisão deve verificar variedade de desenhos e recomendar ajustes antes da ampliação. A planilha de validação não substitui as decisões científicas de triagem e adjudicação da aplicação.

A disponibilidade dos campos revisados limita o mapa científico inicial. População, comparador e limitações podem exigir leitura documental; sua ausência não autoriza inferência. Obtenção automática de textos integrais/OCR e conectores brasileiros completos não são declarados implementados por esta etapa. Nenhuma API paga de IA é necessária.

## Atualização de escopo — 28/10/2026

Este documento passa a ser histórico. O novo PDF Analytics foi adotado e está rastreado na [especificação SDD](../spec/README.md), com IA experimental novamente no objetivo completo, em etapa posterior. A [fundação Python](MIGRACAO_ANALYTICS.md) usa FastAPI/Streamlit/Quarto em paralelo ao legado e preserva os dados, sem declarar curadoria científica concluída.
