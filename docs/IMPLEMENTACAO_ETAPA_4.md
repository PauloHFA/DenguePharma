# Etapa 4 — corpus real e dashboards de ciência de dados

## Arquitetura

- `search_run_document` registra versões encontradas por coleta, incluindo reimportações sem mudança. Não modifica os documentos anteriores.
- `POST /api/analyses/corpus` recebe `protocolId` e `previousAnalysisId` opcional. Congela documentos pertencentes às coletas desse protocolo, metadados permitidos, execução das buscas, identidade química cadastrada e a camada revisada. Demonstrações, estudos retratados e raízes de fusão inválidas ficam fora.
- O evento `AnaliseSolicitada` e o job `ANALYZE_EVIDENCE` existentes atendem v2/v3. Backend valida hashes, limites e compatibilidade com o snapshot; conclusão é atômica com Inbox/lease.
- `POST /api/analyses/{id}/publish` publica explicitamente um corpus v3 concluído. Repetir não duplica a publicação.
- `GET /api/public/analyses`, `/{id}` e `/{id}/artifacts?name=...` permitem leitura anônima apenas de execuções publicadas. A API operacional continua protegida.
- `/` e `/dashboard` abrem sem sessão; `/curadoria` encaminha ao acesso protegido. Relatórios oferece geração e publicação do panorama.

## Execução local

Na raiz do repositório, com backend e worker ativos:

```powershell
$python = '.\workers\.venv\Scripts\python.exe'
& $python -m denguepharma_workers.research --env-file .env collect --stage pilot --output backend/target/runtime/coleta-piloto.json
```

O comando usa credenciais de pesquisador `DENGUEPHARMA_RESEARCH_EMAIL`/`DENGUEPHARMA_RESEARCH_PASSWORD` ou as credenciais locais de bootstrap do `.env`, sem imprimi-las. `BACKEND_URL` define o servidor; `--base-url` permite sobrescrever. O corte padrão usa a data local de São Paulo e fica registrado. O piloto limita a 25 registros por fonte.

Copie o `protocolId` do arquivo de resultado:

```powershell
& $python -m denguepharma_workers.research analyze --protocol UUID_DO_PROTOCOLO --output backend/target/runtime/analise-piloto.json
& $python -m denguepharma_workers.research download --analysis UUID_DA_ANALISE --output backend/target/runtime/piloto-ds3
& $python -m denguepharma_workers.research publish --analysis UUID_DA_ANALISE
```

A publicação disponibiliza o **panorama coletado**. Não aprova a elegibilidade nem campos científicos.

Para reproduzir sem backend ou broker:

```powershell
& $python -m denguepharma_workers.analysis --input backend/target/runtime/piloto-ds3/dataset.json --output backend/target/runtime/reproducao-ds3
```

## Revisão antes da ampliação

Preencher `pilot_review.csv`: `eligibility_decision=INCLUIR/EXCLUIR`, motivo de exclusão quando necessário, `preparation_validated=SIM`, revisor e data. Conferir identificadores, duplicidade, desenho, nomes, países, datas e números contra a fonte. Ajustar o protocolo/dicionário se necessário. Não preencher a planilha com aprovação fictícia.

```powershell
& $python -m denguepharma_workers.research collect --stage full --review-csv CAMINHO_DA_PLANILHA --pilot-dataset CAMINHO_DO_DATASET --output backend/target/runtime/coleta-completa.json
```

O comando confere correspondência dos IDs e registra os hashes do piloto e da revisão. Este controle não torna a busca pública infalível nem impede um pesquisador de criar outros protocolos pela API; a responsabilidade científica permanece no protocolo e na revisão.

## Resultados e apresentação

O ZIP contém entrada congelada, registros preparados, tabelas de documentos, estudos e campos científicos aprovados, temporalidade, distribuições, inscrição, completude, conflitos, vínculos, transformações, mapas revisados, planilha do piloto, resumo, relatório HTML, figuras PNG e manifesto. `reproduction_source.json` preserva os bytes dos módulos analíticos e da cartografia em base64, permitindo recuperar o código daquela execução mesmo após mudanças no repositório. Dependências científicas e hashes ficam no manifesto; gráficos podem variar entre plataformas, mas os resultados numéricos devem coincidir.

Países vêm de Natural Earth v5.1.2, domínio público; o arquivo e os hashes acompanham o módulo. Países sem correspondência aparecem em `geography.unmappedCountries`. A resolução de 1:110m não representa todos os pequenos territórios; suas contagens permanecem na tabela.

O notebook `notebooks/01_exploracao_corpus.ipynb` documenta a exploração com funções importadas. Para usá-lo, selecione um kernel com o pacote workers instalado; Jupyter não é dependência do processamento.

No dashboard, os indicadores e gráficos representam a execução completa. A busca e os seletores filtram as tabelas identificadas; a seleção de outra execução troca todo o conjunto. A camada revisada mantém contextos e estados separados. Todos os downloads usam rotas públicas limitadas à publicação.

## Aceite operacional versus científico

Os testes automatizados verificam a preparação, contagens, permissões e reprodução. O teste de pipeline usa serviços reais isolados. Uma coleta piloto real verifica conectividade e geração dos artefatos; não substitui revisão humana de seu conteúdo.

A coleta completa e a homologação científica do piloto dependem da revisão identificada. O sistema deve apresentar esse estado, sem afirmar que o corpus já foi validado por humanos. IA experimental permanece fora desta entrega.

Limites atuais: entrada de corpus até 8 MiB; pacote compactado/descompactado até 32 MiB e até 256 artefatos. O processamento falha explicitamente ao atingir limites, sem truncar dados. A coleta completa ainda não foi homologada; protocolos maiores podem exigir particionamento adicional ou ampliação desses limites após o piloto.

Datas bibliográficas posteriores ao corte da busca são preservadas e sinalizadas em `temporal_flags.csv`, no resumo e no dashboard. Isso exige conferência na fonte; não autoriza corrigir automaticamente o ano nem afirmar a causa da divergência.
