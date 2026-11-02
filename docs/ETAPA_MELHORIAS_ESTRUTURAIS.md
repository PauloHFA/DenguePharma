# Etapa 0.23.0 — Expansão Multidisciplinar e Salvaguardas Avançadas (CI/CD, ChEMBL, Eixo C, 3D Viewer e Shadow Screening)

## 1. Contexto Geral e Objetivos
A **Versão 0.23.0** consolida uma evolução estrutural do ecossistema DenguePharma, integrando cinco pilares estratégicos de infraestrutura contínua, química medicinal, epidemiologia global, visualização molecular e apoio por inteligência artificial à decisão humana, em conformidade com as salvaguardas científicas RC-01 a RC-07.

---

## 2. As Cinco Melhorias Implementadas

### 2.1. Pipeline de Integração Contínua (CI/CD) com GitHub Actions
- **Arquivo**: `.github/workflows/ci.yml`
- **Capacidades**:
  - Matriz de testes contínuos automatizados para Java 21 (Spring Boot, Flyway, H2/PostgreSQL).
  - Validação estrita de especificação e rastreabilidade (`python spec/check.py`).
  - Execução da suíte de testes analíticos e workers (`pytest` para 177+ casos de teste).
  - Verificação de tipos TypeScript, testes unitários Vitest e build de produção Vite no Frontend.
- **Garantia**: Bloqueio compulsório de qualquer regressão que viole os esquemas SDD ou contratos de API.

### 2.2. Interoperabilidade Bioquímica com ChEMBL (Banco de Dados e API)
- **Migração Flyway**: `backend/src/main/resources/db/migration/V10__substance_bioactivity.sql`
- **Endpoint**: `GET /api/public/bioactivities` em [`BioactivityController.java`](../backend/src/main/java/org/denguepharma/analysis/BioactivityController.java)
- **Estrutura**: Tabela relacional indexada `substance_bioactivity` registrando parâmetros quantitativos de ligação in vitro:
  - $IC_{50}$ (concentração inibitória 50%)
  - $EC_{50}$ (concentração efetiva 50%)
  - $K_i$ (constante de inibição enzimática)
- **Alvos Mapeados**: RdRp/Metiltransferase (NS5), Serino Protease (NS3) e Proteína de Envelope (E) para candidatos líderes (ex.: Balapiravir, Sofosbuvir, Cloroquina).
- **Salvaguarda RC-02**: Os dados in vitro do ChEMBL são rigorosamente mantidos em camada separada dos ensaios clínicos com humanos.

### 2.3. Carga Global de Doença e Desertos de Pesquisa (Eixo C — GBD / DATASUS)
- **Endpoint Backend**: `GET /api/public/disease-burden` em [`DiseaseBurdenController.java`](../backend/src/main/java/org/denguepharma/analysis/DiseaseBurdenController.java)
- **Componente Frontend**: [`DiseaseBurdenView.tsx`](../frontend/src/components/DiseaseBurdenView.tsx) integrado na aba "Carga Global (Eixo C)" do `DashboardPage.tsx`.
- **Métricas e Conceito**:
  - Integra dados epidemiológicos do *Global Burden of Disease* (GBD) e DATASUS: volume de casos anuais estimados, taxas de DALYs (*Disability-Adjusted Life Years*) por 100k habitantes e sorotipos predominantes.
  - **Identificação de Desertos de Pesquisa**: Sinalização de países de alta incidência e mortalidade (ex.: Índia com ~4,5M casos e Bangladesh com taxa de 520,1 DALYs/100k) com sub-representação extrema em ensaios clínicos farmacológicos registrados.
- **Salvaguarda RC-04**: A ausência de registros de ensaios ou notificações em um país nunca é interpretada como carga zero de doença.

### 2.4. Visualizador Molecular Interativo 2D/3D (PubChem Embed)
- **Componente**: [`Molecule3DViewer.tsx`](../frontend/src/components/Molecule3DViewer.tsx) integrado em `TargetExplorerPage.tsx`.
- **Recursos**:
  - Renderização tridimensional interativa de conformações químicas derivadas diretamente do PubChem via iframe seguro com sandboxing restritivo.
  - Alternância rápida para representação vetorial bidimensional (2D SVG).
  - Metadados estruturais: Identificador PubChem CID, fórmula molecular, massa molar e alvos virais primários.
  - Cobertura de candidatos canônicos: Balapiravir (CID 11561674), Sofosbuvir (CID 45375808), Celgosivir (CID 9576787) e Ivermectina (CID 6321424).

### 2.5. Shadow Screening Consultivo por IA para Adjudicação de Conflitos
- **Módulo**: [`shadow_screening.py`](../analytics/src/denguepharma_analytics/clinical/shadow_screening.py)
- **Integração**: [`workspace.py`](../analytics/src/denguepharma_analytics/clinical/workspace.py)
- **Fluxo de Governança e Blinding**:
  1. Durante a triagem independente, a IA opera estritamente em *modo shadow* (invisível aos revisores R1 e R2 para impedir viés de ancoragem).
  2. O parecer é disponibilizado exclusivamente ao papel de **Adjudicador** quando há divergência entre os revisores humanos (estado `CONFLITO`).
  3. O relatório inclui: recomendação (`INCLUIR`, `EXCLUIR`, `INCERTO`), nível de confiança heurística, mapeamento PICO, trechos literais comprobatórios e verificação de conformidade com salvaguardas.
  4. **Salvaguardas RC-01 a RC-07**: O parecer é estritamente consultivo. A decisão final é 100% soberana do adjudicador humano, sendo vedada a tomada de decisão automatizada ou cálculo de ranking de fármacos.

---

## 3. Evidências e Matriz de Verificação

| Componente | Teste / Verificação | Resultado | Tempo |
|---|---|---|---|
| **Backend CI/CD** | `mvn test` (Spring Boot + Controllers) | Sucesso (0 falhas) | 4.8s |
| **ChEMBL Bioactivities** | `BioactivityControllerTest` | 2 testes aprovados | 2.0s |
| **Disease Burden (Eixo C)** | `DiseaseBurdenControllerTest` | 2 testes aprovados | 0.1s |
| **Frontend 3D & Eixo C** | `npm --prefix frontend test` (Vitest) | 27 testes aprovados (6 suítes) | 11.2s |
| **Frontend Build** | `npm --prefix frontend run build` | Sucesso (56 módulos compilados) | 1.1s |
| **Shadow Screening** | `test_shadow_screening.py` (Pytest) | 4 testes de conformidade aprovados | 2.4s |
| **Analytics Suite Completa** | `pytest analytics/tests` | 171 aprovados, 6 pulados, 0 erros | 2m49s |
| **Workers Suite** | `pytest workers/tests` | 31 testes aprovados | 1.4s |
| **Spec Verification** | `python spec/check.py` | 96 requisitos auditados | 0.2s |
