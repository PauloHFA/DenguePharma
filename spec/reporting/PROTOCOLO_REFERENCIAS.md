# Auditoria bibliográfica por PMID

Método `registry-publication-reference-audit-1`, versão de software 0.14.0, definido em 28/10/2026.

Escopo: referências presentes no JSON congelado de registros coletados, com elegibilidade pendente. Não busca artigos, não confirma vínculo clínico, não reclassifica referências e não altera a curadoria.

Os registros são consolidados por NCT válido ou ID documental. As publicações são localizadas apenas por PMID numérico positivo informado no campo próprio; espaços e zeros à esquerda são normalizados. Identificadores ausentes, inválidos e tipos de referência não informados permanecem separados. Não se combinam DOI, título, semelhança textual ou instituição como confirmação automática.

Cada relação válida usa a chave registro × código de referência × PMID, preservando todas as observações, índices na lista original e versões/hash das fontes. Referências sem PMID utilizável mantêm sua ocorrência por documento/versão/índice; não são deduplicadas por texto. Publicações repetidas com o mesmo PMID contam um PMID para cobertura, preservando os documentos correspondentes.

`RESULT`, `DERIVED` e `BACKGROUND` são códigos da fonte, sem inferência de relevância clínica. Outras categorias são conservadas. Um mesmo PMID pode ocorrer em mais de um código; não se somam categorias como publicações únicas.

Indicadores por código:

- Registros com referências / todos os registros consolidados.
- Registros com PMID válido ou candidato no corpus, com a unidade explícita.
- PMIDs válidos distintos e PMIDs encontrados entre as publicações do corpus.
- Cobertura por PMID = PMIDs encontrados / PMIDs válidos distintos daquele código.
- Referências sem PMID utilizável permanecem contabilizadas separadamente.

Denominador zero produz `null`. O código RESULT ausente no snapshot não implica ausência de publicação de resultados, mesmo quando `hasResults` é verdadeiro. O indicador de resultados no registro, as referências declaradas e a confirmação de publicação são variáveis distintas.

Validade de PMID significa formato numérico positivo, sem verificação externa de existência. A cobertura compara identificadores presentes no snapshot, sem reconstrução histórica no corte. Uma publicação pode estar representada por outro identificador e ainda não ser localizada pelo método; documentos sem PMID utilizável são contabilizados.

Um PMID coincidente produz somente `CANDIDATO_NO_CORPUS`. Ausência entre os documentos coletados produz `NAO_RECUPERADO_NO_CORPUS`; não significa ausência na literatura ou inexistência de resultados. Não há aprovação de identidade, relevância, suporte semântico, eficácia ou segurança.

O artefato de lacunas reúne PMIDs ainda não recuperados, com links para consulta e proveniência. Não agenda coleta nem amplia silenciosamente o piloto; recuperação e seleção seguem o protocolo autorizado e as licenças permitidas. Vínculos clínicos conferidos e discrepâncias registro/publicação continuam pendentes no eixo B.
