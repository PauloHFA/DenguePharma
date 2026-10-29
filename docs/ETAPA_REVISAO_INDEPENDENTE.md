# Etapa de apoio à revisão independente do piloto

**Atualização 0.8.0:** o fluxo atual de importação está no [guia de prévia da revisão](ETAPA_PREVIA_REVISAO.md): conferir sem gravar, confirmar a autoria e importar com recibo válido. As instruções abaixo registram a entrega 0.4.0.

Data: 28/10/2026. Software **0.4.0**. Referências: [plano atual](PLANO_ATUAL_SINTESE_CLINICA.md) e [diagnóstico de calibração](CONTINUIDADE_CALIBRACAO.md).

## Objetivo e limite

Transformar o diagnóstico do corpus em material utilizável pelos revisores: fila de pendências, planilha independente, importação auditável e suporte à localização dos trechos. Esta etapa prepara e organiza a revisão; não substitui a leitura das fontes, não aprova calibração e não conclui eficácia de medicamentos.

O piloto clínico mantém 20 documentos e 20 identidades de estudo ainda pendentes de seleção. Há **40 votos iniciais faltantes**, correspondentes a duas revisões independentes por identidade. Conflitos poderão exigir terceiro adjudicador. A identidade dos estudos e os vínculos documentais também devem ser conferidos; esses números não representam 20 estudos clínicos elegíveis.

## Funcionalidades entregues

| Recurso | Comportamento |
|---|---|
| Painel privado de progresso | Mostra seleção resolvida, votos ainda faltantes, pendências, conflitos e aprovação de calibração vinculada à seleção atual |
| Pacote de revisão independente | ZIP reproduzível com planilha humana vazia, referências versionadas, protocolo, contratos de campos e manifesto de hashes |
| Importação de triagem | Registra somente decisões do usuário autenticado, em transação única, sem adjudicar nem publicar |
| Reenvio idêntico | Reconhece decisões já registradas pelo próprio revisor, sem duplicar eventos |
| Gerador de localizadores | Retorna trecho literal, posições e hash da representação textual, com referência à versão e ao hash original |
| Identificação dos espaços | Mostra código do protocolo e número de documentos, priorizando os snapshots mais recentes para distinguir os pilotos de 20 e 50 documentos |

## Pacote gerado

Arquivo local privado: `analytics/data/review-packages/clinical-pilot-20.zip`.

SHA-256: `ba65acbd0d4213460ed3162eb909c9160117f08c03d40e299625517c0ec02666`.

Espaço clínico: `98043ff1652d98455adf3a115125cff18b89967a6c90f15545d87cb880f33e0e`.

Conteúdo:

- `screening_template.csv`: metadados de identificação e hashes, com campos de decisão, classificação, intervenções e justificativa inicialmente vazios.
- `sources.csv`: documentos, versões, hashes do conteúdo original e do texto normalizado, licença e acesso registrados.
- `protocol.json`: cópia do protocolo congelado.
- `classification_schema.json` e `result_schema.json`: valores e estrutura aceitos para triagem e futura extração.
- `manifest.json`: identificação do espaço, entrada, protocolo, estado da auditoria e hashes dos arquivos.
- `README.md`: instruções de preenchimento e importação.

O pacote não contém votos alheios, decisões anteriores, identidades dos revisores, resumos ou textos integrais. As fontes privadas continuam acessíveis na curadoria conforme o acesso permitido. O ZIP permanece fora do versionamento Git e não é disponibilizado como artefato público de análise.

## Fluxo para os revisores

1. Abrir `http://127.0.0.1:8501/`, expandir **Curadoria clínica — acesso protegido** e autenticar com a própria conta.
2. Selecionar o espaço do protocolo `CLINICAL-CALIBRATION` com 20 documentos; não confundir com o piloto operacional anterior de 50 documentos.
3. Em **Preparar e acompanhar a revisão do piloto**, conferir as pendências e preparar/baixar o pacote independente.
4. Consultar as fontes permitidas. Cada revisor deverá preencher sua própria planilha ou usar a triagem por campos, sem copiar decisões do outro.
5. Preencher somente as linhas efetivamente revisadas. Preservar cabeçalhos e identificadores; usar os códigos do contrato e uma lista JSON em `interventions_json`, como `[]` ou `["nome"]`.
6. Salvar CSV UTF-8 separado por vírgulas. Importar pela própria sessão e confirmar que as decisões representam sua revisão independente.
7. Atualizar a fila, conferir os resultados da importação e adjudicar divergências com terceiro usuário independente, quando necessário.
8. Após seleção resolvida, documentar referências sentinela e calibração. A conclusão da seleção, isoladamente, não aprova a calibração nem inicia coleta final.

Use os estados de incerteza permitidos quando a informação não estiver disponível; não adivinhe campos para completar a planilha. Uma decisão de inclusão exige classificação compatível com pacientes com dengue estabelecida e intervenção farmacológica. Dois votos incertos deixam a seleção sem resolução.

O campo `decision` aceita somente `INCLUIR`, `EXCLUIR` ou `INCERTO`. Os demais códigos estão no contrato da classificação. Uma linha concluída deve preencher todos os campos humanos exigidos; as linhas não revisadas devem conservar esses campos inteiramente vazios.

## Regras de importação

- Identidade e papéis vêm da autenticação; não existem colunas para escolher outro revisor ou conceder permissões.
- Campos humanos inteiramente vazios são ignorados. Linhas parcialmente preenchidas são recusadas.
- Workspace, hash da entrada, protocolo e base documental de cada decisão precisam corresponder ao estado atual.
- Qualquer erro recusa o lote inteiro, inclusive decisões anteriores válidas dentro daquele mesmo lote.
- Reenvio de conteúdo já idêntico para o mesmo revisor não duplica eventos; uma decisão corrigida gera novo evento, preservando o histórico.
- Uma terceira pessoa não pode se passar por um dos dois revisores. A adjudicação continua sendo uma ação separada, com suas verificações de independência.
- Limites desta versão: 1 MiB por CSV, até 100 decisões preenchidas por lote e até 10.000 linhas de dados. Não há suporte a importação de votos de terceiros ou aprovação automática de resultados.

Se fontes ou vínculos documentais mudarem, as bases antigas deixam de ser válidas. Gere novo pacote e revise o material alterado. Não troque apenas o hash na planilha para reaproveitar uma revisão sem conferir a fonte.

## Localizadores para a extração

Na área **Fontes permitidas e localizadores**, selecione a versão e marque a exibição do texto normalizado. Informe o campo sustentado e o intervalo: início inclusivo e fim exclusivo, em caracteres Unicode. O gerador preserva espaços e o texto literal, sem recalcular posições em bytes ou na paginação do PDF.

O retorno pode ser usado na lista `evidence` de um rascunho de resultado. O gerador não avalia se o trecho sustenta semanticamente o campo e não aprova o resultado. A validação de números, a revisão independente e a adjudicação continuam obrigatórias. A extração avançada permanece no contrato já implementado; esta etapa acrescenta o auxílio à referência documental.

## Comandos e API

Comandos locais, sem criar contas ou votos:

```powershell
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-progress --workspace 98043ff1652d98455adf3a115125cff18b89967a6c90f15545d87cb880f33e0e
analytics/.venv/Scripts/python.exe -m denguepharma_analytics.cli clinical-review-package --workspace 98043ff1652d98455adf3a115125cff18b89967a6c90f15545d87cb880f33e0e --output analytics/data/review-packages/clinical-pilot-20.zip
```

Os comandos leem o espaço privado sob autorização local do operador. Não registram esse operador como revisor. Um arquivo de saída existente só é reutilizado se os bytes forem idênticos; para pacote atualizado, escolher outro nome.

Endpoints adicionais, todos autenticados e sujeitos aos papéis de curadoria:

- `GET /api/clinical/{workspace}/progress`
- `GET /api/clinical/{workspace}/review-package`
- `POST /api/clinical/{workspace}/screening/import`, corpo `text/csv`
- `POST /api/clinical/{workspace}/locators`, corpo JSON com `version_id`, `field`, `start` e `end`

## Validação e situação científica

**37 testes aprovados**, incluindo PostgreSQL e Quarto reais. Novos cenários verificam pacote reproduzível e sem votos/textos, hashes, rollback integral, reenvio idêntico, dados incompletos, escopo errado, duplicatas, bases alteradas, votos incertos, permissões, equivalência CLI/API e preservação de Unicode/espaços nos trechos.

A matriz passa a conter 86 requisitos. REQ-CLN-008 acompanha este apoio operacional; REQ-CLN-006 permanece pendente de execução científica humana. Nenhum voto, decisão de elegibilidade, aprovação de calibração ou resultado clínico foi criado no corpus real durante os testes. Os cenários que importam decisões usam exclusivamente dados sintéticos em diretórios temporários.

Os resultados gerais anteriores permanecem válidos como diagnóstico dos mesmos snapshots: 20 documentos coletados, zero resultados clínicos revisados e necessidade de calibração antes da coleta final. Esta entrega não amplia a busca nem altera o protocolo científico congelado.

Verificação operacional adicional: autenticação real, seleção padrão do piloto mais recente de 20 documentos, 40 votos pendentes, download com hash idêntico ao CLI, localizador somente de leitura e logout no Chrome, sem erros JavaScript e sem envio de decisões reais. Registros e captura ficam em `analytics/target/review-browser-results.json` e `analytics/target/review-dashboard.png`, ignorados pelo Git.

Execução publicada com software 0.4.0: `5226246b3ed169300e2beb5d07c5865ca08c3db9f300489ef56801ec33b5ed5d`. O hash da entrada clínica permanece `6170bd7583d266c2954a503b630098e7d8c32fbbbbb248f3984ce106077e24eb` e a auditoria do corpus real continua sem votos. Os novos resultados operacionais não alteram as conclusões científicas registradas anteriormente.
