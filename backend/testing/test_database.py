from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

from testing.database_guard import (
    guard_engine_before_write,
    validate_connected_test_database,
    validate_test_database_environment,
)


TENANT_A = uuid.UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
TENANT_B = uuid.UUID("b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22")
ADMIN_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
GESTOR_A = uuid.UUID("11111111-1111-4111-8111-111111111112")
CONSULTA_A = uuid.UUID("11111111-1111-4111-8111-111111111113")
TECH_ADMIN_A = uuid.UUID("11111111-1111-4111-8111-111111111114")
ADMIN_B = uuid.UUID("22222222-2222-4222-8222-222222222221")
GESTOR_B = uuid.UUID("22222222-2222-4222-8222-222222222222")
CONSULTA_B = uuid.UUID("22222222-2222-4222-8222-222222222223")
VIEW_A_SALES = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
VIEW_A_VENDOR = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2")
VIEW_B_SALES = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1")

TEST_TABLES = (
    "test_vendas_lm",
    "test_vendedor_cad_lm",
    "test_clientes_cad_lm",
    "test_produtos_cad_lm",
    "test_financeiro_lm",
)
_BOOTSTRAPPED = False


def _bootstrap_sql() -> str:
    path = Path(__file__).resolve().parents[1] / "tests" / "sql" / "bootstrap_test_database.sql"
    return path.read_text(encoding="utf-8")


async def bootstrap_test_database(engine: Any) -> None:
    """Create test-only schema after both URL and connected-target validation."""

    global _BOOTSTRAPPED
    target = await guard_engine_before_write(engine)
    if _BOOTSTRAPPED:
        return
    async with engine.begin() as connection:
        await validate_connected_test_database(connection, target)
        raw_connection = await connection.get_raw_connection()
        await raw_connection.driver_connection.execute(_bootstrap_sql())

        from database import Base
        import models  # noqa: F401

        await connection.run_sync(Base.metadata.create_all)
    _BOOTSTRAPPED = True


async def reset_and_seed_test_database(engine: Any) -> None:
    """Reset all application/test tables and install the deterministic baseline."""

    target = validate_test_database_environment()
    from database import Base
    from services.auth_service import get_password_hash

    model_tables = [table.name for table in Base.metadata.sorted_tables]
    table_names = [*model_tables, *TEST_TABLES]
    quoted_tables = ", ".join(f'"{name}"' for name in table_names)

    async with engine.begin() as connection:
        await validate_connected_test_database(connection, target)
        await connection.execute(
            text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE")
        )

        admin_hash = get_password_hash("AdminLumina@2026")
        user_hash = get_password_hash("SyntheticUser@2026")
        await connection.execute(
            text(
                """
                INSERT INTO tenants (
                    id, nome, logo_url, tema_config, ia_config, oracle_conn,
                    clone_db_conn, sync_config, ativo
                ) VALUES
                    (:tenant_a, 'Empresa Sintetica A', NULL, '{}'::jsonb,
                     '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                     '{"enabled": false}'::jsonb, TRUE),
                    (:tenant_b, 'Empresa Sintetica B', NULL, '{}'::jsonb,
                     '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                     '{"enabled": false}'::jsonb, TRUE)
                """
            ),
            {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
        )
        await connection.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, nome, email, password_hash, role,
                    ativo, must_change_password
                ) VALUES
                    (:admin_a, :tenant_a, 'Admin A', 'admin@luminaai.demo',
                     :admin_hash, 'ADMIN', TRUE, TRUE),
                    (:gestor_a, :tenant_a, 'Gestor A', 'gestor.a@lumina.internal',
                     :user_hash, 'GESTOR', TRUE, FALSE),
                    (:consulta_a, :tenant_a, 'Consulta A', 'consulta.a@lumina.internal',
                     :user_hash, 'CONSULTA', TRUE, FALSE),
                    (:tech_admin_a, :tenant_a, 'Admin Tecnico A',
                     'technical.admin@lumina.internal',
                     :user_hash, 'ADMIN', TRUE, FALSE),
                    (:admin_b, :tenant_b, 'Admin B', 'admin.b@lumina.internal',
                     :user_hash, 'ADMIN', TRUE, FALSE),
                    (:gestor_b, :tenant_b, 'Gestor B', 'gestor.b@lumina.internal',
                     :user_hash, 'GESTOR', TRUE, FALSE),
                    (:consulta_b, :tenant_b, 'Consulta B', 'consulta.b@lumina.internal',
                     :user_hash, 'CONSULTA', TRUE, FALSE)
                """
            ),
            {
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
                "admin_a": ADMIN_A,
                "gestor_a": GESTOR_A,
                "consulta_a": CONSULTA_A,
                "tech_admin_a": TECH_ADMIN_A,
                "admin_b": ADMIN_B,
                "gestor_b": GESTOR_B,
                "consulta_b": CONSULTA_B,
                "admin_hash": admin_hash,
                "user_hash": user_hash,
            },
        )
        await connection.execute(
            text(
                """
                INSERT INTO view_catalog (
                    id, tenant_id, nome_view_oracle, descricao_para_ia,
                    tipo_grafico_padrao, parametros_schema, ativo
                ) VALUES
                    (:view_a_sales, :tenant_a, 'VW_VENDAS_LM',
                     'Vendas sinteticas do tenant A.',
                     'TABLE', '{}'::jsonb, TRUE),
                    (:view_a_vendor, :tenant_a, 'VW_PERFORMANCE_VENDEDORES',
                     'Ranking sintetico de vendedores do tenant A.',
                     'BAR', '{}'::jsonb, TRUE),
                    (:view_b_sales, :tenant_b, 'VW_VENDAS_LM',
                     'Vendas sinteticas do tenant B.',
                     'TABLE', '{}'::jsonb, TRUE)
                """
            ),
            {
                "tenant_a": TENANT_A,
                "tenant_b": TENANT_B,
                "view_a_sales": VIEW_A_SALES,
                "view_a_vendor": VIEW_A_VENDOR,
                "view_b_sales": VIEW_B_SALES,
            },
        )

        await _seed_analytical_data(connection)


async def _seed_analytical_data(connection: Any) -> None:
    await connection.execute(
        text(
            """
            INSERT INTO test_vendedor_cad_lm (tenant_id, codi_ved, nome_ved) VALUES
                (:tenant_a, '1', 'Vendedor Alfa'),
                (:tenant_a, '2', 'Vendedor Beta'),
                (:tenant_b, '1', 'Vendedor Alfa')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    await connection.execute(
        text(
            """
            INSERT INTO test_clientes_cad_lm (tenant_id, codigo, nome) VALUES
                (:tenant_a, '10', 'Cliente Norte'),
                (:tenant_a, '20', 'Cliente Sul'),
                (:tenant_b, '10', 'Cliente Norte')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    await connection.execute(
        text(
            """
            INSERT INTO test_produtos_cad_lm
                (tenant_id, codigo, nome_produto, categoria, estoque) VALUES
                (:tenant_a, '100', 'Produto Compartilhado', 'Categoria A', 50),
                (:tenant_a, '200', 'Produto Exclusivo A', 'Categoria B', 25),
                (:tenant_b, '100', 'Produto Compartilhado', 'Categoria X', 500)
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    await connection.execute(
        text(
            """
            INSERT INTO test_financeiro_lm
                (tenant_id, financeiro_id, status_pagamento, valor_parcela,
                 data_vencimento, cliente_id) VALUES
                (:tenant_a, 'FA-1', 'EM_ABERTO', 125.00, '2026-07-15', '10'),
                (:tenant_b, 'FB-1', 'EM_ABERTO', 975.00, '2026-07-20', '10')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    sales_rows = [
        # Tenant A - June 2026.
        (TENANT_A, "2026-06-05", "1", "A-JUN-1", "10", "1", 2, "VENDA", 100, 2, 60, "100", "Produto Compartilhado", 20),
        (TENANT_A, "2026-06-10", "2", "A-JUN-2", "20", "2", 61, "VENDA", 200, 2, 110, "200", "Produto Exclusivo A", 20),
        (TENANT_A, "2026-06-12", "1", "A-JUN-RB", "10", "1", 9, "SAIDA RB", 30, 1, 30, "100", "Produto Compartilhado", 0),
        (TENANT_A, "2026-06-15", "1", "A-JUN-DEV", "10", "1", 8, "DEVOLUCAO", -20, -1, 20, "100", "Produto Compartilhado", 0),
        (TENANT_A, "2026-06-18", "2", "A-JUN-BON", "20", "2", 22, "BONIFICACAO", 40, 1, 40, "200", "Produto Exclusivo A", 0),
        (TENANT_A, "2026-06-20", "1", "A-JUN-TR", "10", "1", 3, "TRANSFERENCIA", 500, 5, 100, "100", "Produto Compartilhado", 0),
        # Tenant A - July 2026.
        (TENANT_A, "2026-07-05", "1", "A-JUL-1", "10", "1", 2, "VENDA", 150, 1, 160, "100", "Produto Compartilhado", 10),
        (TENANT_A, "2026-07-10", "2", "A-JUL-2", "20", "2", 61, "VENDA", 250, 2, 135, "200", "Produto Exclusivo A", 20),
        (TENANT_A, "2026-07-12", "2", "A-JUL-RB", "20", "2", 9, "SAIDA RB", 50, 1, 50, "200", "Produto Exclusivo A", 0),
        (TENANT_A, "2026-07-15", "1", "A-JUL-DEV", "10", "1", 8, "DEVOLUCAO", -10, -1, 10, "100", "Produto Compartilhado", 0),
        (TENANT_A, "2026-07-20", "1", "A-JUL-TR", "10", "1", 31, "TRANSFERENCIA", 600, 6, 100, "100", "Produto Compartilhado", 0),
        # Another year to verify date isolation.
        (TENANT_A, "2025-06-05", "1", "A-2025-1", "10", "1", 2, "VENDA", 75, 1, 75, "100", "Produto Compartilhado", 0),
        # Tenant B deliberately reuses names with different values.
        (TENANT_B, "2026-06-05", "1", "B-JUN-1", "10", "1", 2, "VENDA", 900, 3, 310, "100", "Produto Compartilhado", 30),
        (TENANT_B, "2026-07-05", "1", "B-JUL-1", "10", "1", 2, "VENDA", 1200, 4, 310, "100", "Produto Compartilhado", 40),
    ]
    await connection.execute(
        text(
            """
            INSERT INTO test_vendas_lm (
                tenant_id, dtemissao_, filial_, pedido_, nota_, serie_,
                codcliente_, rca_, cfop_, tp_, tpdescricao_, ptotal_, qtde_,
                p_unit_, codprod_, descricao_, desconto_total
            ) VALUES (
                :tenant_id, :dtemissao, :filial, :pedido, :pedido, '1',
                :cliente, :vendedor, '5102', :tipo, :descricao_tipo, :valor,
                :quantidade, :preco_unitario, :produto, :descricao_produto,
                :desconto
            )
            """
        ),
        [
            {
                "tenant_id": row[0],
                "dtemissao": date.fromisoformat(row[1]),
                "filial": row[2],
                "pedido": row[3],
                "cliente": row[4],
                "vendedor": row[5],
                "tipo": row[6],
                "descricao_tipo": row[7],
                "valor": row[8],
                "quantidade": row[9],
                "preco_unitario": row[10],
                "produto": row[11],
                "descricao_produto": row[12],
                "desconto": row[13],
            }
            for row in sales_rows
        ],
    )


def load_expected_baseline() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "tests" / "golden" / "baseline_expected.json"
    return json.loads(path.read_text(encoding="utf-8"))
