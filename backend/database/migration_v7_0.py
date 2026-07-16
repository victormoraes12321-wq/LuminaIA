import sys
import asyncio
import logging
import json
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("luminaai.migration_v7_0")

async def run_migration():
    db_url = settings.DATABASE_URL
    logger.info("Migrando banco analítico: %s", db_url.split("@")[-1])
    engine = create_async_engine(db_url, echo=False)
    
    async with engine.begin() as conn:
        logger.info("Adicionando kpis_suportados a metadata_catalog se necessário...")
        await conn.execute(text("""
            ALTER TABLE metadata_catalog 
            ADD COLUMN IF NOT EXISTS kpis_suportados JSONB NOT NULL DEFAULT '[]'
        """))
        
        logger.info("Criando tabela semantic_catalog se necessário...")
        semantic_commands = [
            """
            CREATE TABLE IF NOT EXISTS semantic_catalog (
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
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_semantic_tenant_id ON semantic_catalog (tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_semantic_nome_oficial ON semantic_catalog (nome_oficial)",
            "CREATE INDEX IF NOT EXISTS idx_semantic_sinonimos ON semantic_catalog USING GIN (sinonimos)",
            "DROP TRIGGER IF EXISTS trg_semantic_atualizado_em ON semantic_catalog",
            """
            CREATE TRIGGER trg_semantic_atualizado_em
                BEFORE UPDATE ON semantic_catalog
                FOR EACH ROW
                EXECUTE FUNCTION fn_update_atualizado_em()
            """
        ]
        for cmd in semantic_commands:
            await conn.execute(text(cmd))
            
        # Seed inicial para o Tenant de Demonstração
        tenant_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        logger.info("Inserindo sementes no Semantic Catalog para o tenant %s...", tenant_id)
        
        seeds = [
            {
                "nome_oficial": "receita_total",
                "descricao": "Total de vendas realizadas em um período comercial.",
                "sinonimos": ["receita", "faturamento", "venda", "venda bruta", "valor vendido", "faturamento_total", "total_vendas"],
                "categoria": "Financeiro",
                "tipo": "Monetário",
                "unidade": "R$",
                "formato": "currency",
                "metodo_agregacao": "Soma",
                "contexto": "Vendas líquidas faturadas no período",
                "kpis_relacionados": ["lucro_bruto", "margem_lucro", "ticket_medio"],
                "indicadores_derivados": ["lucro_bruto"],
                "visualizacoes_recomendadas": ["LINE", "BAR", "KPI"],
                "restricoes": [],
                "permissoes": ["Geral"]
            },
            {
                "nome_oficial": "lucro_bruto",
                "descricao": "Receita total líquida deduzindo custos operacionais diretos, taxas e impostos.",
                "sinonimos": ["lucro", "margem_bruta"],
                "categoria": "Financeiro",
                "tipo": "Monetário",
                "unidade": "R$",
                "formato": "currency",
                "metodo_agregacao": "Soma",
                "contexto": "Lucratividade bruta da operação",
                "kpis_relacionados": ["receita_total", "margem_lucro", "ticket_medio"],
                "indicadores_derivados": ["margem_lucro"],
                "visualizacoes_recomendadas": ["BAR", "KPI"],
                "restricoes": [],
                "permissoes": ["Diretoria", "Financeiro"]
            },
            {
                "nome_oficial": "margem_lucro",
                "descricao": "Margem percentual de lucratividade sobre a receita total gerada.",
                "sinonimos": ["margem", "lucratividade"],
                "categoria": "Financeiro",
                "tipo": "Percentual",
                "unidade": "%",
                "formato": "percentage",
                "metodo_agregacao": "Média",
                "contexto": "Percentual de lucro sobre faturamento",
                "kpis_relacionados": ["lucro_bruto", "receita_total"],
                "indicadores_derivados": [],
                "visualizacoes_recomendadas": ["LINE", "KPI", "BAR"],
                "restricoes": [],
                "permissoes": ["Diretoria", "Financeiro"]
            },
            {
                "nome_oficial": "ticket_medio",
                "descricao": "Valor médio transacionado por cada venda concluída.",
                "sinonimos": ["ticket", "valor_medio_compra"],
                "categoria": "Financeiro",
                "tipo": "Monetário",
                "unidade": "R$",
                "formato": "currency",
                "metodo_agregacao": "Média",
                "contexto": "Valor médio gasto por transação",
                "kpis_relacionados": ["receita_total", "quantidade_pedidos"],
                "indicadores_derivados": [],
                "visualizacoes_recomendadas": ["LINE", "KPI"],
                "restricoes": [],
                "permissoes": ["Geral"]
            },
            {
                "nome_oficial": "quantidade_pedidos",
                "descricao": "Número total de pedidos ou transações de vendas no período.",
                "sinonimos": ["pedidos", "volume_vendas"],
                "categoria": "Comercial",
                "tipo": "Quantidade",
                "unidade": "un",
                "formato": "integer",
                "metodo_agregacao": "Soma",
                "contexto": "Quantidade absoluta de transações faturadas",
                "kpis_relacionados": ["receita_total", "ticket_medio"],
                "indicadores_derivados": ["ticket_medio"],
                "visualizacoes_recomendadas": ["BAR", "KPI"],
                "restricoes": [],
                "permissoes": ["Geral"]
            }
        ]
        
        for s in seeds:
            await conn.execute(
                text("""
                    INSERT INTO semantic_catalog (
                        tenant_id, nome_oficial, descricao, sinonimos, categoria, tipo,
                        unidade, formato, metodo_agregacao, contexto, kpis_relacionados,
                        indicadores_derivados, visualizacoes_recomendadas, restricoes, permissoes, versao
                    ) VALUES (
                        :tenant_id, :nome_oficial, :descricao, :sinonimos, :categoria, :tipo,
                        :unidade, :formato, :metodo_agregacao, :contexto, :kpis_relacionados,
                        :indicadores_derivados, :visualizacoes_recomendadas, :restricoes, :permissoes, 1
                    ) ON CONFLICT (nome_oficial, tenant_id) DO UPDATE SET
                        descricao = EXCLUDED.descricao,
                        sinonimos = EXCLUDED.sinonimos,
                        categoria = EXCLUDED.categoria,
                        tipo = EXCLUDED.tipo,
                        unidade = EXCLUDED.unidade,
                        formato = EXCLUDED.formato,
                        metodo_agregacao = EXCLUDED.metodo_agregacao,
                        contexto = EXCLUDED.contexto,
                        kpis_relacionados = EXCLUDED.kpis_relacionados,
                        indicadores_derivados = EXCLUDED.indicadores_derivados,
                        visualizacoes_recomendadas = EXCLUDED.visualizacoes_recomendadas,
                        restricoes = EXCLUDED.restricoes,
                        permissoes = EXCLUDED.permissoes,
                        versao = semantic_catalog.versao + 1,
                        atualizado_em = NOW();
                """),
                {
                    "tenant_id": tenant_id,
                    "nome_oficial": s["nome_oficial"],
                    "descricao": s["descricao"],
                    "sinonimos": json.dumps(s["sinonimos"]),
                    "categoria": s["categoria"],
                    "tipo": s["tipo"],
                    "unidade": s["unidade"],
                    "formato": s["formato"],
                    "metodo_agregacao": s["metodo_agregacao"],
                    "contexto": s["contexto"],
                    "kpis_relacionados": json.dumps(s["kpis_relacionados"]),
                    "indicadores_derivados": json.dumps(s["indicadores_derivados"]),
                    "visualizacoes_recomendadas": json.dumps(s["visualizacoes_recomendadas"]),
                    "restricoes": json.dumps(s["restricoes"]),
                    "permissoes": json.dumps(s["permissoes"])
                }
            )
            
    await engine.dispose()
    logger.info("✅ Migração v7.0 executada com sucesso!")

if __name__ == '__main__':
    asyncio.run(run_migration())
