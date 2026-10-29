# Plano técnico e decisões

## Arquitetura

Monólito modular Python, FastAPI para serviços, Streamlit para consulta e Quarto para relatórios. PostgreSQL continua como fonte transacional, com Parquet/DuckDB para dados derivados. RabbitMQ e MinIO permanecem na arquitetura futura. Não se iniciam novos consumidores nesta entrega.

O projeto novo vive em `analytics/`, no mesmo repositório. Java/React, suas migrations e o pacote de workers continuam operacionais. Esta fase não substitui coleta, revisão, autenticação, publicação de campos ou fila por implementações incompletas.

## Primeiro marco

- Entrada por JSON v3 ou leitura PostgreSQL consistente, `REPEATABLE READ READ ONLY`, verificando o hash dos bytes canônicos.
- Preparação modular adaptada por equivalência: identidade, documentos, diagnóstico e agregação revisada.
- Bronze privado; prata e ouro com schemas Arrow explícitos e Parquet zstd. O DuckDB materializa essas mesmas tabelas para consulta somente de leitura.
- Run endereçado por conteúdo/configuração/código/dependências, commit por renomeação de diretório temporário e verificação de integridade ao reutilizar.
- Manifesto privado preserva origem e arquivos; manifesto público lista somente derivados autorizados. Entrada bronze, banco DuckDB e prata não são baixáveis pela API.
- Publicação local explícita por CLI. FastAPI não oferece escrita, administração ou credencial de acesso ao PostgreSQL legado.
- Streamlit consulta a FastAPI, sem cache global de dados privados. Página pública sem login; curadoria segue protegida no legado.
- Quarto renderiza HTML sobre tabelas geradas da mesma base DuckDB. Valores externos são escapados; código de documentos nunca é executado. Relatório e seu manifesto são separados do run imutável.

## Compatibilidade e limites

Snapshots v3 antigos não serão reescritos. Os 50 documentos e decisões pendentes permanecem rastreáveis; um panorama revisado vazio permanece vazio. A preparação nova não tem o limite de ZIP do backend Java; consulta paginada até 1.000 linhas por chamada e downloads por tabela.

Reprodução exige versões fixadas: os hashes lógicos e dos Parquet são comparados em preparações independentes. O arquivo binário DuckDB e o HTML Quarto têm hashes de integridade, mas não se presume igualdade binária entre versões/plataformas distintas. O manifesto registra versões e os fontes usados na preparação; o relatório guarda QMD renderizado e versão do Quarto.

## Decisões metodológicas antes dos próximos eixos

- A, B, C e D são obrigatórios no objetivo completo; E opcional. Isso resolve a menção a C como contingente na seção de riscos do PDF, sem reduzi-lo silenciosamente.
- Desafio controlado é contexto; não é fundido com finalidade profilaxia/tratamento/sintomático.
- Separar mediana de tempo (pergunta inicial) da razão de médias geométricas do modelo proposto; congelar o estimando antes do experimento.
- Carga e pesquisa exigem mesma janela, geografia e definição de caso. Sem dado não vira zero; inscritos globais não são distribuídos integralmente entre países.
- Registro e publicação podem ter datas divergentes; regras de evento, censura e vínculos devem ser especificadas antes da análise de sobrevivência.
- O piloto operacional pode apoiar desenvolvimento e seleção da calibração; não vira referência adjudicada ou teste independente automaticamente.

Não foram escolhidos provedor de IA, orçamento, amostra confirmatória ou margem de não inferioridade nesta fundação. Essas decisões pertencem ao eixo D e não impedem os módulos de dados somente de leitura.
