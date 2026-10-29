# Integridade documental — versão 0.19.0

Entrega de 28/10/2026. Foi implementado um fluxo humano para registrar retratações, correções relevantes e outros alertas documentais. O objetivo é impedir que aprovações anteriores continuem sendo usadas na curadoria atual quando a base documental precisar de nova conferência.

O fluxo pertence à curadoria clínica Python. Não altera estados no PostgreSQL, no catálogo ou na curadoria legada Java.

Método e limites: [contrato de integridade documental](../spec/clinical/INTEGRIDADE_DOCUMENTAL.md).

## Como usar

No [dashboard local](http://127.0.0.1:8501/), abrir **Curadoria clínica — acesso protegido → Integridade documental — retratações e correções**. Revisores consultam os estados. Adjudicadores ou administradores podem:

1. Selecionar o documento, a situação e o tipo de alerta, inicialmente vazios.
2. Informar a referência HTTPS do aviso consultado e a justificativa documental.
3. Conferir a prévia de impacto nas revisões, nos resultados e na calibração.
4. Confirmar explicitamente a conferência humana para registrar o evento.

Não registrar um alerta com base apenas em suspeita não documentada como se fosse uma retratação confirmada. Para material que precisa ser conferido, existe `EM_REAVALIACAO`. O sistema valida os campos, as permissões e o estado, mas não acessa a referência para certificar seu conteúdo.

## Comportamento entregue

`EM_REAVALIACAO` e `RETIRADO` suspendem a inclusão e o uso dos resultados do estudo/identidade atual do documento. A mudança da base invalida revisões antigas e exige nova conferência. O dossiê mostra o alerta; os documentos e representações continuam disponíveis para leitura.

`REGULARIZADO` exige bloqueio anterior e justificativa nova. Não restaura aprovações antigas: continuam necessárias novas revisões na base atual. O alerta acompanha o documento quando seu vínculo de identidade é corrigido.

Os eventos são preservados na auditoria e em backup/restauração. A confirmação exige o recibo da prévia atual, ligado ao aviso, à conta e ao estado. Votos, fontes ou vínculos alterados exigem outra prévia. O resumo analítico de uma nova execução registra a existência de documentos bloqueados, sem expor justificativas livres ou nomes de revisores.

**A publicação é separada:** o alerta afeta imediatamente a curadoria e os novos snapshots. Para atualizar os resultados apresentados ao público, é necessário preparar e publicar uma nova execução. Relatórios históricos não são retirados ou reescritos automaticamente. O painel e a prévia deixam essa limitação explícita.

## O que foi conferido nos dados reais

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos preservados | 20 | 50 |
| Alertas humanos registrados | 0 | 0 |
| Novos votos ou eventos na validação real | 0 | 0 |
| Avaliações independentes faltantes | 40 | 100 |
| Hash do snapshot clínico preservado | Sim | Sim |

Os hashes permanecem `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb` e `8c302d1840a70e2309586c6cf0a29e21138790ea5101b87ead75dd84daa90aec`, respectivamente. **Zero alertas registrados não demonstra ausência de retratações ou correções na literatura.** Nenhum documento real foi marcado para validar a funcionalidade.

## Verificação

Dez casos novos usam somente dados sintéticos para conferir prévia sem escrita, impacto quantificado, retirada de resultados atuais, regularização sem reativação, recibos desatualizados, mudança de identidade, permissões, referência inválida, preservação da publicação histórica, nova publicação sem resultados bloqueados, backup/restauração, confirmação humana e recusa de snapshots inconsistentes.

A bateria completa passou: **154 testes**, incluindo PostgreSQL e Quarto reais. A matriz continua com 96 requisitos e 29 com evidência automatizada; CLN-003 recebeu os dez cenários novos. No Chrome, foram conferidos login real, painel, restrição por papel, ausência de confirmação sem prévia e saída da sessão, sem erro de página. Nenhum alerta ou voto real foi enviado. As duas publicações 0.14.0 continuam íntegras.

Evidências técnicas locais, fora do Git:

- `analytics/target/document-integrity-full-junit.xml`.
- `analytics/target/document-integrity-real-results.json`.
- `analytics/target/document-integrity-browser-results.json`.

Os testes não constituem confirmação de retratação de um estudo real. O módulo não detecta retratações automaticamente nem consulta novas APIs. O requisito original do PDF permanece planejado no escopo completo de atualização das fontes e publicações; CLN-003 registra o incremento operacional.

## Situação científica

O piloto clínico ainda requer 40 avaliações humanas independentes; não há resultados clínicos aprovados. A etapa acrescenta controle de integridade para as futuras evidências, sem gerar uma conclusão sobre eficácia, segurança ou melhor medicamento. Os [relatórios publicados anteriormente](resultados/pesquisa-reprodutivel/README.md) continuam preservados.
