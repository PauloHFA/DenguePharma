# DenguePharma — requisitos v2.0

Data: 27/10/2026. Escopo aprovado: curadoria e ciência de dados descritiva sobre evidências revisadas.

Este documento substitui o escopo obrigatório de avaliação de IA da proposta v1. A proposta `DenguePharma_Proposta_Formal.pdf`, a auditoria e os registros das etapas anteriores permanecem históricos. Não se declara que todos os requisitos operacionais históricos já foram homologados.

## Objetivo e questões de análise

Organizar um corpus rastreável de intervenções farmacológicas relacionadas à dengue e descrever sua cobertura, distribuição e qualidade de preenchimento. Os scripts devem produzir resultados reproduzíveis a partir de dados revisados, sem chamadas a modelos de IA.

- Quais substâncias e contextos estão representados no corpus filtrado?
- Como os estudos se distribuem por finalidade, desenho, fase e sorotipo?
- Quais combinações de substância, contexto e categoria de desfecho não têm registros nesse corpus?
- Quais campos estão preenchidos, explicitamente ausentes, pendentes de revisão ou conflitantes?
- Quais anotações têm identificadores, versões e localizadores documentais registrados?

As hipóteses H1/H2/H3 sobre assistência por IA, crossover, ablação, redução de tempo e não inferioridade ficam fora do MVP v2. Não calcular precisão/F1/fidelidade a partir de aprovação humana. Esses conceitos só poderão voltar com outra proposta e referência metodológica apropriada.

## Requisitos funcionais

| ID | Requisito |
| --- | --- |
| RF-01 | Protocolos versionados com fontes, estratégia, elegibilidade e corte temporal; execuções referenciam a versão. |
| RF-02 | Coleta pelas APIs de fontes bibliográficas e de ensaios, com deduplicação, checkpoint e recuperação. Essas APIs permanecem no escopo. |
| RF-03 | Identidade química e vínculos entre estudo/documentos; ambiguidades exigem curadoria e fusões devem ser reversíveis. |
| RF-04 | Triagem independente e adjudicação, preservando decisões e classificações de contexto/finalidade. |
| RF-05 | Extração conservadora por regras com suporte literal e estados explícitos de ausência. Informação não reconhecida não pode ser completada por inferência. |
| RF-06 | Revisão humana com antes/depois e proveniência. Publicação de campos críticos exige adjudicador autorizado. |
| RF-07 | Catálogo com contexto, limitações e status visíveis; manutenção dos fluxos já existentes. |
| RF-08 | Comparação contextualizada, sem ranking de medicamentos ou síntese automática de eficácia. |
| RF-09 | Relatórios e snapshots auditáveis, preservando os relatórios anteriores. |
| RF-10 | Versionamento de fontes e fila de reavaliação; análises congeladas não mudam após atualização/retratação posterior. |
| RF-11 | Outbox, RabbitMQ, Inbox e jobs com lease, retentativas e quarentena. |
| RF-12 | Autenticação, autorização, auditoria, respeito a licenças e exportação reproduzível. |
| RF-13 | Construir snapshot analítico exclusivamente com classificações consolidadas e valores científicos individualmente aprovados/publicados. |
| RF-14 | Executar o mesmo módulo Python por comando e pela aplicação, sem depender de API de IA paga. |
| RF-15 | Produzir inventário descritivo, distribuições, mapas de lacunas, completude e rastreabilidade estrutural. |
| RF-16 | Consultar execução, tabelas e gráficos e baixar pacote reproduzível autenticado com hashes e versões. |
| RF-17 | Retirar os comandos experimentais v1 da interface e responder HTTP 410 nas rotas antigas, sem apagar registros. |

## População, unidade e critérios do snapshot

- Unidade de contagem: `study_id`, uma vez por análise. Vários relatos ou documentos não multiplicam o estudo.
- Elegíveis: estudos ativos, não demonstrativos, não absorvidos, incluídos em `INCLUIDO_NUCLEO`, `INCLUIDO_SEM_RESULTADO` ou `CAMADA_COMPLEMENTAR`, com pelo menos um campo aprovado e publicado.
- Contexto e finalidade vêm da classificação consolidada da triagem. Os demais valores vêm de `extracted_field` aprovado/publicado, nunca de resumos não revisados de `study`.
- Preservar referências de campo, documento, versão, origem, hash e localizador. O snapshot não exporta resumos, textos integrais, citações literais ou dados pessoais de revisores.
- Reavaliação pendente é um sinal visível. O snapshot mantém a evidência aprovada na data da solicitação; não se rotula silenciosamente como atualizada.
- Divergências aprovadas entre documentos ou versões geram `CONFLITO`. Não selecionar automaticamente o último valor. Aprovações concordantes não multiplicam categorias ou estudos.

## Dicionário analítico inicial

Versão: `descriptive-v2.0`. Schema de entrada: `2.0`.

| Campo | Origem |
| --- | --- |
| context, purpose | Classificação consolidada da triagem |
| substance | Campo revisado `substance`; aliases compatíveis: `substance_name`, `substance_published_name` |
| design, phase, serotype, outcome_category | Campos revisados com esses nomes |

Uma substância vinculada apenas ao resumo de `study` não é promovida automaticamente a valor analítico. Combinações/sorotipos compostos são mantidos como categorias conforme revisados, sem dividir participantes ou inventar componentes. Normalização adicional exige mudança versionada do dicionário.

Estados preservados: `PRESENTE`, `NAO_INFORMADO`, `NAO_APLICAVEL`, `NAO_EXTRAIDO`, `INCERTO`, `NAO_HOUVE_EVENTO`. Estados derivados exclusivos da análise: `SEM_REVISAO` e `CONFLITO`; eles não reescrevem os campos de origem.

Os filtros por substância, contexto, finalidade, desenho, fase e sorotipo são aplicados aos valores revisados/resolvidos. Filtros não selecionam um valor arbitrário dentro de um conflito.

## Indicadores e interpretação

1. **Inventário por contexto:** contagem e proporção no corpus filtrado; a comparação é descritiva de cobertura.
2. **Distribuições:** campo/categoria/estado por contexto, sempre com contagem e denominador.
3. **Lacunas:** substância × contexto e substância × categoria de desfecho. Manter categorias previstas sem registros, inclusive zeros, e separar contextos/camadas.
4. **Completude:** número de estudos com valor `PRESENTE` dividido pelo total de estudos aplicáveis no contexto. Excluir apenas `NAO_APLICAVEL` do denominador; pendentes e conflitos permanecem no denominador e são explicitados.
5. **Rastreabilidade:** proporção de anotações com identificador e versão/hash; localizadores e combinação dos três são calculados entre anotações `PRESENTE`. Mostrar numerador/denominador, inclusive quando incompletos.

Denominador zero produz valor nulo/“sem dados”, nunca 100%. Ausência não vira zero clínico. “Não houve evento” mantém seu estado próprio. Um localizador registrado não prova suporte semântico. A unidade de rastreabilidade é a anotação; a unidade de cobertura/completude é o estudo.

Humanos, desafio controlado, animais, in vitro e in silico permanecem contextos separados. Não somar amostras, combinar efeitos ou concluir superioridade terapêutica. Zero registros em uma célula significa apenas zero no corpus consultado, sem comprovar inexistência de evidência na literatura.

## Execução, artefatos e acesso

- Solicitação por pesquisador/administrador; consulta e download por usuários autenticados.
- Snapshot imutável guarda entrada JSON, representação canônica, filtros, versão do dicionário e hash SHA-256. A execução é vinculada a ele.
- Evento `AnaliseSolicitada`, job `ANALYZE_EVIDENCE`; mesma política de lease, idempotência e recuperação do pipeline existente.
- Artefatos: entrada JSON, dataset tabular CSV, distribuições, completude, lacunas e rastreabilidade em CSV, resumo JSON, relatório HTML, gráficos PNG e manifesto. Um ZIP reúne esses arquivos.
- Manifesto registra hash da entrada, versão do script/dicionário, configuração, dependências e hashes dos artefatos. Mesma entrada e versões reproduzem os mesmos resultados numéricos.
- Armazenamento por hash no MinIO. Uma cópia transacional limitada dos artefatos no banco atende aos downloads autenticados. Gravação parcial não aparece como execução concluída.
- Pacotes são limitados a 32 MiB comprimidos/descompactados e 256 arquivos; nomes, hashes e correspondência com a entrada são validados. Limites excedidos geram falha, não resultados truncados.

Rotas novas: `POST /api/analyses`, `GET /api/analyses`, `GET /api/analyses/{id}` e `GET /api/analyses/{id}/artifacts?name=...`.

Rotas retiradas: `POST /api/experiment/split`, `/allocate`, `/sessions` e `GET /api/experiment/metrics` retornam `410 Gone`. Tabelas históricas não são removidas.

## Aceite e limites

Validar contagens conhecidas, vários relatos, dados excluídos/demonstrativos/retratados, conflitos, estados ausentes, denominadores zero, entradas vazias, filtros, permissões, imutabilidade, reentregas e recuperação. Comparar execução por comando com execução pelo worker e executar teste completo com PostgreSQL, RabbitMQ, MinIO e Python reais.

Ficam fora: modelos de IA obrigatórios, extração abrangente de PDF/OCR/tabelas, meta-análise, ranking de eficácia e recomendação terapêutica. A documentação histórica continua registrando pendências operacionais gerais, como backup/restauração, homologação de carga e acessibilidade completa.
