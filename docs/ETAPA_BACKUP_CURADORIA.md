# Backup e restauração da curadoria — versão 0.9.0

Entrega de 28/10/2026. Foi implementado o backup privado dos workspaces clínicos, com restauração em diretório separado e validação de integridade. É uma parte operacional do marco M07; não conclui a migração nem a pesquisa clínica.

## Conteúdo e consistência

O arquivo ZIP contém somente:

- `input.json`: snapshot original do workspace.
- `protocol.json`: protocolo congelado.
- `curation.sqlite3`: fontes normalizadas, versões e decisões da curadoria, com cadeia de auditoria.
- `manifest.json`: identidade do workspace, versão do software, data UTC, hashes, tamanhos, contagem de eventos/fontes e cabeça da auditoria.

A cópia utiliza a API de backup do SQLite, incluindo páginas presentes no WAL. Durante a captura, uma reserva de escrita impede alterações concorrentes por votos/fontes. O ZIP só aparece no destino final depois de concluído; um arquivo existente nunca é substituído.

O backup é **privado e sem criptografia**, podendo conter textos documentais permitidos, trechos e identidades dos revisores. Não possui endpoint de download público, não inclui `.env` e não lê credenciais. O operador precisa de acesso local ao sistema de arquivos; os comandos não são ações da interface autenticada. O hash confere integridade, sem substituir a confiança na origem do arquivo.

## Comandos

Executar na raiz do repositório. O exemplo usa o workspace clínico real de 20 registros:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data clinical-backup --workspace 98043ff1652d98455adf3a115125cff18b89967a6c90f15545d87cb880f33e0e --output analytics/data/backups/NOVO_NOME.zip
```

A resposta informa `archive_hash`, `events`, `sources` e `audit_head`. Guarde o hash obtido dessa operação confiável. Para conferir a recuperação em um diretório separado:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/target/restauracao-verificada clinical-restore --input analytics/data/backups/NOVO_NOME.zip --expected-hash HASH_RETORNADO_PELO_BACKUP
```

`--expected-hash` é obrigatório. A restauração não apaga ou substitui um workspace existente, inclusive no diretório original. Para repetir a verificação, escolha outro diretório isolado.

## Validação da restauração

Antes de disponibilizar o workspace no destino, o comando confere:

1. SHA-256 do ZIP e nomes/tipos dos quatro membros, sem extração genérica de caminhos.
2. Tamanhos e hashes dos arquivos internos, formato do manifesto e identidade de input/protocolo/workspace.
3. Integridade do SQLite, schema conhecido e triggers de proteção append-only.
4. Cadeia de auditoria, contagem de eventos e cabeça da cadeia.
5. Hashes dos textos normalizados e sua correspondência com os documentos e versões do snapshot.
6. Contagens e hashes declarados no manifesto, além de nova conferência do hash do ZIP antes da instalação.

A extração usa área temporária dentro do diretório de destino. Só após as verificações a pasta completa é movida para `clinical/WORKSPACE_ID`. Restaurações locais são serializadas por lock; destinos existentes são recusados novamente imediatamente antes da movimentação. Falhas de validação não deixam um workspace parcialmente restaurado.

Limites do formato atual: 256 MiB por arquivo, 512 MiB para o conjunto de dados e 64 KiB para o manifesto. Links simbólicos, membros adicionais, nomes duplicados e tipos de compressão fora do contrato são recusados. Os arquivos devem estar em sistema de arquivos que suporte a criação atômica por hard link usada no backup.

## Verificação com os dados reais

Foram produzidas e restauradas cópias dos dois pilotos, sem alterar as pastas originais ou publicar as cópias:

| Corpus | Documentos | Representações privadas de fontes | Eventos científicos | SHA-256 do ZIP |
| --- | --- | --- | --- | --- |
| Piloto clínico | 20 | 50 | 0 | `9ce0e1c0217c5318f139b6c9184e011b353a4b887ae3d08adc83811afb18eb50` |
| Piloto operacional | 50 | 125 | 0 | `492d834b6ce02010ed1a232c1b5e3e78e6446e631656d1f76ca8009eb2a3bc29` |

As contagens de representações incluem versões de texto normalizado e não significam novos documentos ou estudos. Os pilotos também não devem ser somados como estudos únicos independentes.

Backups locais: `analytics/data/backups/20261028-160610-0cdd04f1/`. Restauração de verificação: `analytics/target/restore-check/20261028-160610-0cdd04f1/`. Evidência operacional: `analytics/target/clinical-backup-real-results.json`.

Os snapshots clínicos restaurados conservaram os hashes `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb` e `8c302d1840a70e2309586c6cf0a29e21138790ea5101b87ead75dd84daa90aec`, respectivamente. A auditoria e os originais permaneceram iguais. Não foram criados votos, aprovações ou conclusões.

## Escopo e continuidade

Este pacote não inclui PostgreSQL, MinIO, RabbitMQ, importações, checkpoints de coleta, conjuntos Parquet/DuckDB, publicações, relatórios ou contas de usuário. Também não configura backup remoto, agendamento, retenção ou recuperação de perda do disco local. O backup integral da aplicação e os demais critérios de M07 continuam pendentes; Java/React permanecem preservados.

Os relatórios analíticos publicados na versão 0.8.0 continuam válidos e não foram reprocessados nesta entrega operacional. O dashboard permanece em <http://127.0.0.1:8501>.

A situação científica permanece: **20 registros no piloto clínico, 40 votos iniciais pendentes e zero resultados clínicos revisados**. O próximo passo da pesquisa continua sendo executar a [revisão independente](ETAPA_PREVIA_REVISAO.md) e documentar a calibração. A restauração não aprova decisões nem publica evidência automaticamente.

## Evidência de validação

A suíte completa teve **77 testes aprovados**, com PostgreSQL e Quarto reais, incluindo oito cenários de backup/restauração. Foram verificados WAL, preservação de votos/fontes/resultados, hash obrigatório, integridade dos membros e do manifesto, auditoria, schema, limites, caminhos perigosos, links simbólicos, alteração do ZIP durante a recuperação, falhas de gravação e recusa de sobrescrita. Evidência: `analytics/target/clinical-backup-junit.xml`.

A matriz contém **91 requisitos, 24 com evidência automatizada nesta execução**. MIG-013 cobre somente esta entrega; os requisitos futuros do PDF e a revisão científica continuam pendentes. A aplicação foi reiniciada na versão 0.9.0, mantendo as execuções analíticas anteriores.
