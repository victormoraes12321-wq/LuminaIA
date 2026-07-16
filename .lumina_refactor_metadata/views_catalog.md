# Views Catalog — LuminaAI
> Gerado por auditoria estática completa | Data: 2026-07-15 | Versão do Pipeline: 2.0

---

## Resumo

| View | Banco | Origem | Função Principal | Total Colunas |
|------|-------|--------|-----------------|--------------|
| VW_VENDAS_LM | luminaai_analytics_db | Oracle (sync) | Transações de vendas | 14 |
| VW_CLIENTES_CAD_LM | luminaai_analytics_db | Oracle (sync) | Cadastro de clientes | 6 |
| VW_PRODUTOS_CAD_LM | luminaai_analytics_db | Oracle (sync) | Cadastro de produtos | 5 |
| VW_VENDEDOR_CAD_LM | luminaai_analytics_db | Oracle (sync) | Cadastro de vendedores | 3 |
| VW_FINANCEIRO_LM | luminaai_analytics_db | Oracle (sync) | Contas a receber / financeiro | 5 |

---

## 1. VW_VENDAS_LM

**Banco:** `luminaai_analytics_db`  
**Schema:** `public`  
**Origem:** Oracle ERP (sincronizado via `sync_service.py` → `oracle_service.py`)  
**Finalidade:** View principal de transações de vendas (notas fiscais / pedidos). Contém 585.810 registros de produção.  
**Entidade Lógica:** `Venda`  
**Tipo:** View analítica de fatos (fact table)

### Colunas

| Coluna | Tipo Físico | Nullable | Significado de Negócio |
|--------|-------------|----------|----------------------|
| `filial_` | text | sim | Código/nome da filial emissora |
| `tp_` | numeric | sim | Tipo do documento fiscal |
| `codcliente_` | numeric | sim | **FK → VW_CLIENTES_CAD_LM.codigo** — Código do cliente |
| `razao_` | text | sim | Razão social do cliente na emissão |
| `nota_` | numeric | sim | **PK Natural** — Número da nota fiscal |
| `pedido_` | numeric | sim | Número do pedido comercial |
| `dtemissao_` | timestamp | sim | **Data de emissão** — principal filtro temporal |
| `codprod_` | numeric | sim | **FK → VW_PRODUTOS_CAD_LM.codigo** — Código do produto |
| `descricao_` | text | sim | Descrição do produto na nota |
| `qtde_` | numeric | sim | Quantidade vendida |
| `p_unit_` | numeric | sim | Preço unitário |
| `ptotal_` | numeric | sim | **Valor total** — principal métrica de faturamento |
| `rca_` | numeric | sim | **FK → VW_VENDEDOR_CAD_LM.codi_ved** — Código do vendedor/RCA |
| `nome_` | text | sim | Nome do vendedor/RCA na nota |

### Chaves
- **PK Natural:** `nota_` (número da nota fiscal)
- **FK:** `codcliente_` → `VW_CLIENTES_CAD_LM.codigo`
- **FK:** `codprod_` → `VW_PRODUTOS_CAD_LM.codigo`
- **FK:** `rca_` → `VW_VENDEDOR_CAD_LM.codi_ved`

### Quem utiliza
- `metadata_provider.py` → entidade `Venda`
- `query_optimizer_engine.py` → `VIEW_COLUMN_MAPPING["VW_VENDAS_LM"]`
- `planner_engine.py` → nodo central do grafo BFS
- `new_query_orchestrator.py` → execução física de SQL
- `tests/mass_stress_test.py` → todos os cenários analíticos

---

## 2. VW_CLIENTES_CAD_LM

**Banco:** `luminaai_analytics_db`  
**Schema:** `public`  
**Origem:** Oracle ERP (sync)  
**Finalidade:** Cadastro de clientes da empresa (dimensão).  
**Entidade Lógica:** `Cliente`  
**Tipo:** View de dimensão

### Colunas

| Coluna | Tipo Físico | Nullable | Significado de Negócio |
|--------|-------------|----------|----------------------|
| `codigo` | numeric | não | **PK** — Código do cliente |
| `cnpj_cpf` | text | sim | CNPJ ou CPF do cliente |
| `nome` | text | sim | Nome/Razão Social |
| `nome_cidade` | text | sim | Município do cliente |
| `uf` | text | sim | Estado (UF) |
| `tpcli` | text | sim | Tipo/Status do cliente (ex: ATIVO, INATIVO) |

### Chaves
- **PK:** `codigo`
- **Natural Key:** `cnpj_cpf`

### Quem utiliza
- `metadata_provider.py` → entidade `Cliente`
- `query_optimizer_engine.py` → `VIEW_COLUMN_MAPPING["VW_CLIENTES_CAD_LM"]`
- `planner_engine.py` → destino de JOIN via `codcliente_`

---

## 3. VW_PRODUTOS_CAD_LM

**Banco:** `luminaai_analytics_db`  
**Schema:** `public`  
**Origem:** Oracle ERP (sync)  
**Finalidade:** Cadastro de produtos da empresa (dimensão).  
**Entidade Lógica:** `Produto`  
**Tipo:** View de dimensão

### Colunas

| Coluna | Tipo Físico | Nullable | Significado de Negócio |
|--------|-------------|----------|----------------------|
| `codigo` | text | não | **PK** — Código do produto |
| `descricao` | text | sim | Descrição completa |
| `estoque` | numeric | sim | Estoque atual |
| `familia` | text | sim | Família/Categoria do produto |
| `nome_produto` | text | sim | Nome curto do produto |

> ⚠️ **ATENÇÃO:** `codigo` é do tipo `text` enquanto `VW_VENDAS_LM.codprod_` é `numeric`. O JOIN requer cast explícito `::text`.

### Chaves
- **PK:** `codigo` (tipo text)
- **Relacionamento:** JOIN com `VW_VENDAS_LM.codprod_::text`

### Quem utiliza
- `metadata_provider.py` → entidade `Produto`
- `query_optimizer_engine.py` → `VIEW_COLUMN_MAPPING["VW_PRODUTOS_CAD_LM"]`

---

## 4. VW_VENDEDOR_CAD_LM

**Banco:** `luminaai_analytics_db`  
**Schema:** `public`  
**Origem:** Oracle ERP (sync)  
**Finalidade:** Cadastro de vendedores/RCAs (dimensão).  
**Entidade Lógica:** `Vendedor`  
**Tipo:** View de dimensão

### Colunas

| Coluna | Tipo Físico | Nullable | Significado de Negócio |
|--------|-------------|----------|----------------------|
| `codi_ved` | numeric | não | **PK** — Código do vendedor |
| `nome_ved` | text | sim | Nome completo do vendedor |
| `muni_ved` | text | sim | Município de atuação |

> ⚠️ A view também pode conter `carg_ved` (cargo) e `area_ved` (área) — identificadas no mapeamento legado mas não confirmadas como presentes em produção.

### Chaves
- **PK:** `codi_ved` (numeric)
- **Relacionamento:** JOIN com `VW_VENDAS_LM.rca_`

---

## 5. VW_FINANCEIRO_LM

**Banco:** `luminaai_analytics_db`  
**Schema:** `public`  
**Origem:** Oracle ERP (sync)  
**Finalidade:** Contas a receber / parcelas financeiras.  
**Entidade Lógica:** `Financeiro`  
**Tipo:** View de fatos financeiros

### Colunas (conforme metadata_provider.py — não confirmado em produção)

| Coluna | Tipo | Nullable | Significado de Negócio |
|--------|------|----------|----------------------|
| `financeiro_id` | ? | não | **PK** |
| `cliente_id` | ? | sim | FK para cliente |
| `valor_parcela` | numeric | sim | Valor da parcela |
| `status_pagamento` | text | sim | Status do pagamento |
| `data_vencimento` | timestamp | sim | Data de vencimento |

> ⚠️ **RISCO:** Esta view não foi confirmada como existente no `luminaai_analytics_db`. Os nomes de colunas podem não corresponder ao schema físico real.

### Quem utiliza
- `metadata_provider.py` → entidade `Financeiro` (definida mas raramente usada nos testes)
- `planner_engine.py` → grafo BFS — nodo periférico

---

## Views do Banco Operacional (luminaai_db)

> O banco operacional `luminaai_db` contém tabelas ORM do sistema (não views analíticas do negócio).

### Tabelas ORM relevantes (banco: luminaai_db)
| Tabela | Finalidade |
|--------|-----------|
| `tenants` | Cadastro multi-tenant |
| `users` | Usuários do sistema |
| `metadata_catalog` | Catálogo de metadados por tenant |
| `view_catalog` | Registro de views por tenant |
| `business_concepts` | Conceitos de negócio definidos |
| `business_kpis` | KPIs configurados |
| `blueprints` | Blueprints de dashboards |
| `analytical_packages` | Pacotes analíticos |
| `semantic_catalog` | Catálogo semântico |
| `semantic_memory` | Memória semântica de conversas |
| `search_history` | Histórico de buscas |
| `sync_queue` | Fila de sincronização Oracle→PostgreSQL |
| `data_platform_history` | Histórico de execuções |

---

*Auditoria estática — nenhum arquivo modificado.*
