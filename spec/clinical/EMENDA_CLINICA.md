# Emenda clínica — 28/10/2026

Referência prioritária: plano aprovado pelo pesquisador nesta data. O PDF Analytics e seus 66 requisitos permanecem preservados. Esta emenda muda a ordem de execução e acrescenta a pergunta clínica; não declara os eixos anteriores concluídos.

**Pergunta principal:** em adultos e crianças com dengue estabelecida, quais intervenções farmacológicas apresentam evidência de benefício clínico ou alívio sintomático, sinais de dano ou resultados inconclusivos?

O protocolo executável [protocolo.json](protocolo.json) é congelado por hash antes da seleção. Alterar população, busca, desfechos ou método exige outra versão e outro espaço de curadoria. O registro é local à plataforma; não constitui registro em PROSPERO ou outra plataforma externa.

## População e elegibilidade

Incluir intervenções farmacológicas em pacientes com dengue já estabelecida, em adultos e/ou crianças. Preservar a definição e a confirmação diagnóstica usadas pelos autores nas limitações e no suporte documental. Para benefício, priorizar ensaios randomizados. Manter observacionais em camada própria de segurança e contexto; não permitir a categoria de benefício sustentado nessa camada.

Excluir da síntese principal profilaxia, vacinação, voluntários saudáveis, desafio controlado, modelos animais, estudos in vitro/in silico, controle vetorial e diagnóstico isolado. Revisões e editoriais podem orientar busca de referências, mas não fornecem novos participantes nem efeito primário. Hidratação e cuidados de suporte são cointervenções/contexto; não substituem a intervenção farmacológica elegível.

Triagem: dois revisores distintos com votos independentes; desacordo exige terceiro adjudicador. Informação insuficiente permanece incerta. Dois votos incertos não equivalem a inclusão. Fontes novas ou vínculos documentais alterados invalidam a base anterior da revisão. Inclusões não devem ser decididas apenas por um título: buscar o texto permitido e os resultados necessários, registrar motivos e conservar pendências quando o material for insuficiente. Não obter texto por canais sem permissão.

## Resultados e estratos

- Evolução: progressão para dengue grave, complicações, necessidade/duração de internação e mortalidade.
- Sintomas: intensidade/duração da dor e febre, recuperação funcional e outros sintomas definidos.
- Segurança: eventos adversos, graves e interrupções.

Unidade: estudo × comparação × intervenção × comparador × população × gravidade × fase × início da intervenção × população de análise × desfecho/definição × tempo × unidade/medida. Adultos, crianças e populações mistas não são combinados. Resultados pediátricos/adultos separados de um estudo misto exigem suporte específico do subgrupo. Texto livre distinto mantém estratos distintos; harmonização exige revisão, sem fusão semântica automática.

Registrar resultados por braço, denominador analisado, participantes randomizados quando informados, eventos ou média/desvio padrão, cuidados de suporte, limitações, estados de ausência e fontes com offsets. O denominador não pode superar o número randomizado. Não inferir eventos zero de um campo vazio. Sem somatório global de participantes entre documentos, desfechos ou braços potencialmente compartilhados. A identidade e o `comparison_id` precisam ser conferidos pelos revisores, especialmente em estudos com múltiplos braços e publicações.

## Método estatístico e julgamento

RR e IC de 95% por aproximação log-normal somente para braços independentes de ensaio paralelo randomizado, com eventos e denominadores válidos. Células zero ou fronteira degenerada permanecem não estimáveis pelo método implementado, sem correção automática. Interpretar a aproximação com cautela em eventos raros. Diferença de médias usa IC de Welch, com média, desvio padrão e n ≥ 2 por braço. Não converter medianas. Estimativas relatadas RR/OR/HR/MD conservam medida e nível do IC original; não são recalculadas como se fossem efeitos não ajustados.

Sem meta-análise, estimativa combinada, ranking de eficácia, teste de significância da síntese ou categoria inferida de p-valor. Gráficos mostram somente resultados individuais com IC disponível e indicam quantos foram representados. Completude não mede risco de viés. A avaliação metodológica exige nome do instrumento, domínios, justificativa e referências quando marcada como realizada; o software não aplica nem certifica automaticamente RoB 2, ROBINS-I ou GRADE. A escolha e aplicação do instrumento adequado continuam sendo trabalho metodológico dos revisores.

Julgamento final registrado por adjudicador: benefício sustentado, evidência inconclusiva ou sinal de dano, sempre com importância clínica, incerteza, consistência, limitações e justificativa. Benefício exige camada randomizada e avaliação metodológica registrada. A categoria não é definida pelo número de artigos ou pelo cruzamento do IC com a nulidade. Dano pode envolver também piora de desfecho clínico, não apenas eventos adversos.

“Ausência de estudo elegível no corpus” exige calibração documentada, seleção completa e decisão humana para intervenção/população. Não equivale a ausência de estudo na literatura. Um estudo incluído sem resultado extraído não pode gerar essa categoria. Sem resultado revisado, exibir **sem resultados clínicos revisados**, sem atribuir inconclusão artificial.

Conclusões ficam vinculadas ao conjunto de resultados e às decisões que as sustentam. Fonte alterada, nova seleção, novo resultado ou conflito pode exigir nova conclusão. Conflitos de extração bloqueiam o julgamento final até resolução explícita. Rascunhos de correção não retiram resultados aprovados; substituições só entram depois da revisão/adjudicação. Publicações repetidas com mesma comparação são consolidadas; valores divergentes não são resolvidos pela data mais recente.

## Busca e próximo aceite científico

A busca clínica inclui dengue/DENV e termos de tratamento, fármacos, antivirais, analgésicos, antitérmicos e manejo sintomático. ClinicalTrials.gov permanece sensível por condição, sem excluir recrutamentos nem vacinas pela consulta; elegibilidade é decidida na triagem. Sem restrição linguística automática, com obstáculos de tradução/acesso declarados. Publicações e registros não fornecem, por si sós, garantia de elegibilidade.

O novo piloto metodológico contém até 20 registros, 10 por fonte, por conveniência. Definir referências sentinela, revisar elegibilidade e extração, conferir contagens e calibrar a sensibilidade antes de ampliar a busca. O coletor desta entrega limita-se ao piloto. A coleta integral e a síntese final real permanecem pendentes em REQ-CLN-006; o piloto anterior de 50 documentos não é referência adjudicada nem teste experimental independente.

Carga de doença e avaliação de IA passam a prioridade posterior. Tempo até relato não é sobrevida de pacientes. Qualquer meta-análise exige nova emenda e compatibilidade clínica/metodológica demonstrada.

## Rastreabilidade e aceite de software

M08 e REQ-CLN-001 a 005 cobrem protocolo/seleção, cálculos, revisão/proveniência, julgamento e apresentação. REQ-CLN-006 cobre a execução científica ainda pendente. Os testes usam exemplos sintéticos identificados e separados dos dados publicados. Verificação de software não significa conclusão clínica obtida.

REQ-MIG-008 passa a delimitar a independência operacional à leitura pública e aos marts já preparados. Coleta e autenticação da curadoria reutilizam explicitamente o legado nesta etapa. O enunciado anterior foi preservado em `original_statement`; não se declara que a nova curadoria funciona sem o serviço de autenticação Java.

Referências metodológicas: [Cochrane, capítulo 6 — medidas de efeito](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06) e [capítulo 12 — síntese sem meta-análise](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-12). O protocolo incorpora a restrição contra síntese por contagem de resultados estatisticamente significativos.
