# Requisitos OPS

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-OPS-001 (M)

O sistema deve gravar a mutação local e o evento na mesma transação (Outbox); o publicador deve reenviar sem mudar o event_id.

**Aceite:** Dado uma falha entre o commit e o envio, quando o publicador reiniciar, então o evento é enviado com o mesmo event_id.

**Rastreia:** P10; tarefa M07; cenario ACC-OPS-001.

## REQ-OPS-002 (M)

O consumidor deve registrar cada event_id em Inbox e ser idempotente.

**Aceite:** Dado o mesmo evento entregue duas vezes, quando consumido, então o efeito ocorre uma vez (T7).

**Rastreia:** P10; tarefa M07; cenario ACC-OPS-002.

## REQ-OPS-003 (M)

O sistema não deve manter transação SQL aberta durante chamada de IA; deve persistir resultados intermediários e tentativas.

**Aceite:** Dado uma chamada de IA lenta, quando em curso, então não há transação aberta no banco.

**Rastreia:** RNF; tarefa M07; cenario ACC-OPS-003.

## REQ-OPS-004 (M)

O sistema deve reservar tarefas por lease e só aceitar resultado com token vigente; resultado atrasado não substitui revisão mais recente.

**Aceite:** Dado um lease expirado, quando o resultado chegar, então é descartado e registrado.

**Rastreia:** P10; tarefa M07; cenario ACC-OPS-004.

## REQ-OPS-005 (S)

O sistema deve aplicar backoff com jitter, limite de tentativas e quarentena, com reprocessamento autorizado e auditado.

**Aceite:** Dado uma tarefa que falha N vezes, quando excedido o limite, então vai à quarentena visível.

**Rastreia:** RF-11; tarefa M07; cenario ACC-OPS-005.

## REQ-OPS-006 (M)

O sistema deve controlar o orçamento da IA por execução e registrar o custo; ao atingir o teto, deve pausar e alertar.

**Aceite:** Dado um teto de teste, quando atingido, então novas chamadas são suspensas e um alerta é emitido.

**Rastreia:** RNF; tarefa M05; cenario ACC-OPS-006.

## REQ-OPS-007 (M)

O sistema deve usar TLS, proteger segredos e manter backup com restauração testada de metadados e documentos.

**Aceite:** Dado um backup, quando restaurado em ambiente limpo, então metadados e documentos referenciados conferem por hash.

**Rastreia:** RNF-02; tarefa M07; cenario ACC-OPS-007.

## REQ-OPS-008 (S)

O sistema deve responder consultas usuais com p95 de até 2 s em 10 mil registros e 10 usuários, medindo custo e latência da IA separadamente.

**Aceite:** Dado a carga de referência, quando executada, então p95 é igual ou menor que 2 s.

**Rastreia:** RNF-06; tarefa M07; cenario ACC-OPS-008.

## REQ-OPS-009 (M)

O pipeline deve ser regenerável: dado o manifesto de dados e o commit, deve reproduzir as tabelas da camada ouro com hashes idênticos.

**Aceite:** Dado o mesmo manifesto e código, quando reexecutado, então os hashes das tabelas ouro coincidem.

**Rastreia:** P6; tarefa M07; cenario ACC-OPS-009.

## REQ-OPS-010 (M)

O sistema deve testar contratos de dados e de eventos entre produtor e consumidor, com esquemas versionados.

**Aceite:** Dado uma mudança incompatível de esquema, quando o teste de contrato rodar, então o build falha.

**Rastreia:** RNF; tarefa M07; cenario ACC-OPS-010.
