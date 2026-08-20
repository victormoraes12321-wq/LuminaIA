-- ================================================================
-- LuminaAI — Schema PostgreSQL Completo
-- Sistema de Business Intelligence Inteligente
-- Versão: 1.0.0 | Engine: PostgreSQL 14+
-- ================================================================

-- Extensão para geração de UUIDs nativos
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================================
-- ENUMs — Tipos nativos do PostgreSQL
-- ================================================================

CREATE TYPE user_role AS ENUM (
    'ADMIN',     -- Acesso total: gerencia tenant, usuários e catálogo
    'GESTOR',    -- Gerencia catálogo de views e visualiza histórico da equipe
    'CONSULTA'   -- Apenas executa consultas e gerencia seus favoritos
);

CREATE TYPE chart_type AS ENUM (
    'BAR',      -- Grafico de barras (verticais ou horizontais)
    'LINE',     -- Grafico de linhas (serie temporal)
    'PIE',      -- Grafico de pizza / donut
    'TABLE',    -- Tabela de dados paginada
    'KPI',      -- Painel de KPIs / metricas executivas
    'AREA',     -- Grafico de area preenchida
    'SCATTER',  -- Grafico de dispersao (scatter plot)
    'HEATMAP',  -- Mapa de calor
    'TREEMAP',  -- Treemap hierarquico
    'FUNNEL'    -- Funil de conversao
);


-- ================================================================
-- FUNÇÃO: Atualiza coluna atualizado_em automaticamente
-- ================================================================

CREATE OR REPLACE FUNCTION fn_update_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ================================================================
-- TABELA: tenants
-- Empresas clientes do sistema LuminaAI (Multi-tenant SaaS)
-- ================================================================

CREATE TABLE tenants (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    nome            VARCHAR(255)    NOT NULL,
    logo_url        TEXT,
    tema_config     JSONB           NOT NULL DEFAULT '{}',
    ia_config       JSONB           NOT NULL DEFAULT '{}',
    oracle_conn     JSONB           NOT NULL DEFAULT '{}',
    clone_db_conn   JSONB           NOT NULL DEFAULT '{}',
    sync_config     JSONB           NOT NULL DEFAULT '{"enabled": false, "times": []}',
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_tenants PRIMARY KEY (id)
);

COMMENT ON TABLE  tenants               IS 'Empresas clientes do sistema LuminaAI (multi-tenant)';
COMMENT ON COLUMN tenants.tema_config   IS 'JSON com configurações visuais: primary_color, dark_mode, font, logo_url_override';
COMMENT ON COLUMN tenants.ia_config     IS 'JSON com config de IA por tenant: model, temperature, max_tokens, custom_instructions';
COMMENT ON COLUMN tenants.oracle_conn   IS 'JSON criptografado com dados de conexão Oracle: host, port, sid, user, password (Fernet encrypted)';
COMMENT ON COLUMN tenants.clone_db_conn IS 'JSON criptografado com dados de conexão PostgreSQL do Clone: host, port, user, password, database (Fernet encrypted)';
COMMENT ON COLUMN tenants.sync_config   IS 'JSON com configurações de sincronização: enabled (bool), times (array of strings)';

CREATE INDEX idx_tenants_ativo
    ON tenants (ativo)
    WHERE ativo = TRUE;

CREATE TRIGGER trg_tenants_atualizado_em
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: users
-- Usuários do sistema, segmentados por tenant
-- ================================================================

CREATE TABLE users (
    id              UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id       UUID            NOT NULL,
    nome            VARCHAR(255)    NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    password_hash   TEXT            NOT NULL,
    role            user_role       NOT NULL DEFAULT 'CONSULTA',
    ativo           BOOLEAN         NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN    NOT NULL DEFAULT TRUE,
    ultimo_acesso   TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_users                     PRIMARY KEY (id),
    CONSTRAINT fk_users_tenant              FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT uq_users_email_per_tenant    UNIQUE (email, tenant_id)
);

COMMENT ON TABLE  users             IS 'Usuários autenticados do sistema, isolados por tenant';
COMMENT ON COLUMN users.role        IS 'ADMIN: acesso total | GESTOR: gerencia catálogo | CONSULTA: apenas consultas';
COMMENT ON COLUMN users.ultimo_acesso IS 'Timestamp do último login bem-sucedido';

CREATE INDEX idx_users_tenant_id        ON users (tenant_id);
CREATE INDEX idx_users_email            ON users (email);
CREATE INDEX idx_users_role             ON users (role);
CREATE INDEX idx_users_tenant_email     ON users (tenant_id, email);
CREATE INDEX idx_users_ativo            ON users (ativo) WHERE ativo = TRUE;

CREATE TRIGGER trg_users_atualizado_em
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: view_catalog
-- Catálogo de views Oracle disponíveis por tenant
-- ================================================================

CREATE TABLE view_catalog (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    nome_view_oracle        VARCHAR(255)    NOT NULL,
    descricao_para_ia       TEXT            NOT NULL,
    tipo_grafico_padrao     chart_type      NOT NULL DEFAULT 'BAR',
    parametros_schema       JSONB           NOT NULL DEFAULT '{}',
    ativo                   BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_view_catalog                      PRIMARY KEY (id),
    CONSTRAINT fk_view_catalog_tenant               FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT uq_view_catalog_nome_per_tenant      UNIQUE (nome_view_oracle, tenant_id)
);

COMMENT ON TABLE  view_catalog                      IS 'Catálogo de views Oracle que a IA pode identificar e executar';
COMMENT ON COLUMN view_catalog.descricao_para_ia    IS 'Descrição semântica rica, enviada ao LLM como contexto para identificação da intenção';
COMMENT ON COLUMN view_catalog.parametros_schema    IS 'Schema JSON dos parâmetros aceitos: {campo: {type, required, description, example}}';

CREATE INDEX idx_view_catalog_tenant_id     ON view_catalog (tenant_id);
CREATE INDEX idx_view_catalog_tenant_ativo  ON view_catalog (tenant_id, ativo) WHERE ativo = TRUE;
CREATE INDEX idx_view_catalog_tipo          ON view_catalog (tipo_grafico_padrao);

CREATE TRIGGER trg_view_catalog_atualizado_em
    BEFORE UPDATE ON view_catalog
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: search_history
-- Histórico completo de consultas realizadas
-- ================================================================

CREATE TABLE search_history (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL,
    view_catalog_id         UUID,
    pergunta_texto          TEXT            NOT NULL,
    parametros_extraidos    JSONB           NOT NULL DEFAULT '{}',
    ia_confianca            NUMERIC(5, 4),
    tempo_resposta_ms       INTEGER,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_search_history        PRIMARY KEY (id),
    CONSTRAINT fk_sh_user               FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_sh_view_catalog       FOREIGN KEY (view_catalog_id) REFERENCES view_catalog (id) ON DELETE SET NULL,
    CONSTRAINT chk_sh_confianca         CHECK (ia_confianca IS NULL OR (ia_confianca >= 0 AND ia_confianca <= 1)),
    CONSTRAINT chk_sh_tempo             CHECK (tempo_resposta_ms IS NULL OR tempo_resposta_ms >= 0)
);

COMMENT ON TABLE  search_history                        IS 'Auditoria completa de todas as consultas realizadas no sistema';
COMMENT ON COLUMN search_history.ia_confianca           IS 'Score de confiança da IA no matching de intenção (0.0000 a 1.0000)';
COMMENT ON COLUMN search_history.tempo_resposta_ms      IS 'Latência total da requisição em milissegundos (IA + Oracle + overhead)';
COMMENT ON COLUMN search_history.view_catalog_id        IS 'Nulo se a IA não identificou uma view correspondente';

CREATE INDEX idx_sh_user_id             ON search_history (user_id);
CREATE INDEX idx_sh_view_catalog_id     ON search_history (view_catalog_id);
CREATE INDEX idx_sh_criado_em_desc      ON search_history (criado_em DESC);
CREATE INDEX idx_sh_user_criado_em      ON search_history (user_id, criado_em DESC);


-- ================================================================
-- TABELA: favorites
-- Consultas salvas pelos usuários com parâmetros persistidos
-- ================================================================

CREATE TABLE favorites (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL,
    view_catalog_id         UUID            NOT NULL,
    titulo_personalizado    VARCHAR(255),
    parametros_salvos       JSONB           NOT NULL DEFAULT '{}',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_favorites                     PRIMARY KEY (id),
    CONSTRAINT fk_favorites_user                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_favorites_view_catalog        FOREIGN KEY (view_catalog_id) REFERENCES view_catalog (id) ON DELETE CASCADE,
    CONSTRAINT uq_favorites_user_view           UNIQUE (user_id, view_catalog_id)
);

COMMENT ON TABLE  favorites                         IS 'Análises favoritadas pelos usuários com parâmetros salvos para re-execução rápida';
COMMENT ON COLUMN favorites.titulo_personalizado    IS 'Nome customizado dado pelo usuário ao favorito (ex: "Vendas Q4 2024 - Minha Região")';
COMMENT ON COLUMN favorites.parametros_salvos       IS 'Snapshot dos parâmetros extraídos na consulta original (data_inicio, filtros, etc.)';

CREATE INDEX idx_favorites_user_id          ON favorites (user_id);
CREATE INDEX idx_favorites_view_catalog_id  ON favorites (view_catalog_id);


-- ================================================================
-- TABELA: blueprint_repository
-- Repositório de Blueprints Inteligentes da Data Platform
-- ================================================================

CREATE TABLE blueprint_repository (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    intent_id               VARCHAR(255)    NOT NULL,
    nome_consulta           VARCHAR(255)    NOT NULL,
    objetivo                TEXT            NOT NULL,
    tipo_analise            VARCHAR(100)    NOT NULL DEFAULT 'AGGREGATION',
    view_catalog_id         UUID,
    view_name               VARCHAR(255)    NOT NULL,
    metrics                 JSONB           NOT NULL DEFAULT '[]',
    group_by                JSONB           NOT NULL DEFAULT '[]',
    filters                 JSONB           NOT NULL DEFAULT '{}',
    visualization_type      VARCHAR(100)    NOT NULL DEFAULT 'TABLE',
    layout                  JSONB           NOT NULL DEFAULT '{}',
    exemplos_perguntas      JSONB           NOT NULL DEFAULT '[]',
    categoria               VARCHAR(100)    NOT NULL DEFAULT 'Geral',
    dominio_negocio         VARCHAR(100)    NOT NULL DEFAULT 'GERAL',
    area                    VARCHAR(100)    NOT NULL DEFAULT 'Geral',
    tags                    JSONB           NOT NULL DEFAULT '[]',
    autor                   VARCHAR(255)    NOT NULL DEFAULT 'IA',
    status                  VARCHAR(50)     NOT NULL DEFAULT 'ACTIVE',
    marketplace_scope       VARCHAR(50)     NOT NULL DEFAULT 'TENANT',
    is_marketplace          BOOLEAN         NOT NULL DEFAULT FALSE,
    fingerprint             JSONB           NOT NULL DEFAULT '{}',
    fingerprint_hash        VARCHAR(64)     NOT NULL DEFAULT '',
    identity                JSONB           NOT NULL DEFAULT '{}',
    business_intent         JSONB           NOT NULL DEFAULT '{}',
    semantic_context        JSONB           NOT NULL DEFAULT '{}',
    business_context        JSONB           NOT NULL DEFAULT '{}',
    kpi_strategy            JSONB           NOT NULL DEFAULT '{}',
    visualization_strategy  JSONB           NOT NULL DEFAULT '{}',
    component_strategy      JSONB           NOT NULL DEFAULT '{}',
    filter_strategy         JSONB           NOT NULL DEFAULT '{}',
    grouping_strategy       JSONB           NOT NULL DEFAULT '{}',
    navigation_strategy     JSONB           NOT NULL DEFAULT '{}',
    dashboard_template_reference JSONB      NOT NULL DEFAULT '{}',
    metadata_info           JSONB           NOT NULL DEFAULT '{}',
    dependencies_map        JSONB           NOT NULL DEFAULT '{}',
    version_info            JSONB           NOT NULL DEFAULT '{}',
    performance_profile     JSONB           NOT NULL DEFAULT '{}',
    quality_profile         JSONB           NOT NULL DEFAULT '{}',
    health_profile          JSONB           NOT NULL DEFAULT '{}',
    version                 INTEGER         NOT NULL DEFAULT 1,
    dependencias            JSONB           NOT NULL DEFAULT '[]',
    permissoes              JSONB           NOT NULL DEFAULT '[]',
    quantidade_utilizacoes  INTEGER         NOT NULL DEFAULT 0,
    tempo_acumulado_ms      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    tempo_ia_acumulado_ms   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    tokens_economizados     INTEGER         NOT NULL DEFAULT 0,
    ultima_utilizacao       TIMESTAMPTZ,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_blueprint_repository          PRIMARY KEY (id),
    CONSTRAINT fk_blueprint_tenant              FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX idx_blueprint_tenant_id ON blueprint_repository (tenant_id);
CREATE INDEX idx_blueprint_intent_id ON blueprint_repository (intent_id);
CREATE INDEX idx_blueprint_fingerprint_hash ON blueprint_repository (fingerprint_hash);
CREATE INDEX idx_blueprint_status ON blueprint_repository (status);
CREATE INDEX idx_blueprint_marketplace ON blueprint_repository (marketplace_scope, is_marketplace);
CREATE UNIQUE INDEX uq_blueprint_identity_version ON blueprint_repository (tenant_id, intent_id, version);

CREATE TRIGGER trg_blueprint_atualizado_em
    BEFORE UPDATE ON blueprint_repository
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: metadata_catalog
-- Catálogo de metadados operacionais das views analíticas
-- ================================================================

CREATE TABLE metadata_catalog (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    nome_view               VARCHAR(255)    NOT NULL,
    origem                  VARCHAR(100)    NOT NULL DEFAULT 'ERP_ORACLE',
    tabelas_utilizadas      JSONB           NOT NULL DEFAULT '[]',
    campos_utilizados       JSONB           NOT NULL DEFAULT '[]',
    relacionamentos         JSONB           NOT NULL DEFAULT '[]',
    filtros_padrao          JSONB           NOT NULL DEFAULT '{}',
    periodos_suportados     JSONB           NOT NULL DEFAULT '[]',
    versao                  INTEGER         NOT NULL DEFAULT 1,
    status                  VARCHAR(100)    NOT NULL DEFAULT 'success',
    ultima_sincronizacao    TIMESTAMPTZ,
    proxima_sincronizacao   TIMESTAMPTZ,
    quantidade_consultas    INTEGER         NOT NULL DEFAULT 0,
    dependencias            JSONB           NOT NULL DEFAULT '[]',
    tempo_medio_atualizacao NUMERIC(10, 2)  NOT NULL DEFAULT 0.00,
    tempo_medio_execucao    Numeric(10, 2)  NOT NULL DEFAULT 0.00,
    integridade             VARCHAR(100)    NOT NULL DEFAULT 'valid',
    hash_integridade        VARCHAR(128)    NOT NULL DEFAULT '',
    kpis_suportados         JSONB           NOT NULL DEFAULT '[]',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_metadata_catalog              PRIMARY KEY (id),
    CONSTRAINT fk_metadata_tenant               FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT uq_metadata_view_per_tenant      UNIQUE (nome_view, tenant_id)
);

CREATE INDEX idx_metadata_tenant_id ON metadata_catalog (tenant_id);
CREATE INDEX idx_metadata_nome_view ON metadata_catalog (nome_view);

CREATE TRIGGER trg_metadata_atualizado_em
    BEFORE UPDATE ON metadata_catalog
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: semantic_catalog
-- Fonte oficial de significado, contexto e relacionamento de conceitos de negócio
-- ================================================================

CREATE TABLE semantic_catalog (
    id                          UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id                   UUID            NOT NULL,
    nome_oficial                VARCHAR(100)    NOT NULL,
    descricao                   TEXT            NOT NULL,
    sinonimos                   JSONB           NOT NULL DEFAULT '[]',
    categoria                   VARCHAR(100)    NOT NULL DEFAULT 'Geral',
    tipo                        VARCHAR(100)    NOT NULL DEFAULT 'Fato',
    unidade                     VARCHAR(50)     NOT NULL DEFAULT '',
    formato                     VARCHAR(100)    NOT NULL DEFAULT 'number',
    metodo_agregacao            VARCHAR(100)    NOT NULL DEFAULT 'Soma',
    contexto                    TEXT,
    kpis_relacionados           JSONB           NOT NULL DEFAULT '[]',
    indicadores_derivados       JSONB           NOT NULL DEFAULT '[]',
    visualizacoes_recomendadas  JSONB           NOT NULL DEFAULT '[]',
    restricoes                  JSONB           NOT NULL DEFAULT '[]',
    permissoes                  JSONB           NOT NULL DEFAULT '[]',
    versao                      INTEGER         NOT NULL DEFAULT 1,
    criado_em                   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_semantic_catalog              PRIMARY KEY (id),
    CONSTRAINT fk_semantic_tenant               FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT uq_semantic_concept_per_tenant   UNIQUE (nome_oficial, tenant_id)
);

CREATE INDEX idx_semantic_tenant_id ON semantic_catalog (tenant_id);
CREATE INDEX idx_semantic_nome_oficial ON semantic_catalog (nome_oficial);
CREATE INDEX idx_semantic_sinonimos ON semantic_catalog USING GIN (sinonimos);

CREATE TRIGGER trg_semantic_atualizado_em
    BEFORE UPDATE ON semantic_catalog
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: datasets
-- Armazena os datasets analíticos estruturados, versionados e tipados
-- ================================================================

CREATE TABLE datasets (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    dados_estruturados      JSONB           NOT NULL DEFAULT '[]',
    tipagem_correta         JSONB           NOT NULL DEFAULT '{}',
    metadados               JSONB           NOT NULL DEFAULT '{}',
    version                 INTEGER         NOT NULL DEFAULT 1,
    origem                  VARCHAR(255)    NOT NULL,
    blueprint_id            VARCHAR(255),
    dashboard_id            UUID,
    view_catalog_id         UUID,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_datasets PRIMARY KEY (id),
    CONSTRAINT fk_datasets_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX idx_datasets_tenant_id ON datasets (tenant_id);
CREATE INDEX idx_datasets_origem ON datasets (origem);
CREATE INDEX idx_datasets_blueprint_id ON datasets (blueprint_id);
CREATE INDEX idx_datasets_dashboard_id ON datasets (dashboard_id);
CREATE INDEX idx_datasets_view_catalog_id ON datasets (view_catalog_id);
CREATE INDEX idx_datasets_criado_em ON datasets (criado_em DESC);
CREATE INDEX idx_datasets_dados_gin ON datasets USING gin (dados_estruturados);

CREATE TRIGGER trg_datasets_atualizado_em
    BEFORE UPDATE ON datasets
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();


-- ================================================================
-- TABELA: data_platform_history
-- Registro histórico imutável das mudanças estruturais na Data Platform
-- ================================================================

CREATE TABLE data_platform_history (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    estrutura_tipo          VARCHAR(100)    NOT NULL, -- 'VIEW', 'BLUEPRINT', 'DATASET', 'METADADOS'
    estrutura_id            VARCHAR(255)    NOT NULL,
    acao                    VARCHAR(100)    NOT NULL, -- 'CREATE', 'UPDATE', 'RECONSTRUCT', 'VERSION_UP'
    detalhes                JSONB           NOT NULL DEFAULT '{}',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_data_platform_history PRIMARY KEY (id),
    CONSTRAINT fk_history_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX idx_history_tenant_id ON data_platform_history (tenant_id);
CREATE INDEX idx_history_lookup ON data_platform_history (estrutura_tipo, estrutura_id);
CREATE INDEX idx_history_criado_em ON data_platform_history (criado_em DESC);


-- ================================================================
-- SEED: Dados de demonstração LuminaAI

-- ================================================================

-- Tenant de demonstração
INSERT INTO tenants (id, nome, logo_url, tema_config, ia_config, oracle_conn)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'LuminaAI Demo Corp',
    'https://cdn.luminaai.com/logos/demo-corp.png',
    '{
        "primary_color": "#6C63FF",
        "secondary_color": "#00D2D3",
        "accent_color": "#FF6B6B",
        "dark_mode": true,
        "font_family": "Inter",
        "border_radius": "12px"
    }',
    '{
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 1024,
        "custom_instructions": "Responda sempre em português brasileiro. Priorize precisão sobre velocidade."
    }',
    '{
        "encrypted": true,
        "algorithm": "Fernet",
        "payload": "DEMO_TENANT_ORACLE_CONN_ENCRYPTED_REPLACE_WITH_REAL"
    }'
);

-- Usuário Admin de demonstração
-- ATENÇÃO: Substituir password_hash por hash bcrypt real antes de uso em produção
INSERT INTO users (id, tenant_id, nome, email, password_hash, role, must_change_password)
VALUES (
    'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380b22',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Administrador LuminaAI',
    'ti@casadocampo.vet.br',
    '$2b$12$BQ59GtiaJqGsmvOZ6Anp0OqLwJdBlC2vpCBlB5L02VKxgWOYwEUb6',
    'ADMIN',
    FALSE
);

-- Catálogo de views Oracle de demonstração
INSERT INTO view_catalog (tenant_id, nome_view_oracle, descricao_para_ia, tipo_grafico_padrao, parametros_schema)
VALUES
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'VW_VENDAS_MENSAIS',
        'Exibe o volume e valor total de vendas agrupados por mês e ano fiscal. '
        'Útil para análise de desempenho comercial, tendências de faturamento, '
        'receita mensal acumulada, comparativo de períodos e sazonalidade de vendas. '
        'Indicado quando o usuário pergunta sobre faturamento, receita, vendas, '
        'quanto foi vendido, performance comercial ou resultados financeiros por período.',
        'BAR',
        '{
            "ano": {"type": "integer", "required": false, "description": "Ano fiscal (ex: 2024)", "example": "2024"},
            "mes": {"type": "integer", "required": false, "description": "Mês numérico 1-12", "example": "6"},
            "data_inicio": {"type": "date", "required": false, "description": "Data inicial do período (ISO 8601)", "example": "2024-01-01"},
            "data_fim": {"type": "date", "required": false, "description": "Data final do período (ISO 8601)", "example": "2024-12-31"}
        }'
    ),
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'VW_EVOLUCAO_CLIENTES',
        'Apresenta a evolução temporal da base de clientes ativos, novos clientes adquiridos '
        'e taxa de churn (cancelamentos) ao longo do tempo. Útil para análise de crescimento '
        'da carteira de clientes, retenção, fidelização, churn rate, NRR (Net Revenue Retention) '
        'e tendências de expansão ou contração da base. '
        'Indicado quando o usuário pergunta sobre clientes, crescimento, churn, cancelamentos, '
        'retenção ou evolução da carteira.',
        'LINE',
        '{
            "data_inicio": {"type": "date", "required": false, "description": "Início do período de análise", "example": "2024-01-01"},
            "data_fim": {"type": "date", "required": false, "description": "Fim do período de análise", "example": "2024-12-31"},
            "segmento": {"type": "string", "required": false, "description": "Segmento de clientes (ex: Enterprise, SMB, Mid-Market)", "example": "Enterprise"}
        }'
    ),
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'VW_MARKET_SHARE_PRODUTOS',
        'Apresenta a participação percentual de cada linha ou categoria de produto no '
        'faturamento total da empresa. Útil para análise de mix de produtos, '
        'concentração de receita, diversificação do portfólio, share de mercado interno '
        'e identificação de produtos mais rentáveis. '
        'Indicado quando o usuário pergunta sobre participação de produtos, mix, '
        'distribuição de receita, quais produtos vendem mais ou contribuição por produto.',
        'PIE',
        '{}'
    ),
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'VW_DETALHE_PEDIDOS',
        'Lista detalhada e paginada de pedidos com informações completas: número do pedido, '
        'cliente, valor, status atual, data de criação, prazo de entrega e nota fiscal. '
        'Útil para auditoria operacional, rastreamento de pedidos individuais, '
        'relatórios de status, análise de inadimplência e controle de SLA de entrega. '
        'Indicado quando o usuário pergunta sobre pedidos específicos, status de pedidos, '
        'listagem detalhada, auditoria ou rastreamento.',
        'TABLE',
        '{
            "status": {"type": "string", "required": false, "description": "Status do pedido: APROVADO, PENDENTE, CANCELADO, EM_PROCESSAMENTO", "example": "APROVADO"},
            "data_inicio": {"type": "date", "required": false, "description": "Data inicial de criação do pedido", "example": "2024-01-01"},
            "data_fim": {"type": "date", "required": false, "description": "Data final de criação do pedido", "example": "2024-12-31"},
            "cliente_id": {"type": "string", "required": false, "description": "ID ou nome parcial do cliente", "example": "ACME Corp"}
        }'
    ),
    (
        'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
        'VW_KPI_EXECUTIVO',
        'Painel consolidado de KPIs estratégicos para visão executiva da empresa: '
        'receita total, margem bruta, ticket médio, Net Promoter Score (NPS), '
        'número de novos clientes e taxa de crescimento. '
        'Útil para reuniões de board, apresentações executivas, visão geral de performance '
        'e monitoramento de metas estratégicas. '
        'Indicado quando o usuário pede um resumo geral, dashboard executivo, '
        'KPIs, métricas-chave, performance geral ou visão consolidada.',
        'KPI',
        '{
            "periodo": {"type": "string", "required": false, "description": "Período de referência: mes_atual, trimestre, semestre, ano", "example": "trimestre"},
            "data_referencia": {"type": "date", "required": false, "description": "Data de corte para os KPIs", "example": "2024-12-31"}
        }'
    );

-- ================================================================
-- TABELAS: Dashboard Studio Enterprise
-- Personalizacao visual isolada da inteligencia analitica
-- ================================================================

CREATE TABLE dashboard_templates (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    blueprint_id            UUID,
    analytical_package_id   UUID,
    name                    VARCHAR(255)    NOT NULL,
    description             TEXT,
    category                VARCHAR(100)    NOT NULL DEFAULT 'CUSTOM',
    status                  VARCHAR(50)     NOT NULL DEFAULT 'ACTIVE',
    version                 INTEGER         NOT NULL DEFAULT 1,
    layout                  JSONB           NOT NULL DEFAULT '{}',
    grid                    JSONB           NOT NULL DEFAULT '{}',
    components              JSONB           NOT NULL DEFAULT '[]',
    component_order         JSONB           NOT NULL DEFAULT '[]',
    groups                  JSONB           NOT NULL DEFAULT '[]',
    tabs                    JSONB           NOT NULL DEFAULT '[]',
    sections                JSONB           NOT NULL DEFAULT '[]',
    responsive              JSONB           NOT NULL DEFAULT '{}',
    theme                   JSONB           NOT NULL DEFAULT '{}',
    visual_config           JSONB           NOT NULL DEFAULT '{}',
    default_state           JSONB           NOT NULL DEFAULT '{}',
    available_components    JSONB           NOT NULL DEFAULT '[]',
    permissions             JSONB           NOT NULL DEFAULT '{}',
    created_by              UUID,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_templates PRIMARY KEY (id),
    CONSTRAINT fk_dashboard_templates_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_templates_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX idx_dashboard_templates_tenant ON dashboard_templates (tenant_id);
CREATE INDEX idx_dashboard_templates_status ON dashboard_templates (status);
CREATE INDEX idx_dashboard_templates_blueprint ON dashboard_templates (blueprint_id);
CREATE INDEX idx_dashboard_templates_package ON dashboard_templates (analytical_package_id);
CREATE INDEX idx_dashboard_templates_grid_gin ON dashboard_templates USING GIN (grid);

CREATE TRIGGER trg_dashboard_templates_atualizado_em
    BEFORE UPDATE ON dashboard_templates
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();

CREATE TABLE dashboard_instances (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    template_id             UUID            NOT NULL,
    user_id                 UUID            NOT NULL,
    name                    VARCHAR(255)    NOT NULL,
    status                  VARCHAR(50)     NOT NULL DEFAULT 'ACTIVE',
    is_favorite             BOOLEAN         NOT NULL DEFAULT FALSE,
    version                 INTEGER         NOT NULL DEFAULT 1,
    current_filters         JSONB           NOT NULL DEFAULT '{}',
    expanded_components     JSONB           NOT NULL DEFAULT '[]',
    panel_positions         JSONB           NOT NULL DEFAULT '{}',
    favorites               JSONB           NOT NULL DEFAULT '[]',
    visible_columns         JSONB           NOT NULL DEFAULT '{}',
    sort_orders             JSONB           NOT NULL DEFAULT '{}',
    preferences             JSONB           NOT NULL DEFAULT '{}',
    current_state           JSONB           NOT NULL DEFAULT '{}',
    layout_override         JSONB           NOT NULL DEFAULT '{}',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_instances PRIMARY KEY (id),
    CONSTRAINT fk_dashboard_instances_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_instances_template FOREIGN KEY (template_id) REFERENCES dashboard_templates (id) ON DELETE CASCADE,
    CONSTRAINT fk_dashboard_instances_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX idx_dashboard_instances_tenant_user ON dashboard_instances (tenant_id, user_id);
CREATE INDEX idx_dashboard_instances_template ON dashboard_instances (template_id);
CREATE INDEX idx_dashboard_instances_favorite ON dashboard_instances (tenant_id, user_id, is_favorite);
CREATE INDEX idx_dashboard_instances_status ON dashboard_instances (status);

CREATE TRIGGER trg_dashboard_instances_atualizado_em
    BEFORE UPDATE ON dashboard_instances
    FOR EACH ROW
    EXECUTE FUNCTION fn_update_atualizado_em();

CREATE TABLE dashboard_studio_versions (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    template_id             UUID,
    instance_id             UUID,
    target_type             VARCHAR(30)     NOT NULL,
    version                 INTEGER         NOT NULL,
    snapshot                JSONB           NOT NULL DEFAULT '{}',
    author_id               UUID,
    description             TEXT,
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_dashboard_studio_versions PRIMARY KEY (id),
    CONSTRAINT fk_dsv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_template FOREIGN KEY (template_id) REFERENCES dashboard_templates (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_instance FOREIGN KEY (instance_id) REFERENCES dashboard_instances (id) ON DELETE CASCADE,
    CONSTRAINT fk_dsv_author FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_dashboard_studio_version_single_target CHECK (
        (template_id IS NOT NULL AND instance_id IS NULL)
        OR (template_id IS NULL AND instance_id IS NOT NULL)
    )
);

CREATE INDEX idx_dsv_tenant ON dashboard_studio_versions (tenant_id);
CREATE INDEX idx_dsv_template ON dashboard_studio_versions (template_id);
CREATE INDEX idx_dsv_instance ON dashboard_studio_versions (instance_id);
CREATE INDEX idx_dsv_author ON dashboard_studio_versions (author_id);
CREATE UNIQUE INDEX uq_dsv_template_version ON dashboard_studio_versions (template_id, version) WHERE template_id IS NOT NULL;
CREATE UNIQUE INDEX uq_dsv_instance_version ON dashboard_studio_versions (instance_id, version) WHERE instance_id IS NOT NULL;


-- ================================================================
-- TABELA: semantic_memory
-- Repositório de Memória Semântica Corporativa do CSIE
-- ================================================================

CREATE TABLE semantic_memory (
    id                      UUID            NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               UUID            NOT NULL,
    expressao               VARCHAR(500)    NOT NULL,
    objeto_resolvido        JSONB           NOT NULL DEFAULT '{}',
    score                   NUMERIC(5, 2)   NOT NULL DEFAULT 100.0,
    blueprint_associado     VARCHAR(255),
    frequencia              INTEGER         NOT NULL DEFAULT 1,
    confianca               VARCHAR(50)     NOT NULL DEFAULT 'ALTA',
    origem                  VARCHAR(50)     NOT NULL DEFAULT 'IA',
    criado_em               TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_semantic_memory PRIMARY KEY (id),
    CONSTRAINT fk_semantic_memory_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
);

CREATE INDEX idx_semantic_memory_tenant ON semantic_memory (tenant_id);
CREATE INDEX idx_semantic_memory_expressao ON semantic_memory (expressao);

