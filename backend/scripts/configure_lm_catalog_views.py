"""Configure and optionally synchronize LuminaAI LM registration views.

The script is intentionally idempotent:
- upserts ViewCatalog and MetadataCatalog entries;
- keeps new views inactive until their clone table is synchronized;
- only deactivates the legacy customer view after the new customer table exists.

It never prints document values such as CPF/CNPJ.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any

from sqlalchemy import select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_context
from models.tenant import Tenant
from models.view_catalog import ChartType, ViewCatalog
from services.data_platform.catalog_api import catalog_api
from services.data_platform.sync_engine import sync_engine
from services.oracle_service import (
    _close_oracle_resource,
    decrypt_connection_details,
    get_oracle_connection,
)
from services.postgresql_clone_service import get_clone_db_connection, release_clone_db_connection


TENANT_ID = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")


VIEW_CONFIGS: list[dict[str, Any]] = [
    {
        "name": "VW_CLIENTES_CAD_LM",
        "category": "Clientes",
        "description": (
            "Cadastro mestre de clientes do ERP. Use para listar, buscar e filtrar clientes cadastrados, "
            "incluindo codigo, nome, fantasia, CPF/CNPJ, tipo de cliente, endereco, bairro, cidade, UF, "
            "telefone, email, classe e praca. Nao representa vendas, faturamento, ranking ou metricas financeiras."
        ),
        "params": {
            "cliente_nome": {"type": "string", "description": "Nome ou fantasia do cliente"},
            "documento": {"type": "string", "description": "CPF ou CNPJ do cliente"},
            "cidade": {"type": "string", "description": "Cidade/municipio do cliente"},
            "bairro": {"type": "string", "description": "Bairro do cliente"},
            "uf": {"type": "string", "description": "Estado/UF do cliente"},
            "telefone": {"type": "string", "description": "Telefone/celular do cliente"},
            "email": {"type": "string", "description": "Email do cliente"},
            "classe": {"type": "string", "description": "Classe/categoria cadastral"},
            "praca": {"type": "string", "description": "Praca/regiao comercial"},
            "limite": {"type": "integer", "description": "Quantidade maxima de registros"},
        },
        "tags": ["cadastro", "clientes", "documento", "cpf", "cnpj", "contato", "endereco"],
    },
    {
        "name": "VW_VENDEDOR_CAD_LM",
        "category": "Vendedores",
        "description": (
            "Cadastro mestre de vendedores/representantes do ERP. Use para listar e buscar vendedores, "
            "representantes, consultores e seus dados cadastrais. Nao representa performance, metas ou faturamento."
        ),
        "params": {
            "vendedor_nome": {"type": "string", "description": "Nome do vendedor/representante"},
            "codigo_vendedor": {"type": "string", "description": "Codigo do vendedor"},
            "uf": {"type": "string", "description": "UF/estado relacionado ao vendedor"},
            "limite": {"type": "integer", "description": "Quantidade maxima de registros"},
        },
        "tags": ["cadastro", "vendedores", "representantes", "consultores"],
    },
    {
        "name": "VW_PRODUTOS_CAD_LM",
        "category": "Produtos",
        "description": (
            "Cadastro mestre de produtos/itens/SKUs do ERP. Use para listar e buscar produtos cadastrados, "
            "descricoes, categorias, codigos, marcas e atributos cadastrais. Nao representa vendas ou ranking."
        ),
        "params": {
            "produto_nome": {"type": "string", "description": "Nome/descricao do produto"},
            "codigo_produto": {"type": "string", "description": "Codigo ou SKU do produto"},
            "categoria": {"type": "string", "description": "Categoria/grupo do produto"},
            "fornecedor_nome": {"type": "string", "description": "Fornecedor vinculado ao produto, quando existir"},
            "limite": {"type": "integer", "description": "Quantidade maxima de registros"},
        },
        "tags": ["cadastro", "produtos", "itens", "sku", "categorias"],
    },
    {
        "name": "VW_FORNECEDOR_CAD_LM",
        "category": "Fornecedores",
        "description": (
            "Cadastro mestre de fornecedores do ERP. Use para listar e buscar fornecedores, razao social, fantasia, "
            "CPF/CNPJ, cidade, UF, contato e dados cadastrais. Nao representa compras, pagamentos ou financeiro."
        ),
        "params": {
            "fornecedor_nome": {"type": "string", "description": "Nome, razao social ou fantasia do fornecedor"},
            "documento": {"type": "string", "description": "CPF/CNPJ do fornecedor"},
            "cidade": {"type": "string", "description": "Cidade/municipio do fornecedor"},
            "uf": {"type": "string", "description": "Estado/UF do fornecedor"},
            "telefone": {"type": "string", "description": "Telefone do fornecedor"},
            "email": {"type": "string", "description": "Email do fornecedor"},
            "limite": {"type": "integer", "description": "Quantidade maxima de registros"},
        },
        "tags": ["cadastro", "fornecedores", "documento", "cpf", "cnpj", "contato"],
    },
    {
        "name": "VW_VENDAS_LM",
        "category": "Vendas",
        "description": (
            "View analitica de vendas/faturamento do ERP. Use para totais de vendas, faturamento, receita, "
            "quantidade vendida, pedidos/notas, ranking de vendedores, ranking de produtos, clientes que mais "
            "compraram, filtros por filial, cliente, produto, vendedor, CFOP, NCM, plano e periodo por data de emissao. "
            "Campos principais: DTEMISSAO_ como data, PTOTAL_ como valor total da venda, QTDE_ como quantidade, "
            "P_UNIT_ como preco unitario, RAZAO_ como cliente, DESCRICAO_ como produto, NOME_ como vendedor e RCA_ "
            "como codigo do vendedor. Nao use para cadastros mestres quando a pergunta pedir apenas listar clientes, "
            "produtos, vendedores ou fornecedores cadastrados."
        ),
        "params": {
            "data_inicio": {"type": "date", "description": "Data inicial de emissao da venda"},
            "data_fim": {"type": "date", "description": "Data final de emissao da venda"},
            "date_range": {"type": "string", "description": "Intervalo de datas da consulta"},
            "cliente_nome": {"type": "string", "description": "Razao/nome do cliente comprador"},
            "codigo_cliente": {"type": "string", "description": "Codigo do cliente comprador"},
            "produto_nome": {"type": "string", "description": "Descricao do produto vendido"},
            "codigo_produto": {"type": "string", "description": "Codigo do produto vendido"},
            "vendedor_nome": {"type": "string", "description": "Nome do vendedor/representante"},
            "codigo_vendedor": {"type": "string", "description": "Codigo RCA do vendedor"},
            "filial": {"type": "string", "description": "Filial da venda"},
            "nota": {"type": "string", "description": "Numero da nota fiscal"},
            "pedido": {"type": "string", "description": "Numero do pedido"},
            "cfop": {"type": "string", "description": "CFOP da operacao"},
            "ncm": {"type": "string", "description": "NCM do produto"},
            "plano": {"type": "string", "description": "Plano/condicao comercial"},
            "limite": {"type": "integer", "description": "Quantidade maxima de registros ou grupos"},
        },
        "tags": ["vendas", "faturamento", "receita", "pedidos", "notas", "produtos", "clientes", "vendedores"],
        "periodos": ["dia", "semana", "mes", "trimestre", "ano", "intervalo_customizado"],
        "kpis": ["receita_total", "faturamento_realizado", "quantidade_pedidos", "unidades_vendidas", "ticket_medio"],
    },
]


async def _upsert_catalog_entries() -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    async with get_db_context() as session:
        for cfg in VIEW_CONFIGS:
            stmt = select(ViewCatalog).where(
                ViewCatalog.tenant_id == TENANT_ID,
                ViewCatalog.nome_view_oracle == cfg["name"],
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.descricao_para_ia = cfg["description"]
                existing.tipo_grafico_padrao = ChartType.TABLE
                existing.parametros_schema = cfg["params"]
                ids[cfg["name"]] = existing.id
            else:
                view = ViewCatalog(
                    tenant_id=TENANT_ID,
                    nome_view_oracle=cfg["name"],
                    descricao_para_ia=cfg["description"],
                    tipo_grafico_padrao=ChartType.TABLE,
                    parametros_schema=cfg["params"],
                    ativo=False,
                )
                session.add(view)
                await session.flush()
                ids[cfg["name"]] = view.id
        await session.commit()

    for cfg in VIEW_CONFIGS:
        await catalog_api.register(
            tenant_id=TENANT_ID,
            tipo="VIEW",
            dados={
                "nome_view": cfg["name"],
                "estrutura_id": cfg["name"],
                "origem": "ERP_ORACLE",
                "owner": "DONWMS",
                "categoria": cfg["category"],
                "tags": cfg["tags"],
                "campos_utilizados": list(cfg["params"].keys()),
                "tabelas_utilizadas": [f"DONWMS.{cfg['name']}"],
                "filtros_padrao": {},
                "periodos_suportados": cfg.get("periodos", []),
                "kpis_suportados": cfg.get("kpis", []),
                "dependencias": [f"DONWMS.{cfg['name']}"],
                "status": "registered",
            },
            lineage_tabelas=[f"DONWMS.{cfg['name']}"],
            upstream_ids=[f"DONWMS.{cfg['name']}"],
        )
    return ids


async def _activate_synced_views(successful: set[str]) -> None:
    async with get_db_context() as session:
        for cfg in VIEW_CONFIGS:
            view = (
                await session.execute(
                    select(ViewCatalog).where(
                        ViewCatalog.tenant_id == TENANT_ID,
                        ViewCatalog.nome_view_oracle == cfg["name"],
                    )
                )
            ).scalar_one_or_none()
            if view:
                view.ativo = cfg["name"] in successful

        if "VW_CLIENTES_CAD_LM" in successful:
            legacy = (
                await session.execute(
                    select(ViewCatalog).where(
                        ViewCatalog.tenant_id == TENANT_ID,
                        ViewCatalog.nome_view_oracle == "VW_CLIENTES_CADASTRADO",
                    )
                )
            ).scalar_one_or_none()
            if legacy:
                legacy.ativo = False
        await session.commit()


async def _clone_quality(pg_conn, table_name: str) -> dict[str, Any]:
    exists = await pg_conn.fetchval(
        "SELECT exists(SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1)",
        table_name,
    )
    if not exists:
        return {"table": table_name, "exists": False}

    columns = await pg_conn.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position",
        table_name,
    )
    col_names = [r["column_name"] for r in columns]
    result: dict[str, Any] = {
        "table": table_name,
        "exists": True,
        "row_count": await pg_conn.fetchval(f'SELECT count(*) FROM "{table_name}"'),
        "columns": col_names[:80],
    }
    for doc_col in ("cnpj_cpf", "cpf_cnpj", "cpf", "cnpj", "documento", "cgc", "cgc_cpf"):
        if doc_col in col_names:
            row = await pg_conn.fetchrow(
                f"""
                SELECT count(*) total,
                       count(*) filter (
                           WHERE regexp_replace(coalesce({doc_col}::text,''), '\\D','','g') ~ '^[0]+$'
                           AND regexp_replace(coalesce({doc_col}::text,''), '\\D','','g') <> ''
                       ) all_zero,
                       count(*) filter (
                           WHERE regexp_replace(coalesce({doc_col}::text,''), '\\D','','g') !~ '^[0]*$'
                       ) non_zero
                FROM "{table_name}"
                """
            )
            result[f"{doc_col}_quality"] = dict(row)
    return result


async def main() -> None:
    ids = await _upsert_catalog_entries()
    report: dict[str, Any] = {"catalog_ids": {k: str(v) for k, v in ids.items()}, "sync": []}
    successful: set[str] = set()

    async with get_db_context() as session:
        tenant = (await session.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one()
        oracle_details = decrypt_connection_details(tenant.oracle_conn)
        pg_details = decrypt_connection_details(tenant.clone_db_conn)

    oracle_conn = None
    pg_conn = None
    try:
        oracle_conn = await get_oracle_connection(oracle_details, ignore_mock_global=True)
        pg_conn = await get_clone_db_connection(pg_details)

        for cfg in VIEW_CONFIGS:
            started = time.perf_counter()
            try:
                imported = await sync_engine._sync_single_view(
                    tenant_id=TENANT_ID,
                    view_name=cfg["name"],
                    view_catalog_id=ids[cfg["name"]],
                    oracle_conn=oracle_conn,
                    pg_conn=pg_conn,
                )
                successful.add(cfg["name"])
                quality = await _clone_quality(pg_conn, cfg["name"].lower())
                report["sync"].append(
                    {
                        "view": cfg["name"],
                        "status": "success",
                        "imported_rows": imported,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        "quality": quality,
                    }
                )
            except Exception as exc:
                report["sync"].append(
                    {
                        "view": cfg["name"],
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "safe_error": str(exc)[:500],
                    }
                )
    except Exception as exc:
        report["connection_error"] = {
            "error_type": type(exc).__name__,
            "safe_error": str(exc)[:500],
        }
    finally:
        if oracle_conn:
            await _close_oracle_resource(oracle_conn)
        if pg_conn:
            await release_clone_db_connection(pg_conn)

    if successful:
        await _activate_synced_views(successful)
    else:
        report["activation_skipped"] = "Nenhuma view foi sincronizada nesta execucao; status ativo existente preservado."
    report["activated_views"] = sorted(successful)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
