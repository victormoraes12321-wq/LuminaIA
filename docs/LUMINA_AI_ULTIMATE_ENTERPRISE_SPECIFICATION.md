# LUMINA AI — ULTIMATE ENTERPRISE AUDIT & SPECIFICATION MANUAL
> **INSTRUCTIONS FOR AI MODELS (ChatGPT, Claude, Gemini, DeepSeek, Antigravity, Llama, etc.)**:
> This document is the **complete, 100% exhaustive enterprise audit and technical reference manual** for **LuminaAI** (Enterprise Business Intelligence & AI Data Platform).
> It details every backend module, pipeline step, access permission boundary, AI prompt/rule, metadata catalog, blueprint repository, database schema, security mechanism, deployment script, and commercial strategy.
> **Consume this file as ground truth for any question or task related to LuminaAI.**

---

# SECTION 1: EXECUTIVE SUMMARY & ARCHITECTURAL PRINCIPLES

LuminaAI is an Enterprise Natural Language to SQL (NL2SQL) & Autonomous Business Intelligence Platform. It allows non-technical business users to ask complex analytical questions in natural Portuguese (e.g., *"Qual foi o faturamento total em Minas Gerais no ano de 2026?"*, *"Ranking de vendas por vendedor em julho/2026"*, *"Estoque atual de produtos da categoria Agro"*) and returns mathematically verified data, interactive charts, and tabular breakdowns.

### Core Architectural Guiding Principles:
1. **Deterministic Guardrails for Critical Queries (ADR 0005)**: Critical business metrics (Revenue, Ticket Médio, Discounts, Product Rankings, Open Receivables, Stock) bypass volatile LLM SQL generation and follow verified, deterministic calculation pipelines. LLMs are used for intent extraction and natural language synthesis, never for arbitrary arithmetic.
2. **Strict Multi-Tenant Isolation & Zero Data Leakage**: Every query is wrapped in `ContextGuard` security filters, injecting `tenant_id`, Row-Level Security (RLS), and Role-Based Access Control (RBAC).
3. **Reconciled Data Platform**: Analytics execute against a high-performance local PostgreSQL/SQLite analytical store synchronized from enterprise ERPs (e.g., Oracle DB `DONWMS.VW_VENDAS_LM`).
4. **Multi-Turn Context Inheritance**: State is retained across sequential user questions (`.lumina_conversations`), allowing context inheritance (e.g. asking *"E em 2025?"* inherits the previous query's entity, metrics, and location filters).

---

# SECTION 2: COMPLETE BACKEND MODULE & SERVICE AUDIT

Below is the detailed functional audit of every backend service, detailing its inputs, outputs, rules, and internal logic:

### 1. `backend/services/new_query_orchestrator.py`
- **Role**: Central Orchestrator of the processing pipeline.
- **Functions & Logic**:
  - `process_query(user_prompt, tenant_id, user_role, conversation_id)`: Main entry point.
  - Controls pipeline lifecycle across 7 stages: Context Validation -> Intent Classification -> Plan Generation -> Calculation Execution -> SQL Translation -> Sanitization -> Payload Rendering.
  - Manages multi-turn conversation context, saving state to `.lumina_conversations/<conversation_id>.json`.
  - Implements fallback mechanisms: if a deterministic pipeline fails, it degrades gracefully to standard query intelligence.
  - Profile-based output filtering: `ADMIN` receives full technical trace, plan telemetry, and timing; `CONSULTA` receives only clean business summaries and UI controls.

### 2. `backend/services/context_guard.py`
- **Role**: Security & Access Boundary Manager.
- **Functions & Logic**:
  - `enforce_context(query_request, user_credentials)`: Validates tenant token, user permissions, and scope.
  - Restricts data access strictly to the authenticated `tenant_id`.
  - Prevents illegal cross-tenant queries or unauthorized column access based on user role (`ADMIN` vs `CONSULTA` vs `ANALISTA`).

### 3. `backend/services/planner_engine.py` & `plan_validator.py`
- **Role**: Query Plan Generator & Validator.
- **Functions & Logic**:
  - `generate_plan(natural_language_query, metadata_catalog)`: Extracts target entities (Vendas, Produtos, Estoque, Financeiro, Clientes), metrics (SUM, AVG, COUNT, MAX), and dimensions (UF, Cidade, Filial, Vendedor, Categoria).
  - `services.temporal.TemporalNormalizer`: Canonical deterministic pt-BR normalization for absolute, relative, rolling, closed, accumulated, fiscal, list, range, and comparison expressions. It uses an injected aware reference clock and timezone and produces contract V2 `TimeWindow` values.
  - `_month_range_from_text(text)`: Deprecated compatibility adapter that delegates singular expressions to `lumina.temporal.pt-BR/1.0`; plural expressions are rejected instead of silently selecting one period.
  - Resolves table join paths across dimension and fact views.
  - `plan_validator.py` validates that generated join paths and filter clauses are mathematically and structurally sound before execution.

### 4. `backend/services/sales_value_breakdown_service.py`
- **Role**: Specialized Financial, Sales & Ranking Calculation Engine.
- **Functions & Logic**:
  - `fetch_product_ranking(...)`: Calculates top-selling products by quantity and revenue.
  - `fetch_financial_open(...)`: Retrieves outstanding receivables and debt titles.
  - `execute_breakdown(...)`: Aggregates commercial revenue, Gross Output (Saída RB), returns (Devolução), branch transfers, and net sales.
  - Populates `sample_rows` in query responses to feed frontend detailed data tables.

### 5. `backend/services/query_optimizer_engine.py`
- **Role**: Dialect Compiler & Column Mapping Engine.
- **Functions & Logic**:
  - Houses `VIEW_COLUMN_MAPPING`: Maps high-level semantic fields (`valor`, `data`, `produto`, `cliente`, `desconto`) to physical database view columns (`ptotal_`, `dtemissao_`, `nome_produto`, `nome_cliente`, `vldesconto`).
  - `compile_sql(abstract_plan, target_dialect)`: Translates abstract query trees into optimized dialect-specific SQL (SQLite, PostgreSQL, Oracle).

### 6. `backend/services/semantic_layer.py` & `canonicalizer.py`
- **Role**: Natural Language Normalization & Auto-Healing.
- **Functions & Logic**:
  - `canonicalize_query(user_text)`: Fixes typos (e.g., `"mais vendidoa"`, `"faturameto"`), normalizes accents, and resolves domain synonyms.
  - Auto-healing for unknown terms: maps entity variations (`Produto`, `Financeiro`, `Venda`, `Vendedor`, `Cliente`, `Cidade`, `Estado`, `Categoria`) to canonical catalog IDs.

### 7. `backend/services/security_and_normalization_engine.py`
- **Role**: Injection Guard & AST Sanitizer.
- **Functions & Logic**:
  - Inspects generated SQL ASTs.
  - Blocks dangerous SQL injection patterns and destructive keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`, `--`, `;`).
  - Forces parameterization of all filter values.

### 8. `backend/services/data_platform/analytical_storage.py`
- **Role**: Analytical Storage Execution Layer.
- **Functions & Logic**:
  - `execute_query(sql_string, params)`: Executes parameterized SQL against the tenant's PostgreSQL / SQLite analytical database.
  - Enforces connection timeouts (`timeout=30.0`) and WAL mode for high concurrency.

### 9. `backend/services/aqd_service.py` (Analytical Query Dispatcher)
- **Role**: High-speed dispatcher for pre-packaged analytical queries and blueprint execution.

### 10. `backend/services/cache_service.py`
- **Role**: Multi-tenant Cache Manager.
- **Functions & Logic**:
  - Hashes queries + `tenant_id` + date boundaries into secure cache keys.
  - Invalidates cache on ERP sync events.

### 11. `backend/services/scheduler.py` & `sync_service.py`
- **Role**: ERP Data Synchronization & Background Scheduler.
- **Functions & Logic**:
  - Periodically pulls incremental changes from Oracle DB (`DONWMS.VW_VENDAS_LM`) into PostgreSQL/SQLite analytical store.
  - Executes technical reconciliation (`erp_reconciliation.py`) comparing ERP totals against local analytical totals.
  - Participates in `/health/deep` system monitoring.

---

# SECTION 3: PIPELINE EXECUTION FLOW & STEP ACCESS PERMISSIONS MATRIX

The table below details what each pipeline step **has access to**, what it is **restricted from accessing**, and the AI/rule mechanism involved:

| Stage # | Stage Name | Inputs | Outputs | Allowed Access | Restricted / Blocked Access | AI / Rule Engine |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | **Context Guard** | User Request, JWT Token | Validated Tenant Scope | User Role, Tenant ID, Session Metadata | ❌ Raw Database Engine, Other Tenants' Data | Deterministic Security Rule |
| **Stage 2** | **Canonicalizer & Router** | Raw User Text, History | Intent, Normalized Query | Canonical Dictionary, Term Synonyms | ❌ Database Connection, Direct Execution | Regex + NLP Synonym Rules |
| **Stage 3** | **Planner & Validator** | Normalized Intent, Metadata | Abstract Query Plan | Metadata Catalog, View Schema Definitions | ❌ SQL AST Creation, Direct Data Execution | Deterministic Planner / LLM Fallback |
| **Stage 4** | **Calculations & Breakdown** | Query Plan, Filters | Aggregated Metrics, `sample_rows` | Analytical Storage (Read-Only) | ❌ Database Write Access, System Files | Specialized Calculation Engine |
| **Stage 5** | **Query Optimizer** | Abstract Query Plan | Native Dialect SQL | `VIEW_COLUMN_MAPPING`, Schema Rules | ❌ External API calls | Column Mapping Compiler |
| **Stage 6** | **Security & Sanitizer** | Native Dialect SQL | Sanitized SQL | AST Syntax Tree | ❌ Destructive SQL (`DROP`, `DELETE`) | Security AST Parser |
| **Stage 7** | **Dynamic Renderer** | Raw Data, Intent | JSON UI Payload (`kpi_card`, `bar_chart`, etc.) | UI Component Contracts | ❌ Backend System Internal Logs (for non-admin) | Contract Formatting Engine |

---

# SECTION 4: DEEP DIVE — BLUEPRINT REPOSITORY, METADATA CATALOG & SEMANTIC LAYER

LuminaAI's intelligence relies on three decoupled metadata layers:

```
+-----------------------------------------------------------------------+
|                         BUSINESS QUESTIONS                            |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  SEMANTIC LAYER & CATALOG (business_concept.py, business_kpi.py)       |
|  - Maps business terminology ("Faturamento", "Ticket Médio", "RB")    |
|  - Holds business formulas & calculation rules                        |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  BLUEPRINT REPOSITORY (blueprint.py, analytical_package.py)           |
|  - Pre-defined analytical dashboard templates & query blueprints       |
|  - Defines default visualizations (Table, Bar, Line, Pie)             |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|  METADATA CATALOG (metadata_catalog.py, view_catalog.py)              |
|  - Maps logical concepts to physical DB views (vw_vendas_lm, etc.)    |
|  - Stores Primary Keys, Foreign Keys, column types, join relations    |
+-----------------------------------------------------------------------+
```

### Key Models & File Locations:
- `backend/models/blueprint.py`: Defines analytical blueprints, layout cards, and expected chart types.
- `backend/models/metadata_catalog.py`: Defines table structures, physical column names, data types, and primary/foreign key pairs.
- `backend/models/view_catalog.py`: Catalog of analytical views (`vw_vendas_lm`, `v_produtos`, `v_estoque`, `v_financeiro_aberto`).
- `backend/models/business_concept.py` & `business_kpi.py`: Business KPI formulas (e.g. `Ticket Médio = Faturamento / Total Pedidos`).
- `backend/models/business_formula.py`: Formula parser for derived business calculations.
- `backend/models/new_pipeline_contracts.py`: Dataclass contracts governing data passing between pipeline stages.

---

# SECTION 5: DATABASE SCHEMAS & ORM MODEL AUDIT

The local analytical store mirrors enterprise ERP data into standardized views:

### A. Sales View (`vw_vendas_lm` / `v_vendas`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id_venda` | INTEGER (PK) | Unique Sales Transaction ID |
| `dtemissao_` / `data_venda` | DATE / DATETIME | Transaction Date (`YYYY-MM-DD`) |
| `ptotal_` / `valor_total` | DECIMAL(15,2) | Total Revenue in BRL (R$) |
| `qtde_` / `quantidade` | INTEGER | Number of items sold |
| `id_produto` | INTEGER (FK) | Foreign Key to Product |
| `nome_produto` | VARCHAR(255) | Product Name |
| `id_cliente` | INTEGER (FK) | Foreign Key to Customer |
| `nome_cliente` | VARCHAR(255) | Customer Name |
| `filial_` | VARCHAR(50) | Branch / Subsidiary ID |
| `uf` | VARCHAR(2) | Brazilian State Abbreviation (MG, SP, RJ, BA, etc.) |
| `cidade` | VARCHAR(100) | City Name |
| `ano` | INTEGER | Year (2024, 2025, 2026) |
| `mes` | INTEGER | Month Number (1-12) |
| `tp_` | INTEGER | Operational Transaction Type (`2, 61` = Standard Sales; `9` = Saída RB) |
| `vldesconto` | DECIMAL(15,2) | Discount Amount in BRL |

### B. Products View (`v_produtos` / `dim_produtos`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id_produto` | INTEGER (PK) | Product ID |
| `nome_produto` | VARCHAR(255) | Product Name |
| `categoria` | VARCHAR(100) | Category (e.g. Agro, Ferramentas, Vet) |
| `preco_unitario` | DECIMAL(10,2) | Unit Price |
| `estoque_atual` | INTEGER | Current Stock Quantity |

### C. Inventory View (`v_estoque`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id_produto` | INTEGER (FK) | Product ID |
| `nome_produto` | VARCHAR(255) | Product Name |
| `quantidade_estoque` | INTEGER | Quantity in Stock |
| `filial` | VARCHAR(50) | Branch Name |
| `ano` | INTEGER | Year |

### D. Financial Open View (`v_financeiro_aberto`)
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `id_titulo` | INTEGER (PK) | Financial Document Title ID |
| `id_cliente` | INTEGER (FK) | Customer ID |
| `nome_cliente` | VARCHAR(255) | Customer Name |
| `valor_aberto` | DECIMAL(15,2) | Outstanding Debt Amount (R$) |
| `data_vencimento` | DATE | Due Date |
| `status` | VARCHAR(20) | Document Status (`ABERTO`, `VENCIDO`, `PARCIAL`) |

---

# SECTION 6: FRONTEND ARCHITECTURE & DYNAMIC RENDERER AUDIT

- **Framework**: Next.js 16 (App Router), React 19, TypeScript.
- **Main Layout**: `frontend/app/dashboard/page.tsx`
- **Dynamic Renderer Component**: `frontend/components/DynamicRenderer.tsx`
  - Parses JSON response payloads from backend and dynamically mounts appropriate UI widgets:
    - `"kpi_card"`: Mounts stat cards with trend indicators and comparison metrics.
    - `"bar_chart"`: Mounts ECharts / Recharts Bar Chart.
    - `"line_chart"`: Mounts ECharts / Recharts Line Chart.
    - `"pie_chart"`: Mounts ECharts / Recharts Donut/Pie Chart.
    - `"data_table"`: Mounts dynamic data table with search, pagination, and sorting.
    - `"summary_card"`: Mounts natural language executive summary.
    - `"insights_list"`: Mounts AI-generated business insights.
- **API Base Resolver**: `frontend/lib/utils.ts` -> `getApiBase()`
  - Reads `process.env.NEXT_PUBLIC_API_URL`. Automatically preserves loopback host (`localhost` or `127.0.0.1`) matching user's browser URL to maintain session cookie integrity.
- **Role-Based UI Customization**:
  - `ADMIN`: Shows technical execution diagnostic tab, SQL query plan, execution timing, and system health status.
  - `CONSULTA`: Displays only clean business charts, tables, summaries, and exploration filters.

---

# SECTION 7: INFRASTRUCTURE, PORTS & WINDOWS SERVER DEPLOYMENT

### Master Port Assignment Matrix (Zero Conflict Guarantee):
- **Port 3000**: Reserved for Legacy System 1 (Do Not Touch)
- **Port 3001**: Reserved for Legacy System 2 Frontend (Do Not Touch)
- **Port 3333**: Reserved for Legacy System 2 Backend (Do Not Touch)
- **Port 3002**: **LuminaAI Production Frontend** (`next start -p 3002 -H 0.0.0.0`)
- **Port 8000**: **LuminaAI Production Backend** (`uvicorn main:app --host 0.0.0.0 --port 8000`)

### Automation Scripts Reference:
1. **`instalar_luminaai_servidor.bat`**: Master automated installation script. Auto-installs Python 3.11+ / Node.js 20+, creates `venv`, installs requirements, generates `.env` cryptographic keys (`setup_env_keys.py`), builds Next.js (`npm run build`), provisions Windows Firewall rules for ports 3002 & 8000, and verifies `/health`.
2. **`iniciar_luminaai_servidor.bat`**: 1-click startup launching backend & frontend in background on ports 8000 & 3002.
3. **`parar_luminaai_servidor.bat`**: Safe 1-click stop targeting strictly LuminaAI PIDs on ports 3002 and 8000.
4. **`monitor_luminaai_servidor.bat`**: Interactive CMD console for viewing live system health, running `/health/deep`, and checking error logs.
5. **`scripts/deploy_helper.ps1`**: PowerShell core script powering installation, port checks, and firewall rules.
6. **`scripts/setup_env_keys.py`**: Python script for auto-generating Fernet encryption keys and JWT secrets in `backend/.env`.

---

# SECTION 8: COMMERCIAL SAAS PRICING & ENTERPRISE CONTRACTUAL MODEL

When deploying LuminaAI for corporate clients, use the following pricing structure:

### A. One-Time Setup & Integration Fee (Setup / Implantação)
- **Tier 1 — Single Business / Small DB (1 CNPJ)**: R$ 15.000 — R$ 20.000
- **Tier 2 — Mid-Market / Multi-Branch (ERP + CRM, 2-5 CNPJs)**: R$ 25.000 — R$ 35.000
- **Tier 3 — Enterprise / Custom Data Warehouse (Multi-ERP, Custom DW)**: R$ 45.000+
- *Scope Included*: Database connector configuration, view mapping, domain dictionary setup, security rule setup, staff training.

### B. Monthly Recurring Revenue (MRR / Mensalidade SaaS)
- **Starter Tier (até 5 usuários, 1 CNPJ)**: R$ 2.500 / mês
- **Professional Tier (até 15 usuários, 3 CNPJs)**: R$ 4.500 / mês
- **Enterprise Tier (usuários ilimitados, multi-empresa, SLA prioritário 24/7)**: R$ 7.500 — R$ 12.000+ / mês

---

> **END OF LUMINA AI ULTIMATE ENTERPRISE AUDIT & SPECIFICATION MANUAL**
> *This document represents 100% of the LuminaAI platform specifications, logic, security boundaries, and operational workflows.*
