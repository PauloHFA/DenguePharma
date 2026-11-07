# DenguePharma — Project Master Specification & Audit

## Architecture
DenguePharma is an open-science pharmacological evidence curation and reproducible data science platform for dengue (DENV-1, DENV-2, DENV-3, DENV-4).
The system follows a multi-tier, resilient architecture:
1. **Core Curatorial & API Backend**: Spring Boot 3.4.5, Java 21, PostgreSQL 16 (Flyway V1–V9), JWT Bearer authentication, and Transactional Outbox/Inbox with lease-based concurrency (`job`, `outbox`, `inbox`).
2. **Workers & Extraction Engine**: Python 3.12 (`denguepharma_workers`), deterministic rule pipelines (`rules-2`), prompt injection defense (T10), numeric validation (T5), literal evidence span verification with explicit abstention (T4), and offline H3 ablation.
3. **Data Science & Analytical Marts**: Python 3.12, DuckDB, Parquet (`analytics/`), FastAPI (port 18081), Streamlit (port 8501), and Quarto reproducible reporting.
4. **Curatorial & Public Frontend**: React 18, Vite, TypeScript, TailwindCSS, Vitest. Implements public observatory dashboard, compound catalog, methodological comparator (RC-01/RC-04), PRISMA-ScR screening, and side-by-side extraction review.
5. **Infrastructure**: Docker Compose (`docker-compose.yml`), MinIO S3 object storage, RabbitMQ 3.13 message broker, PostgreSQL 16 database.

---

## Comprehensive Audit Matrix (DenguePharma_Proposta_Formal.pdf vs. Implementation)

| Req ID | Formal Proposal Requirement | Component / Layer | Status | Concrete File Paths | Audit Findings & Gaps |
|---|---|---|---|---|---|
| **OE1 / QP1** | Identify candidate drugs for dengue repurposing | Backend / DB / Worker | **PARTIALLY_IMPLEMENTED** | `backend/.../catalog/CatalogService.java`, `workers/.../corpus.py` | Catalog filters candidate substances (PubChem normalized), but ChEMBL bioactivity and biological target links are missing. |
| **OE2 / QP2** | Evaluate consistency across study designs (in silico, in vitro, in vivo, human) | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../catalog/CatalogService.java:261`, `frontend/.../ComparatorPage.tsx:44` | Enforces Rule RC-01: flags context incompatibility between pre-clinical and human trials. |
| **OE3 / QP3** | Characterize safety profiles and adverse events | Backend / DB / Frontend | **FULLY_IMPLEMENTED** | `backend/.../db/migration/V4.sql`, `frontend/.../CatalogPage.tsx:142` | Enforces Rule RC-03: `adverse_events_status` explicitly distinguishes `AUSENCIA_DE_RELATO` from proven safety. |
| **OE4 / QP4** | Measure AI extraction quality and human review concordance | Worker / DB / Backend | **PARTIALLY_IMPLEMENTED** | `workers/.../extractor.py:213`, `backend/.../db/migration/V5.sql` | Precision, recall, and F1 implemented in worker; backend crossover endpoints retired with HTTP 410 GONE in MVP v2. |
| **OE5 / QP5** | Open interactive observatory of pharmacological evidence | Frontend / Backend / Analytics | **FULLY_IMPLEMENTED** | `frontend/.../DashboardPage.tsx`, `backend/.../analysis/PublicAnalysisController.java` | Public dashboard with 4 tabs, external deep links, PNG figures, and download bundle. |
| **OE6 / H3** | Offline ablation study of span constraint and abstention | Worker | **FULLY_IMPLEMENTED** | `workers/.../extractor.py:288`, `workers/tests/test_extractor.py:102` | `run_ablation_h3` compares extraction with vs. without span/abstention, guaranteed unpublished. |
| **RF-01** | Versioned protocol registration and freeze | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../protocol/ProtocolService.java`, `frontend/.../ProtocolsPage.tsx` | Protocols transition DRAFT -> REGISTERED -> FROZEN; immutable once frozen. |
| **RF-02** | Multi-source batch ingestion with checkpoints | Backend / Connectors | **FULLY_IMPLEMENTED** | `backend/.../ingest/PubMedConnector.java`, `ClinicalTrialsConnector.java`, `ImportService.java` | Checkpoint resumption, rate limiting, and date partitioning implemented. |
| **RF-03** | Reversible study-document linking & deduplication | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../substance/StudyLinkService.java`, `frontend/.../ScreeningPage.tsx` | Study link proposals, approval/rejection, full undo with audit log. |
| **RF-04** | Two-stage double-blind screening & PRISMA | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../screening/ScreeningService.java`, `frontend/.../ScreeningPage.tsx` | Independent dual review, conflict adjudication, PRISMA flowchart calculation. |
| **RF-05** | 7-step structured AI extraction pipeline | Backend / Worker | **PARTIALLY_IMPLEMENTED** | `workers/.../pipeline.py`, `workers/.../extractor.py` | Deterministic pipeline, prompt injection defense, and validation implemented; live LLM adapter not wired into loop. |
| **RF-06** | Side-by-side human review with exact span locators | Backend / Frontend | **PARTIALLY_IMPLEMENTED** | `backend/.../extraction/ExtractionService.java`, `frontend/.../ReviewPage.tsx` | Quoted span and character locators displayed; backend allows mock span on correction; review button action mapping divergence. |
| **RF-07** | Public catalog with mandatory limitations disclosure | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../catalog/CatalogService.java:37`, `frontend/.../CatalogPage.tsx` | Regulatory status, risk of bias, and mandatory notices visible on all views. |
| **RF-08** | Contextual comparator without universal ranking | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../catalog/CatalogService.java:214`, `frontend/.../ComparatorPage.tsx` | Enforces Rule RC-04: explicitly forbids ranking or universal efficacy scoring. |
| **RF-09** | Reproducible multi-format report export (PDF/CSV/JSON) | Backend / Frontend | **FULLY_IMPLEMENTED** | `backend/.../ops/ReportAndOpsService.java:446`, `frontend/.../ReportsPage.tsx` | Generates PDF, CSV, and JSON exports with content hashes and filter criteria. |
| **RF-10** | Reassessment queue on source document changes | Backend / DB | **FULLY_IMPLEMENTED** | `backend/.../db/migration/V4.sql`, `backend/.../ops/ReportAndOpsService.java:254` | Enqueues reassessment tasks on document version updates; preserves past decisions. |
| **RF-11** | Transactional Outbox/Inbox with leased worker jobs | Backend / DB / Worker | **FULLY_IMPLEMENTED** | `backend/.../pipeline/PipelineService.java`, `workers/.../runtime.py` | Leased execution with token validation and atomic PostgreSQL state updates. |
| **RF-12** | Complete audit trail with immutable logs | Backend / DB | **FULLY_IMPLEMENTED** | `backend/.../audit/AuditService.java`, `backend/.../db/migration/V1.sql:35` | PL/pgSQL `forbid_mutation()` trigger prevents update/delete on audit logs. |
| **RNF-01** | Security, RBAC & Secret Hygiene | Backend / Security | **PARTIALLY_IMPLEMENTED** | `backend/.../security/SecurityConfig.java`, `ApiExceptionHandler.java` | Stateless JWT auth, BCrypt password hashing; **MISSING: CORS configuration** and complete exception handling. |
| **RNF-02** | Performance (<2s query latency) | Backend / DB | **FULLY_IMPLEMENTED** | `backend/.../db/migration/V1.sql` | Strategic indexes on study, document, substance, and hash columns. |
| **RNF-03** | Scientific Reproducibility | Backend / Workers / Notebooks | **FULLY_IMPLEMENTED** | `workers/.../idempotency.py`, `notebooks/`, `spec/check.py` | Deterministic SHA-256 hashes, reproduction package export, reproducible notebooks. |
| **RNF-04** | Regulatory Compliance (LGPD, Open Access) | Backend / Storage | **FULLY_IMPLEMENTED** | `backend/.../ingest/EuropePmcConnector.java`, `ReportAndOpsService.java:369` | Open access verification; sanitized exports omit proprietary full texts. |
| **RNF-05** | Resilience, Backoff & Checkpoints | Backend / Connectors | **FULLY_IMPLEMENTED** | `backend/.../ingest/PubMedConnector.java`, `ClinicalTrialsConnector.java` | Retry-After, exponential backoff with jitter, cursor checkpointing. |
| **RNF-06** | Data Quality & Abstention Guarantee | Backend / Worker | **FULLY_IMPLEMENTED** | `workers/.../extractor.py:73`, `ExtractionService.java:436` | Strict abstention when literal text quote is absent (T4). |
| **RNF-07** | Usability & Human-Centered Workflow | Frontend | **FULLY_IMPLEMENTED** | `frontend/src/pages/*.tsx` | Comprehensive React interface across all curatorial and public roles. |
| **RNF-08** | Interoperability (PubChem, ChEMBL, MeSH) | Backend / Worker | **PARTIALLY_IMPLEMENTED** | `backend/.../substance/PubChemClient.java` | PubChem PUG REST implemented; **ChEMBL connector missing**. |
| **Targets** | Biological Target Explorer (NS5, NS3, DENV 1-4) | Backend / Frontend / DB | **MISSING** | `backend/.../`, `frontend/.../` | No target entities, no target explorer UI screen, no viral/host target catalog. |
| **Budget** | AI Execution Budget Guard & Quota Tracking | Backend / Worker / Frontend | **PARTIALLY_IMPLEMENTED** | `workers/.../extractor.py:268`, `backend/.../ops/` | Worker implements `BudgetGuard`; backend lacks persistent quota table; frontend lacks Budget Monitor UI. |
| **Infra** | Full Multi-Container Orchestration | Infrastructure | **PARTIALLY_IMPLEMENTED** | `docker-compose.yml` | Postgres, RabbitMQ, MinIO, and Worker defined; **backend and frontend services missing**. |
| **Tests** | Automated Test Verification | Backend / Frontend / Workers | **PARTIALLY_IMPLEMENTED** | `backend/src/test/`, `frontend/src/`, `workers/tests/` | Frontend (21/21) and Worker (38/38) pass 100%; Backend integration tests mandate Docker daemon for Testcontainers. |

---

## Prioritized Gap Catalog

### Priority 0 (Immediate Execution — This Run)
1. **GAP-BE-01: Spring Security CORS Configuration**:
   - *Impact:* High. Cross-origin browser requests from external frontend clients fail.
   - *Resolution:* Add `corsConfigurationSource()` and `.cors(Customizer.withDefaults())` to `SecurityConfig.java`.
2. **GAP-BE-02: Comprehensive API Exception Handling**:
   - *Impact:* High. Unhandled validation errors (`MethodArgumentNotValidException`), access denied (`AccessDeniedException`), and database constraint violations return HTTP 500 instead of clean ProblemDetail.
   - *Resolution:* Expand `ApiExceptionHandler.java` with handlers for validation, security, and data integrity exceptions.
3. **GAP-BE-03: Critical Field Adjudication Role Enforcement**:
   - *Impact:* High integrity risk. `CRITICAL_FIELDS` declared in `ExtractionService.java` is not checked against user role, permitting unprivileged reviewers to publish critical fields.
   - *Resolution:* Enforce `ROLE_ADJUDICADOR` in `ExtractionService.java` for any critical field review.
4. **GAP-BE-04: Genuine Quote Enforcement on Human Correction**:
   - *Impact:* High scientific integrity risk. When a reviewer corrects a value, missing quote generated `'Corrigido pelo revisor'` dummy span.
   - *Resolution:* Validate and require authentic quote from source document text in `ExtractionService.java`.
5. **GAP-FE-01: Review Page Action Mapping Alignment**:
   - *Impact:* Medium. `frontend/src/pages/ReviewPage.tsx` submits `APPROVED/CORRECTED/REJECTED` while backend expects `ACEITAR/CORRIGIR/REJEITAR`.
   - *Resolution:* Standardize review actions across frontend and backend.
6. **GAP-FE-02: Target Explorer Screen & Routing**:
   - *Impact:* High domain requirement. Biological targets (NS5 RdRp/MTase, NS3 protease/helicase, structural proteins E/C/prM, DENV serotypes 1-4) need dedicated visibility.
   - *Resolution:* Implement `TargetExplorerPage.tsx`, register route `/alvos` in frontend navigation and screens catalog.
7. **GAP-FE-03: PubChem 2D Structure Rendering & Budget Monitor UI**:
   - *Impact:* Medium. Compounds lack 2D chemical structure image preview; budget status lacks operational dashboard widget.
   - *Resolution:* Integrate PubChem 2D structure image in `CatalogPage.tsx` and budget monitor card in `OperationalPanelPage.tsx`.
8. **GAP-WRK-01: ChEMBL Connector & Target Bioactivity Module**:
   - *Impact:* High interoperability requirement (`REQ-IDN-002`).
   - *Resolution:* Implement `chembl.py` in `denguepharma_workers` to query ChEMBL bioactivities for dengue viral targets and compounds, with unit tests.
9. **GAP-INF-01: Complete Docker Compose Stack**:
   - *Impact:* High operational requirement. `docker-compose.yml` lacks `backend` and `frontend` services.
   - *Resolution:* Add container definitions for Spring Boot backend and Vite frontend.
10. **GAP-TST-01: Backend Test Suite Portability (Docker-Independent Execution)**:
    - *Impact:* High testability requirement. Integration tests strictly fail when Docker daemon is not active.
    - *Resolution:* Enable graceful fallback or environment-aware execution for Testcontainers in `AbstractIntegrationTest.java` or standalone unit test profile.

### Priority 1 (Subsequent Phase Milestones)
- **GAP-P1-01**: Live LLM Worker Loop Integration with active streaming token counters (currently deterministic `rules-2`).
- **GAP-P1-02**: Quarto multi-page report compilation and PDFBox multi-page layout.
- **GAP-P1-03**: Interactive network graph visualization for evidence topology (Eixo E).
- **GAP-P1-04**: Full human curation and review execution of the 120-document corpus (E6 / REQ-CLN-006).

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Audit Matrix Documentation | Document full audit matrix comparing proposal to code | M1 | Survey |
| 2 | Spring Security CORS | Enable CORS with configurable origins in SecurityConfig | M2 | GAP-BE-01 |
| 3 | Comprehensive Exception Handling | Handle validation, access denied, and constraint errors | M2 | GAP-BE-02 |
| 4 | Critical Field Adjudication | Enforce ROLE_ADJUDICADOR check on critical field publication | M2 | GAP-BE-03 |
| 5 | Genuine Quote Enforcement | Reject dummy spans and require authentic document quote | M2 | GAP-BE-04 |
| 6 | Testcontainers Docker Fallback | Graceful fallback/environment handling for backend tests | M2 | GAP-TST-01 |
| 7 | ChEMBL Data Connector | Python worker client for ChEMBL bioactivity and target queries | M3 | GAP-WRK-01 |
| 8 | Biological Targets Registry | Data structures and mapping for NS5, NS3, E, prM, DENV 1-4 | M3 | GAP-WRK-01 |
| 9 | ChEMBL Worker Unit Tests | Pytest test suite for ChEMBL connector and bioactivity queries | M3 | GAP-WRK-01 |
| 10 | Review Action Contract Alignment | Align ReviewPage.tsx actions with backend API | M4 | GAP-FE-01 |
| 11 | Target Explorer Frontend Screen | Public Target Explorer view with viral/host targets | M4 | GAP-FE-02 |
| 12 | 2D Chemical Structure Visualization | PubChem 2D structure preview in Catalog cards | M4 | GAP-FE-03 |
| 13 | Budget Monitor UI Widget | Operational dashboard widget for AI budget tracking | M4 | GAP-FE-03 |
| 14 | Docker Compose Stack Completion | Add backend and frontend container services | M4 | GAP-INF-01 |
| 15 | Automated Verification Suite | Execute backend, frontend, workers, and spec verification | M5 | Acceptance Criteria |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| **M1** | Comprehensive Audit Matrix Documentation | Finalize `PROJECT.md` and `docs/AUDITORIA_FORMAL_PROPOSTA.md` | none | **DONE** |
| **M2** | Backend Security, Integrity & Exception Handling | Fix CORS, `ApiExceptionHandler`, critical field adjudication, genuine quote validation, and test portability | M1 | **IN_PROGRESS** |
| **M3** | Workers ChEMBL Connector & Target Modeling | Implement `chembl.py`, target data models, and pytest suite | M1 | **PLANNED** |
| **M4** | Frontend Target Explorer, 2D Structures & Compose | Add Target Explorer screen, review contract fix, 2D chemical structure, budget widget, and docker-compose services | M2, M3 | **PLANNED** |
| **M5** | Comprehensive Automated Verification | Verify `mvn test`, `npm test`, `npm run build`, `pytest`, `python spec/check.py` | M2, M3, M4 | **PLANNED** |

---

## Interface Contracts

### Backend ↔ Frontend
- `POST /api/extractions/fields/{id}/review`:
  - Request: `{ "action": "ACEITAR" | "CORRIGIR" | "REJEITAR", "reason": string?, "quotedText": string?, "locator": string? }`
  - Roles: `ROLE_REVISOR` for regular fields, `ROLE_ADJUDICADOR` mandatory if field is in `CRITICAL_FIELDS`.
  - Errors: HTTP 400 with RFC 7807 `ProblemDetail` on validation failure; HTTP 403 when critical field is reviewed without adjudicator role.
- CORS Contract:
  - Allowed origins: `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:5173`
  - Allowed methods: `GET, POST, PUT, DELETE, OPTIONS, HEAD`
  - Allowed headers: `Authorization, Content-Type, Accept, X-Requested-With`

### Worker ↔ ChEMBL API
- `ChEMBLClient.get_target_bioactivities(target_chembl_id, activity_type="IC50")`:
  - Returns list of bioactivity records with compound name, ChEMBL ID, standard value, standard units, and reference.
- `ChEMBLClient.lookup_compound(pref_name_or_smiles)`:
  - Resolves molecular formula, canonical SMILES, and max phase.

---

## Code Layout
- `backend/`:
  - `src/main/java/org/denguepharma/security/`: SecurityConfig.java, ApiExceptionHandler.java
  - `src/main/java/org/denguepharma/extraction/`: ExtractionService.java, ExtractionController.java
  - `src/main/java/org/denguepharma/catalog/`: CatalogService.java, CatalogController.java
  - `src/test/java/org/denguepharma/`: AbstractIntegrationTest.java, unit and integration tests
- `workers/`:
  - `src/denguepharma_workers/`: chembl.py, extractor.py, pipeline.py, corpus.py, runtime.py
  - `tests/`: test_chembl.py, test_extractor.py, test_corpus.py, test_analysis.py
- `frontend/`:
  - `src/pages/`: TargetExplorerPage.tsx, ReviewPage.tsx, CatalogPage.tsx, OperationalPanelPage.tsx, DashboardPage.tsx
  - `src/`: screens.ts, App.tsx, api.ts
- Infrastructure:
  - `docker-compose.yml`
