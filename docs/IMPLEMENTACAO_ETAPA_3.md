# Etapa 3 — Ciência de dados descritiva

Implementa [Requisitos v2](REQUISITOS_V2.md). A proposta PDF e a auditoria original permanecem históricas.

## O que mudou

- Snapshots específicos de análise, imutáveis e separados dos relatórios anteriores; dados científicos vêm exclusivamente de campos aprovados/publicados.
- Conflitos e pendências permanecem explícitos. Classificações de contexto/finalidade são as da triagem. Estudos demonstrativos, excluídos, absorvidos e retratados não entram em novos snapshots.
- Análise Python com pandas/Matplotlib, tabelas, gráficos por contexto, mapas de lacunas, completude e rastreabilidade estrutural. Nenhuma chamada a IA é realizada.
- Job `ANALYZE_EVIDENCE` integrado à Outbox/RabbitMQ/MinIO e protegido pelo lease. Interface em **Relatórios → Análises descritivas**.
- APIs de experimento v1 respondem 410 e botões correspondentes foram removidos. Seus dados continuam preservados.

## Utilização pela aplicação

1. Reinicie o backend com o ambiente habitual; Flyway aplica V8.
2. Atualize o worker: `docker compose --profile pipeline up -d --build worker`. A configuração de MinIO, RabbitMQ e credencial interna segue a [etapa 2](IMPLEMENTACAO_ETAPA_2.md).
3. Reinicie o frontend. Em **Relatórios**, selecione filtros e clique em **Gerar análise descritiva** com papel PESQUISADOR/ADMINISTRADOR.
4. Acompanhe o estado e use **Consultar análise** para tabelas/gráficos. Baixe o ZIP para obter os arquivos completos.

O leitor consulta e baixa análises, mas não solicita novas execuções. O painel atualiza os estados periodicamente; falhas podem ser retomadas pelo administrador no painel operacional.

## Utilização por comando

Com o Python dos workers:

```powershell
workers\.venv\Scripts\python.exe -m pip install -r workers/requirements.lock
workers\.venv\Scripts\python.exe -m pip install --no-deps -e workers
workers\.venv\Scripts\python.exe -m denguepharma_workers.analysis --input snapshot.json --output resultados
```

Use **Baixar entrada JSON** para obter `dataset.json`, disponível assim que a análise é solicitada, mesmo sem worker ativo. O módulo compartilhado pela CLI e pelo worker é o mesmo; nenhuma credencial da aplicação é necessária para analisar esse arquivo local.

## Artefatos

- `dataset.json`: bytes do snapshot, sem resumos/textos/citações integrais.
- `dataset.csv`: uma linha por estudo com valores e estados.
- `distributions.csv`, `completeness.csv`, `gaps.csv`, `traceability.csv`.
- `summary.json`: resultados estruturados usados pela aplicação.
- `figures/*.png`: gráficos e mapas, separados por contexto/camada, paginados quando necessário.
- `report.html`: relatório local com tabelas e imagens relativas; extraia o ZIP para abri-lo com suas figuras.
- `manifest.json`: versões, configuração e hashes; `bundle.zip`: pacote completo.

Valores potencialmente interpretados como fórmulas são neutralizados nos CSVs. O JSON mantém o valor revisado original. O HTML escapa os textos; gráficos e tabelas não dependem de recursos externos.

Os artefatos são gravados e verificados no MinIO antes do commit. O backend valida o ZIP, o manifesto e o dataset exato e armazena uma cópia dos arquivos em `analysis_artifact` para servir downloads autenticados sem credenciais públicas de armazenamento. O limite é de 32 MiB/256 arquivos. Pacotes maiores falham explicitamente e podem ser solicitados com filtros mais restritos.

## Reprodução e testes

```powershell
workers\.venv\Scripts\python.exe -m pytest workers -q
npm test --prefix frontend -- --run
npm run build --prefix frontend
mvn -B -f backend/pom.xml test
```

Para o teste completo, construa a imagem MinIO conforme a etapa 2 e habilite:

```powershell
$env:PIPELINE_INTEGRATION = 'true'
$env:PIPELINE_PYTHON = (Resolve-Path workers/.venv/Scripts/python.exe).Path
mvn -B -f backend/pom.xml test
```

O teste completo executa o worker real, confere hashes dos objetos, geração dos gráficos/pacote, conclusão do job e reentrega do evento analítico sem duplicação.

Validação da entrega: 52 testes Java passaram com o teste completo habilitado (sem falhas ou ignorados), 24 testes Python e 18 testes frontend passaram; TypeScript/Vite compilaram. A imagem do worker foi reconstruída e a análise com gráficos também foi executada dentro do container Linux.

## Limites importantes

Uma análise pode conter muitos campos pendentes: o extrator atual só cobre alguns padrões. Substância, desenho, fase e categoria de desfecho só aparecem quando esses campos foram efetivamente revisados. Não são substituídos por dados de resumo para tornar os gráficos mais completos.

Snapshots mantêm o estado da data da solicitação. Uma retratação posterior afeta novos snapshots, sem reescrever os antigos. A presença de identificador/versão/localizador mede estrutura documental, não qualidade metodológica ou fidelidade semântica.

Documentação técnica: [tabelas cruzadas do pandas](https://pandas.pydata.org/docs/reference/api/pandas.crosstab.html). As categorias vazias são mantidas explicitamente com `dropna=False` e reindexação.
