import sys
import os
sys.path.append(os.getcwd())

import asyncio
from database import engine, Base
import models  # Importa para registrar os modelos na metadata do Base

async def main():
    print("Iniciando migração de banco de dados para a v5.0 (Data Platform)...")
    async with engine.begin() as conn:
        # Cria as tabelas registradas no metadata (incluindo blueprint_repository e metadata_catalog)
        await conn.run_sync(Base.metadata.create_all)
    print("Migração v5.0 concluída com sucesso!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
