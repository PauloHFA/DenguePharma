# Requisitos REV

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-REV-001 (M)

O sistema deve mostrar sugestão e fonte lado a lado e permitir aceitar, corrigir ou rejeitar; toda correção registra antes e depois, responsável, motivo e instante.

**Aceite:** Dado uma sugestão corrigida, quando salva, então o histórico mostra antes, depois, autor, motivo e hora.

**Rastreia:** OE4; tarefa M02; cenario ACC-REV-001.

## REQ-REV-002 (M)

Campos críticos só devem ser publicados após aprovação de um adjudicador.

**Aceite:** Dado um campo crítico aprovado só por um revisor, quando tentar publicar, então a publicação é negada.

**Rastreia:** P5; tarefa M02; cenario ACC-REV-002.

## REQ-REV-003 (M)

O sistema não deve sobrescrever valor aprovado por extração automática posterior.

**Aceite:** Dado um valor aprovado, quando nova extração divergir, então o valor aprovado permanece e a divergência vira alerta.

**Rastreia:** P5; tarefa M02; cenario ACC-REV-003.

## REQ-REV-004 (S)

O sistema deve identificar rascunhos automáticos e excluí-los de exportações públicas.

**Aceite:** Dado um rascunho, quando exportar o catálogo público, então ele não aparece.

**Rastreia:** P5; tarefa M02; cenario ACC-REV-004.

## REQ-REV-005 (M)

O sistema deve registrar o tempo ativo por documento e por campo, com pausas, para o estudo de tempo.

**Aceite:** Dado uma sessão de revisão com pausa, quando concluída, então o tempo ativo exclui a pausa.

**Rastreia:** RQ5, H1; tarefa M05; cenario ACC-REV-005.
