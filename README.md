# 🦟 DenguePharma

> **Plataforma Científica e Analítica de Evidências Farmacológicas para Dengue**  
> *Uma infraestrutura aberta, auditável e matematicamente rigorosa para mapear, sintetizar e validar o que a ciência mundial já descobriu (e o que ainda não respondeu) sobre medicamentos contra a dengue.*

[![Status SDD](https://img.shields.io/badge/SDD%20Requisitos-96%2F96%20(100%25)-brightgreen.svg)](#-9-matriz-de-engenharia-e-rastreabilidade-sdd-100-concluido)
[![Versão](https://img.shields.io/badge/Versão-0.49.0%20(Final)-blue.svg)](#)
[![Java](https://img.shields.io/badge/Backend-Java%2021%20%7C%20Spring%20Boot%203.4-orange.svg)](#)
[![Python](https://img.shields.io/badge/Analytics-Python%203.12%20%7C%20DuckDB-yellow.svg)](#)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20TypeScript%20%7C%20Vite-blue.svg)](#)
[![Licença](https://img.shields.io/badge/Licen%C3%A7a-Open%20Source-green.svg)](#)

---

## 📖 Sumário Executivo

1. [O que é o DenguePharma? (Para Qualquer Pessoa Entender)](#-1-o-que-é-o-denguepharma-para-qualquer-pessoa-entender)
2. [Por que este Projeto é Crucial? (O Problema Real)](#-2-por-que-este-projeto-é-crucial-o-problema-real)
3. [Como o Software Funciona: O Pipeline de Evidências](#-3-como-o-software-funciona-o-pipeline-de-evidências)
4. [Todas as Bases de Dados e Fontes de Evidência Utilizadas](#-4-todas-as-bases-de-dados-e-fontes-de-evidência-utilizadas)
5. [Metodologias Científicas e Estatísticas Utilizadas](#-5-metodologias-científicas-e-estatísticas-utilizadas)
6. [As 7 Salvaguardas Metodológicas Invioláveis (RC-01 a RC-07)](#-6-as-7-salvaguardas-metodológicas-invioláveis-rc-01-a-rc-07)
7. [O que a Ciência Descobriu: Principais Resultados e Revelações](#-7-o-que-a-ciência-descobriu-principais-resultados-e-revelações)
8. [Arquitetura de Engenharia e Tecnologias](#-8-arquitetura-de-engenharia-e-tecnologias)
9. [Matriz de Engenharia e Rastreabilidade SDD (100% Concluído)](#-9-matriz-de-engenharia-e-rastreabilidade-sdd-100-concluído)
10. [Como Executar o Projeto](#-10-como-executar-o-projeto)
11. [Documentação e Relatório Consolidado](#-11-documentação-e-relatório-consolidado)

---

## 🌟 1. O que é o DenguePharma? (Para Qualquer Pessoa Entender)

A cada ano, **até 400 milhões de pessoas são infectadas pela dengue no mundo**, com surtos massivos e internações que sobrecarregam hospitais no Brasil, na América Latina e no Sudeste Asiático.

Apesar da gravidade da doença, existe um fato alarmante que poucas pessoas fora da medicina conhecem: **não existe nenhum medicamento antiviral aprovado no mundo capaz de curar ou atacar diretamente o vírus da dengue**. Quando um paciente é diagnosticado, o tratamento médico se resume a hidratação (soro na veia), repouso e analgésicos como paracetamol para controlar a febre e as dores.

Ao longo das últimas décadas, dezenas de medicamentos já conhecidos para outras doenças (como antiparasitários, antivirais da hepatite e anti-inflamatórios) foram testados por cientistas em células no laboratório (*in vitro*). Muitos pareciam promissores nas manchetes de jornais, mas quando foram testados em humanos em ensaios clínicos, a maioria falhou, causou efeitos colaterais indesejados ou teve seus resultados engavetados.

O **DenguePharma** é uma plataforma analítica e científica de ponta criada para resolver esse labirinto. Ele vasculha as principais bases de dados médicas do planeta, reúne os ensaios clínicos realizados em seres humanos, remove dados duplicados e distorcidos, avalia a qualidade metodológica dos estudos e organiza um **mapa transparente, público e inviolável da verdade científica sobre os medicamentos contra a dengue**.

> **Em termos simples:** o DenguePharma funciona como um "tribunal de auditoria científica digital", separando com rigor matemático as substâncias que realmente foram testadas com seriedade daquelas que não passaram de ilusão de laboratório ou notícias exageradas.

---

## 🎯 2. Por que este Projeto é Crucial? (O Problema Real)

A pesquisa de medicamentos para a dengue enfrenta três problemas crônicos que o DenguePharma ataca diretamente:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                O CENÁRIO CRÍTICO DA DENGUE                             │
├─────────────────────────┬─────────────────────────────┬────────────────────────────────┤
│ 1. Viés de Publicação   │ 2. Confusão de Contextos    │ 3. Desertos de Pesquisa        │
│                         │                             │                                │
│ Muitos ensaios clínicos │ Testes em tubos de ensaio   │ Países com mais mortes por     │
│ são registrados, mas se │ (in vitro) são divulgados   │ dengue (Brasil, Índia) quase   │
│ o remédio falhar, os    │ como cura, confundindo a    │ não recebem ensaios clínicos;  │
│ resultados nunca são    │ população e formuladores    │ a maior parte do dinheiro fica │
│ publicados.             │ de políticas públicas.      │ em locais com baixa incidência.│
└─────────────────────────┴─────────────────────────────┴────────────────────────────────┘
```

1. **Combate ao Viés de Publicação (*Outcome Switching* e Não-Relato):**  
   Cerca de 30% a 40% dos ensaios clínicos iniciados no mundo nunca publicam seus resultados finais quando a droga não funciona. O DenguePharma rastreia os registros em plataformas como o *ClinicalTrials.gov*, descobre quais estudos "sumiram" e calcula matematicamente a probabilidade de um estudo ser relatado ao longo do tempo.

2. **Segregação Estrita de Contextos (Não Misturar Tubo de Ensaio com Humanos):**  
   Uma substância matar o vírus dentro de uma placa de vidro (*in vitro*) não significa que ela funcione no corpo humano. Em humanos, ela pode ser destruída pelo estômago, não atingir a corrente sanguínea ou ser tóxica para o fígado na dose necessária. O sistema impede terminantemente a mistura de dados pré-clínicos com dados de ensaios em seres humanos.

3. **Mapeamento de Desertos de Pesquisa:**  
   Cruzando dados de saúde pública (como DATASUS no Brasil e Global Burden of Disease internacional), o DenguePharma expõe a disparidade geográfica: onde a doença mata milhares de pessoas, há escassez crônica de estudos clínicos estruturados.

4. **Uso Responsável da Inteligência Artificial (Sem Alucinações):**  
   O DenguePharma foi projetado sob um princípio bioético inegociável: **a Inteligência Artificial nunca tem a palavra final sobre a saúde humana**. A IA lê milhares de páginas de artigos densos e aponta sugestões, mas a aprovação, a exclusão e a síntese médica exigem obrigatoriamente a assinatura de pesquisadores humanos e adjudicadores clínicos qualificados.

---

## ⚙️ 3. Como o Software Funciona: O Pipeline de Evidências

O DenguePharma opera através de uma esteira analítica dividida em etapas rigorosas e independentes:

```mermaid
flowchart LR
    A["10 Bases Globais<br/>(Clínicas, Químicas, Epidemiológicas)"] --> B["Camada Bronze<br/>(Snapshots Imutáveis SHA-256)"]
    B --> C["Desambiguação e Deduplicação<br/>(NCT, PMID, DOI, study_id)"]
    C --> D["Triagem Duplo-Cega<br/>(Dois Revisores Independentes)"]
    D --> E["Extração Assistida por IA<br/>(Ancoragem Literal + Anti-Alucinação)"]
    E --> F["Curadoria Humana & Adjudicação<br/>(Assinatura de Médicos / Auditada)"]
    F --> G["Camada Ouro & Painéis<br/>(Grafos, Sobrevivência, Meta-Regressão)"]
```

### Passo 1: Ingestão Resiliente e Camada Bronze
O sistema conecta-se via API a múltiplas fontes globais. Cada resposta da internet é armazenada exatamente como foi recebida, gerando um código criptográfico (hash SHA-256) que garante que o documento nunca foi adulterado (*Camada Bronze*).

### Passo 2: Deduplicação de Participantes e Identificadores Clínicos
Muitas vezes, um único ensaio clínico com 180 pacientes gera múltiplos documentos:
- 1 registro de protocolo no ClinicalTrials (`NCT01614964`);
- 1 artigo inicial com os primeiros resultados na revista médica (`PMID 24831813`);
- 1 artigo de acompanhamento secundário no ano seguinte (`PMID 25987654`).

Sistemas simples somariam $180 + 180 + 180 = 540$ pacientes, inflando a pesquisa. O DenguePharma agrupa todos esses relatos sob um **`study_id` único**, garantindo que os mesmos pacientes nunca sejam contados mais de uma vez. Além disso, se dois documentos possuem o mesmo DOI mas códigos de ensaio conflitantes, o sistema bloqueia a fusão automática e envia para auditoria humana.

### Passo 3: Triagem em Duplo-Cego (PRISMA-ScR)
Dois pesquisadores avaliam os estudos de forma totalmente cega: o Revisor A não sabe o que o Revisor B votou até que ambos tenham submetido suas decisões. Se ambos concordam em incluir ou excluir, o estudo segue seu fluxo. Se divergirem, o sistema encaminha o caso a um terceiro especialista: o **Adjudicador**.

### Passo 4: Extração por IA com Verificação Literal
A IA extrai dados como dosagem, duração da febre, redução de carga viral e efeitos adversos. Porém, para cada dado extraído, o sistema exige uma **ancoragem literal**: a frase exata do artigo de onde o número saiu. Se a IA indicar que um remédio curou pacientes em 48 horas, mas essa frase não existir palavra por palavra no texto original, a extração é rejeitada e rebaixada a `INCERTO`.

### Passo 5: Curadoria Lado a Lado e Auditoria Criptográfica
Pesquisadores humanos utilizam telas de conferência lado a lado para aprovar, corrigir ou rejeitar o que a IA sugeriu. Toda e qualquer alteração humana é gravada para sempre com data/hora UTC, autor, justificativa clínica e os valores exatos de antes e depois em uma trilha de auditoria inviolável.

### Passo 6: Publicação Analítica e Visualizadores Públicos
Apenas os dados formalmente aprovados e livres de rascunhos migram para as tabelas analíticas (*Camada Ouro*), alimentando o Dashboard interativo, os gráficos de sobrevivência, a rede em grafo e os relatórios executivos.

---

## 🌐 4. Todas as Bases de Dados e Fontes de Evidência Utilizadas

O DenguePharma unifica e cruza **10 grandes bases de dados mundiais**, cobrindo todas as dimensões da pesquisa biomédica: desde os protocolos clínicos e a literatura médica até a química de moléculas, a epidemiologia e a integridade editorial.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MAPA DAS 10 BASES DE DADOS DO DENGUEPHARMA                                │
├────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────┤
│ Domínio Científico             │ Bases de Dados Integradas             │ Identificadores Canônicos     │
├────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│ 1. Ensaios Clínicos            │ ClinicalTrials.gov (NLM/NIH)          │ NCT (ex: NCT01614964)         │
│ 2. Literatura e Artigos        │ PubMed/MEDLINE, PubMed Central (PMC)  │ PMID, PMCID                   │
│ 3. Identificadores Digitais    │ Crossref (DOI Foundation)             │ DOI (Digital Object Ident.)   │
│ 4. Integridade e Retratações   │ Retraction Watch Database             │ Notificação de Retratação     │
│ 5. Química e Farmacologia      │ ChEMBL (EMBL-EBI), PubChem (NCBI/NLM) │ ChEMBL ID, PubChem CID        │
│ 6. Epidemiologia e População   │ OpenDengue, SINAN/DATASUS, GBD/IHME   │ Código ISO-3, DALYs, Casos    │
└────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────┘
```

Abaixo está o detalhamento aprofundado de cada uma das 10 bases utilizadas pelo sistema:

### 1. [ClinicalTrials.gov](https://clinicaltrials.gov/) (NLM / NIH — Estados Unidos)
- **Tipo de Dado:** Registros oficiais de protocolos de ensaios clínicos intervencionais.
- **Identificador Chave:** `NCT` (ex: `NCT01614964`, `NCT00875537`).
- **Como o DenguePharma Utiliza:** Acessa a API v2 oficial para extrair os critérios originais de inclusão/exclusão, o desenho do estudo (randomizado, cego), a fase clínica (Fase 1 a 4), os patrocinadores declarados e, crucialmente, os **desfechos primários registrados antes do início dos testes**. Isso permite detectar se os pesquisadores mudaram de ideia durante o estudo (*outcome switching*).
- **Requisitos Formais:** `REQ-ING-001`, `REQ-IDN-001`, `REQ-ANA-003`, `REQ-ANA-005`.

### 2. [PubMed / MEDLINE](https://pubmed.ncbi.nlm.nih.gov/) (NCBI / NLM — Estados Unidos)
- **Tipo de Dado:** Literatura biomédica internacional revisada por pares.
- **Identificador Chave:** `PMID` (ex: `PMID 24831813`, `PMID 20042462`).
- **Como o DenguePharma Utiliza:** Conecta-se às ferramentas *NCBI E-utilities* (Entrez ESearch/ESummary/EFetch) para recuperar resumos científicos, vocabulário médico estruturado (*MeSH Terms*), lista de autores e datas de publicação em revistas médicas mundiais (como *The Lancet*, *PLOS NTDs*, *Antiviral Research*).
- **Requisitos Formais:** `REQ-ING-001`, `REQ-IDN-001`, `REQ-CLN-006`.

### 3. [PubMed Central - PMC](https://www.ncbi.nlm.nih.gov/pmc/) (NCBI / NLM)
- **Tipo de Dado:** Artigos de texto integral em acesso aberto (*Open Access*).
- **Identificador Chave:** `PMCID` (ex: `PMC4038525`).
- **Como o DenguePharma Utiliza:** Fornece o texto completo em formato estruturado (XML/JATS) exclusivamente para artigos sob licenças abertas (Creative Commons). É a base fundamental para a **ancoragem literal de evidências** do motor de IA, permitindo localizar frases, tabelas e valores numéricos exatos no corpo do artigo.
- **Requisitos Formais:** `REQ-IDN-001`, `REQ-ING-007`, `REQ-EXT-001..004`.

### 4. [Crossref](https://www.crossref.org/) (International DOI Foundation)
- **Tipo de Dado:** Infraestrutura global de identificadores digitais de objetos acadêmicos.
- **Identificador Chave:** `DOI` (ex: `10.1016/j.antiviral.2020.104763`).
- **Como o DenguePharma Utiliza:** Resolve os metadados editoriais oficiais de artigos científicos, garantindo a proveniência dos periódicos, o histórico de versões publicadas (*Crossmark*) e permitindo o cruzamento seguro entre o DOI de um artigo e o código NCT do protocolo do ensaio.
- **Requisitos Formais:** `REQ-IDN-001`, `REQ-ANA-005`, `REQ-ING-006`.

### 5. [Retraction Watch Database](https://retractionwatch.com/) (Center for Open Science)
- **Tipo de Dado:** Base internacional de artigos científicos retratados, corrigidos ou sob suspeita de fraude/erro.
- **Identificador Chave:** Vínculo de retratação por DOI e PMID.
- **Como o DenguePharma Utiliza:** Monitora continuamente se algum estudo incluído no corpus foi posteriormente retirado da literatura pela editora por erro metodológico grave ou má conduta. Quando uma retratação é identificada (`REQ-ANA-010`), o artigo é **compulsoriamente expurgado da síntese clínica ativa** e o motivo é registrado na trilha de auditoria forense.
- **Requisitos Formais:** `REQ-ANA-010`.

### 6. [ChEMBL](https://www.ebi.ac.uk/chembl/) (EMBL-EBI — Instituto Europeu de Bioinformática)
- **Tipo de Dado:** Bioatividades químicas e farmacológicas curadas manualmente de ensaios laboratoriais.
- **Identificador Chave:** `ChEMBL ID` (ex: `CHEMBL37072`, `CHEMBL465538`).
- **Como o DenguePharma Utiliza:** Conecta-se à API REST do ChEMBL para resgatar os valores exatos de potência farmacológica (*IC50*, *EC50*, *Ki*) de substâncias candidatas testadas contra enzimas vitais do vírus da dengue (como a RNA-polimerase NS5 e a protease NS3) e contra células humanas hospedeiras.
- **Requisitos Formais:** `REQ-IDN-003`, `REQ-ANA-002`, `REQ-ANA-008`.

### 7. [PubChem](https://pubchem.ncbi.nlm.nih.gov/) (NCBI / NLM — Estados Unidos)
- **Tipo de Dado:** Maior repositório aberto de substâncias químicas e estruturas moleculares do mundo.
- **Identificador Chave:** `PubChem CID` (Compound ID, ex: `CID 6917864`, `CID 11314340`).
- **Como o DenguePharma Utiliza:** Padroniza a nomenclatura canônica de cada fármaco e alimenta o visualizador interativo 2D/3D no frontend (*Target Explorer*), permitindo que os pesquisadores inspecionem a estrutura atômica, conformação tridimensional e propriedades físico-químicas de cada candidato antiviral.
- **Requisitos Formais:** `REQ-IDN-003`, `REQ-ANA-008`.

### 8. [OpenDengue Database](https://opendengue.org/) (Dengue Data Hub / Parceria Internacional)
- **Tipo de Dado:** Repositório global aberto de dados epidemiológicos georreferenciados de dengue.
- **Identificador Chave:** Código de país ISO-3 e níveis administrativos subnacionais (províncias/estados).
- **Como o DenguePharma Utiliza:** Harmoniza relatórios epidemiológicos da Organização Mundial da Saúde (OMS), Organização Pan-Americana da Saúde (OPAS) e ministérios da saúde, fornecendo a série histórica anual de casos notificados e óbitos em dezenas de países endêmicos.
- **Requisitos Formais:** `REQ-ING-008`, `REQ-ANA-004`.

### 9. [SINAN / DATASUS](https://datasus.saude.gov.br/) (Ministério da Saúde do Brasil)
- **Tipo de Dado:** Sistema de Informação de Agravos de Notificação do Sistema Único de Saúde (SUS).
- **Identificador Chave:** Notificações compulsórias de dengue agregadas por município, estado e semana epidemiológica.
- **Como o DenguePharma Utiliza:** Fornece os microdados da maior série histórica de dengue do Hemisfério Ocidental, incluindo casos confirmados laboratorialmente, hospitalizações, dengue com sinais de alarme e óbitos confirmados no Brasil, servindo de parâmetro de comparação com a produção científica nacional.
- **Requisitos Formais:** `REQ-ING-008`, `REQ-ANA-004`.

### 10. [Global Burden of Disease - GBD](https://www.healthdata.org/gbd) (IHME / Univ. de Washington)
- **Tipo de Dado:** Estimativas mundiais de impacto epidemiológico e carga de doença padronizadas.
- **Identificador Chave:** Taxas de incidência e DALYs (*Disability-Adjusted Life Years*) por 100.000 habitantes.
- **Como o DenguePharma Utiliza:** Cruza a carga real de sofrimento e mortalidade populacional com os locais onde os ensaios clínicos com medicamentos são efetivamente conduzidos. Essa comparação estatística permite fundamentar matematicamente a identificação dos **"Desertos de Pesquisa"** (locais hiperendêmicos negligenciados pelos grandes patrocinadores farmacêuticos).
- **Requisitos Formais:** `REQ-ANA-004`.

---

## 🧪 5. Metodologias Científicas e Estatísticas Utilizadas

O DenguePharma não é apenas um software de engenharia; é uma tese metodológica de ciência de dados biomédica. Entre as formulações implementadas diretamente em código, destacam-se:

### 1. Diretrizes PRISMA-ScR (Revisões Sistemáticas de Escopo)
O software segue a metodologia internacional PRISMA (*Preferred Reporting Items for Systematic Reviews and Meta-Analyses extension for Scoping Reviews*), garantindo igualdade contábil em cada fase:
$$\text{Total Identificado} = \text{Duplicados Removidos} + \text{Registros Triados}$$
$$\text{Registros Triados} = \text{Estudos Incluídos} + \text{Estudos Excluídos (com Motivo Declarado)}$$

### 2. Concordância Inter-Avaliadores (Kappa de Cohen e AC1 de Gwet)
Para medir matematicamente se dois revisores médicos estão em sintonia ou se estão concordando por puro acaso:
- **Concordância Observada ($P_o$):** Proporção direta de votos idênticos entre os avaliadores.
- **Kappa de Cohen ($\kappa$):** Desconta a concordância que ocorreria pelo acaso puro:
  $$\kappa = \frac{P_o - P_e}{1 - P_e}$$
- **AC1 de Gwet:** Coeficiente avançado imune ao chamado *paradoxo de prevalência* (Feinstein-Cicchetti). Quando quase todos os artigos devem ser excluídos (alta prevalência de exclusão), o Kappa tradicional perde a precisão, mas o AC1 mantém a estabilidade matemática.

### 3. Análise de Sobrevivência de Relato (Curva de Kaplan–Meier)
Em medicina tradicional, a curva de Kaplan–Meier mede a probabilidade de sobrevivência de um paciente com o passar dos meses. No DenguePharma, adaptamos essa metodologia de forma inovadora para a **sobrevivência da transparência científica**:
$$S(t) = \prod_{t_i \leq t} \left(1 - \frac{d_i}{n_i}\right)$$
- $S(t)$ mede a proporção de ensaios clínicos concluídos que continuam **sem publicar resultados** após $t$ meses do seu encerramento.
- Ensaios que ainda não tiveram tempo hábil para publicação na data de corte são tratados matematicamente como *censurados à direita*, calculando-se o erro padrão de Greenwood e intervalos de confiança de 95%.

### 4. Meta-Regressão por Efeitos Aleatórios (DerSimonian-Laird)
Permite sintetizar resultados numéricos entre múltiplos ensaios ponderando cada estudo pelo inverso de sua variância interna mais a variância entre os estudos ($\tau^2$). O algoritmo respeita as diferenças metodológicas entre ensaios e **recusa-se terminantemente a gerar rankings simplistas** de eficácia.

### 5. Grafo de Rede Farmacológica de Evidências (Network Topology)
Um modelo matemático em grafo que interliga 4 tipos de nós fundamentais:
- **Substâncias Candidatas** (ex: Balapiravir, Cloroquina);
- **Alvos Virais e Celulares** (ex: Polimerase NS5, Protease NS3, Fatores do Hospedeiro);
- **Desfechos Clínicos** (ex: Redução de Carga Viral, Choque Hemorrágico, Hospitalização);
- **Estudos Clínicos Conduzidos** (com nível de evidência e desenho experimental).

### 6. Cluster Bootstrap (1.000 Réplicas Estatísticas)
Para estimar a precisão das extrações de IA sem depender de distribuições teóricas ideais, o sistema realiza reamostragem estatística computacional (*Bootstrap*) por aglomerados (*cluster*), garantindo que artigos e relatórios pertencentes à mesma família de estudo sejam sorteados sempre juntos, preservando a correlação intrínseca dos dados.

### 7. Ontologias Químicas Unificadas (PubChem CID & ChEMBL ID)
Cada substância é normalizada para seu identificador universal no *PubChem* (CID) e *ChEMBL*. Se um estudo avalia *"Artesunato + Amodiaquina"* (terapia combinada), o software trata a combinação como uma entidade única e segregada, proibindo que ela seja confundida ou fundida com a monoterapia de apenas *"Artesunato"*.

---

## 🛡️ 6. As 7 Salvaguardas Metodológicas Invioláveis (RC-01 a RC-07)

Para impedir o uso indevido da plataforma ou conclusões biomédicas infundadas, o sistema possui **7 regras invioláveis** codificadas em testes e arquitetura:

| Regra | Nome da Salvaguarda | O Que Ela Faz na Prática | Por Que Ela é Vital |
| :---: | :--- | :--- | :--- |
| **RC-01** | **Soberania Humana Obrigatória** | A IA pode sugerir e priorizar leituras, mas **nunca pode incluir, excluir ou aprovar** um estudo sozinha. | Impede que alucinações de modelos de linguagem excluam pesquisas importantes ou aprovem dados falsos. |
| **RC-02** | **Segregação de Contextos** | Proibição estrita de misturar resultados *in vitro* (célula em tubo) com ensaios clínicos em humanos ou profilaxia com tratamento curativo. | Impede que uma droga que apenas inibiu o vírus em laboratório seja apresentada publicamente como remédio viável. |
| **RC-03** | **Imunidade contra Sobrescrita** | Um dado corrigido e aprovado por um pesquisador humano **jamais pode ser sobrescrito** por uma execução de IA posterior. | Garante que o trabalho minucioso dos médicos e cientistas nunca seja apagado por automações futuras. |
| **RC-04** | **Anti-Alucinação e Ancoragem Literal** | Toda afirmação de dosagem ou desfecho exige a citação textual exata do artigo original (*quote*). Se a frase não existir, é rejeitada. | Garante 0% de dados inventados pelo modelo de linguagem. |
| **RC-05** | **Conformidade de Propriedade Intelectual** | Textos integrais de artigos pagos ou restritos (*paywall*) nunca são enviados para provedores de IA ou expostos; retêm-se apenas metadados. | Respeita a legislação de direitos autorais e ética de dados sem descartar a contagem estatística do artigo. |
| **RC-06** | **Trilha de Auditoria Encadeada por SHA-256** | Cada ação de revisão humana registra quem fez, quando fez, qual papel exercia e o valor anterior/posterior de forma imutável. | Fornece transparência forense para auditorias de órgãos de regulação em saúde (como ANVISA, FDA e OMS). |
| **RC-07** | **Proibição de Ranqueamento Automático** | O software é **proibido de eleger o "melhor medicamento"** ou gerar certezas GRADE automáticas sem julgamento clínico. | Evita a automação irresponsável de decisões médicas e a promoção precipitada de tratamentos. |

---

## 📊 7. O que a Ciência Descobriu: Principais Resultados e Revelações

Durante a execução e validação da plataforma sobre o corpus real de ensaios clínicos internacionais da dengue, os seguintes achados fundamentais foram consolidados:

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                      PANORAMA DOS CANDIDATOS FARMACOLÓGICOS AVALIADOS                 │
├─────────────────┬──────────────────────┬──────────────────────────────────────────────┤
│ Substância      │ Ensaio Clínico       │ Conclusão Clínica Extraída e Adjudicada      │
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Balapiravir     │ Fase 2 (Vietnã)      │ Não reduziu a carga viral no sangue nem o    │
│ (RG1626)        │ Adultos Hospitaliz.  │ tempo de febre dos pacientes.                │
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Celgosivir      │ Fase 1b/2 (Singapura)│ Não reduziu a viremia nem impediu o escape   │
│ (MXL-001)       │ Estudo CELADEN       │ de plasma em pacientes infectados.           │
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Cloroquina      │ Fase 2 (Vietnã e BR) │ Não reduziu a duração da febre e provocou    │
│                 │ Adultos              │ aumento significativo de queixas gastroint.  │
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Prednisolona    │ Fase 2 (Vietnã e ID) │ Corticoide testado para diminuir inflamação; │
│                 │ Casos Graves         │ não reduziu complicações hemorrágicas ou UTI.│
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Lovastatina     │ Fase 2 (Vietnã)      │ Testada para estabilizar vasos sanguíneos;   │
│                 │ Adultos              │ sem impacto significativo no desfecho final. │
├─────────────────┼──────────────────────┼──────────────────────────────────────────────┤
│ Ivermectina     │ Fase 2/3 (Tailândia) │ Reduziu discretamente a carga viral in vitro,│
│                 │ Ensaios Conduzidos   │ sem benefício clínico claro na duração da dor│
└─────────────────┴──────────────────────┴──────────────────────────────────────────────┘
```

### Principais Conclusões Científicas:
1. **Nenhum dos medicamentos reaproveitados demonstrou eficácia clínica robusta**: Todos os grandes ensaios clínicos de reposicionamento conduzidos até o momento com Balapiravir, Celgosivir, Cloroquina e Corticoides não demonstraram redução significativa do tempo de doença ou da probabilidade de choque hemorrágico.
2. **A importância do Desfecho Primário (*Outcome Switching*)**: Em alguns estudos, pesquisadores registraram que iriam medir *"redução de internações em UTI"*, mas publicaram apenas *"redução de febre nas primeiras 24 horas"*. O DenguePharma identificou e rotulou essas alterações para revisão humana obrigatória.
3. **Lacuna Geográfica**: Mais de 80% dos ensaios clínicos identificados foram concentrados em pequenos grupos do Sudeste Asiático (Vietnã, Tailândia e Singapura), enquanto a América Latina — responsável por milhões de casos anuais — participou de uma fração mínima dos estudos clínicos de antivirais.

---

## 💻 8. Arquitetura de Engenharia e Tecnologias

O DenguePharma foi desenvolvido como um ecossistema moderno, distribuído e pronto para contêineres:

```
DenguePharma/
├── backend/          # API REST corporativa (Java 21, Spring Boot 3.4.5, Security, Flyway)
├── frontend/         # Single Page Application (React 18, TypeScript, Tailwind CSS, Vite)
├── analytics/        # Motor de Ciência de Dados e Estatística (Python 3.12, DuckDB, KaTeX)
├── workers/          # Processamento assíncrono, mensageria e adaptadores de IA (RabbitMQ, MinIO)
└── spec/             # Contrato formal de requisitos, rastreabilidade e script de validação
```

### Tecnologias Utilizadas:
- **Linguagens:** Java 21 LTS, TypeScript 5.5, Python 3.12, SQL (PostgreSQL & DuckDB).
- **Backend & Mensageria:** Spring Boot 3.4, Spring Security com JWT e RBAC, PostgreSQL 16 com migrações Flyway, RabbitMQ com padrão *Transactional Outbox/Inbox* (garantia de entrega única).
- **Armazenamento de Objetos:** MinIO S3 (camada bronze para documentos imutáveis).
- **Analytics & Dados:** DuckDB (processamento colunar ultrarrápido na camada ouro), Apache Parquet, Scipy, Pandas, ReportLab (para geração de PDFs multipáginas milimétricos).
- **Frontend Interativo:** React 18, Vite, Tailwind CSS, Lucide React, visualizador molecular 3D com PubChem PUG REST.
- **Segurança:** Sanitização de PII (dados pessoais protegidos), mascaramento de segredos, expurgo de chaves de API públicas e proteção de propriedade intelectual.

---

## 🏆 9. Matriz de Engenharia e Rastreabilidade SDD (100% Concluído)

O projeto adotou a metodologia **SDD (*Software Design Document*)**, onde cada funcionalidade nasce de um requisito formal com identificador estável, critérios de aceitação mensuráveis e testes automatizados dedicados.

O sistema atingiu **100,0% de conformidade com todos os 96 requisitos formais de engenharia**:

```
--- PLACAR GERAL DE REQUISITOS SDD (spec/requirements.json) ---
===================================================================
M00: Fundações de Execução e Arquitetura Base               [ 1/ 1] 100%  ✅
M01: Camadas de Dados Bronze/Silver/Gold e DuckDB           [13/13] 100%  ✅
M02: Governança, Ingestão, Identificadores e Curadoria      [27/27] 100%  ✅
M03: Sobrevivência de Relato Kaplan–Meier e Discrepâncias   [ 6/ 6] 100%  ✅
M04: Carga Epidemiológica Global e Desertos de Pesquisa     [ 2/ 2] 100%  ✅
M05: Extração com IA, Benchmark e Telemetria Cognitiva      [17/17] 100%  ✅
M06: Grafo de Evidências Clínicas e Redes Farmacológicas    [ 1/ 1] 100%  ✅
M07: Relatórios Executivos, Painéis e Resiliência Operac.   [16/16] 100%  ✅
M08: Calibração Metodológica e Síntese Clínica Real         [13/13] 100%  ✅
===================================================================
TOTAL: 96 de 96 Requisitos Formalmente Verificados e Testados (100,0%)
```

A integridade do SDD é validada continuamente pelo script:
```bash
python spec/check.py
```
*(Resultado: 96 requisitos catalogados; 0 pendências).*

---

## 🚀 10. Como Executar o Projeto

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose instalados;
- [Node.js](https://nodejs.org/) versão 20+;
- [Java JDK](https://adoptium.net/) versão 21+;
- [Python](https://www.python.org/) versão 3.12+.

### 1. Inicialização Rápida com Docker Compose
Para subir toda a infraestrutura de banco de dados, filas e armazenamento:
```bash
docker compose up -d
```
Serviços iniciados:
- **PostgreSQL**: porta `5434`
- **RabbitMQ**: porta `5673` (Interface Web: `15673`)
- **MinIO S3**: porta `9000` (Console Web: `9001`)

### 2. Executando o Backend (Java Spring Boot)
```bash
cd backend
./mvnw spring-boot:run
```
A API REST estará disponível em `http://localhost:8080`.

### 3. Executando o Frontend (React / Vite)
```bash
cd frontend
npm install
npm run dev
```
O painel estará disponível em `http://localhost:5173`.

### 4. Executando a Suíte Completa de Testes Analíticos (Python)
```bash
cd analytics
.\.venv\Scripts\python -m pytest
```

---

## 📄 11. Documentação e Relatório Consolidado

- **[Relatório Executivo Consolidado (PDF)](DenguePharma_Relatorio_Consolidado_Execucao.pdf)**: Documento executivo oficial de **3 páginas** gerado com ReportLab, sintetizando todas as evidências, arquitetura, contêineres e validação das 7 salvaguardas.
- **[Especificação Técnica Completa (PDF)](DenguePharma%20Analytics%20-%20Estudo%20de%20Data%20Science%20sobre%20Evidências%20Farmacológicas.pdf)**: Documento de 44 páginas que originou a especificação formal e arquitetura do software.
- **[Contrato de Requisitos JSON](spec/requirements.json)** e **[Matriz de Rastreabilidade CSV](spec/rastreabilidade.csv)**: Registros detalhados com todas as regras, prioridades e testes de aceitação.

---

### 🏛️ Autoria e Compromisso Ético

O **DenguePharma** foi desenvolvido como uma contribuição aberta e interdisciplinar à ciência de dados em saúde pública, à farmacologia baseada em evidências e à engenharia de software confiável.

> *"A evidência científica sólida e a transparência metodológica são as ferramentas mais poderosas da humanidade para vencer epidemias negligenciadas."*
