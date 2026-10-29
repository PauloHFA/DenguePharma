# Requisitos IDN

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-IDN-001 (M)

O sistema deve tratar NCT, PMID, PMCID e DOI como identificadores complementares e não intercambiáveis.

**Aceite:** Dado dois documentos com o mesmo DOI e NCT diferentes, quando o vínculo for avaliado, então fica “divergente” e vai à revisão, sem fusão automática (T3).

**Rastreia:** P1; tarefa M02; cenario ACC-IDN-001.

## REQ-IDN-002 (M)

QUANDO um vínculo documento-estudo tiver certeza abaixo do limiar, o sistema deve exigir confirmação humana, e toda fusão deve poder ser desfeita.

**Aceite:** Dado um vínculo ambíguo, quando um revisor o aprovar e depois o desfizer, então o estado anterior é restaurado e auditado.

**Rastreia:** OE2; tarefa M02; cenario ACC-IDN-002.

## REQ-IDN-003 (M)

O sistema deve normalizar substâncias com PubChem e ChEMBL, manter aliases e tratar combinações com componentes separados, sem fundi-las à monoterapia.

**Aceite:** Dado “A + B”, quando normalizada, então existe uma combinação com dois componentes que não conta como “A”.

**Rastreia:** RQ1, P2; tarefa M02; cenario ACC-IDN-003.

## REQ-IDN-004 (M)

O sistema deve agrupar todos os documentos de uma mesma investigação sob um study_id, para que participantes não sejam contados mais de uma vez.

**Aceite:** Dado um registro, um artigo e um seguimento do mesmo ensaio, quando somar participantes, então o total é o n do estudo.

**Rastreia:** RQ1, RQ3; tarefa M02; cenario ACC-IDN-004.
