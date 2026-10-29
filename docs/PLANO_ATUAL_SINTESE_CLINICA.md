# Plano atual — síntese clínica do DenguePharma Analytics

## 27. Integridade documental da evidência corrente

O [fluxo 0.19.0](ETAPA_INTEGRIDADE_DOCUMENTAL.md) permite registrar alertas humanos e suspender evidências correntes, sem reativar aprovações após regularização. Snapshots e relatórios anteriores são preservados; a apresentação pública atualizada exige nova execução publicada. Os documentos reais não receberam alertas ou votos na validação. Permanecem 40 avaliações independentes faltantes no piloto clínico.

## 26. Redução da espera durante a revisão

A [curadoria 0.18.0](ETAPA_ATUALIZACAO_CURADORIA.md) passou a atualizar uma área independente do dashboard. O ganho foi medido no navegador sem registrar votos, mantendo as consultas privadas e os controles de autorização. Não acrescenta evidência científica: permanecem 40 avaliações independentes faltantes no piloto clínico.

## 25. Trabalho pessoal de revisão

A [fila pessoal 0.17.0](ETAPA_FILA_PESSOAL.md) distingue o trabalho da conta autenticada dos votos globais faltantes, sem reservar vagas ou automatizar decisões. Atualizações documentais e de identidade exigem reavaliação; revisões incertas não resolvem seleção. O piloto clínico mantém 40 avaliações faltantes. O próximo marco científico continua dependendo da leitura e decisão independente dos revisores.

## 24. Documentação dos motivos e contagens da seleção

O [painel privado 0.16.0](ETAPA_FLUXO_SELECAO.md) apresenta estados e motivos principais humanos das exclusões resolvidas, com contagens verificáveis. Não reconstrói o universo da busca a partir do piloto, não considera documentos adicionais como duplicados e não exclui por falta de texto integral. A seleção e a calibração continuam exigindo revisão humana; o piloto clínico mantém 40 avaliações faltantes.

## 23. Leitura das fontes integrada à triagem

O [dossiê documental 0.15.0](ETAPA_DOSSIE_TRIAGEM.md) permite consultar documentos e versões do estudo selecionado antes de preencher a própria decisão. Mantém o cegamento dos votos, as permissões e a base documental atual. Sua entrega não registra avaliações em nome dos revisores e não altera a seleção. Permanecem 40 avaliações independentes faltantes no piloto clínico, sem calibração aprovada ou resultados clínicos revisados.

## 22. Exploração consolidada e reproduzível

O [notebook de pesquisa](ETAPA_NOTEBOOK_PESQUISA.md) foi executado sobre as publicações 0.14.0 dos dois pilotos, separadamente. Os [HTMLs e manifestos](resultados/pesquisa-reprodutivel/README.md) apresentam as análises disponíveis e os limites do corpus, sem gerar conclusões clínicas automáticas. A reprodução foi conferida por hashes das tabelas e saídas das células. Não foi ampliada a coleta nem alterada a seleção.

O próximo marco científico permanece a seleção independente e a extração revisada: faltam 40 avaliações no piloto clínico. Nenhuma evidência clínica foi aprovada nesta entrega. Essa dependência humana não é resolvida por ampliar dashboards ou contar artigos.

Data de referência: 28/10/2026. Este documento consolida o plano aprovado para orientar as próximas etapas do estudo. A [emenda clínica](../spec/clinical/EMENDA_CLINICA.md) e o [protocolo versionado](../spec/clinical/protocolo.json) detalham as regras metodológicas; o [guia de implementação](IMPLEMENTACAO_SINTESE_CLINICA.md) registra o software entregue, os comandos e a validação técnica.

## 1. Objetivo principal

> Em adultos e crianças com dengue já estabelecida, quais intervenções farmacológicas apresentam evidência de benefício clínico ou alívio sintomático, quais apresentam sinais de dano e quais permanecem inconclusivas?

A contribuição principal será a preparação dos dados, a análise reproduzível e a síntese das evidências revisadas. A aplicação apresentará esses resultados por dashboards, tabelas, fichas e relatórios. O estudo poderá concluir que a evidência disponível é insuficiente, sem necessidade de apontar um medicamento vencedor.

O panorama bibliográfico continua útil para descrever o corpus, mas contagens de publicações não medem eficácia. A análise de tempo até relato prevista no PDF mede publicação/disponibilização de resultados, e não sobrevida de pacientes.

## 2. População e limites da síntese

Incluir pacientes com dengue estabelecida e intervenções farmacológicas destinadas a tratar a doença ou aliviar sintomas. Preservar população, confirmação diagnóstica, gravidade, fase da doença, momento de início, comparador e cuidados de suporte.

Adultos e crianças serão analisados separadamente. Populações mistas sem resultados separados formarão estrato próprio, com essa limitação explícita. Resultados de subgrupos só serão utilizados quando estiverem identificados e sustentados pela fonte.

Priorizar ensaios randomizados para benefício. Manter estudos observacionais em camada separada para segurança e contexto. Hidratação e cuidados de suporte serão registrados como cointervenções.

Excluir da síntese principal profilaxia, vacinação, voluntários saudáveis, desafio controlado e estudos pré-clínicos. Revisões podem ajudar a localizar estudos, mas não serão contadas como novos estudos primários ou participantes.

## 3. Desfechos prioritários

| Finalidade | Desfechos |
|---|---|
| Evolução da doença | Progressão para dengue grave, complicações, necessidade e duração de internação, mortalidade |
| Alívio de sintomas | Intensidade e duração da dor e febre, recuperação funcional e outros sintomas definidos |
| Segurança nas duas finalidades | Eventos adversos, eventos graves e interrupções do tratamento |

Definições diferentes de um desfecho e períodos de avaliação diferentes devem permanecer identificados. Não combinar automaticamente contextos, unidades, comparadores ou populações incompatíveis.

## 4. Produto científico esperado

Produzir uma tabela de síntese e fichas rastreáveis por intervenção, comparador, população, desfecho e período de avaliação, mantendo os resultados individuais por estudo e comparação.

Cada ficha deverá apresentar:

- Estudos e participantes disponíveis, com identidade consolidada e sem duplicação entre publicações.
- Resultados por braço, denominadores e estimativa de efeito com intervalo de confiança, quando disponíveis.
- Benefícios e eventos adversos relatados, cuidados de suporte e limitações.
- Dados ausentes, situação de revisão e avaliação metodológica.
- Referências, versões, hashes e localizadores do suporte documental.
- Conclusão humana revisada e justificada para aquele desfecho e contexto.

As categorias de conclusão serão **benefício sustentado**, **evidência inconclusiva**, **sinal de dano** e **ausência de estudo elegível no corpus**. Nenhuma será atribuída automaticamente pelo número de artigos ou por um p-valor isolado. Ausência de estudo exige seleção completa e justificativa humana; não significa inexistência de estudo na literatura.

Enquanto não houver resultados revisados, apresentar **sem resultados clínicos revisados**. Isso não equivale a evidência inconclusiva nem a ausência de benefício.

## 5. Métodos de análise

Combinar seleção sistemática conforme protocolo, análise descritiva e síntese clínica sem meta-análise nesta etapa.

- Calcular risco relativo e intervalo de confiança por estudo apenas quando desenho, braços e dados forem compatíveis com o método implementado.
- Calcular diferença de médias e intervalo de confiança quando média, desvio padrão e denominadores estiverem disponíveis e forem adequados.
- Preservar a medida e o nível de confiança das estimativas publicadas, sem confundir estimativas ajustadas com cálculos não ajustados.
- Gerar gráficos de efeitos individuais e mapas de benefício/incerteza baseados nos julgamentos humanos.
- Preservar ausências: não converter campo vazio em zero, nem mediana em média. Não somar participantes entre documentos, desfechos ou braços potencialmente sobrepostos.

A implementação atual utiliza RR com IC log-Wald e diferença de médias com IC de Welch nos casos previstos pelo protocolo. Células zero e situações incompatíveis não recebem correção ou cálculo automático indevido. Avaliação de risco de viés requer instrumento adequado, domínios e revisão; completude não substitui essa avaliação. Não há GRADE automático.

Não realizar ranking de medicamentos, previsão de eficácia ou combinação estatística dos estudos. Qualquer meta-análise exigirá emenda metodológica prévia e demonstração de compatibilidade dos estudos.

## 6. Sequência de execução e critérios de avanço

| Etapa | Trabalho necessário | Critério para avançar |
|---|---|---|
| 1. Protocolo | Registrar pergunta, critérios, desfechos, busca, corte e métodos antes da seleção final | Versão congelada e alterações posteriores documentadas |
| 2. Calibração | Definir referências sentinela, revisar o piloto de até 20 registros e ajustar critérios, dicionário e busca | Decisões e contagens conferidas, divergências resolvidas e calibração documentada |
| 3. Coleta final | Ampliar a coleta conforme a estratégia calibrada, preservando respostas, versões e proveniência | Coleta reproduzível, com limites e falhas registrados; não apenas os primeiros resultados |
| 4. Seleção e identidade | Executar triagem independente, adjudicar divergências e confirmar vínculos entre registros/publicações | Estudos elegíveis consolidados, exclusões justificadas e pendências explícitas |
| 5. Extração e avaliação | Obter textos por canais permitidos, extrair por braço/comparação/população/tempo, revisar e avaliar metodologia | Valores conferidos nas fontes, revisão independente e adjudicação registradas |
| 6. Síntese | Gerar tabelas e gráficos individuais; justificar benefício, incerteza ou dano por desfecho | Conclusões vinculadas ao conjunto atual de resultados revisados e sem conflitos não resolvidos |
| 7. Publicação | Congelar nova execução, conferir artefatos e publicar dashboards e relatório científico | Filtros, unidades, denominadores, fontes, limitações e manifesto disponíveis |

A estratégia da busca poderá mudar após a calibração, mas a alteração deverá gerar nova versão documentada. A seleção dos primeiros registros por fonte é uma amostra de conveniência e não substitui a coleta final.

## 7. Situação registrada na entrega de 28/10/2026

| Componente | Situação |
|---|---|
| Protocolo clínico e emenda de escopo | Documentados e versionados localmente |
| Curadoria, revisão independente e adjudicação | Software implementado; interface inicial por formulário JSON orientado por contrato |
| Cálculos individuais, tabelas, fichas, gráficos e relatório | Implementados e testados; resultados reais dependem de revisão |
| Piloto operacional anterior | 50 documentos preservados; não constitui referência adjudicada |
| Novo piloto clínico | 20 registros coletados: 10 PubMed + 10 ClinicalTrials.gov, corte de 28/10/2026 |
| Calibração científica e seleção do novo piloto | Pendentes de revisão independente e adjudicação |
| Corpus clínico final e conclusões sobre intervenções | Ainda não produzidos |

A entrega de software teve 24 testes aprovados, incluindo PostgreSQL, Quarto e verificação da interface no navegador, conforme o guia de implementação. Esses testes não comprovam eficácia de intervenções nem substituem a avaliação científica do corpus.

Os requisitos CLN-001 a CLN-005 acompanham o software; **REQ-CLN-006** acompanha a execução científica ainda pendente. O registro do protocolo é local à plataforma e não constitui registro externo em PROSPERO ou serviço equivalente.

## 8. Infraestrutura e responsabilidades

Manter a migração gradual no mesmo repositório: Python para preparação e análises, FastAPI para serviços, Streamlit para visualização e curadoria protegida e Quarto para relatórios. Reaproveitar coletores, armazenamento e processamento existentes, preservando dados, decisões, identificadores e snapshots históricos.

Na etapa atual, a coleta e a autenticação reutilizam serviços legados. A curadoria clínica tem espaço privado próprio, e a leitura dos resultados publicados permanece aberta. Os detalhes operacionais e a arquitetura efetivamente entregue estão no guia de implementação.

A coleta, a preparação e os cálculos podem ser executados pelo software. A calibração, a interpretação das fontes, a avaliação metodológica e as conclusões exigem trabalho humano documentado. O fluxo de resultados exige autor, revisor e adjudicador com identidades distintas; não criar aprovações automáticas para substituir essa independência.

Nenhuma API paga de IA é necessária para esta etapa. A avaliação experimental de IA e a integração com carga de doença ficam para depois. O experimento antigo não será reativado como substituto desse protocolo clínico.

## 9. Aceite final do estudo

- Busca calibrada e coleta final reproduzível, com corte temporal e limitações declarados.
- Seleção independente e divergências adjudicadas.
- Identidade dos estudos e participantes conferida, evitando duplicação indevida.
- Resultados científicos revisados, sustentados por fontes permitidas e rastreáveis.
- Contagens, denominadores, unidades e cálculos conferidos; ausências preservadas.
- Avaliação metodológica registrada e conclusões justificadas por desfecho/contexto.
- Equivalência entre execução por comando e resultados apresentados na aplicação.
- Execução publicada e versionada, com dados exportáveis conforme as licenças e relatório de reprodução.

**Próximo marco:** revisar e calibrar o piloto clínico de 20 registros antes de ampliar a coleta. O resultado final será uma síntese das evidências disponíveis sobre benefício, sintomas e segurança, podendo demonstrar insuficiência de evidência, sem prometer identificar o melhor medicamento para dengue.

## 10. Continuidade da implementação — versão 0.3.0

O [diagnóstico de calibração](CONTINUIDADE_CALIBRACAO.md) acrescenta sinais literais rastreáveis, tipos declarados de intervenção, resultados gerais exportáveis e triagem por campos. Os [resultados descritivos obtidos](RESULTADOS_GERAIS_PESQUISA.md) estão disponíveis no dashboard e em `docs/resultados/`. Nenhum desses recursos executa revisão ou aprovação científica automática. O próximo marco humano e REQ-CLN-006 continuam pendentes; não houve ampliação da coleta nem mudança do protocolo congelado.

## 11. Apoio à execução da revisão — versão 0.4.0

A [etapa de revisão independente](ETAPA_REVISAO_INDEPENDENTE.md) acrescenta pacote privado com planilha em branco, importação autenticada/atômica, painel de pendências e gerador de localizadores literais. O pacote real do piloto de 20 documentos está preparado; faltam 40 votos iniciais e eventual adjudicação. A ferramenta não substitui revisores humanos e não aprova calibração automaticamente. A prioridade científica continua sendo executar essa revisão antes de ampliar a coleta.

## 12. Extração e revisão por campos — versão 0.5.0

A [extração clínica por campos](ETAPA_EXTRACAO_CLINICA.md) acrescenta entrada por braço/desfecho/tempo, referências por ocorrência, prévia sem gravação e formulários de revisão/adjudicação. O acesso à extração depende da seleção independente concluída para cada estudo. A validação atualiza a compatibilidade com a classificação consolidada e preserva snapshots anteriores. O piloto real permanece sem estudos incluídos ou resultados revisados; não houve avanço automático da etapa científica.

## 13. Calibração e síntese por campos — versão 0.6.0

A [calibração e síntese clínica](ETAPA_CALIBRACAO_SINTESE.md) acrescenta formulários de decisão metodológica, conclusão justificada por desfecho e ausência no corpus. Aprovações passam a exigir o hash da seleção atual; conclusões exigem seleção completa, calibração vigente e resultados revisados. Estudos mistos impedem declarar ausência indevida para adultos/crianças. Os bloqueios também são aplicados na API. O corpus real permanece pendente de revisão humana, sem conclusões automáticas.

## 14. Coleta completa controlada — versão 0.7.0

A [coleta completa controlada](ETAPA_COLETA_COMPLETA.md) acrescenta plano privado, estratégia e corte congelados, retomada por IDs, reconciliação de respostas perdidas e exportação de metadados pelo PostgreSQL somente de leitura. A execução depende da seleção e calibração humanas vigentes. O snapshot novo não transfere votos ou resultados aprovados e não é publicado automaticamente. O piloto real mantém 20 registros, 40 votos iniciais pendentes e zero resultados clínicos revisados; o próximo marco científico permanece a revisão independente.

## 15. Conferência da revisão independente — versão 0.8.0

A [prévia da revisão independente](ETAPA_PREVIA_REVISAO.md) permite conferir CSVs sem gravar votos e confirmar a importação com recibo vinculado à base atual. A melhoria facilita a execução humana do piloto, preservando independência, validação atômica e rastreabilidade. O próximo marco científico permanece revisar os 20 registros e registrar a calibração; não houve coleta adicional ou conclusão clínica automática.

## 16. Preservação da curadoria — versão 0.9.0

O [backup e a restauração isolada](ETAPA_BACKUP_CURADORIA.md) preservam a curadoria antes das revisões reais. Cópias dos dois pilotos foram restauradas com os mesmos snapshots, fontes e auditoria, sem sobrescrever ou publicar dados. Esta entrega operacional não altera a pergunta científica, não cria votos e não libera a coleta completa. A próxima etapa científica permanece a revisão independente e a calibração do piloto clínico.

## 17. Identidade documental — versão 0.10.0

A [conferência da identidade dos estudos](ETAPA_IDENTIDADE_ESTUDOS.md) acrescenta prévia e confirmação dos vínculos, correção auditável e bloqueios para ambiguidades. A mudança protege a unidade de contagem e exige nova revisão após alterar a identidade, inclusive ao desfazer vínculos. Os pilotos reais permaneceram iguais; a seleção independente e a calibração continuam sendo o próximo marco científico.

## 18. Acompanhamento de atualizações — versão 0.11.0

A [comparação entre execuções publicadas](ETAPA_COMPARACAO_EXECUCOES.md) permite registrar mudanças do corpus, suas referências e suas tabelas, com escopo compatível e exportações reproduzíveis. As comparações reais entre as versões 0.6.0 e 0.8.0 confirmaram preservação dos dados, sem nova coleta ou resultado clínico. A revisão independente e a calibração continuam sendo o próximo marco científico.

## 19. Panorama dos patrocinadores — versão 0.12.0

A [análise de patrocinadores declarados](ETAPA_PATROCINADORES.md) amplia o diagnóstico documental com dados reais e rastreáveis, separando ausência e conflito. Trata-se do corpus coletado, ainda sujeito à elegibilidade, sem inferência sobre eficácia, financiamento efetivo ou risco de viés. A nova publicação é de metadados e não transporta aprovações clínicas. A seleção independente e a calibração do workspace original continuam pendentes.

## 20. Auditoria de relato — versão 0.13.0

A [auditoria descritiva de datas](ETAPA_AUDITORIA_RELATO.md) reutiliza os metadados congelados para analisar disponibilidade declarada, precisão, conflitos e intervalos entre pares válidos. Não inclui censura/Kaplan–Meier nem sobrevida dos pacientes. Os resultados são suplementares ao estudo principal e não alteram a pendência de revisão independente e calibração.

## 21. Cobertura bibliográfica — versão 0.14.0

A [auditoria por PMID](ETAPA_REFERENCIAS_PUBLICACOES.md) identifica referências já representadas ou não localizadas entre os documentos coletados, com códigos da fonte e proveniência. A lista é material para conferência e calibração, sem obrigatoriedade de inclusão, coleta automática ou confirmação clínica. O próximo marco científico continua sendo a seleção independente e a revisão dos resultados elegíveis.
