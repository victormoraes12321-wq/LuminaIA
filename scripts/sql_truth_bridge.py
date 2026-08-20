import sys
import os
import json
import asyncio
from pathlib import Path
import dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

BACKEND_DIR = Path("C:/LuminaAI/backend").resolve()
dotenv.load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from config import settings

async def run_query(sql_query: str):
    base_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    clone_url = f"{base_url}/luminaai_clone"
    engine = create_async_engine(clone_url)
    async with engine.connect() as conn:
        res = await conn.execute(text(sql_query))
        if res.returns_rows:
            rows = [dict(r._mapping) for r in res.fetchall()]
            # Convert non-serializable types
            clean_rows = []
            for row in rows:
                clean_row = {}
                for k, v in row.items():
                    if hasattr(v, "isoformat"):
                        clean_row[k] = v.isoformat()
                    elif isinstance(v, (int, float, str, bool)) or v is None:
                        clean_row[k] = v
                    else:
                        clean_row[k] = str(v)
                clean_rows.append(clean_row)
            print(json.dumps({"success": True, "rows": clean_rows}))
        else:
            print(json.dumps({"success": True, "rows": []}))
    await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = sys.stdin.read().strip()
    if not query:
        print(json.dumps({"success": False, "error": "No query provided"}))
        sys.exit(1)
    asyncio.run(run_query(query))
