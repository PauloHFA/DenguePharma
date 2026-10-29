# Requisitos ANA

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-ANA-001 (M)

O sistema deve gerar o panorama de estudos por substância, finalidade, fase, desenho, ano, país e patrocinador, contando estudos (e não documentos) e exibindo denominadores e limitações.

**Aceite:** Dado um conjunto de teste, quando agrupar por finalidade, então a soma das categorias é igual ao total de study_id.

**Rastreia:** RQ1; tarefa M02; cenario ACC-ANA-001.

## REQ-ANA-002 (M)

O sistema deve impedir síntese que combine contextos incompatíveis (in silico, in vitro, animal e humano; profilaxia, tratamento e sintomático).

**Aceite:** Dado uma tentativa de agregar humano e in vitro, quando executada, então é bloqueada com mensagem explicativa.

**Rastreia:** P2; tarefa M02; cenario ACC-ANA-002.

## REQ-ANA-003 (M)

O sistema deve calcular indicadores de relato para ensaios concluídos (resultados depositados, publicação ligada, datas e intervalo), tratando os não relatados como censurados à direita na data de corte.

**Aceite:** Dado 10 ensaios com datas conhecidas, quando o Kaplan-Meier for calculado, então os valores batem com o cálculo de referência.

**Rastreia:** RQ2, H4; tarefa M03; cenario ACC-ANA-003.

## REQ-ANA-004 (M)

O sistema deve ligar sítios e participantes de ensaios, por país e ano, a contagens de casos com a mesma janela temporal e definição de caso declarada, sinalizando países sem dados de carga.

**Aceite:** Dado um país sem registro de casos, quando analisado, então aparece como “sem dado de carga”, e não como zero.

**Rastreia:** RQ3, H5; tarefa M04; cenario ACC-ANA-004.

## REQ-ANA-005 (S)

O sistema deve comparar campos do registro e da publicação (desfecho primário, n, datas) e classificar as discrepâncias para revisão humana.

**Aceite:** Dado um desfecho primário diferente entre registro e artigo, quando comparado, então a discrepância é criada e enviada à revisão.

**Rastreia:** RQ4; tarefa M03; cenario ACC-ANA-005.

## REQ-ANA-006 (M)

O sistema deve calcular precisão, recall e F1 por campo e estrato frente à referência adjudicada, com regras congeladas para sinônimos e números, reportando a ausência correta separadamente.

**Aceite:** Dado uma referência e uma extração de teste, quando avaliar, então os valores coincidem com o cálculo manual e os verdadeiros negativos não entram no recall.

**Rastreia:** RQ5; tarefa M05; cenario ACC-ANA-006.

## REQ-ANA-007 (M)

O sistema deve calcular intervalos de confiança de 95% por reamostragem por família de estudo (cluster bootstrap).

**Aceite:** Dado documentos do mesmo study_id , quando reamostrados, então são sempre sorteados juntos.

**Rastreia:** RQ5; tarefa M05; cenario ACC-ANA-007.

## REQ-ANA-008 (S)

ONDE o grafo estiver habilitado, o sistema deve gerar arestas substância-estudo-desfecho-comparador apenas a partir de campos aprovados.

**Aceite:** Dado um campo em rascunho, quando o grafo for construído, então ele não gera aresta.

**Rastreia:** RQ6; tarefa M06; cenario ACC-ANA-008.

## REQ-ANA-009 (M)

O sistema não deve produzir ranking de eficácia, pontuação do "melhor fármaco" nem certeza GRADE automática.

**Aceite:** Dado qualquer relatório, quando inspecionado, então não existe campo ou texto de ranking ou de certeza automática.

**Rastreia:** P4; tarefa M07; cenario ACC-ANA-009.

## REQ-ANA-010 (M)

QUANDO um estudo for retratado, o sistema deve retirá-lo da síntese vigente, com motivo, e manter o histórico.

**Aceite:** Dado um estudo retratado, quando atualizado, então sai da síntese, mas permanece consultável com a justificativa (T6).

**Rastreia:** RQ4; tarefa M03; cenario ACC-ANA-010.
