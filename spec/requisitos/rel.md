# Requisitos REL

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-REL-001 (M)

Todo relatório (PDF, CSV ou JSON) deve incluir fontes, data de consulta, versões, filtros, status da evidência e limitações.

**Aceite:** Dado um relatório gerado, quando inspecionado, então todos esses itens estão presentes (T8).

**Rastreia:** P1; tarefa M07; cenario ACC-REL-001.

## REQ-REL-002 (M)

O sistema deve reproduzir um relatório antigo de forma idêntica a partir do ReportSnapshot , mesmo após a atualização das fontes.

**Aceite:** Dado um relatório de ontem, quando regenerado hoje, então o hash do conteúdo é igual.

**Rastreia:** P6; tarefa M07; cenario ACC-REL-002.

## REQ-REL-003 (S)

O sistema deve oferecer painéis por eixo, com estados vazios, atualização pendente e acesso limitado ao texto integral.

**Aceite:** Dado um eixo sem dados, quando aberto, então exibe estado vazio explicativo.

**Rastreia:** OE4; tarefa M07; cenario ACC-REL-003.

## REQ-REL-004 (M)

Os relatórios de avaliação devem incluir resultados desfavoráveis e metas não atingidas.

**Aceite:** Dado uma meta não atingida, quando o relatório for gerado, então ela aparece com destaque.

**Rastreia:** P8; tarefa M07; cenario ACC-REL-004.

## REQ-REL-005 (S)

Cada figura deve trazer legenda com denominador e período, e não depender apenas de cor.

**Aceite:** Dado uma figura, quando inspecionada, então tem legenda completa e marcadores além da cor.

**Rastreia:** RNF acessibilidade; tarefa M07; cenario ACC-REL-005.
