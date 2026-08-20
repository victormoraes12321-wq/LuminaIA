import asyncio
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from database import get_db_context

async def check():
    async with get_db_context() as session:
        # Lista as tabelas no schema public com suas colunas reais
        print("=== TABELAS E COLUNAS NO SCHEMA PUBLIC ===")
        res = await session.execute(text(
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema='public' "
            "ORDER BY table_name, ordinal_position"
        ))
        
        tables = {}
        for r in res.fetchall():
            tables.setdefault(r[0], []).append(f"{r[1]} ({r[2]})")
            
        for name, cols in tables.items():
            if "cad_lm" in name or "vw_vendas_lm" in name:
                print(f"\nTabela: {name}")
                for c in cols:
                    print(f"  {c}")

if __name__ == "__main__":
    asyncio.run(check())
