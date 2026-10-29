# Validação local — ciência de dados v3

Data local: 27/10/2026, America/Sao_Paulo. Este registro descreve validação operacional; não certifica revisão científica do corpus.

## Coleta e execução reais

- Protocolo: `7dbd3866-0b8f-4e80-bdf5-756e281ac90b`.
- Corte solicitado: `2026-10-27`.
- Piloto: 25 registros do PubMed e 25 do ClinicalTrials.gov, sem dados demonstrativos.
- Totais informados pelas buscas: 9.342 resultados PubMed e 322 ClinicalTrials.gov. São totais das estratégias, não contagens de estudos farmacológicos elegíveis.
- Execução publicada final: `5dc0c29f-234e-4ec4-8f32-91459358b472`.
- Script: `corpus-3.0.2`; entrada `3.0`; dicionário `corpus-v3.0`.
- Hash da entrada: `6cd0c7c07456e66a70ecbe3aa49de40c2e11977449177edde68f8af53fcf264e`.
- Resultado: 50 documentos, 25 publicações, 25 registros de ensaios e zero estudos com campos científicos revisados.
- Pacote: 33 arquivos, incluindo 19 tabelas CSV e oito figuras PNG. O objeto ZIP também está no MinIO, totalizando 34 objetos desta execução.

O corpus contém registros que podem ser excluídos na triagem, incluindo vacinação e controle vetorial. Dois registros apresentam ano bibliográfico posterior ao corte e estão sinalizados para conferência, sem alteração automática de seus valores. Singapore permanece na tabela de países e aparece como não representado na cartografia de baixa resolução.

## Verificações

- Testes Java, incluindo PostgreSQL, permissões, snapshots, coletas, particionamento PubMed e campos científicos aprovados: 57 aprovados, sem falhas, erros ou testes ignorados nos relatórios consolidados.
- Teste de pipeline com servidor HTTP, RabbitMQ, MinIO e worker Python reais, em recursos isolados: aprovado para análises v2 e v3.
- Testes Python: 38 aprovados.
- Testes frontend: 21 aprovados; build TypeScript/Vite aprovado.
- Reprodução usando os módulos recuperados de `reproduction_source.json`: resumo numérico e as 19 tabelas CSV coincidiram com os artefatos gerados pelo worker em Docker.
- SHA-256 dos 34 objetos no MinIO: verificados.
- Chrome sem sessão: abertura do dashboard, troca de abas, filtros da tabela, links de fontes, carregamento das figuras e download do ZIP verificados.
- Layout móvel: sem transbordamento da página; tabelas têm rolagem horizontal local.
- Acesso anônimo à API de importação: HTTP 401, mantendo operações protegidas.

## Artefatos locais

Arquivos de execução ficam em `backend/target/runtime/`, ignorados pelo Git:

- `piloto-ds3/dataset.json`, `summary.json`, `bundle.zip` e `pilot_review.csv`;
- `coleta-piloto-ds3.json` e `analise-piloto-ds3-final.json`;
- `reproducao-ds3-resultado.json` e diretórios da reprodução congelada;
- `dashboard-ds3-browser.json`, capturas desktop/móvel e ZIP baixado pelo navegador.

Interface local: `http://127.0.0.1:5173/`. Backend: `http://127.0.0.1:18080`.

## Pendências científicas

A revisão identificada dos 50 registros ainda está pendente. Não foram atribuídas aprovações fictícias, não foi executada a coleta completa e não foram feitas conclusões clínicas. A planilha do piloto deve conferir preparação, elegibilidade, variedade dos estudos e divergências temporais, orientando ajustes antes da ampliação. A triagem e a publicação de campos científicos continuam nos fluxos protegidos.

## Registro final

O [registro consolidado das alterações](ALTERACOES_CONSOLIDADAS.md) reúne o histórico das etapas, o escopo vigente, os contratos implementados e os limites desta validação.
