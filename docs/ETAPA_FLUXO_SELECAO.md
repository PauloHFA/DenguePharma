# Resumo auditável da seleção — versão 0.16.0

Entrega de 28/10/2026. A curadoria agora apresenta contagens da seleção e permite documentar motivos principais de exclusões já resolvidas. O [contrato e os critérios](../spec/clinical/MOTIVOS_EXCLUSAO.md) registram o escopo, as unidades, as categorias e as limitações.

## Onde está

No [dashboard local](http://127.0.0.1:8501/), abrir **Curadoria clínica — acesso protegido**, entrar com a própria conta e selecionar **Fluxo da seleção e motivos de exclusão**. O painel permite consultar a situação e preparar o download de um resumo agregado JSON. O acesso permanece autenticado; os dashboards públicos continuam abertos.

Adjudicadores e administradores podem selecionar uma exclusão resolvida, escolher explicitamente seu motivo principal, justificar o critério e confirmar a conferência humana. A interface não oferece formulário de motivo quando não há exclusão resolvida. Revisores não recebem a lista de decisões individuais desse painel; consultam as contagens agregadas.

## O que mudou

- Categorias padronizadas para população, contexto, intervenção, desenho e outro critério explícito do protocolo.
- Registro append-only da anotação, sem modificar a triagem ou as justificativas antigas.
- Detecção de anotação desatualizada após mudanças documentais, de identidade, dos votos ou da adjudicação.
- Contagens separadas para documentos e identidades de estudo, com estados e motivos que fecham nas respectivas unidades.
- Exportação privada agregada com hashes e versão do dicionário, sem votos, nomes, justificativas livres ou textos de fontes.

Não há inferência automática de motivo. Exclusões antigas sem anotação permanecem como **sem motivo atual**, mesmo que tenham justificativa livre. A falta de texto integral não é categoria de exclusão. Documentos agrupados sob uma identidade não são automaticamente duplicados.

## Resultado dos pilotos reais

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos preservados | 20 | 50 |
| Identidades atuais | 20 | 50 |
| Seleção pendente | 20 | 50 |
| Inclusões resolvidas | 0 | 0 |
| Exclusões resolvidas | 0 | 0 |
| Avaliações independentes faltantes | 40 | 100 |
| Novos votos ou motivos registrados na validação | 0 | 0 |

As consultas repetidas produziram resultados iguais e não modificaram os eventos. Os zeros de inclusão/exclusão significam que ainda não existem decisões resolvidas nesses espaços; não demonstram ausência de estudos elegíveis. Os pilotos não foram somados.

Os totais de registros identificados, duplicados removidos e registros triados da revisão completa permanecem **não reconstruídos (`null`)**. O painel não é um fluxograma PRISMA completo e não apresenta um piloto limitado como seleção final da literatura. O requisito SEL-004 do PDF continua planejado.

## Validação

Oito casos novos verificam unidades, ausências, cegamento, permissão, seleção resolvida, correções de motivos, fontes/votos/identidades/adjudicações alterados, exportação e confirmação explícita no formulário. Os casos usam exclusivamente dados sintéticos. Evidências locais, fora do Git:

A bateria completa passou: **131 testes**, incluindo PostgreSQL e Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada; CLN-001 recebeu os oito cenários adicionais. No Chrome, o login, o painel, o download agregado e a saída da curadoria foram conferidos, sem erro de página ou gravação de decisões. O JSON baixado coincidiu com a consulta direta do módulo. As publicações 0.14.0 tiveram a integridade novamente confirmada.

- `analytics/target/selection-flow-full-junit.xml`: bateria completa.
- `analytics/target/selection-flow-real-results.json`: consultas somente de leitura nos dois espaços reais.
- `analytics/target/selection-flow-browser-results.json`: verificação do painel e download no navegador.

## Situação científica

O próximo marco continua sendo a seleção independente dos estudos reais, seguida da calibração e extração revisada. Nenhum voto foi registrado em nome de uma pessoa e nenhum resultado clínico foi aprovado nesta entrega. A pesquisa ainda não responde quais medicamentos beneficiam pacientes com dengue.

Os [relatórios e notebooks existentes](resultados/pesquisa-reprodutivel/README.md) continuam vinculados às publicações 0.14.0. Não foram refeitos para incorporar decisões inexistentes. O incremento 0.16.0 afeta a curadoria privada e sua documentação.
