# Protocolo de auditoria das datas dos registros

Versão `registry-reporting-audit-1`, definida em 28/10/2026 para a entrega 0.13.0. É uma análise descritiva suplementar do corpus coletado, com elegibilidade pendente. Não substitui o protocolo clínico nem conclui REQ-ANA-003.

Unidade: registro consolidado por NCT válido, ou por ID documental quando o NCT está ausente/inválido. Fontes repetidas preservam referências e observações; valores divergentes não são escolhidos pela data mais recente. Não é uma garantia de identidade clínica única entre registros distintos.

Indicadores de disponibilidade refletem `hasResults` e `overallStatus` da versão documental congelada. Não reconstituem historicamente o estado de todos os registros no corte. O indicador de resultados e a existência de publicação vinculada são variáveis distintas; publicações não são inferidas nesta etapa.

O intervalo de calendário usa origem `primaryCompletionDateStruct.date` e término `resultsFirstPostDateStruct.date`. É calculado somente quando:

- O status declarado é `COMPLETED` e `hasResults` é explicitamente verdadeiro.
- Não há conflito nos campos usados.
- O corte é uma data válida com precisão diária.
- Conclusão primária, primeiro depósito e última atualização têm precisão diária e tipo `ACTUAL`.
- Essas três datas não são posteriores ao corte.
- O primeiro depósito não é anterior à conclusão primária.

Datas `ESTIMATED`, tipos ausentes, mês/ano, valores inválidos e contradições permanecem identificados. Não se completa mês/ano com o primeiro ou último dia. Depósito anterior à conclusão pode refletir relato parcial, não necessariamente erro; o caso exige conferência e fica fora do intervalo definido.

Um intervalo de zero dias é válido quando ambas as datas diárias são iguais e os demais critérios são atendidos. Ausência nunca vira zero. `hasResults=false` não é convertido em evento nem em censura. Resultados indicados como disponíveis sem data válida não são classificados como não relatados.

Resumo numérico: n de pares calculáveis, mínimo, máximo, mediana e quartis pandas sobre esses pares. Não são somados participantes. O gráfico mostra mediana e intervalo interquartil, sem intervalo de confiança. A seleção dos pares pode introduzir viés; esse resumo não estima o atraso de todo o corpus.

Disponibilidade por status usa tabela cruzada com categorias de resultados fixas (`DISPONIVEL`, `NAO_DECLARADO_DISPONIVEL`, `NAO_INFORMADO`, `CONFLITO`), preservando células zero. Denominadores são explícitos, e zeros significam ausência de registros naquela célula, não ausência de evidência na literatura.

Não há Kaplan–Meier, censura, modelos associados, testes de significância, avaliação de cumprimento legal de prazos, conclusão de eficácia ou análise da sobrevida dos pacientes. Essas extensões exigem critérios e validação próprios, além da seleção e conferência necessárias ao protocolo científico.
