# Execução local e teste das análises

Data local: 27/10/2026.

## Aplicação em execução

- Interface: http://127.0.0.1:5173
- API: http://127.0.0.1:18080
- Saúde da API: http://127.0.0.1:18080/actuator/health
- PostgreSQL: porta 5434.
- RabbitMQ: porta 5673; painel de administração em 15673.
- MinIO: portas 9000/9001.

As portas 8080 e 5672 já eram usadas por outros serviços. A configuração local foi ajustada no `.env`, sem interrompê-los. O proxy do Vite agora aceita `DENGUEPHARMA_API_TARGET`; as portas externas do RabbitMQ são configuráveis no Compose.

Backend e frontend foram iniciados em segundo plano. PostgreSQL, RabbitMQ, MinIO e worker estão em Docker. A credencial de acesso é a do administrador configurado no `.env`; os segredos não são reproduzidos neste documento. Os logs atuais do backend usam nível INFO.

## Teste real pelo navegador

Foi utilizado Chrome headless com sessão isolada, acessando a interface real e a API local:

1. Login do administrador.
2. Acesso a Relatórios e solicitação de análise descritiva.
3. Processamento pelo worker e conclusão em `COMPLETED`.
4. Exibição do resultado na interface.
5. Downloads da entrada JSON e do pacote ZIP.
6. Verificação dos hashes do manifesto e correspondência entre a entrada baixada e a incluída no pacote.
7. Confirmação de HTTP 410 para métricas experimentais antigas.

Análise criada: `7a57fd01-c0df-4800-a722-ca0f7e3c0a97`.

A base local não tinha estudos no catálogo nem campos extraídos para revisão. O resultado foi `NO_DATA`, com zero estudos, e os indicadores sem denominador ficaram nulos/“sem dados”. Nenhum erro JavaScript de página foi registrado no teste.

Evidências locais, não versionadas, em `backend/target/runtime/`:

- `app-test-result.json`: resultado do teste.
- `analyses-app.png`: captura da tela de resultados.
- `app-dataset.json` e `app-analysis.zip`: downloads reais.

## Exemplo sintético separado

Para exercitar resultados não vazios, foram gerados quatro registros explicitamente sintéticos, sem inserção na base científica. O exemplo cobre HUMANO, DESAFIO_CONTROLADO e IN_VITRO; inclui conflito, ausência de informação, não aplicabilidade e reavaliação pendente.

Foram validados:

- Quatro estudos distintos e contagens por contexto.
- Preservação do conflito.
- Completude de fase no contexto HUMANO: 1 campo presente / 1 estudo aplicável, com 2 estudos totais.
- Categorias sem registros preservadas nos mapas.
- Geração de 24 gráficos e verificação dos hashes dos arquivos.

Relatório: `backend/target/runtime/exemplo-sintetico/resultados/report.html`.

Pacote: `backend/target/runtime/exemplo-sintetico/resultados/bundle.zip`.

Esse exemplo demonstra o funcionamento dos scripts; não constitui evidência científica. Para gerar gráficos científicos na interface, é necessário importar, triar e revisar dados reais.

## Retomar a execução

O `.env` local contém `SERVER_PORT=18080`, `DENGUEPHARMA_API_TARGET=http://127.0.0.1:18080`, `PIPELINE_BACKEND_URL=http://host.docker.internal:18080` e as portas alternativas do RabbitMQ. Recarregue esse ambiente antes de iniciar o backend e consulte o README para os comandos de inicialização.

Não substitua o `.env` existente pelo exemplo: ele contém as credenciais e os endereços desta execução. Artefatos em `target/` podem desaparecer se for executado `mvn clean`.
