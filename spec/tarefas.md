# Tarefas e dependências

| Marco | Entrega | Dependência | Situação inicial |
| --- | --- | --- | --- |
| M00 | Constituição, glossário, requisitos, cenários e rastreabilidade verificável | PDF e plano adotados | Implementação nesta entrega |
| M01 | Entrada somente de leitura, módulos Python, Parquet/DuckDB, FastAPI pública, Streamlit e Quarto | M00 | Implementação nesta entrega |
| M02 | Migração de coleta, identidade, seleção, revisão, permissões, publicação de campos e conclusão do eixo A | M01 e paridade dos contratos | Planejado |
| M03 | Mart de relato, vínculos, discrepâncias, correções e sobrevivência | M02, datas e vínculos conferidos | Planejado |
| M04 | OpenDengue/SINAN agregado, geografia/tempo e análise de carga × pesquisa | M02 e definições de caso registradas | Planejado |
| M05 | Licenças, referência adjudicada, tempo ativo, provedor, orçamento e experimento de extração | M02, protocolo e condições de avaliação | Planejado |
| M06 | Grafo de evidências revisadas | Dados aprovados disponíveis | Opcional |
| M07 | Contratos, observabilidade, restauração, carga e retirada do legado | Marcos científicos e paridade operacional | Planejado |

O primeiro marco não promete concluir os 66 requisitos do PDF. Cada ID aponta para um cenário e marco em `rastreabilidade.csv`. Os requisitos MIG descrevem o que pode ser verificado nesta entrega. Requisitos de autorização/curadoria, embora existam parcialmente em Java, precisam ser revalidados quando migrados.

A retirada do legado depende de backup/restauração validada, equivalência de permissões, idempotência e preservação dos dados. A próxima arquitetura terá banco de migração separado e namespace de fila `denguepharma.analytics.pipeline.v1`; não compartilhar consumidores com a fila antiga.

## M08 — emenda clínica prioritária

Continuidade 0.19.0: [integridade documental](clinical/INTEGRIDADE_DOCUMENTAL.md), coberta por CLN-003. Alertas humanos com prévia/recibo, suspensão corrente, regularização sem reativação e preservação de snapshots. A detecção automática e o atendimento integral do requisito de retratação do PDF continuam planejados.

Continuidade 0.18.0: [atualização independente da curadoria](../docs/ETAPA_ATUALIZACAO_CURADORIA.md), coberta por MIG-006 e CLN-008. Fragmento privado e escolha do escopo de atualização, sem cache de dados clínicos, repetição automática de ações ou alteração das validações científicas.

Continuidade 0.17.0: [fila e progresso pessoais](../docs/ETAPA_FILA_PESSOAL.md), cobertos por CLN-008. Estados e filtros consideram somente a revisão da conta atual e a disponibilidade de vagas. Não há alocação automática, reativação de votos antigos ou conclusão científica pela quantidade de revisões registradas.

Continuidade 0.16.0: [motivos principais e resumo privado da seleção](clinical/MOTIVOS_EXCLUSAO.md), cobertos por CLN-001. Totais desconhecidos permanecem nulos; SEL-004 e o relato PRISMA completo continuam planejados. A documentação dos motivos não modifica as decisões independentes.

Continuidade 0.15.0: [dossiê documental por estudo](../docs/ETAPA_DOSSIE_TRIAGEM.md) integrado à triagem, coberto por CLN-008. Consulta privada com escopo documental, base atual, hashes e ausência de votos; não substitui a execução científica CLN-006.

Protocolo clínico congelado, piloto de calibração separado, triagem independente, extração por braço/desfecho/tempo, revisão e adjudicação, ICs individuais, conclusões humanas, tabelas e gráficos públicos. REQ-CLN-001 a 005 verificam o software; REQ-CLN-006 acompanha a execução científica real. SQLite privado não substitui nem altera o PostgreSQL legado. A coleta usa uma ponte explícita para os jobs existentes, sem consumidor concorrente novo. M04/M05 (carga e IA) foram adiados; não são declarados concluídos.

## Continuidade de M07 — versão 0.9.0

MIG-013 delimita o backup privado dos workspaces clínicos e a restauração isolada com conferência de hashes, fontes e auditoria. O [guia operacional](../docs/ETAPA_BACKUP_CURADORIA.md) registra a verificação com os pilotos reais. M07 permanece parcial: PostgreSQL, armazenamento de objetos, filas, contas, conjuntos analíticos e retirada do legado exigem seus próprios testes e procedimentos.

## Continuidade de M03 — versão 0.13.0

MIG-016 implementa a [auditoria descritiva de datas](../docs/ETAPA_AUDITORIA_RELATO.md), usando entradas congeladas e sem transferir aprovações. M03 e o eixo B continuam parciais: não há censura/Kaplan–Meier, modelos, vínculos de publicação conferidos ou discrepâncias. ANA-003 conserva seu aceite original e permanece planejado. A revisão clínica continua prioritária.

## Continuidade de M03 — versão 0.14.0

MIG-017 implementa a [auditoria bibliográfica por PMID](../docs/ETAPA_REFERENCIAS_PUBLICACOES.md), sem substituir a conferência de vínculos clínicos, discrepâncias ou a seleção independente. M03 e o eixo B permanecem parciais. A lista de referências não amplia automaticamente o corpus autorizado.
