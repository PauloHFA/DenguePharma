# Requisitos MIG

Fonte: PDF Analytics (secao 8) ou plano de migracao; estado detalhado em requirements.json.

## REQ-MIG-001 (M)

O sistema deve ler a base legada em transacao somente de leitura e conferir o hash canonico.

**Aceite:** Dado um snapshot existente, Quando lido pelo adaptador PostgreSQL, Entao os bytes e o hash coincidem e uma escrita e recusada.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-001.

## REQ-MIG-002 (M)

O sistema deve preservar entrada, IDs, versoes e referencias na exportacao bronze/prata.

**Aceite:** Dado o piloto, Quando exportado, Entao os 50 documentos conservam suas referencias e a entrada bronze e identica.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-002.

## REQ-MIG-003 (M)

O sistema deve preservar resultados equivalentes ao adaptar as regras Python existentes.

**Aceite:** Dado um conjunto conhecido, Quando analisado nas duas implementacoes, Entao preparacao, contagens e estados coincidem.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-003.

## REQ-MIG-004 (M)

O sistema deve gerar Parquet e DuckDB com schemas explicitos e tabelas reproduziveis.

**Aceite:** Dada a mesma entrada e codigo, Quando preparados em diretorios distintos, Entao os hashes Parquet e os conteudos DuckDB coincidem.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-004.

## REQ-MIG-005 (M)

O sistema deve servir apenas leitura publica de execucoes explicitamente publicadas.

**Aceite:** Dada execucao nao publicada, Quando consultada pela API, Entao recebe 404; operacoes de escrita nao estao expostas.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-005.

## REQ-MIG-006 (M)

O sistema deve exibir panorama coletado e estudos revisados em camadas separadas no Streamlit.

**Aceite:** Dado o piloto sem estudos revisados, Quando o dashboard abre, Entao mostra os documentos e estado vazio cientifico, sem login.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-006.

## REQ-MIG-007 (M)

O sistema deve renderizar relatorio Quarto HTML a partir dos mesmos marts.

**Aceite:** Dado um run preparado, Quando o Quarto renderiza, Entao o HTML informa as contagens, denominadores, corte e limitacoes.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-007.

## REQ-MIG-008 (M)

O sistema deve manter a migracao paralela sem dependencias operacionais do Java ou alteracao dos dados legados.

**Aceite:** Dada a nova aplicacao, Quando serve um run exportado, Entao funciona sem chamar o Java e sem consumir a fila antiga.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-008.

## REQ-MIG-009 (M)

O sistema deve validar especificacao e rastreabilidade sem apresentar requisitos futuros como concluidos.

**Aceite:** Dado um ID inexistente ou criterio ausente, Quando a verificacao SDD roda, Entao falha; requisitos futuros ficam planejados.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M00; cenario ACC-MIG-009.

## REQ-MIG-010 (M)

O sistema deve declarar os eixos B, C e D planejados e o E opcional enquanto nao implementados.

**Aceite:** Dado o primeiro marco, Quando consultadas as capacidades, Entao nao exibe resultados simulados para os eixos futuros.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-010.

## REQ-MIG-011 (M)

O sistema deve excluir dados privados e entrada bronze das interfaces publicas.

**Aceite:** Dado um snapshot com marcadores privados, Quando consultados API e artefatos publicos, Entao nenhum marcador ou texto integral e exposto.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-011.

## REQ-MIG-012 (M)

O sistema deve impedir sobrescrita de runs e detectar alteracao dos artefatos.

**Aceite:** Dado um run persistido, Quando alterado ou reexportado, Entao divergencias falham e nao sobrescrevem o resultado.

**Rastreia:** P1, P5, P6; fundacao da migracao; tarefa M01; cenario ACC-MIG-012.
