# Conferência da identidade dos estudos — versão 0.10.0

Entrega de 28/10/2026. Esta etapa permite conferir os vínculos entre documentos e estudos antes da síntese clínica. A finalidade é evitar contagens indevidas quando um estudo possui várias publicações ou um registro de ensaio. Identidade documental não demonstra elegibilidade, benefício ou suporte semântico.

## Fluxo na aplicação

Na [curadoria protegida do dashboard](http://127.0.0.1:8501), abrir **Identidade dos estudos — documentos e vínculos**. A tabela mostra documento, título, fonte, versão, hash, identificadores e identidade atual. Os vínculos legados são apresentados como referências iniciais; não são tratados como decisões clínicas aprovadas.

Revisores autenticados podem consultar a tabela. Alterar vínculos exige papel `ADJUDICADOR` ou `ADMINISTRADOR`:

1. Conferir os documentos e as fontes permitidas para estabelecer se representam o mesmo estudo.
2. Selecionar explicitamente o documento e o estudo de destino, dentre as identidades conhecidas no workspace.
3. Registrar a justificativa e as fontes conferidas.
4. Clicar em **Conferir impacto do vínculo**. A prévia apresenta grupos antes/depois, documentos afetados e votos que precisarão de nova revisão.
5. Conferir o impacto, marcar a confirmação e clicar em **Confirmar vínculo documental auditável**.

A prévia não grava eventos nem modifica documentos. O recibo vincula a operação à identidade autenticada, aos papéis, à justificativa e à base/auditoria atuais. Mudanças de entrada ou sessão removem a prévia no formulário. Mudanças de estado no backend fazem a confirmação antiga ser recusada. Não há sugestão de fusão por título, substância ou semelhança textual.

## Ambiguidades e correções

Um documento com vários vínculos legados `CONFIRMADO` divergentes não escolhe mais o primeiro estudo. Ele recebe provisoriamente sua própria identidade documental e fica marcado como `AMBIGUIDADE_LEGADA`.

Essa ambiguidade impede a inclusão clínica daquele grupo e bloqueia a aprovação da calibração/coleta completa até conferência humana. Votos de exclusão ou incerteza não resolvem automaticamente a identidade. Se a conferência concluir que o documento deve permanecer separado, é possível confirmar explicitamente a identidade documental provisória. Esse registro também é auditado.

São aceitos destinos já presentes no catálogo ou referenciados na entrada original. Isso permite devolver um documento a uma identidade original que tenha ficado temporariamente sem documentos. A criação livre de IDs de estudo não faz parte deste fluxo. Para reunir vários documentos, cada alteração precisa ser conferida; não há fusão automática em lote.

Depois de um vínculo, as bases dos estudos de origem e destino mudam. Os IDs dos eventos de identidade passam a integrar essas bases. Assim, **corrigir ou desfazer o vínculo não reativa votos, resultados ou calibrações antigos**. É necessária nova revisão dos grupos afetados. Eventos anteriores, representações documentais e snapshots históricos permanecem preservados.

Uma solicitação redundante para um vínculo já registrado é recusada com `NO_IDENTITY_CHANGE`. Não se apagam eventos para desfazer uma alteração: registra-se outro vínculo justificado para o destino original conhecido.

## API e compatibilidade

- `GET /api/clinical/{workspace}/identity`: consulta privada dos documentos, destinos conhecidos e permissão de alteração; histórico de vínculos apenas para adjudicadores/administradores.
- `POST /api/clinical/{workspace}/identity/preview`: recebe `document_id`, `study_id` e `reason`; exige papel de adjudicação.
- `POST /api/clinical/{workspace}/identity/confirm`: recebe `link` com os mesmos campos e `receipt`; valida o estado novamente na transação que registra `DOCUMENT_LINKED`.

O endpoint genérico de ações continua aceitando `DOCUMENT_LINKED` para clientes anteriores, com as mesmas verificações de documento, destino, justificativa e papel. A prévia e o recibo são obrigatórios no novo fluxo específico da interface/API, sem afirmar que todos os clientes antigos já os utilizam.

Não são retornados votos de triagem alheios na consulta de identidade. A prévia de adjudicação mostra apenas contagens dos votos afetados. Nenhuma alteração de identidade publica resultados, aprova extrações ou elimina a exigência de dois revisores e adjudicação.

## Verificação e situação real

A suíte completa teve **85 testes aprovados**, incluindo oito cenários novos de identidade e as verificações existentes com PostgreSQL e Quarto reais. Os testes cobrem ambiguidades, bloqueios de inclusão/calibração, prévia sem escrita, permissões, recibos desatualizados, mudança de agrupamento, correção sem reativação de revisões, interface e preservação pelo backup/restauração.

Evidência: `analytics/target/study-identity-junit.xml`. A matriz contém **92 requisitos: 66 do PDF, 13 MIG e 13 CLN**. REQ-CLN-013 cobre esta entrega; a execução científica CLN-006 e os requisitos futuros permanecem pendentes.

Nos dois pilotos reais, a verificação inicial encontrou zero documentos com vínculos legados divergentes e zero eventos de alteração de identidade. Portanto, esta correção não mudou seus agrupamentos ou snapshots atuais. Os fluxos de confirmação foram exercitados com dados sintéticos; nenhum vínculo real foi confirmado durante a implementação.

O piloto clínico continua com **20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados**. Não houve coleta adicional, fusão automática ou nova conclusão sobre medicamentos. As execuções analíticas publicadas na versão 0.8.0 e os backups da versão 0.9.0 continuam preservados.

O próximo marco científico permanece executar a [revisão independente](ETAPA_PREVIA_REVISAO.md), corrigir eventuais identidades após conferência das fontes e documentar a calibração antes da [coleta completa](ETAPA_COLETA_COMPLETA.md).

A conferência autenticada no ambiente real validou o painel de identidade, a exigência de selecionar documento/destino e a ausência de confirmação antes de uma prévia. Login/logout funcionaram sem erros JavaScript e nenhuma decisão de vínculo foi enviada. Evidência: `analytics/target/study-identity-browser-results.json`.

A consulta privada dos dois pilotos confirmou 20 e 50 identidades operacionais ativas, respectivamente, sem ambiguidades legadas ou eventos novos. Isso não certifica cientificamente seus vínculos. Os snapshots atuais e as cópias restauradas da etapa 0.9.0 continuaram idênticos, com os mesmos hashes dos backups. Evidência: `analytics/target/study-identity-real-results.json`. Nesta execução, 25 dos 92 requisitos possuem evidência automatizada; os demais requisitos futuros não foram declarados concluídos.
