# Calibração da busca e síntese clínica por campos

Data: 28/10/2026. Software **0.6.0**. Referências: [plano atual](PLANO_ATUAL_SINTESE_CLINICA.md), [revisão independente](ETAPA_REVISAO_INDEPENDENTE.md) e [extração clínica](ETAPA_EXTRACAO_CLINICA.md).

## Entrega e situação científica

Foram implementados formulários para aprovação metodológica da calibração, conclusão clínica por desfecho/contexto e registro de ausência de estudo elegível no corpus. O fluxo principal deixa de exigir JSON para essas decisões; as ações por contrato continuam disponíveis.

**Nenhuma decisão científica foi criada no corpus real.** O piloto permanece com 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados. A calibração e as conclusões permanecem bloqueadas até a resolução das etapas necessárias. Este documento registra software implementado, sem afirmar que a pesquisa já concluiu benefício ou dano de medicamentos.

## Formulários na curadoria

### Calibração da busca — decisão humana

A tela mostra se a seleção está resolvida e se existe calibração aprovada para o conjunto atual de decisões. O adjudicador escolhe referências sentinela conferidas e documenta achados, limitações e ajustes necessários. É preciso confirmar a conferência humana antes do envio; a aprovação exige papel autorizado e seleção integralmente resolvida.

As referências selecionáveis são estudos/identidades já presentes naquele espaço. Referências externas não são inventadas ou adicionadas automaticamente. A definição prévia de sentinelas e a adequação metodológica da busca continuam exigindo documentação humana. Selecionar um identificador, por si só, não comprova sensibilidade ou validade da busca.

Se a calibração exigir mudar consulta, critérios, desfechos ou métodos, versionar o protocolo e preparar o conjunto correspondente. Não reaproveitar a aprovação de uma versão como se validasse outra estratégia. O botão registra uma decisão local; não inicia coleta completa nem registra protocolo em serviço externo.

### Síntese clínica por desfecho — julgamento humano

O formulário apresenta somente grupos de resultados revisados e aprovados, mantendo intervenção, comparador, população, gravidade, fase, início da intervenção, população de análise, desfecho/definição, período, unidade e medida. Mostra estudos distintos, estimativas e intervalos individuais, avaliação metodológica e limitações.

A categoria começa sem opção escolhida. O adjudicador precisa registrar justificativa, importância clínica, incerteza/precisão, consistência e limitações, além de confirmar que conferiu o grupo inteiro. Não há categoria inferida de p-valor, número de artigos, intervalo de confiança ou completude.

Categorias possíveis: benefício sustentado, evidência inconclusiva ou sinal de dano. A opção de benefício só fica disponível na camada randomizada com avaliação metodológica registrada em todos os resultados do grupo. Essa condição é um requisito mínimo de software, não uma certificação automática da adequação do instrumento, do risco de viés ou da certeza da evidência. A mesma restrição é aplicada na API.

Sem grupos revisados, a tela informa **sem grupos de resultados revisados**. Não preenche “inconclusivo” nem “ausência de estudo” para compensar campos vazios.

### Ausência de estudo elegível no corpus — conferência humana

Exige seleção completa, calibração vigente, papel autorizado, intervenção/população explícitas e justificativa. A confirmação humana diferencia ausência de estudo de resultado ainda não extraído.

A validação é conservadora para populações mistas: se existe estudo incluído da intervenção em população mista sem separação, não permite concluir ausência para adultos ou crianças. A inexistência de resultado extraído daquele estudo também não permite registrar ausência.

O curador deve conferir a identidade normalizada da intervenção e seus sinônimos. A comparação textual implementada não substitui normalização química ou avaliação semântica. A categoria descreve o corpus selecionado, nunca a inexistência de evidência em toda a literatura.

## Guardas na API

As regras se aplicam também a chamadas diretas, independentemente dos botões da interface:

- Corpus vazio não pode receber aprovação de calibração.
- Dois votos incertos não resolvem a seleção; pendências e conflitos precisam ser tratados.
- Aprovação de calibração exige referências conhecidas e sem repetição, além de papel de adjudicador/administrador.
- Conclusão clínica exige seleção completa, calibração vigente e conjunto atual de resultados aprovados; conflitos de extração bloqueiam o julgamento.
- A seleção exibida é conferida novamente no momento da gravação. Formulário de uma seleção anterior é recusado, mesmo que os campos pareçam semelhantes.
- O conjunto de resultados também é conferido por hash. Adicionar resultados ou mudar decisões pode exigir novo julgamento.
- Decisões ficam no histórico e não publicam automaticamente os resultados.

## Mudança de contrato em 0.6.0

`CALIBRATION_APPROVED`, `SYNTHESIS_CONCLUDED` e `ABSENCE_CONCLUDED` passam a exigir `selection_hash`. O hash é obtido em `GET /api/clinical/{workspace}/synthesis` e enviado automaticamente pelos formulários. Conclusões continuam exigindo também `result_set_hash` e o escopo completo do grupo.

Clientes antigos precisam acrescentar esse campo; requisições incompletas são recusadas. Os [exemplos de ações](../analytics/examples/clinical-actions.json) foram atualizados. A verificação ocorre dentro da mesma transação da decisão, evitando aprovar uma seleção alterada entre consulta e envio.

Uma nova decisão de triagem muda a identidade do conjunto de decisões, mesmo quando apenas atualiza a justificativa. A calibração anterior deixa de ser vigente e as conclusões dependentes precisam ser reconferidas. Resultados históricos não são apagados, e snapshots já publicados continuam imutáveis. Julgamentos antigos sem o vínculo à seleção não são reutilizados silenciosamente como conclusões atuais.

O protocolo científico congelado e o formato analítico v3 não foram substituídos. A mudança reforça o controle operacional da sequência já prevista; não introduz meta-análise, ranking ou novo método de avaliação de eficácia.

## Consulta e publicação

Abrir `http://127.0.0.1:8501/`, autenticar na curadoria e selecionar o espaço correto. Os três formulários ficam após extração/revisão dos resultados. Usuários pesquisadores podem consultar pendências, mas somente adjudicadores/administradores autorizados registram essas decisões finais.

O endpoint privado adicional é `GET /api/clinical/{workspace}/synthesis`. Ele apresenta seleção atual, calibração vigente, grupos, bloqueios e permissões. A gravação continua em `POST /api/clinical/{workspace}/actions/{kind}`, com os eventos existentes.

Após uma conclusão válida, usar os comandos já documentados de congelamento, conferência, relatório e publicação para gerar outra execução. O registro de uma conclusão não altera um relatório ou snapshot anterior.

## Validação

**53 testes aprovados**, incluindo PostgreSQL e Quarto reais. Os oito novos cenários verificam seleção/calibração obrigatórias, alteração de seleção, permissões, conflitos, benefício sem avaliação metodológica, populações mistas, sentinelas repetidas, ausência de hash, corpus vazio, consulta privada e formulários com confirmação humana explícita.

Os testes que registram calibração ou conclusões usam dados sintéticos em diretórios temporários. Testes anteriores foram ajustados para executar a sequência metodológica completa antes do julgamento, mantendo as verificações de evidência, independência e invalidação.

A matriz contém 88 requisitos. REQ-CLN-010 acompanha esta entrega de software; REQ-CLN-006 continua pendente da execução científica real. O próximo marco científico permanece executar as duas revisões independentes do piloto, resolver divergências e calibrar a busca antes da coleta final.

Verificação com login real no Chrome: piloto de 20 registros selecionado, 40 votos pendentes, calibração e ausência bloqueadas, nenhum botão de conclusão clínica disponível sem grupos revisados, pacote de revisão preservado por hash e logout sem erros JavaScript. Nenhuma decisão foi enviada ao corpus real. Registros operacionais e captura ficam em `analytics/target/synthesis-browser-results.json` e `analytics/target/synthesis-dashboard.png`, ignorados pelo Git.

Execução publicada com software 0.6.0: `234e2aab4c96ee7ffb287e735439db3bf4d6f4c2a0d3dbf63ec16c0d56239df6`. A entrada clínica conserva o hash `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb`, a auditoria permanece sem votos e as 29 tabelas mantêm os mesmos hashes lógicos da versão anterior. A publicação dessa execução descreve o diagnóstico e as pendências; não representa aprovação da calibração nem obtenção de conclusões terapêuticas.
