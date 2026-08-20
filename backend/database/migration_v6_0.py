import sys
import os
sys.path.append(os.getcwd())

import asyncio
from database import engine, Base
import models  # Importa para registrar os modelos na metadata do Base

async def main():
    print("Iniciando migração de banco de dados para a v6.0 (Business Knowledge Engine)...")
    async with engine.begin() as conn:
        # Cria as tabelas registradas no metadata (incluindo business_concepts, business_kpis, etc.)
        await conn.run_sync(Base.metadata.create_all)
    print("Migração v6.0 concluída com sucesso!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
