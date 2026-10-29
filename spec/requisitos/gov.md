# Requisitos GOV

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-GOV-001 (M)

O sistema deve aplicar os perfis Leitor, Revisor, Adjudicador, Pesquisador e Administrador.

**Aceite:** Dado um Leitor, quando tentar corrigir um campo, então recebe 403 ; teste de acesso cruzado entre perfis.

**Rastreia:** RNF-01; tarefa M02; cenario ACC-GOV-001.

## REQ-GOV-002 (M)

O sistema deve pseudonimizar dados de revisores e limitar o acesso; o recrutamento só ocorre após a avaliação ética pertinente.

**Aceite:** Dado resultados do estudo de tempo, quando exportados, então revisores aparecem por código.

**Rastreia:** Ética; tarefa M05; cenario ACC-GOV-002.

## REQ-GOV-003 (M)

O sistema deve manter trilha de auditoria de todas as alterações de campos e decisões.

**Aceite:** Dado uma alteração, quando consultada a auditoria, então autor, instante e valores constam.

**Rastreia:** P1; tarefa M02; cenario ACC-GOV-003.

## REQ-GOV-004 (M)

O pacote público deve excluir chaves, dados pessoais e material sem licença, publicando identificadores, hashes, esquemas e métricas.

**Aceite:** Dado o pacote gerado, quando varrido, então não há segredos nem texto sem licença (T9).

**Rastreia:** P7; tarefa M02; cenario ACC-GOV-004.

## REQ-GOV-005 (M)

A interface e os relatórios devem exibir o aviso de uso em pesquisa e a ausência de recomendação individual.

**Aceite:** Dado qualquer tela de evidência, quando aberta, então o aviso está visível.

**Rastreia:** P4; tarefa M02; cenario ACC-GOV-005.

## REQ-GOV-006 (M)

O protocolo e o plano estatístico devem ser registrados e congelados antes do teste final, e as alterações versionadas.

**Aceite:** Dado o teste final, quando iniciado, então existe um commit do plano com data anterior.

**Rastreia:** P9; tarefa M02; cenario ACC-GOV-006.
