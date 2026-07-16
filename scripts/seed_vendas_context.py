"""
LuminaAI — Seed: Contexto Unificado de Vendas v3.0

Popula o catálogo de views com o Contexto Vendas para o tenant de demonstração.
Execute APÓS o setup_db.py e com o PostgreSQL rodando.

Usage:
    cd backend
    python ../scripts/seed_vendas_context.py
    python ../scripts/seed_vendas_context.py <tenant_id>
"""
import asyncio
import sys
import os

# Garante que o backend está no path de importação
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import select
from database import AsyncSessionLocal
from models.view_catalog import ViewCatalog, ChartType
from models.tenant import Tenant


# ── Catálogo do Contexto Vendas ────────────────────────────────────────────────

VENDAS_VIEWS = [
    {
        "nome": "VW_VENDAS_CONTEXTO_GERAL",
        "tipo": ChartType.TABLE,
        "descricao": (
            "Visão geral e completa de todas as vendas e pedidos da loja. "
            "Contém: número do pedido, data da venda, nome do vendedor, nome do cliente, "
            "produtos vendidos, quantidade, valor unitário, valor total, desconto aplicado, "
            "forma de pagamento (dinheiro/cartão/pix/boleto), status do pedido "
            "(APROVADO/PENDENTE/CANCELADO/EM_PROCESSAMENTO), número da nota fiscal, "
            "loja/filial, região. "
            "Use para: listar vendas de um período específico, buscar pedidos de um cliente, "
            "ver o que um vendedor vendeu, consultar histórico de compras de qualquer pessoa, "
            "filtrar por status, produto, forma de pagamento ou qualquer combinação de filtros."
        ),
        "parametros": {
            "data_inicio": {"type": "date", "required": False, "description": "Data início do período"},
            "data_fim": {"type": "date", "required": False, "description": "Data fim do período"},
            "vendedor_nome": {"type": "string", "required": False, "description": "Nome parcial do vendedor"},
            "cliente_nome": {"type": "string", "required": False, "description": "Nome parcial do cliente"},
            "produto_nome": {"type": "string", "required": False, "description": "Nome parcial do produto"},
            "status": {"type": "string", "required": False, "description": "Status do pedido"},
            "loja": {"type": "string", "required": False, "description": "Nome da loja/filial"},
            "forma_pagamento": {"type": "string", "required": False, "description": "Forma de pagamento"},
            "limite": {"type": "number", "required": False, "description": "Máximo de registros (padrão: 500)"},
        },
    },
    {
        "nome": "VW_FATURAMENTO_MENSAL",
        "tipo": ChartType.LINE,
        "descricao": (
            "Evolução do faturamento mês a mês com comparativo entre meta e realizado. "
            "Dados por mês: mês de referência, faturamento realizado (R$), meta mensal (R$), "
            "percentual de atingimento da meta, crescimento vs mês anterior (%), "
            "número de transações, ticket médio. "
            "Use para: analisar crescimento de vendas ao longo do tempo, ver tendência, "
            "comparar meses, histórico de faturamento do ano, evolução do negócio, "
            "gráfico de vendas mensais, faturamento do ano passado ou desse ano."
        ),
        "parametros": {
            "data_inicio": {"type": "date", "required": False},
            "data_fim": {"type": "date", "required": False},
            "ano": {"type": "number", "required": False},
            "loja": {"type": "string", "required": False},
            "regiao": {"type": "string", "required": False},
        },
    },
    {
        "nome": "VW_PERFORMANCE_VENDEDORES",
        "tipo": ChartType.BAR,
        "descricao": (
            "Ranking e performance completa de todos os vendedores do período. "
            "Dados por vendedor: nome completo, código do funcionário, faturamento realizado (R$), "
            "meta mensal (R$), percentual de atingimento da meta (%), número de vendas fechadas, "
            "ticket médio por venda, comissão calculada (R$), posição no ranking, "
            "número de clientes atendidos, produtos mais vendidos por vendedor. "
            "Use para: ver ranking de vendedores, quem bateu ou não bateu a meta, "
            "comparar desempenho entre vendedores, top vendedores do mês, comissões a pagar, "
            "dados específicos de um vendedor, meta de qualquer vendedor."
        ),
        "parametros": {
            "mes": {"type": "number", "required": False},
            "ano": {"type": "number", "required": False},
            "data_inicio": {"type": "date", "required": False},
            "data_fim": {"type": "date", "required": False},
            "vendedor_nome": {"type": "string", "required": False},
            "limite": {"type": "number", "required": False},
        },
    },
    {
        "nome": "VW_CLIENTES_HISTORICO",
        "tipo": ChartType.TABLE,
        "descricao": (
            "Dados completos de clientes e seu histórico total de compras. "
            "Dados por cliente: nome completo, código de cliente, telefone, email, "
            "cidade, estado, data do primeiro pedido, data da última compra, "
            "dias desde a última compra, total de pedidos realizados, "
            "valor total gasto (R$), ticket médio por pedido, produtos mais comprados, "
            "classificação do cliente (VIP/regular/inativo). "
            "Use para: buscar dados de um cliente específico, ver histórico de compras de alguém, "
            "clientes inativos há X dias, maiores compradores, clientes por região ou cidade, "
            "o que um cliente comprou, total gasto por cliente, lista de clientes."
        ),
        "parametros": {
            "cliente_nome": {"type": "string", "required": False},
            "data_inicio": {"type": "date", "required": False},
            "data_fim": {"type": "date", "required": False},
            "regiao": {"type": "string", "required": False},
            "status": {"type": "string", "required": False},
            "limite": {"type": "number", "required": False},
        },
    },
    {
        "nome": "VW_PRODUTOS_MAIS_VENDIDOS",
        "tipo": ChartType.PIE,
        "descricao": (
            "Análise completa de produtos: ranking dos mais vendidos e market share por categoria. "
            "Dados por produto: nome, código, categoria, subcategoria, "
            "quantidade total vendida, faturamento gerado (R$), participação no total de vendas (%), "
            "margem de contribuição (%), preço médio de venda, estoque atual. "
            "Use para: produtos mais vendidos do período, market share de produtos, "
            "análise de mix de produtos, quais categorias vendem mais, produto mais lucrativo, "
            "desempenho de uma categoria específica, produtos menos vendidos."
        ),
        "parametros": {
            "mes": {"type": "number", "required": False},
            "ano": {"type": "number", "required": False},
            "data_inicio": {"type": "date", "required": False},
            "data_fim": {"type": "date", "required": False},
            "categoria": {"type": "string", "required": False},
            "produto_nome": {"type": "string", "required": False},
            "limite": {"type": "number", "required": False},
        },
    },
    {
        "nome": "VW_KPI_EXECUTIVO_VENDAS",
        "tipo": ChartType.KPI,
        "descricao": (
            "Painel de KPIs executivos consolidados do negócio para o período selecionado. "
            "Métricas principais: faturamento total (R$), meta do período (R$), "
            "percentual de atingimento da meta, ticket médio por venda, "
            "número total de transações, novos clientes captados, NPS (satisfação), "
            "margem bruta (%), comparativo vs período anterior com variação percentual. "
            "Use para: resumo executivo, visão geral do negócio, como estão as vendas hoje/mês/semana, "
            "painel de indicadores, KPIs do mês, números gerais, performance geral da loja."
        ),
        "parametros": {
            "mes": {"type": "number", "required": False},
            "ano": {"type": "number", "required": False},
            "data_inicio": {"type": "date", "required": False},
            "data_fim": {"type": "date", "required": False},
            "loja": {"type": "string", "required": False},
        },
    },
    {
        "nome": "VW_ESTOQUE_STATUS",
        "tipo": ChartType.TABLE,
        "descricao": (
            "Status atual e completo do estoque de todos os produtos da loja. "
            "Dados por produto: nome, código, categoria, estoque atual (unidades), "
            "estoque mínimo configurado, estoque máximo, situação "
            "(OK/ALERTA/CRÍTICO/ZERADO), dias sem reposição, data última entrada, "
            "valor do estoque em R$, custo unitário. "
            "Use para: produtos com estoque crítico ou zerado, quais produtos repor, "
            "alertas de estoque, inventário completo, valor total em estoque, "
            "estoque de um produto específico, produtos em falta na loja."
        ),
        "parametros": {
            "produto_nome": {"type": "string", "required": False},
            "categoria": {"type": "string", "required": False},
            "tipo_alerta": {"type": "string", "required": False, "description": "ok|alerta|critico|zerado"},
            "limite": {"type": "number", "required": False},
        },
    },
    {
        "nome": "VW_METAS_ATINGIMENTO",
        "tipo": ChartType.BAR,
        "descricao": (
            "Análise de metas vs realizado por vendedor e por loja/filial com projeção. "
            "Dados: nome do vendedor ou filial, meta definida para o período (R$), "
            "valor realizado até o momento (R$), percentual de atingimento (%), "
            "valor faltante para atingir a meta ou valor excedente (R$), "
            "projeção de fechamento do mês baseada no ritmo atual, "
            "dias restantes no período. "
            "Use para: quem atingiu ou vai atingir a meta, percentual de atingimento, "
            "quanto falta para cada vendedor bater a meta, metas do mês, "
            "projeção e forecast de vendas, ranking por atingimento de metas."
        ),
        "parametros": {
            "mes": {"type": "number", "required": False},
            "ano": {"type": "number", "required": False},
            "vendedor_nome": {"type": "string", "required": False},
            "loja": {"type": "string", "required": False},
        },
    },
]


async def seed_vendas_context(tenant_id: str | None = None) -> None:
    """Popula o catálogo com as views do Contexto Vendas."""
    async with AsyncSessionLocal() as session:
        # Determina o tenant alvo
        if tenant_id:
            import uuid
            try:
                tid = uuid.UUID(tenant_id)
            except ValueError:
                print(f"❌ tenant_id inválido: {tenant_id!r}")
                return
        else:
            result = await session.execute(select(Tenant).limit(1))
            tenant = result.scalar_one_or_none()
            if not tenant:
                print("❌ Nenhum tenant encontrado. Execute setup_db.py primeiro.")
                return
            tid = tenant.id
            print(f"✅ Tenant encontrado: {tenant.nome} (ID: {tid})")

        print(f"\n🔧 Populando catálogo para tenant {tid}...\n")
        created = 0
        skipped = 0
        errors = 0

        for view_def in VENDAS_VIEWS:
            try:
                # Verifica se já existe
                existing_result = await session.execute(
                    select(ViewCatalog).where(
                        ViewCatalog.nome_view_oracle == view_def["nome"],
                        ViewCatalog.tenant_id == tid,
                    )
                )
                if existing_result.scalar_one_or_none():
                    print(f"  ⏭️  Já existe: {view_def['nome']}")
                    skipped += 1
                    continue

                view = ViewCatalog(
                    tenant_id=tid,
                    nome_view_oracle=view_def["nome"],
                    descricao_para_ia=view_def["descricao"],
                    tipo_grafico_padrao=view_def["tipo"],
                    parametros_schema=view_def["parametros"],
                    ativo=True,
                )
                session.add(view)
                print(f"  ✅ Criado: {view_def['nome']} ({view_def['tipo'].value})")
                created += 1

            except Exception as e:
                print(f"  ❌ Erro ao criar {view_def['nome']}: {e}")
                errors += 1

        await session.commit()

        print(f"\n{'='*60}")
        print(f"📊 Seed Contexto Vendas concluído!")
        print(f"   ✅ Criadas:      {created}")
        print(f"   ⏭️  Já existiam:  {skipped}")
        if errors:
            print(f"   ❌ Erros:        {errors}")
        print(f"{'='*60}\n")
        print("💡 Próximos passos:")
        print("   1. Inicie o backend: python -m uvicorn main:app --reload")
        print("   2. Configure as views reais no Oracle quando for ao servidor")
        print("   3. Teste queries livres como:")
        print("      • 'Quanto faturei esse mês?'")
        print("      • 'Quais produtos estão com estoque crítico?'")
        print("      • 'Me mostre o ranking dos vendedores de junho'")


if __name__ == "__main__":
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(seed_vendas_context(tenant_id))
