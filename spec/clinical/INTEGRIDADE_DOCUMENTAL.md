# Alertas documentais e suspensão da evidência corrente

Incremento de software 0.19.0, em 28/10/2026, coberto por CLN-003. Complementa a emenda clínica sem alterar os protocolos congelados. A detecção automática de retratações e a atualização automática das publicações históricas continuam fora desta entrega; o requisito completo do PDF não é declarado atendido.

## Decisão humana e estados

Adjudicadores ou administradores podem registrar um alerta para um documento existente no workspace, mediante prévia e confirmação vinculada ao estado atual. O alerta exige uma referência HTTPS e justificativa documental. Não é inferido de título, palavras-chave ou texto de justificativas antigas; o módulo não acessa a URL para confirmar seu conteúdo.

| Estado | Comportamento |
| --- | --- |
| `SEM_ALERTA_REGISTRADO` | Estado de apresentação quando não existe evento humano; não certifica ausência de problemas na literatura |
| `EM_REAVALIACAO` | Bloqueia inclusão e uso dos resultados do estudo/identidade atual do documento |
| `RETIRADO` | Mantém bloqueio documental, com retirada da evidência corrente e preservação do histórico |
| `REGULARIZADO` | Encerra um bloqueio ativo mediante nova conferência; exige novas revisões para a nova base |

Tipos de alerta: `RETRATACAO`, `CORRECAO_RELEVANTE` ou `OUTRO_ALERTA_DOCUMENTAL`. Um tipo não é atribuído automaticamente, e a situação não constitui avaliação de eficácia ou risco de viés. Regularização inicial sem alerta ativo é recusada. Repetição exatamente idêntica não gera outro evento.

## Prévia e confirmação

O contrato `IntegrityNotice` contém `document_id`, `status`, `category`, `source_reference` e `reason`. `IntegrityConfirmation` acrescenta o recibo da prévia. A confirmação grava `DOCUMENT_INTEGRITY_RECORDED`, com versão e hash originais do documento, na auditoria append-only.

O recibo considera workspace, entrada, documento e aviso, ator e papéis, seleção atual e cabeça da auditoria. Mudanças de fonte, identidade, decisão, sessão ou conteúdo do aviso exigem outra prévia. O registro é transacional. A rota genérica de ações não aceita esse tipo de evento; a confirmação específica não pode ser substituída por uma gravação sem recibo.

A prévia informa votos atuais, resultados aprovados, grupos de síntese e calibração que exigirão nova conferência. Não contém identidades dos revisores ou votos individuais. Ela própria não grava eventos ou publica uma análise.

## Efeito nas revisões

Os eventos documentais passam a compor a base do estudo afetado. Os votos e resultados anteriores deixam de corresponder à base atual; a seleção e a calibração precisam ser revistas. O uso conservador é por estudo/identidade: mesmo um resultado que cita outro documento do mesmo estudo fica retido para conferência. O módulo não decide automaticamente quais partes de uma correção são clinicamente relevantes.

O bloqueio acompanha o documento se seu vínculo de identidade for corrigido. Os efeitos dessa correção nos estudos de origem e destino continuam seguindo a validação de identidade existente. O documento e suas representações não são removidos, permanecendo disponíveis para leitura e auditoria.

Regularizar cria outra revisão da base; não restaura votos, aprovações, calibrações ou conclusões antigos. Após a regularização, novas inclusões e novas extrações/revisões podem ser registradas conforme o protocolo. Exclusões e decisões incertas continuam sendo decisões humanas; o alerta não exclui automaticamente um estudo.

## Snapshots e publicação

Novos snapshots com alertas incluem `document_integrity`, com metadados e referências, sem justificativas livres ou nomes dos atores. A associação ao estudo é reconstruída pelos vínculos atuais. Um snapshot que mistura documento/estudo bloqueado com resultado aprovado é recusado pelo módulo analítico. Metadados duplicados, inesperados ou com justificativa privada também são recusados.

Quando não existe alerta, a chave opcional é omitida, preservando a representação e o hash dos snapshots anteriores sem alterações. O resumo analítico de uma nova execução com alertas informa as situações registradas e o número de documentos bloqueados.

**Confirmar um alerta não atualiza automaticamente um dashboard já publicado.** O efeito é imediato na curadoria corrente e nos próximos snapshots. O pesquisador deve preparar e publicar uma nova execução para apresentar a situação atual. Snapshots, relatórios e execuções históricas permanecem imutáveis e consultáveis; não são apagados nem reescritos.

## Interfaces e acesso

- `GET /api/clinical/{workspace}/integrity`: papéis de revisão; lista documental e estados; histórico completo somente para adjudicador/administrador; `Cache-Control: no-store`.
- `POST /api/clinical/{workspace}/integrity/preview`: adjudicador/administrador; prévia sem gravação.
- `POST /api/clinical/{workspace}/integrity/confirm`: adjudicador/administrador; recibo e aviso validados sob a mesma transação.
- Dossiê de triagem: alerta quando um documento do estudo está bloqueado.
- Curadoria: painel **Integridade documental — retratações e correções**, com seleções vazias, referência, justificativa, prévia de impacto e confirmação explícita.

O cadastro de alertas não busca artigos, corrige dados científicos, concede licença documental ou aprova evidência clínica. Não requer uma API externa nova.

O alcance é a síntese clínica Python; não modifica estados ou campos científicos aprovados no sistema legado. A migração e atualização dessas outras camadas continuam com seus contratos próprios.
