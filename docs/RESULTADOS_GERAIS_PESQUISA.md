# Resultados gerais da pesquisa — DenguePharma Analytics

Referência: 28/10/2026. Versão de software: 0.3.0.

Execução: `ad0c3d88b792684e14f3b5cc40f60e36deeccb7aac63f97bc01fbbb057b33361`.

Dashboard: http://127.0.0.1:8501/ — aba **Resultados gerais**.

Este registro descreve o piloto clínico de 20 documentos. O piloto operacional anterior de 50 documentos continua preservado e não deve ser somado como se todos os documentos fossem estudos distintos. Os [CSVs e o gráfico](resultados/README.md) permitem conferir os números e consultar as fontes. Os [detalhes da implementação e validação](CONTINUIDADE_CALIBRACAO.md) registram as limitações desta etapa.

## Resultados gerais — diagnóstico do corpus

**Resultados descritivos do snapshot; não constituem síntese de eficácia.**

Entrada: `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb`.
Corte registrado: 2026-10-28.

| Indicador | Resultado |
|---|---:|
| Documentos deduplicados | 20 |
| Publicações | 10 |
| Registros de ensaio | 10 |
| Resultados clínicos revisados | 0 |

## Registros de ensaio

- Desenho declarado — INTERVENTIONAL: 8/10.
- Desenho declarado — OBSERVATIONAL: 2/10.
- Situação declarada — ACTIVE_NOT_RECRUITING: 1/10.
- Situação declarada — COMPLETED: 8/10.
- Situação declarada — TERMINATED: 1/10.
- Resultados disponíveis no registro — False: 4/10.
- Resultados disponíveis no registro — True: 6/10.

Disponibilidade de resultados não comprova benefício nem confirma elegibilidade. Os registros podem incluir vacinas, prevenção, desafio controlado ou outros contextos.

## Sinais para calibração

Sinais automáticos de metadados, não revisados e não exclusivos. Não são decisões de inclusão/exclusão. Ausência de sinal não confirma elegibilidade. Resultados no registro não comprovam benefício clínico.

| Sinal | Documentos / total |
|---|---:|
| Menção a vacina | 6/20 |
| Menção a desafio/infecção humana controlada | 2/20 |
| Menção a vetores | 3/20 |
| Tipo ou título de revisão | 3/20 |
| Menção a rastreio/diagnóstico | 1/20 |
| Menção ou finalidade declarada de prevenção | 10/20 |

Documentos com pelo menos um sinal: 17/20. Categorias se sobrepõem; não somar como exclusões.

Tipos de intervenção são os declarados pelo registro. DRUG e BIOLOGICAL não são sinônimos de terapia elegível; OTHER não deve ser interpretado como substância farmacológica.

## Busca e limites

- PUBMED: 10 documentos no conjunto; total informado pela execução da busca: 7765.
- CLINICALTRIALS: 10 documentos no conjunto; total informado pela execução da busca: 322.

Os totais das buscas são históricos, amplos e específicos de cada fonte. Não somá-los como estudos únicos ou elegíveis. A fração recuperada não mede representatividade ou sensibilidade da busca.

## Conclusão permitida nesta etapa

Há material coletado para calibração, mas nenhum resultado clínico revisado. Não é possível apontar medicamentos benéficos, prejudiciais ou inconclusivos para pacientes com dengue com base nesta execução.

Próxima etapa: conferir referências sentinela, revisar o piloto de forma independente e calibrar a busca antes da coleta final. Zero campos revisados não significa ausência de efeito ou de estudos na literatura.
