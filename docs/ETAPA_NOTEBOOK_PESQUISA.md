# Pesquisa reproduzível — consolidação das análises

Entrega de 28/10/2026, sobre as execuções publicadas da versão 0.14.0. Esta etapa atende à documentação da exploração em notebook prevista na metodologia. Não acrescenta método estatístico, coleta ou resultado clínico.

O [notebook-fonte](../notebooks/03_pesquisa_reprodutivel.ipynb) consulta as mesmas tabelas públicas usadas pela aplicação. As transformações permanecem nos módulos Python existentes. O notebook-fonte fica sem saídas; as cópias executadas e os HTMLs ficam separados por piloto.

## Onde consultar

- [Relatório HTML do piloto clínico de 20 documentos](resultados/pesquisa-reprodutivel/clinical-20/pesquisa.html).
- [Relatório HTML do piloto operacional de 50 documentos](resultados/pesquisa-reprodutivel/operational-50/pesquisa.html).
- [Manifestos e notebooks executados](resultados/pesquisa-reprodutivel/README.md).
- Dashboard existente: http://127.0.0.1:8501, quando os serviços locais estiverem ativos.

Os HTMLs incorporam os três gráficos PNG e podem ser abertos localmente sem executar Python. Não carregam dados de APIs externas. Os pilotos permanecem separados; não devem ser somados como estudos ou participantes únicos.

## Conteúdo e resultados

O relatório reúne panorama temporal, distribuições, tamanho amostral informado, patrocinadores, completude, auditoria de relato, referências por PMID e disponibilidade de resultados clínicos. Cada tabela é consultada integralmente por paginação, sem limitar silenciosamente a apresentação às primeiras mil linhas. Numeradores, denominadores, ausências e alertas são preservados.

No piloto clínico há 10 publicações e 10 registros. Seis registros declaram resultados disponíveis; cinco pares de datas permitem calcular intervalos de relato, com mediana de 709 dias. Há 71 PMIDs citados sem coincidência nas publicações coletadas. Duas publicações apresentam ano bibliográfico 2027, posterior ao corte de 28/10/2026: o alerta da fonte permanece visível e exige conferência, sem correção automática.

No operacional há 25 publicações e 25 registros, seis com resultados declarados; três intervalos calculáveis apresentam mediana de 1.288 dias. A união dos tipos de referência contém 69 PMIDs não localizados no corpus.

Esses indicadores descrevem os registros coletados, ainda com elegibilidade pendente. Intervalo até relato não é sobrevida dos pacientes, PMID coincidente não confirma vínculo clínico e completude não mede qualidade metodológica. **Ambas as execuções continuam sem resultados clínicos revisados. Não há conclusão sobre o melhor medicamento ou sobre benefício, ausência de benefício ou dano.**

## Como reproduzir

Com as dependências de `analytics/.venv` e o Quarto já instalados, executar na raiz do repositório:

```powershell
analytics/.venv/Scripts/python.exe analytics/scripts/reproduce-notebook.py --run 7a1897915598231a92e7b969185fc13d33e23d88e245d5c015bab26b13984424 --output analytics/target/pesquisa-clinica-reproduzida
```

Para o operacional, substituir `--run` por `7f3b1e541a1c8a2c1a5cc5ab245ae84de7995870b13dabb50aa64f541a83ac90` e escolher outra pasta nova. `--data-dir` e `--quarto` permitem informar caminhos alternativos. As execuções publicadas precisam estar disponíveis localmente; esta etapa não as recria nem publica automaticamente.

O script exige publicação íntegra, executa com o mesmo interpretador que o iniciou, usa um kernel temporário, renderiza com Quarto sem executar novamente e recusa pasta de destino existente. Registra versões do ambiente, hashes da entrada, código analítico congelado, notebook-fonte, executor, manifesto publicado e artefatos. O manifesto contém também as contagens e hashes lógicos das 34 tabelas públicas. Comparar esses hashes entre reproduções; HTML e notebook podem conter identificadores de renderização diferentes.

Para execução interativa, escolher o Python de `analytics/.venv`. As variáveis `ANALYTICS_DATA_DIR` e `DENGUEPHARMA_RUN_ID` selecionam diretório e execução; sem configuração usa-se o piloto clínico publicado indicado no notebook. Não carregar `.env` nem snapshots privados no notebook.

## Validação e limites

As duas execuções reais concluíram as sete células de código sem erros; formato dos notebooks, hashes dos artefatos e integridade das publicações foram conferidos. Os HTMLs contêm três imagens incorporadas cada. O notebook-fonte continua sem resultados anexados. Não houve alteração nos módulos analíticos, filas, snapshots, decisões de curadoria ou versões publicadas; a versão do pacote permanece 0.14.0 e a matriz de requisitos não foi promovida como atendimento científico completo.

A repetição do piloto clínico produziu saídas idênticas nas sete células e os mesmos hashes lógicos das 34 tabelas públicas. Os dois HTMLs foram abertos no Chrome: três imagens carregadas por relatório, com nenhuma requisição externa. O [registro de validação](resultados/pesquisa-reprodutivel/validation.json) resume as verificações, incluindo a recusa de sobrescrita e de execução não publicada.

O próximo marco científico continua sendo a revisão humana do piloto clínico: faltam 40 avaliações independentes, seguidas da adjudicação de divergências e da extração revisada dos resultados elegíveis. O notebook apresenta o estado publicado; não consulta nem expõe a área privada de revisão. As 40 pendências são o estado operacional registrado nesta entrega, não uma contagem calculada pelo notebook público.
