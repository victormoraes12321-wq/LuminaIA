DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('ADMIN', 'GESTOR', 'CONSULTA');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chart_type') THEN
        CREATE TYPE chart_type AS ENUM (
            'BAR', 'LINE', 'PIE', 'TABLE', 'KPI', 'KPI_CARD',
            'AREA', 'SCATTER', 'HEATMAP', 'TREEMAP', 'FUNNEL', 'DONUT'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS test_vendas_lm (
    tenant_id UUID NOT NULL,
    dtemissao_ DATE NOT NULL,
    filial_ TEXT NOT NULL,
    pedido_ TEXT NOT NULL,
    nota_ TEXT,
    serie_ TEXT,
    codcliente_ TEXT,
    rca_ TEXT,
    cfop_ TEXT,
    tp_ INTEGER NOT NULL,
    tpdescricao_ TEXT,
    ptotal_ NUMERIC(18, 2) NOT NULL,
    qtde_ NUMERIC(18, 4) NOT NULL DEFAULT 0,
    p_unit_ NUMERIC(18, 4) NOT NULL DEFAULT 0,
    codprod_ TEXT,
    descricao_ TEXT,
    desconto_total NUMERIC(18, 2) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_vendedor_cad_lm (
    tenant_id UUID NOT NULL,
    codi_ved TEXT NOT NULL,
    nome_ved TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_clientes_cad_lm (
    tenant_id UUID NOT NULL,
    codigo TEXT NOT NULL,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_produtos_cad_lm (
    tenant_id UUID NOT NULL,
    codigo TEXT NOT NULL,
    nome_produto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    estoque NUMERIC(18, 4) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_financeiro_lm (
    tenant_id UUID NOT NULL,
    financeiro_id TEXT NOT NULL,
    status_pagamento TEXT NOT NULL,
    valor_parcela NUMERIC(18, 2) NOT NULL,
    data_vencimento DATE NOT NULL,
    cliente_id TEXT NOT NULL
);

CREATE OR REPLACE VIEW vw_vendas_lm AS
SELECT * FROM test_vendas_lm;

CREATE OR REPLACE VIEW vw_vendedor_cad_lm AS
SELECT * FROM test_vendedor_cad_lm;

CREATE OR REPLACE VIEW vw_clientes_cad_lm AS
SELECT * FROM test_clientes_cad_lm;

CREATE OR REPLACE VIEW vw_produtos_cad_lm AS
SELECT * FROM test_produtos_cad_lm;

CREATE OR REPLACE VIEW vw_financeiro_lm AS
SELECT * FROM test_financeiro_lm;
