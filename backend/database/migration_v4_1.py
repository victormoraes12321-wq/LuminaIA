import sys
import os
sys.path.append(os.getcwd())

import asyncio
import sqlalchemy
from database import engine

async def main():
    print("Iniciando migração de banco de dados...")
    async with engine.connect() as conn:
        # Adiciona colunas se não existirem
        await conn.execute(sqlalchemy.text(
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS clone_db_conn JSONB NOT NULL DEFAULT '{}';"
        ))
        await conn.execute(sqlalchemy.text(
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sync_config JSONB NOT NULL DEFAULT '{\"enabled\": false, \"times\": []}';"
        ))
        await conn.commit()
    print("Migração concluída com sucesso!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
