# Requisitos SEL

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-SEL-001 (M)

O sistema deve permitir triagem independente por dois revisores, preservando cada decisão e o motivo final.

**Aceite:** Dado dois revisores, quando ambos decidirem, então as duas decisões ficam gravadas separadamente.

**Rastreia:** OE1; tarefa M02; cenario ACC-SEL-001.

## REQ-SEL-002 (M)

SE os revisores divergirem, ENTÃO o sistema deve encaminhar à adjudicação, sem revelar a decisão de um ao outro antes de concluir a sua.

**Aceite:** Dado uma divergência, quando o segundo revisor abrir o item, então a decisão do primeiro está oculta.

**Rastreia:** OE1; tarefa M02; cenario ACC-SEL-002.

## REQ-SEL-003 (M)

O sistema não deve excluir registros automaticamente por modelo; a IA só pode ordenar a fila de leitura.

**Aceite:** Dado um modelo de priorização, quando a triagem terminar, então nenhum registro está "excluído" sem decisão humana registrada.

**Rastreia:** P5; tarefa M02; cenario ACC-SEL-003.

## REQ-SEL-004 (M)

O sistema deve registrar o motivo de exclusão em categorias padronizadas e gerar as contagens do fluxograma PRISMA-ScR.

**Aceite:** Dado uma triagem concluída, quando o fluxograma for gerado, então identificados = duplicados + triados e exclusões somam por motivo.

**Rastreia:** OE1; tarefa M02; cenario ACC-SEL-004.

## REQ-SEL-005 (S)

QUANDO o texto integral não puder ser obtido, o sistema deve manter o status "somente resumo" ou "texto não obtido" e declarar o impacto na cobertura.

**Aceite:** Dado um artigo atrás de paywall, quando triado, então não é excluído e aparece no relatório de cobertura.

**Rastreia:** P1; tarefa M02; cenario ACC-SEL-005.
