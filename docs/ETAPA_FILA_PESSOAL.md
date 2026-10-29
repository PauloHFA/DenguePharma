# Fila pessoal de revisão — versão 0.17.0

Entrega de 28/10/2026. A curadoria passa a separar o trabalho da conta autenticada das pendências globais do estudo. Isso facilita a revisão independente sem registrar votos automaticamente ou usar sinais científicos para ordenar a leitura.

## Como usar

1. Abrir o [dashboard local](http://127.0.0.1:8501/) e entrar em **Curadoria clínica — acesso protegido** com a própria conta.
2. Selecionar o piloto clínico com 20 documentos.
3. Conferir **Preparar e acompanhar a revisão do piloto**: o painel mostra a carga pessoal, além dos votos globais faltantes.
4. Em **Triagem por campos — revisão humana**, usar **Mostrar na minha fila**. O filtro inicial é **Minha revisão pendente**.
5. Ler o dossiê e as fontes permitidas, preencher a própria decisão e justificativa e salvar. O formulário atualiza a fila e abre a próxima pendência disponível. Não reaproveita os campos humanos do estudo anterior.

Os filtros são **Minha revisão pendente**, **Minha revisão registrada**, **Conflitos para adjudicação** e **Toda a fila**. Revisões registradas podem ser consultadas e corrigidas pelo próprio autor. Conflitos só aparecem no filtro de adjudicação para quem tem papel autorizado e não é um dos revisores atuais. Adjudicar continua exigindo conferência explícita e a validação existente no servidor.

## Estados pessoais

| Estado | Significado |
| --- | --- |
| Sem minha revisão | A conta não tem voto atual ou anterior nessa identidade, e há vaga para revisão |
| Minha revisão precisa de reavaliação | Há revisão anterior da conta, mas ela não vale para a base atual; existe vaga para revisar novamente |
| Minha revisão registrada na base atual | Existe um voto atual da própria conta; pode ser consultado/corrigido |
| Duas vagas de revisão já ocupadas | A conta não tem voto atual e duas outras contas já registraram os votos atuais |

As contagens pessoais usam identidades atuais de estudo, não número de documentos ou total global de votos. Os estados são derivados dos registros existentes; não reservam nem atribuem vagas. Se outra pessoa ocupar uma vaga entre a consulta e o envio, a API mantém a validação transacional e recusa um terceiro voto.

Uma revisão registrada com decisão `INCERTO` conta como participação da pessoa, mas não resolve a seleção. Uma fila pessoal vazia não aprova calibração, extração ou resultados. Identidades e fontes alteradas invalidam os votos como antes; a fila mostra a reavaliação sem copiar ou reativar a classificação antiga.

## Implementação e privacidade

`GET /api/clinical/{workspace}/progress` acrescenta `my_review`, calculado para a identidade autenticada. O resumo informa total de identidades, revisões registradas, iniciais pendentes, reavaliações, vagas ocupadas e tarefas disponíveis. Não recebe um identificador de revisor escolhido pelo cliente e não contém votos ou nomes de outros usuários.

`GET /api/clinical/{workspace}/state` acrescenta `personal_review` e `can_adjudicate_screening` a cada linha da fila. Permanecem as regras existentes para consulta da própria decisão e adjudicação. Os dois endpoints agora retornam `Cache-Control: no-store`. Não há cache global de trabalho pessoal; ao sair, os filtros e avisos pessoais são limpos.

O módulo `clinical/personal_review.py` concentra a derivação dos estados e filtros. Nenhuma transformação científica, cálculo de efeito, contrato de extração ou conjunto publicado foi alterado.

## Situação dos pilotos

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos e identidades atuais | 20 | 50 |
| Votos independentes globais faltantes | 40 | 100 |
| Tarefas disponíveis para uma conta sem revisão atual, no estado verificado | 20 | 50 |
| Revisões atuais registradas nessa conta | 0 | 0 |
| Novos eventos de decisão na validação real | 0 | 0 |

Os pilotos foram conferidos separadamente. A contribuição de uma conta não deve ser multiplicada ou registrada em nome de outra para encerrar pendências. No clínico, as 40 avaliações continuam exigindo duas revisões independentes por identidade; divergências poderão exigir adjudicação. Nenhum resultado clínico foi aprovado nesta entrega.

## Validação e reprodução

Oito casos novos verificam carga individual versus global, corpus vazio, incerteza, vagas ocupadas, restrição de adjudicação, mudanças de fontes e identidade, autenticação, ausência de escrita na navegação, filtros e atualização após envio humano. Os votos usados nesses testes são exclusivamente sintéticos e ficam em diretórios temporários.

A bateria completa passou: **139 testes**, incluindo PostgreSQL e Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada; CLN-008 recebeu os oito cenários adicionais. As publicações 0.14.0 foram novamente conferidas e permanecem íntegras, com zero resultados clínicos revisados.

No Chrome, a autenticação real mostrou 20 tarefas pessoais disponíveis e 40 votos globais faltantes. O filtro de revisões registradas apresentou a lista vazia esperada; voltar às pendências restaurou o formulário. A saída da sessão retirou os controles pessoais. Não houve erro de página ou envio de voto. A troca de filtros foi exercitada também pelo teclado, aguardando a atualização da tela.

Evidências locais, fora do Git:

- `analytics/target/personal-review-full-junit.xml`: regressão completa.
- `analytics/target/personal-review-real-results.json`: consultas repetidas nos espaços reais, sem novos eventos.
- `analytics/target/personal-review-browser-results.json`: painel pessoal, filtros e saída da sessão no navegador.

Para executar os testes novos:

```powershell
analytics/.venv/Scripts/python.exe -m pytest analytics/tests/test_personal_review.py -q
```

O próximo marco científico permanece a revisão independente dos estudos reais, seguida da calibração, extração e revisão dos resultados elegíveis. Os [relatórios científicos anteriores](resultados/pesquisa-reprodutivel/README.md) continuam vinculados às publicações 0.14.0 e não foram substituídos.
