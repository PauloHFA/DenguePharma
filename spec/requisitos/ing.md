# Requisitos ING

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-ING-001 (M)

QUANDO uma coleta for iniciada em uma fonte, o sistema deve registrar um SearchRun com consulta, parâmetros, paginação, instante, total retornado e versão do conector.

**Aceite:** Dado uma coleta no ClinicalTrials.gov com condição dengue, quando concluir, então o SearchRun existe e o total é igual à soma dos registros paginados.

**Rastreia:** RQ1-RQ6, P6; tarefa M02; cenario ACC-ING-001.

## REQ-ING-002 (M)

QUANDO o mesmo registro for importado novamente, o sistema não deve criar novo estudo nem novo documento, e só deve criar nova versão de o hash mudar.

**Aceite:** Dado um NCT já importado, quando reimportar sem mudança, então as contagens de Study e de DocumentVersion ficam iguais (T1).

**Rastreia:** P10; tarefa M02; cenario ACC-ING-002.

## REQ-ING-003 (M)

O sistema deve guardar cada resposta bruta como snapshot imutável, com hash, data, URL e versão da fonte, na camada bronze.

**Aceite:** Dado um snapshot gravado, quando se tentar alterá-lo ou apagá-lo, então a operação é rejeitada e o hash recalculado coincide.

**Rastreia:** P1, P6; tarefa M02; cenario ACC-ING-003.

## REQ-ING-004 (M)

SE a fonte responder 429 ou 5xx, ENTÃO o sistema deve respeitar Retry-After, aplicar backoff exponencial com jitter e retomar do checkpoint sem perder nem duplicar registros.

**Aceite:** Dado um 429 simulado na página 3 de 10, quando a coleta continuar, então são recuperadas as 10 páginas, sem duplicatas.

**Rastreia:** RNF, P10; tarefa M02; cenario ACC-ING-004.

## REQ-ING-005 (M)

O sistema deve manter checkpoint por fonte e consulta, de modo que uma coleta interrompida seja retomada.

**Aceite:** Dado uma coleta interrompida na página 5, quando reiniciar, então ela continua da página 5.

**Rastreia:** P10; tarefa M02; cenario ACC-ING-005.

## REQ-ING-006 (S)

QUANDO o hash de um registro mudar, o sistema deve criar nova DocumentVersion, calcular a diferença de campos e abrir fila de reavaliação, sem sobrescrever decisão anterior.

**Aceite:** Dado um registro cujo status mudou, quando for reimportado, então há duas versões, o difí e uma tarefa de reavaliação (T2).

**Rastreia:** RQ4, RF original; tarefa M03; cenario ACC-ING-006.

## REQ-ING-007 (M)

O sistema deve registrar a licença por documento e só armazenar texto integral quando a licença permitir.

**Aceite:** Dado um artigo sem licença de reuso, quando for importado, então só metadados são guardados e o status é “texto não obtido” (T9).

**Rastreia:** P7; tarefa M02; cenario ACC-ING-007.

## REQ-ING-008 (M)

O sistema deve ingerir contagens de casos (OpenDengue e SINAN agregado) com país (ISO), ano, fonte, versão, definição de caso e unidade geográfica.

**Aceite:** Dado uma linha sem país, quando ingerida, então vai para quarentena com motivo; linhas válidas têm definição de caso e fonte.

**Rastreia:** RQ3; tarefa M04; cenario ACC-ING-008.

## REQ-ING-009 (M)

O sistema deve manter um manifesto de dados com URL, versão, data de acesso, parâmetros, total, hash e licença de cada fonte.

**Aceite:** Dado uma execução concluída, quando o manifesto for gerado, então todas as fontes usadas constam com hash verificável.

**Rastreia:** P1, P6; tarefa M02; cenario ACC-ING-009.
