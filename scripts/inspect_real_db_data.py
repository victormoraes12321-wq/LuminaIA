import sys, os, json, asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def inspect():
    clone_url = "postgresql+asyncpg://lumina_preprod_user:H0llyw00d26@127.0.0.1:5432/luminaai_clone"
    engine = create_async_engine(clone_url)
    async with engine.connect() as conn:
        print("=== DATES IN vw_vendas_lm ===")
        sales = (await conn.execute(text("SELECT MIN(dtemissao_), MAX(dtemissao_), COUNT(*), SUM(ptotal_) FROM vw_vendas_lm;"))).fetchone()
        print(f"Min Date: {sales[0]}, Max Date: {sales[1]}, Count: {sales[2]}, Total Revenue: {sales[3]}")

        print("\n=== MONTHLY EVOLUTION ===")
        months = (await conn.execute(text("""
            SELECT TO_CHAR(dtemissao_, 'YYYY-MM') as ym, COUNT(*), SUM(ptotal_) as total, SUM(qtde_) as qt
            FROM vw_vendas_lm
            GROUP BY ym
            ORDER BY ym;
        """))).fetchall()
        for m in months:
            print(f"Month: {m[0]} | Rows: {m[1]} | Revenue: R$ {float(m[2]):,.2f} | Quantity: {float(m[3]):,.0f}")

        print("\n=== REAL BRANCHES ===")
        branches = (await conn.execute(text("""
            SELECT filial_, COUNT(*) as tx_count, SUM(ptotal_) as revenue, SUM(qtde_) as qt, COUNT(DISTINCT rca_) as sellers, COUNT(DISTINCT codcliente_) as clients
            FROM vw_vendas_lm
            GROUP BY filial_
            ORDER BY revenue DESC;
        """))).fetchall()
        for b in branches:
            print(f"Filial: '{b[0]}' | Revenue: R$ {float(b[2]):,.2f} | Rows: {b[1]} | Qtd: {float(b[3]):,.0f} | Sellers: {b[4]} | Clients: {b[5]}")

        print("\n=== REAL TOP 10 SELLERS (Overall) ===")
        sellers = (await conn.execute(text("""
            SELECT rca_, nome_, filial_, SUM(ptotal_) as revenue, COUNT(DISTINCT nota_) as invoices, SUM(qtde_) as items_sold
            FROM vw_vendas_lm
            GROUP BY rca_, nome_, filial_
            ORDER BY revenue DESC
            LIMIT 10;
        """))).fetchall()
        for s in sellers:
            print(f"RCA: {s[0]} | Name: '{s[1]}' | Filial: {s[2]} | Revenue: R$ {float(s[3]):,.2f} | Invoices: {s[4]} | Qtd: {float(s[5]):,.0f}")

        print("\n=== REAL TOP 10 PRODUCTS ===")
        prods = (await conn.execute(text("""
            SELECT codprod_, descricao_, SUM(ptotal_) as revenue, SUM(qtde_) as quantity, COUNT(*) as tx_count
            FROM vw_vendas_lm
            GROUP BY codprod_, descricao_
            ORDER BY revenue DESC
            LIMIT 10;
        """))).fetchall()
        for p in prods:
            print(f"Code: {p[0]} | Desc: '{p[1]}' | Revenue: R$ {float(p[2]):,.2f} | Qtd: {float(p[3]):,.0f} | Rows: {p[4]}")

        print("\n=== REAL TOP 10 CLIENTS ===")
        clients = (await conn.execute(text("""
            SELECT codcliente_, razao_, SUM(ptotal_) as revenue, COUNT(DISTINCT nota_) as invoices, SUM(qtde_) as items
            FROM vw_vendas_lm
            GROUP BY codcliente_, razao_
            ORDER BY revenue DESC
            LIMIT 10;
        """))).fetchall()
        for c in clients:
            print(f"CodCli: {c[0]} | Name: '{c[1]}' | Revenue: R$ {float(c[2]):,.2f} | Invoices: {c[3]} | Items: {float(c[4]):,.0f}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(inspect())
