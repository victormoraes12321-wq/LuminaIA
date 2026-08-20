import sys
import os
import asyncio
import asyncpg

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import settings
from services.postgresql_clone_service import execute_clone_view

async def test_quarterly_husqvarna():
    base_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    clone_url = base_url.rsplit('/', 1)[0] + '/luminaai_clone'
    conn = await asyncpg.connect(clone_url)

    params = {
        'marca': 'Husqvarna',
        '_group_by': 'trimestre',
        '_metrics': 'unidades_vendidas,receita_total',
        '_order_metric': 'trimestre',
        '_order_direction': 'ASC'
    }

    print("\n--- Testing Quarterly Aggregation for Husqvarna in Clone ---")
    rows = await execute_clone_view(conn, 'VW_VENDAS_LM', params)
    print(f"Returned {len(rows)} quarters:")
    for r in rows:
        print(" ", r)

    await conn.close()

if __name__ == '__main__':
    asyncio.run(test_quarterly_husqvarna())
