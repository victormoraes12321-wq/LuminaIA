import sys
import os
import asyncio
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import get_db_context
from models.user import User
from models.tenant import Tenant
from models.view_catalog import ViewCatalog
from schemas.query import QueryRequest
from schemas.view_catalog import ViewCatalogSummary
from services.ai_service import identify_intention
from services.query_intelligence_engine import query_intelligence_engine
from sqlalchemy import select

async def test_user_query():
    query_text = "QUero a lista de todos os produtos da Husqvarna, por ordem do que mais vendeu para o que menos vendeu, e precisa ter as seguintes informações: quantidade vendida, quantidade comprada"
    print(f"\n=======================================================")
    print(f"TESTING QUERY: {query_text}")
    print(f"=======================================================\n")

    async with get_db_context() as db:
        user_stmt = select(User).where(User.email == 'ti@casadocampo.vet.br')
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        
        tenant_stmt = select(Tenant).where(Tenant.id == user.tenant_id)
        tenant_res = await db.execute(tenant_stmt)
        tenant = tenant_res.scalar_one_or_none()

        views_stmt = select(ViewCatalog).where(ViewCatalog.tenant_id == user.tenant_id, ViewCatalog.ativo.is_(True))
        views_res = await db.execute(views_stmt)
        views = list(views_res.scalars().all())
        catalog_summaries = [ViewCatalogSummary.model_validate(v) for v in views]

        payload = QueryRequest(
            pergunta=query_text,
            tenant_id=user.tenant_id
        )

        class DummyBackgroundTasks:
            def add_task(self, *args, **kwargs):
                pass

        resp = await query_intelligence_engine.process_query(
            payload=payload,
            current_user=user,
            db=db,
            background_tasks=DummyBackgroundTasks(),
            instrucoes_finais="",
            ia_api_key=None,
            ia_model=None,
            ia_temp=None,
            catalog_summaries=catalog_summaries,
            tenant=tenant,
            intent_identifier=identify_intention,
        )

        print("\n--- FULL RESPONSE JSON ---")
        data_dict = resp.model_dump(mode="json")
        print("View name:", data_dict.get("view_name"))
        print("Chart type:", data_dict.get("tipo_grafico_sugerido"))
        print("Parameters:", data_dict.get("parametros_identificados"))
        print("Explicacao IA:", data_dict.get("explicacao_ia"))
        print("Data summary:", len(data_dict.get("dados", {}).get("rows", [])) if "rows" in data_dict.get("dados", {}) else "no rows")
        if "rows" in data_dict.get("dados", {}):
            print("First 3 rows:", data_dict["dados"]["rows"][:3])
            print("Columns:", data_dict["dados"].get("columns"))

if __name__ == '__main__':
    asyncio.run(test_user_query())
