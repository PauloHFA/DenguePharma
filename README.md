# DenguePharma — Plataforma Auditável de Evidências Farmacológicas para Dengue

> **Aviso de finalidade (Seção 16 / RC-02 / RC-04):** Plataforma destinada exclusivamente a pesquisa científica, revisão de escopo (PRISMA-ScR) e curadoria de evidências. **Não realiza diagnóstico clínico, prescrição médica, cálculo de dose nem gera ranking universal de eficácia de medicamentos.**

---

## 1. Visão Geral e Arquitetura (Seções 12 e 13)

O projeto está organizado como um monorepo modular:

- **`backend/` (Java 21 + Spring Boot 3.4.5 + PostgreSQL 16 + Flyway):**
  - Autenticação JWT e 5 perfis de acesso (`LEITOR`, `REVISOR`, `ADJUDICADOR`, `PESQUISADOR`, `ADMINISTRADOR`) — **RNF-01**.
  - Trilha de auditoria imutável (`audit_log`) e preservação de versões documentais (`document_version`) protegidas por triggers no banco — **RNF-04**.
  - Protocolos versionados e imutáveis após registro/congelamento — **RF-01**.
  - Conectores de busca com *checkpoint*, controle de taxa (`Retry-After` + *backoff*) e deduplicação por identificador externo e hash SHA-256 (`PUBMED`, `CLINICALTRIALS`, `EUROPE_PMC` / `PMC_OA`, e importação assistida `LILACS` / `WHO_ICTRP`) — **RF-02, RNF-05, T1, T2**.
  - Normalização química via **PubChem PUG-REST** preservando o nome publicado, separando combinação fixa de monoterapia e propondo vínculos/fusões de estudos com aprovação e desfazimento auditados — **RF-03, T3**.
  - Triagem dupla independente cega, adjudicação obrigatória de divergências, camada complementar pré-clínica e fluxograma **PRISMA-ScR** — **RF-04**.
  - Extração estruturada exigindo trecho literal (`evidence_span` com `char_start..char_end`), estados explícitos de ausência (`NOT_REPORTED`, `NOT_APPLICABLE`, `UNCERTAIN`, `CONFLICTING`), validação numérica/unidades e bloqueio de *prompt injection* — **RF-05, T4, T5, T10**.
  - Revisão humana lado a lado registrando antes/depois, responsável, justificativa e timestamp — **RF-06**.
  - Catálogo público de evidências aprovadas (filtros nunca ocultam limitações nem avisos científicos) e comparador metodológico por desfecho/janela temporal sem ranking clínico — **RF-07, RF-08, RC-01 a RC-07**.
  - Geração de relatórios reproduzíveis com *snapshot* imutável (`report_snapshot`) e exportação em **PDF, CSV e JSON** — **RF-09, T8**.
  - Fila de reavaliação por mudança de fonte, errata ou retratação (que invalida imediatamente a síntese vigente preservando histórico) — **RF-10, RC-06, T6**.
  - Padrão **Transactional Outbox / Inbox**, jobs com *lease* exclusivo, retentativa e quarentena — **RF-11, T7**.
  - Pacote de reprodução respeitando licenças por documento (omitindo texto integral sem licença aberta e publicando IDs, hashes, versões e anotações aprovadas) — **RF-12, RNF-03, T9**.
  - Módulo de avaliação experimental crossover **A/B/C**, ablação offline **H3**, partição 25%/25%/50% por família de estudo, cronometragem com pausas, **Kappa de Cohen** e semente do **Piloto de 20 registros** — **Seções 14 a 20 (Entregas E2 e E5)**.
- **`workers/` (Python 3.12):**
  - Chave determinística de idempotência (`document_version_id + pipeline_version + model_version + prompt_hash + execution_variant`).
  - Extrator estruturado, sanitização contra *prompt injection* (**T10**), validação numérica (**T5**), abstenção por ausência de suporte literal (**T4**), guarda de orçamento (`BudgetGuard`), ablação offline **H3** e cálculo de precisão/recall/F1 excluindo verdadeiros negativos de ausência.
- **`frontend/` (Vite + React 18 + TypeScript):**
  - 8 telas acessíveis por teclado e controladas por perfil: `Protocolos`, `Importações`, `Triagem`, `Revisão de extração`, `Catálogo`, `Comparador`, `Relatórios` e `Painel operacional`.

---

## 2. Como Executar Localmente

### 2.1. Subir Infraestrutura (PostgreSQL 16, RabbitMQ e MinIO)
```powershell
docker compose up -d
```

### 2.2. Executar o Backend (Spring Boot)
```powershell
mvn -f backend/pom.xml spring-boot:run
```
> As chaves externas (`NCBI_API_KEY`, provedores de IA) são **opcionais**; o sistema opera integralmente sem chaves configuradas (respeitando o limite público de 3 req/s do NCBI E-utilities e usando o extrator híbrido determinístico).

### 2.3. Executar o Frontend (Vite + React)
```powershell
npm install --prefix frontend
npm run dev --prefix frontend
```

### 2.4. Popular o Piloto de 20 Registros (Seção 20)
Após autenticar como `ADMINISTRADOR` ou `PESQUISADOR`, clique em **"Carregar Piloto de 20 Registros (Seção 20)"** na tela **Painel operacional** (ou envie `POST /api/admin/seed-pilot`).

---

## 3. Como Executar as Suítes de Teste (Cenários T1 a T10 e Entregas E1 a E6)

### Backend (35 testes de integração com Testcontainers PostgreSQL 16)
```powershell
mvn -B -q -f backend/pom.xml test
```

### Workers Python (9 testes unitários e de métricas)
```powershell
workers\.venv\Scripts\python.exe -m pytest workers -q
```

### Frontend (7 testes Vitest + Build TypeScript)
```powershell
npm test --prefix frontend -- --run
npm run build --prefix frontend
```

