# Etapa 2 — Pipeline de documentos e relatórios

Data: 27/10/2026. Complementa a [etapa 1](IMPLEMENTACAO_ETAPA_1.md).

Atualização de escopo: os [Requisitos v2](REQUISITOS_V2.md) e a [etapa 3](IMPLEMENTACAO_ETAPA_3.md) acrescentam análises descritivas e retiram IA obrigatória. Este documento preserva o registro da etapa 2.

## Entregue e validado

O fluxo `importação → Outbox → RabbitMQ → worker Python → MinIO → extração em rascunho` está conectado. Relatórios também são processados como tarefas: PDF, CSV e JSON são armazenados com seus hashes e manifesto. Nada é publicado cientificamente pelo worker.

O primeiro extrator é determinístico, sem chamadas a IA ou necessidade de chave externa. Reconhece sorotipo e tamanho amostral em texto compatível com as regras existentes; mantém estados de ausência nos outros casos. Registros ClinicalTrials e outros metadados podem produzir abstenções. Isso não representa extração completa dos campos científicos, leitura de PDFs, OCR ou tabelas.

### Garantias implementadas

- A importação preserva o JSON canônico antes da normalização do PostgreSQL, mantendo os bytes necessários à conferência do hash.
- O publicador reserva eventos por token/tempo, publica mensagem persistente em fila durável com `mandatory` e publisher confirms, e só então marca o envio. Uma falha entre essas etapas pode causar reentrega, preservando o mesmo `event_id`.
- Mensagens contêm somente identificador e versão do envelope. Documento e tipo de operação vêm da Outbox autorizada, não do conteúdo recebido no broker.
- Cada evento cria no máximo um job. A Inbox só recebe `processed_at` quando o resultado e a conclusão da tarefa são confirmados na mesma transação.
- O processamento usa lease de 120 segundos, renovado a cada 30 segundos. Gravação, falha e renovação exigem token vigente. Um resultado atrasado não substitui a tarefa de outro executor.
- Falhas usam espera exponencial com jitter, até cinco tentativas, depois quarentena. O administrador pode autorizar retomada com auditoria. Jobs interrompidos e entregas perdidas são recuperados periodicamente pelo publicador.
- O worker verifica SHA-256 antes do upload e após reler o objeto no MinIO. Objetos divergentes existentes não são sobrescritos. Metadados de arquivamento ficam em tabela imutável separada, sem alterar a versão documental.
- PDF/CSV/JSON são arquivados por hash; o backend confere tamanho e hash contra o snapshot antes de concluir a tarefa.
- Mensagens malformadas vão para a fila `denguepharma.pipeline.invalid.v1`. Versões desconhecidas de eventos na Outbox ficam com `UNSUPPORTED_SCHEMA` para inspeção.
- O worker tem credencial de serviço própria, `PIPELINE_TOKEN`, restrita às rotas `/api/internal/pipeline/**`. Ela não concede acesso administrativo. Vazia desabilita essa integração; valores configurados exigem ao menos 32 caracteres.
- O painel atualiza a cada cinco segundos e mostra confirmação de envio, tentativas, erros e estado dos jobs. O botão de envio apenas antecipa eventos; não simula confirmação do broker.

Eventos suportados nesta etapa: `DocumentoImportado`, `FonteAlterada` e `RelatorioSolicitado`. Eventos como `ExtracaoConcluida` e `EvidenciaAprovada` permanecem disponíveis para integrações futuras, sem serem marcados falsamente como processados.

## Executar localmente

Use o `.env` existente com senhas de PostgreSQL, RabbitMQ e MinIO. A credencial do worker é local e pode ser gerada sem exibi-la:

```powershell
.\scripts\configure-pipeline.ps1
```

Recarregue as variáveis e reinicie o backend com o código novo. Flyway aplica V7:

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#=]+)=(.*)$') { [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim()) } }
mvn -f backend/pom.xml spring-boot:run
```

Em outro terminal, construa e suba os serviços do pipeline:

```powershell
docker compose --profile pipeline up -d --build postgres rabbitmq minio worker
docker compose logs --tail 50 worker
```

O backend continua executando no host. O worker em Docker usa `host.docker.internal:8080`; `PIPELINE_BACKEND_URL` permite alterar esse endereço. Não é necessário expor os endpoints internos na internet.

Alternativa para executar o worker no host:

```powershell
workers\.venv\Scripts\python.exe -m pip install -r workers/requirements.lock
workers\.venv\Scripts\python.exe -m pip install --no-deps -e workers
workers\.venv\Scripts\python.exe -m denguepharma_workers.runtime --env-file .env
```

Nesse modo, os padrões são backend `localhost:8080`, RabbitMQ `localhost:5672` e MinIO `localhost:9000`. `--once` executa uma rodada de envio e consumo, útil para diagnóstico.

Crie/registre um protocolo e importe registros. O worker arquiva o JSON da fonte e cria campos em rascunho na tela de revisão. O texto disponível permanece limitado ao que o conector recuperou; arquivar metadados não significa obter o artigo integral.

### Imagem MinIO reproduzível

A imagem pública `minio/minio` não estava disponível no registro consultado durante a validação. O projeto agora constrói `denguepharma-minio:local` a partir da [fonte oficial](https://github.com/minio/minio), usando a tag `RELEASE.2025-04-22T22-12-26Z` fixada pelo objeto Git `f19c534b9f457773dcd043d977433e1a71525c3b`, que aponta para o commit `0d7408fc9969caf07de6a8c3a84f9fbb10a6739e`. A licença AGPL do MinIO acompanha a imagem. A primeira compilação leva alguns minutos e exige acesso a GitHub/Go modules.

Dependências Python testadas estão fixadas em `workers/requirements.lock`. O Dockerfile do worker instala esse conjunto e roda como usuário sem privilégios. A imagem do MinIO também usa usuário próprio; volumes reaproveitados de instalações antigas precisam permitir acesso a esse usuário.

## Validação executada

- 48 testes Java passaram, sem falhas/erros/ignorados, com o teste completo habilitado.
- 17 testes Python passaram.
- 14 testes frontend e compilação TypeScript/Vite passaram.
- Imagens Docker do MinIO e do worker foram construídas.

O teste completo cria PostgreSQL, RabbitMQ e MinIO isolados, inicia um servidor HTTP real e chama o processo Python real. Confere hash dos quatro objetos armazenados, campos não publicados, conclusão da Inbox/job e reentrega pelo broker sem duplicar extração. Os dados são fixtures de teste, não um corpus científico coletado.

Para repetir:

```powershell
docker compose build minio
$env:PIPELINE_INTEGRATION = 'true'
$env:PIPELINE_PYTHON = (Resolve-Path workers/.venv/Scripts/python.exe).Path
mvn -B -f backend/pom.xml test
```

Sem `PIPELINE_INTEGRATION=true`, a suíte Java executa os 47 testes comuns e ignora o teste completo opcional. O Python indicado deve ter os workers/dependências instalados. O teste não usa nem altera a base de desenvolvimento ou seus containers existentes.

## Limites e próximos passos

- Integração com modelo de IA, escolha de provedor, permissão de envio externo e controle de custo ainda estão pendentes. A função de montagem do payload de extração está separada da orquestração para permitir essa extensão.
- Os workers atuais processam JSON/metadados; extração de PDFs, tabelas e OCR ainda precisa ser implementada.
- Versões históricas sem bytes canônicos só são processadas quando a reconstrução confere com o hash original. Divergência causa falha recuperável/quarentena; o sistema não inventa outro hash nem reescreve a fonte.
- Jobs antigos criados pelo relay anterior não têm `source_event_id` e permanecem como tarefas legadas; eventos suportados publicados sem job novo podem ser reenviados após 60 segundos. A nova chave de idempotência evita duplicar extrações equivalentes.
- Downloads públicos de relatórios continuam gerados a partir do snapshot pela API; os artefatos no MinIO funcionam como cópia arquivada verificável. Não há recuperação direta do MinIO pela interface nesta etapa.
- Retenção/backup/restauração, monitoramento contínuo, avaliação científica, corpus adjudicado, formulários completos e as demais pendências da auditoria continuam para próximas etapas.

Contratos consultados: [publicação obrigatória e confirmação no Pika](https://github.com/pika/pika/blob/e27afa4982fe7acd398df69b7d6044968324beb2/docs/examples/blocking_publish_mandatory.md), [API do cliente MinIO](https://github.com/minio/minio-py/blob/master/docs/API.md) e [distribuição por fonte do MinIO](https://github.com/minio/minio/blob/master/README.md).
