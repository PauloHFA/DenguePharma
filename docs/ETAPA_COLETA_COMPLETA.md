# Coleta completa controlada — versão 0.7.0

Etapa de implementação de 28/10/2026. O software permite ampliar a coleta **depois da seleção independente e da calibração humana do piloto**. Esta entrega não representa uma coleta completa executada nem uma conclusão sobre medicamentos.

## Implementação

- Plano privado com fontes, estratégia, corte, hash da seleção e evento de calibração congelados.
- Execução por etapas curtas, IDs persistidos, checkpoint e retomada conservadora.
- Exportação de metadados pelo PostgreSQL em transação somente de leitura e isolamento repetível, evitando o limite HTTP de 8 MiB do endpoint legado de snapshots.
- Snapshot e manifesto imutáveis, com hashes, gravados integralmente antes de aparecerem no caminho final.
- Painel Streamlit **Coleta completa — plano e pré-requisitos** e endpoint privado `GET /api/clinical/{workspace}/collection-plan`. Consultá-los não inicia coleta.

Os coletores Java existentes executam as importações. Não foi criado outro consumidor de filas. Pilotos, snapshots e Java/React foram preservados.

## Pré-requisitos

Seleção concluída e calibração aprovada para o mesmo hash são obrigatórias. Corpus vazio, votos pendentes ou aprovação desatualizada bloqueiam a execução antes de qualquer chamada remota ou criação do diretório da coleta.

O corte vem do protocolo do piloto e não pode estar no futuro, considerando America/Sao_Paulo. Os comandos não aceitam substituições silenciosas de corte ou estratégia. Alterações exigem outra versão e calibração. `maxRecords=0` retira o limite do piloto, mantendo os termos calibrados.

O operador remoto precisa de papel `PESQUISADOR` ou `ADMINISTRADOR`, conferido por `/api/auth/me`. As credenciais vêm do `.env`; tokens e senhas não são gravados. O plano local é uma consulta, não uma autorização remota.

## Comandos

Na raiz do repositório, consulte o plano:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data clinical-collection-plan --workspace WORKSPACE_ID
```

Somente com `ready=true`, use o `configuration_hash` retornado:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data clinical-collect-full --workspace WORKSPACE_ID --collection CONFIGURATION_HASH --env-file .env
```

Cada chamada avança uma etapa curta ou consulta o processamento. Repita o mesmo comando para continuar. A sequência é criar protocolo, registrar, importar PubMed, importar ClinicalTrials.gov e exportar após ambas as importações terminarem. As fontes são processadas sequencialmente neste runner.

| Estado | Ação |
| --- | --- |
| `FULL_COLLECTION_BLOCKED` | Concluir seleção e calibração humanas |
| `PROTOCOL_REGISTERED` / `IMPORT_STARTED` | Repetir o comando para acompanhar |
| `WAITING_IMPORT` | Coletor ainda trabalhando; consultar depois |
| `IMPORT_FAILED_RESUME_REQUIRED` | Inspecionar a falha e usar `--resume-failed` para retomar o mesmo ID |
| `REMOTE_ACTION_UNCONFIRMED` | Conferir operação pendente; não criar outra manualmente |
| `RECOVERED_REMOTE_ACTION` | Operação localizada; repetir para continuar |
| `SNAPSHOT_READY_PENDING_REVIEW` | Metadados congelados; revisão e publicação ainda separadas |

Antes de um POST, o runner persiste a intenção. Se a resposta se perder, procura a operação por código/protocolo/fonte, sem repetir cegamente o POST. A listagem legada de importações retorna até 200 itens; operações antigas podem exigir `--recover-id UUID_CONFERIDO`. O ID precisa corresponder à ação pendente. Zero ou múltiplos candidatos mantêm o processamento bloqueado para conferência operacional.

Um lock do sistema operacional impede runners simultâneos para a mesma configuração e é liberado ao encerrar o processo. Checkpoints são substituídos atomicamente. Artefatos usam temporário, `fsync` e criação atômica sem substituir destinos existentes; uma interrupção antes dessa criação não deixa JSON parcial no caminho final. Temporários órfãos de encerramento abrupto podem permanecer privados e não são considerados resultados.

## Dados e reprodução

Diretório canônico: `analytics/data/collections/CONFIGURATION_HASH/`, com `checkpoint.json`, `dataset.json`, `manifest.json` e lock. O manifesto registra configuração, IDs, contadores, versão, hashes, `published=false` e `clinical_reviews_transferred=false`.

O adaptador usa as versões vinculadas às importações indicadas, confere hashes e conserva identificadores, datas, licenças e referências de identidade. Documentos associados apenas a estudos demonstrativos/inativos não entram. Vínculos e classificações legadas são referências históricas, sem se tornarem votos ou aprovações da nova seleção.

A exportação contém metadados permitidos, sem resumos, textos integrais, contatos ou resultados científicos transferidos como aprovados. `studies` e `scientificFields` ficam vazios. O JSON não tem o limite HTTP de 8 MiB; ainda é construído em memória e depende da capacidade da máquina.

Após o snapshot, prepare e confira explicitamente:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data prepare --input analytics/data/collections/CONFIGURATION_HASH/dataset.json --expected-hash DATASET_HASH
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data verify --run RUN_ID
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli --data-dir analytics/data report --run RUN_ID --quarto analytics/.tools/bin/quarto.cmd
```

`publish --run RUN_ID` é uma etapa separada de disponibilização de metadados; não aprova evidência. Para curadoria do novo corpus, use `clinical-init` com o protocolo correspondente, confira fontes por `clinical-enrich` e execute seleção, extração e revisão humanas. Os votos do piloto não são transferidos automaticamente.

## Validação e situação científica

REQ-CLN-011 cobre bloqueios, permissões, respostas perdidas, não duplicação de POST, retomada, lock, gravação atômica, integridade, consulta sem coleta e preservação das versões. Aprovações e coleta completa são testadas com cenários sintéticos. A integração real usa somente leitura das versões do piloto existente.

O piloto real permanece com **20 registros, 40 votos iniciais faltantes e zero resultados clínicos revisados**. A coleta completa real continua bloqueada; REQ-CLN-006 permanece planejado. O próximo passo científico é revisar o piloto com pessoas independentes e registrar sua calibração.

Dashboard: <http://127.0.0.1:8501>. Consulte também os [resultados descritivos anteriores](RESULTADOS_GERAIS_PESQUISA.md), que não identificam o melhor medicamento para dengue.

### Evidências da entrega 0.7.0

- **61 testes aprovados**: 59 na primeira execução e dois testes PostgreSQL aprovados após iniciar o Docker. As falhas iniciais eram de conexão; foram mantidas no registro original. Evidência consolidada: `analytics/target/full-collection-verified-junit.xml`.
- Matriz verificada: **89 requisitos, 22 com evidência automatizada**. Isso não representa atendimento integral ao PDF; os requisitos futuros permanecem planejados.
- O novo adaptador produziu os mesmos registros preparados do piloto real de 20 documentos. IDs, versões e hashes foram preservados.
- O fluxo real recusou a coleta com `FULL_COLLECTION_BLOCKED:SCREENING_NOT_COMPLETE`, sem chamada remota e sem criar o diretório da coleta.
- Os dois pilotos foram reprocessados na versão 0.7.0; as 29 tabelas de cada execução preservaram seus hashes lógicos. Os inputs e a cadeia de auditoria, ainda sem eventos científicos, permaneceram iguais.

| Corpus | Nova execução publicada localmente |
| --- | --- |
| Piloto clínico de 20 documentos | `024f065a66895fb0d16dca25542bc968c04cdf215224eca5f9be05fb25e4d89e` |
| Piloto operacional de 50 documentos | `ca70747decd858cdc55c6789e62ca29ac0a0f7391bbffee494691b428f61ad46` |

Os relatórios Quarto HTML foram gerados para ambas as execuções. Os dois pilotos não devem ser somados como estudos independentes. Reprocessar os mesmos dados com código novo não produz novos achados clínicos.

O teste em navegador real validou login e logout, os indicadores 20/10/10/0, as 40 revisões pendentes, o painel de bloqueio e a ausência de comando/botão de execução antes da calibração. Nenhuma decisão foi enviada e não houve erro JavaScript. Evidência local: `analytics/target/full-collection-browser-results.json`.
