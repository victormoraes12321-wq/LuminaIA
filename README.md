# LuminaAI — Enterprise BI & Governed AI Analytics Platform

[![Release](https://img.shields.io/badge/release-v2.0.0--rc4-blue.svg)](CHANGELOG.md)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.12-green.svg)](backend/)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20React%2019-black.svg)](frontend/)
[![Database](https://img.shields.io/badge/database-PostgreSQL%20Safe%20Analytical%20Clone-blue.svg)](backend/database/)
[![Security](https://img.shields.io/badge/security-AES--256--GCM%20%7C%20Fail--Closed-red.svg)](docs/security.md)

LuminaAI é uma plataforma Enterprise de **Business Intelligence Executivo** e **Processamento de Linguagem Natural para Analytics (NL-to-SQL)** desenvolvida para ambientes corporativos de alta criticidade. A plataforma combina um backend assíncrono em FastAPI, um frontend executivo em Next.js 16 (React 19, Turbopack, Apache ECharts) e uma arquitetura determinística de clone analítico em PostgreSQL.

---

## 1. Destaques da Versão V2 Release Candidate 4 (RC4)

- **Cockpit Executivo em Tempo Real**: Métricas e rankings consolidados da empresa (Faturamento, Quantidade, Ticket Médio, Notas/Pedidos, Clientes Ativos, Vendedores Ativos, Mix de Produtos e Filiais) agregados diretamente da base analítica auditada.
- **Drill-Downs Interativos & Títulos Dinâmicos**: Navegação multidimensional por Filial, Vendedor, Produto e Cliente com breadcrumb contextual inteligente e zeramento atômico de filtros.
- **Consultar Dados com IA (`/consultar`)**: Assistente executivo de linguagem natural com alternância instantânea de modelos visuais (Barras, Linhas, Pizza/Donut, Planilha Completa, Cards KPI) e painel proativo de refinamento de regras de negócio (Faturamento Líquido vs Bruto).
- **Centro de Comando SaaS Modernizado**:
  - **Gerenciamento de Usuários (`/dashboard/admin/users`)**: Fita de estatísticas em tempo real, filtros por papel com iluminação neon e cartões cyber glassmorphism.
  - **Dicionário de Views Semântico (`/dashboard/admin/catalog`)**: Mapeamento de views físicas relacionais com parametrização dinâmica governada.
  - **Configurações & Telemetria (`/dashboard/admin/settings`)**: Monitoramento de tenant, roteamento de múltiplos provedores de LLM (GPT-4o, Groq), base PostgreSQL Clone e chaves AES-256-GCM segregadas por tenant.

---

## 2. Visão Geral da Arquitetura

O LuminaAI V2 adota uma arquitetura determinística onde modelos de IA atuam na interpretação semântica e intenção, enquanto todos os cálculos matemáticos, agregações e geração SQL são executados por motores determinísticos governados.

```
                  ┌──────────────────────────────────────────────┐
                  │          Usuário / Executive Cockpit         │
                  │             (Next.js 16 + React 19)          │
                  └──────────────────────┬───────────────────────┘
                                         │ HTTPS / REST / SSE
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │              FastAPI Backend (V2)            │
                  │  ┌────────────────────────────────────────┐  │
                  │  │ Executive Metrics Service (Direct SQL) │  │
                  │  ├────────────────────────────────────────┤  │
                  │  │ Intent Engine & LLM Routing (Groq/GPT) │  │
                  │  ├────────────────────────────────────────┤  │
                  │  │ Context Resolution & Semantic Layer    │  │
                  │  ├────────────────────────────────────────┤  │
                  │  │ Validation & Provenance Certifier      │  │
                  │  └────────────────────────────────────────┘  │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       PostgreSQL Safe Analytical Clone       │
                  │          (Isolamento Multi-Tenant)           │
                  └──────────────────────────────────────────────┘
```

---

## 3. Estrutura do Repositório

```text
├── backend/                        # API FastAPI e serviços analíticos
│   ├── contracts/                  # Contratos Pydantic canônicos V2
│   ├── database/                   # Migrações e esquemas de dados
│   ├── models/                     # Modelos ORM SQLAlchemy
│   ├── routers/                    # Endpoints HTTP da API (Dashboard, Consultar, Admin, Auth)
│   ├── schemas/                    # Schemas Pydantic de validação
│   ├── services/                   # Motores de IA, regras de negócio e agregação direta
│   └── tests/                      # Suíte de testes automatizados pytest
├── frontend/                       # Aplicação Next.js 16 (React 19)
│   ├── app/                        # App Router (Dashboard, Consultar, Admin, Login)
│   ├── components/                 # Cockpit executivo, ECharts, chat e painéis SaaS
│   ├── hooks/                      # Hooks de telemetria, autenticação e SSE
│   ├── lib/                        # Clientes de API, exportadores e utilitários
│   └── types/                      # Definições estritas TypeScript
├── docs/                           # Documentação técnica e arquitetural
├── configure-luminaai-firewall.ps1 # Configuração de portas no Windows Firewall
├── start-luminaai-windows.ps1      # Inicialização segura dos serviços em segundo plano
├── status-luminaai-windows.ps1     # Monitoramento de status, PIDs e sondas de saúde
└── stop-luminaai-windows.ps1       # Encerramento seguro de processos
```

---

## 4. Execução e Operação no Windows Server

### Inicialização do Sistema

```powershell
# Iniciar backend (porta 8000) e frontend (porta 3002) com monitoramento
.\start-luminaai-windows.ps1 -Wait
```

### Verificação de Status

```powershell
# Verificar saúde dos serviços e portas
.\status-luminaai-windows.ps1
```

### Encerramento Seguro

```powershell
# Encerrar processos Node.js e Python do LuminaAI
.\stop-luminaai-windows.ps1
```

---

## 5. Endpoints de Diagnóstico e Saúde (Health)

- **Liveness:** `GET /health` — Retorna 200 quando o processo FastAPI está ativo.
- **Readiness:** `GET /health/deep` — Executa verificação profunda de dependências (PostgreSQL, IA, Configurações de Segurança e Migrações).
- **Frontend Health:** `GET /healthz` — Endpoint de integridade da aplicação Next.js.

---

## 6. Licença e Governança

LuminaAI V2 RC4 — Todos os direitos reservados.
Desenvolvido com isolamento lógico multi-tenant e segurança em conformidade corporativa.
