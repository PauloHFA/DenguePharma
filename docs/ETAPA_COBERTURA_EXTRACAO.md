# Cobertura da extração por desfecho — versão 0.20.0

Entrega de 28/10/2026. O novo painel organiza o trabalho de extração dos estudos incluídos, mostrando quais desfechos do protocolo têm resultados revisados e quais permanecem sem resultados revisados ou em conflito. Não estima benefício, aplicabilidade dos desfechos ou qualidade metodológica.

## Onde está

No [dashboard local](http://127.0.0.1:8501/), entrar em **Curadoria clínica — acesso protegido → Cobertura da extração por desfecho**. A área permite filtrar a situação e baixar um ZIP autenticado com CSV, resumo JSON e manifesto.

## Unidade e método

Cada célula representa **uma identidade de estudo incluída × um desfecho do protocolo**. A inclusão precisa estar resolvida pela seleção independente atual. Identidades pendentes, excluídas ou com inclusão desatualizada não geram células.

Para cada célula, o módulo consulta os resultados canônicos já aprovados pelo fluxo existente. Publicações repetidas não aumentam a contagem quando representam o mesmo resultado consolidado. A tabela informa quantidade de resultados revisados, comparações distintas, IDs rastreáveis e presença de conflito. Não soma participantes ou efeitos.

| Situação | Significado |
| --- | --- |
| `SEM_RESULTADO_REVISADO` | Não existe resultado aprovado vigente nessa célula; rascunhos não bastam |
| `COM_RESULTADO_REVISADO` | Há pelo menos um resultado aprovado vigente e nenhum conflito nessa célula |
| `CONFLITO_PENDENTE` | Existe comparação com resultados conflitantes; outras comparações da mesma célula podem ter resultados revisados |

As contagens de células com e sem resultados revisados dividem o conjunto de células. A contagem de conflitos é um indicador sobreposto: não deve ser somada às duas anteriores. Um resultado revisto não implica aprovação da calibração, conclusão clínica ou publicação; a situação da calibração aparece separadamente.

**Uma célula sem resultado revisado não significa desfecho não medido, não aplicável, zero eventos ou ausência de benefício.** Os desfechos do protocolo são perguntas para conferência, sem assumir que todos se aplicam a cada estudo. Não é calculada uma porcentagem genérica de completude.

Adultos, crianças, comparações e tempos não são combinados para calcular efeitos. Uma célula pode contar vários estratos e comparações como organização do trabalho, sem afirmar equivalência clínica entre eles.

## Estado e integridade

O mapa é reconstruído da base atual, sem gravar eventos. Fonte ou identidade alterada pode invalidar a inclusão e retirar as células correspondentes até nova triagem. Mesmo após nova inclusão, aprovações antigas não reaparecem automaticamente. Conflitos vêm do fluxo de resultados existente; não são resolvidos por data ou quantidade de documentos.

O módulo não muda a coleta, a seleção, a extração ou as conclusões. O acesso é privado e usa os papéis de revisão já existentes. Os endpoints retornam `Cache-Control: no-store`:

- `GET /api/clinical/{workspace}/extraction-coverage`.
- `GET /api/clinical/{workspace}/extraction-coverage/export`.

## Pacote exportado

O ZIP contém:

- `coverage.csv`: células e contagens, com IDs dos resultados consolidados.
- `summary.json`: unidade, limites, contagens, hashes e situação da calibração.
- `manifest.json`: versão do software, hash do código, da entrada, do protocolo, da seleção e da auditoria, além dos hashes dos arquivos.

O pacote é reproduzível para o mesmo estado e código. Não contém votos, nomes de revisores, justificativas livres, resumos, textos integrais ou valores clínicos por braço. A exportação não publica uma execução. Arquivos baixados da curadoria continuam privados e não devem ser adicionados ao Git.

## Resultado nos pilotos reais

| Indicador | Piloto clínico | Piloto operacional |
| --- | --- | --- |
| Documentos preservados | 20 | 50 |
| Inclusões independentes resolvidas | 0 | 0 |
| Células do mapa | 0 | 0 |
| Avaliações independentes faltantes | 40 | 100 |
| Novos eventos na validação real | 0 | 0 |

O mapa permanece vazio porque não há inclusões resolvidas. Não foram criadas 20 ou 50 linhas de evidência artificial a partir dos metadados. Os hashes dos snapshots clínicos existentes foram preservados.

## Verificação e versionamento

Seis casos novos verificam o conjunto vazio, distinção entre rascunho e revisão, deduplicação documental, conflitos com resultados coexistentes, fontes desatualizadas, exportação determinística, hashes, permissões e interface sem criação de decisões.

A bateria completa passou: **160 testes**, incluindo PostgreSQL e Quarto reais. A matriz permanece com 96 requisitos e 29 com evidência automatizada; CLN-009 recebeu os seis cenários adicionais. No Chrome, foram conferidos login real, estado vazio, download autenticado e saída da conta, sem erros de página ou novos votos. Os bytes do ZIP baixado coincidiram com o módulo Python e os hashes dos arquivos foram verificados.

Evidências locais, fora do Git: `analytics/target/extraction-coverage-full-junit.xml`, `extraction-coverage-real-results.json` e `extraction-coverage-browser-results.json`. O ZIP baixado no teste de navegador fica somente em `analytics/target/`.

Esta etapa segue a [política de versionamento](VERSIONAMENTO.md): o checkpoint anterior é `0d2739f`, e a implementação 0.20.0 recebe um commit separado após a validação.

O próximo marco científico continua sendo concluir a revisão independente e a calibração, ampliar a coleta conforme o protocolo e revisar os resultados elegíveis. O painel organiza pendências; não responde, por si, quais fármacos beneficiam pacientes.
