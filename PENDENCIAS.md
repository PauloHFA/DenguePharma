# 📋 Pendências e Próximos Passos — DenguePharma

> Documento de rastreabilidade do status técnico, validações automatizadas e pendências operacionais da plataforma **DenguePharma** (especificação formal em [`PROJECT.md`](PROJECT.md)).

---

## ✅ 1. O que já está Concluído e Validado

- **Backend Curatorial (`backend/` — Java 21 + Spring Boot 3.4.5):**
  - Migrations Flyway V1–V9, PostgreSQL 16, autenticação JWT/RBAC, trilha de auditoria imutável (`forbid_mutation()`), Outbox/Inbox transacional com lease, conectores PubMed, Europe PMC, ClinicalTrials.gov e PubChem.
  - Suíte completa Spring Boot + Testcontainers validada na esteira CI.
- **Workers & Extração (`workers/` — Python 3.12):**
  - Pipeline determinístico (`rules-2`), defesa contra prompt injection, validação numérica, abstenção estrita por suporte literal (T4), ablação offline H3, conector ChEMBL e ingestão epidemiológica.
  - **55/55 testes passando** (`pytest workers/tests`).
- **Analytics & Data Science (`analytics/` — Python 3.12 + DuckDB + FastAPI + Streamlit + Quarto):**
  - Marts reprodutíveis, síntese clínica, auditoria de discrepâncias (RC-01 a RC-07), grafo de evidências, análise de sobrevivência e calibração do piloto metodológico.
  - **256/256 testes passando** (6 skips condicionais para banco ao vivo), zero erros de lint no `ruff`.
- **Frontend SPA (`frontend/` — React 18 + TypeScript + Vite):**
  - Observatório público, catálogo de compostos, comparador metodológico, triagem PRISMA-ScR, revisão lado a lado e explorador de alvos biológicos.
  - **31/31 testes passando** (`vitest run`) e build de produção validado (`tsc -b && vite build`).
- **Especificação SDD (`spec/check.py`):** 96/96 requisitos rastreados.

---

## 🚀 2. Melhorias Futuras Opcionais (Backlog de Engenharia)
- [ ] **Integração do Loop LLM ao Vivo nos Workers:** Ligar o `llm_adapter.py` em streaming ao loop de extração contínua com tabela persistente de cotas no PostgreSQL (atualmente operando com pipeline determinístico `rules-2` e `BudgetGuard` em memória).
- [ ] **Relatórios Quarto Multi-Página e PDFBox Avançado:** Expandir compilação de relatórios executivos multi-página em Quarto e layout avançado em PDFBox.
- [ ] **Visualização Interativa de Grafo de Evidências (Eixo E):** Evoluir componentes visuais do grafo de topologia de evidências com exploração dinâmica no frontend.
- [ ] **Execução Local Sem Docker:** Disponibilizar perfil Maven dedicado para isolar testes unitários puros dos testes `@SpringBootTest` que exigem Testcontainers/Docker ativo.

---

## 🛠️ 3. Dependências Externas (Infraestrutura e Curadoria Humana)
- [ ] **Stack Docker Completa (`docker-compose.yml`):** Subir PostgreSQL 16, RabbitMQ 3.13, MinIO S3, backend, workers e frontend em ambiente local ou cloud para coleta e ingestão ao vivo.
- [ ] **Variáveis de Ambiente e Chaves Externas (`.env`):** Configurar credenciais de banco (`DB_USER`, `DB_PASSWORD`), chaves de APIs científicas (NCBI/PubMed, LLM) e `ANALYTICS_LIVE_POSTGRES=true` quando rodar o pipeline contra base viva.
- [ ] **Adjudicação Humana do Corpus Completo (REQ-CLN-006):** Concluir a curadoria humana dupla independente dos 120 documentos completos fora do piloto de 50 estudos já validado.
