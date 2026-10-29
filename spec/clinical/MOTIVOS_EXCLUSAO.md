# Registro de motivos e resumo operacional da seleção

Contrato de software `clinical-exclusion-reasons-1`, introduzido na versão 0.16.0. Complementa a apresentação da seleção clínica; não altera os protocolos congelados, as decisões anteriores ou os critérios de elegibilidade. Não substitui o relato completo da revisão.

## Motivo principal

Um adjudicador ou administrador confere e registra um motivo principal por identidade de estudo cuja exclusão já esteja resolvida pela seleção independente atual. São aceitos:

| Código | Descrição |
| --- | --- |
| `POPULACAO_FORA_ESCOPO` | População fora do escopo |
| `CONTEXTO_FORA_ESCOPO` | Contexto fora do escopo clínico |
| `INTERVENCAO_NAO_ELEGIVEL` | Intervenção fora do escopo farmacológico |
| `DESENHO_NAO_ELEGIVEL` | Desenho não elegível |
| `OUTRO_CRITERIO_PROTOCOLO` | Outro critério explícito do protocolo, explicado na justificativa |

A interface começa sem categoria selecionada e exige justificativa e confirmação humana. Não classificar por palavras-chave ou interpretar automaticamente justificativas antigas. A anotação não muda a decisão de excluir, nem a classificação científica consolidada. Ausência de texto integral ou paywall não é categoria de exclusão. Duplicidade deve ser tratada no fluxo de identidade documental, sem ser confundida com inelegibilidade.

O evento `EXCLUSION_REASON_RECORDED` exige `study_id`, `resolution_hash`, `category` e `reason`. O servidor acrescenta `dictionary_version`. A justificativa deve explicitar o critério conferido; o software valida estrutura e estado, sem julgar semanticamente o motivo informado.

## Atualidade e histórico

O hash da resolução contém a base documental, o conjunto atual de votos, a decisão, a classificação consolidada e a identificação da adjudicação aplicável. Mudanças de fonte, identidade, votos ou adjudicação exigem nova conferência. Reverter a decisão para o mesmo texto não reativa uma anotação antiga. Uma correção do motivo cria outro evento; apenas a anotação mais recente e válida conta na distribuição. Anotações anteriores permanecem no histórico append-only.

Identidades ambíguas não recebem anotação. A anotação não aprova calibração, não altera o hash da seleção, não desencadeia coleta e não publica uma execução.

## Unidades e contagens

O resumo é privado e apresenta separadamente:

- Documentos do snapshot de entrada.
- Identidades atuais de estudo, após os vínculos humanos registrados.
- Identidades pendentes, incertas, em conflito, incluídas e excluídas.
- Exclusões resolvidas por motivo principal e exclusões sem motivo atual.

As identidades somam os cinco estados; os motivos principais mais as exclusões sem motivo atual somam as exclusões resolvidas. São duas conferências distintas. Vários documentos de um estudo não são automaticamente registros duplicados.

O piloto limitado não reconstrói o universo de registros identificados, a remoção de duplicados ou os registros triados em uma revisão completa. Esses três campos permanecem `null`, identificados como `NAO_RECONSTRUIDO_PARA_O_PILOTO`. Não deduzir duplicados pela diferença entre documentos e estudos. Corpus vazio não representa seleção concluída.

Este resumo **não é um fluxograma PRISMA-ScR completo**, não tem contagens por etapas título/resumo e texto integral e não comprova cobertura de toda a literatura. O requisito original SEL-004 continua planejado. CLN-001 cobre o incremento operacional verificado.

## Acesso e exportação

Os papéis de revisão existentes consultam contagens agregadas; somente adjudicadores/administradores recebem a lista de exclusões resolvidas e seus motivos individuais, para documentação. O endpoint de exportação sempre retira essa lista, independentemente do papel. Não retorna votos, nomes de revisores, justificativas livres ou trechos de fontes.

- `GET /api/clinical/{workspace}/selection-flow`
- `GET /api/clinical/{workspace}/selection-flow/export`
- `POST /api/clinical/{workspace}/actions/EXCLUSION_REASON_RECORDED`

Consultas privadas retornam `Cache-Control: no-store`. O JSON exportado inclui hashes de entrada, protocolo, seleção e cabeça da auditoria, além da versão do dicionário. Não há publicação automática ou novo conjunto analítico público nesta entrega.
