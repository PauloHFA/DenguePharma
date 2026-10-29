# Especificação vigente — DenguePharma Analytics

**Acompanhamento 0.14.0:** 96 requisitos: 66 do PDF, 17 MIG e 13 CLN. MIG-017 cobre a [auditoria bibliográfica por PMID](../docs/ETAPA_REFERENCIAS_PUBLICACOES.md), regida pelo [protocolo de referências](reporting/PROTOCOLO_REFERENCIAS.md). Vínculos clínicos conferidos e o restante do eixo B continuam pendentes.

**Acompanhamento 0.13.0:** 95 requisitos: 66 do PDF, 16 MIG e 13 CLN. MIG-016 cobre a [auditoria descritiva de datas](../docs/ETAPA_AUDITORIA_RELATO.md), regida pelo [protocolo específico](reporting/PROTOCOLO_DATAS_REGISTROS.md). O eixo B é parcial; ANA-003 continua planejado, sem censura/Kaplan–Meier implementados.

**Acompanhamento 0.12.0:** 94 requisitos: 66 do PDF, 15 MIG e 13 CLN. MIG-015 cobre o [panorama de patrocinadores dos registros coletados](../docs/ETAPA_PATROCINADORES.md). Patrocinadores por estudo clínico revisado e os demais itens científicos futuros continuam pendentes.

**Acompanhamento 0.11.0:** 93 requisitos: 66 do PDF, 14 MIG e 13 CLN. MIG-014 cobre a [comparação de execuções publicadas](../docs/ETAPA_COMPARACAO_EXECUCOES.md). A comparação descreve atualizações do corpus e não encerra a revisão científica nem os requisitos futuros.

**Acompanhamento 0.10.0:** 92 requisitos: 66 do PDF, 13 MIG e 13 CLN. CLN-013 cobre a [conferência dos vínculos documento–estudo](../docs/ETAPA_IDENTIDADE_ESTUDOS.md) e as invalidações após correções de identidade. A revisão real do piloto continua pendente.

**Acompanhamento 0.9.0:** 91 requisitos: 66 do PDF, 13 MIG e 12 CLN. MIG-013 cobre o [backup da curadoria e sua restauração isolada](../docs/ETAPA_BACKUP_CURADORIA.md), uma parte de M07. O backup integral da aplicação, a migração e a revisão científica continuam pendentes.

**Acompanhamento 0.8.0:** a matriz contém 90 requisitos: 66 do PDF, 12 MIG e 12 CLN. REQ-CLN-012 cobre a [prévia da revisão independente](../docs/ETAPA_PREVIA_REVISAO.md). Verificação do software não encerra a revisão científica; CLN-006 segue pendente.

**Acompanhamento 0.7.0:** a matriz passa a 89 requisitos: 66 do PDF, 12 MIG e 11 CLN. REQ-CLN-011 trata da [coleta completa controlada](../docs/ETAPA_COLETA_COMPLETA.md). A execução científica real e CLN-006 continuam pendentes.

**Acompanhamento 0.6.0:** a matriz contém 88 requisitos (66 do PDF, 12 MIG e 10 CLN). As entregas de apoio incluem revisão, extração e [calibração/síntese por campos](../docs/ETAPA_CALIBRACAO_SINTESE.md). CLN-006 permanece pendente da execução científica humana; verificações de software não concluem a pesquisa nem os requisitos futuros do PDF.

**Emenda prioritária de 28/10/2026:** [síntese clínica](clinical/EMENDA_CLINICA.md), com protocolo executável congelado, seis requisitos CLN e tarefa M08. Benefício, alívio de sintomas e segurança passam a objetivo principal; carga de doença e experimento de IA ficam para etapas posteriores. Os requisitos originais permanecem preservados. Os requisitos CLN de software não equivalem à revisão do corpus; CLN-006 continua pendente de execução científica.

Fonte: **DenguePharma Analytics – Estudo de Data Science sobre Evidências Farmacológicas.pdf**, proposta 2.0. A adoção do PDF completo e a migração para FastAPI, Streamlit e Quarto foram escolhidas pelo usuário em 27/10/2026. Os requisitos v2/v3 em `docs/` permanecem históricos.

`requirements.json` registra os 66 requisitos da seção 8 do PDF, incluindo texto de aceite, prioridade, forma de verificação e rastreabilidade. Os arquivos em `requisitos/` apresentam a leitura por capacidade. Foram acrescentados 12 requisitos MIG para delimitar a primeira entrega, sem renumerar os IDs do PDF.

Estados deste acompanhamento: `planejado`, `parcial`, `implementado`, `verificado`. “Verificado” exige teste associado aprovado no JUnit; não significa aprovação científica do corpus. Requisitos do PDF que dependem das próximas fases continuam planejados, mesmo quando parte do comportamento existe no legado.

Cada requisito possui cenário de aceite identificado. Cenário escrito não equivale a teste executado. A matriz `rastreabilidade.csv` distingue esses cenários dos nomes de testes automatizados efetivos. Não serão criados testes fictícios ou marcados como aprovados apenas para satisfazer uma contagem.

```powershell
analytics\.venv\Scripts\python.exe spec/check.py
analytics\.venv\Scripts\python.exe -m pytest analytics/tests --junitxml=analytics/target/junit.xml
analytics\.venv\Scripts\python.exe spec/check.py --junit analytics/target/junit.xml --verify-foundation
```

A validação reprova IDs desconhecidos, duplicados, aceites ausentes, tarefas inexistentes, matriz divergente ou declaração de verificação sem evidência. A verificação das fases futuras exigirá testes de seus próprios critérios, além dos testes desta fundação.

O CI do primeiro marco verifica a fundação e registra as lacunas dos requisitos futuros. O comando `python spec/check.py --junit analytics/target/junit.xml --release-all` bloqueia a declaração de release completo enquanto qualquer requisito obrigatório do PDF estiver sem teste efetivo e verificação aprovada. Um cenário escrito não libera esse portão.
