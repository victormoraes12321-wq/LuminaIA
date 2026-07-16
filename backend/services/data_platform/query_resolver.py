"""
Query Resolver — LuminaAI Data Platform
---------------------------------------
Responsável por localizar estruturas analíticas (Views, Datasets, Metadados,
KPIs, Filtros) na Data Platform, sem nunca consultar o ERP.
"""
import uuid
import logging
from typing import Any

from sqlalchemy import select
from database import get_db_context
from models.view_catalog import ViewCatalog
from models.dataset import Dataset
from models.metadata_catalog import MetadataCatalog

logger = logging.getLogger("luminaai.data_platform.query_resolver")


class QueryResolver:
    """
    Localizador e resolvedor de metadados e datasets na Data Platform.
    """

    async def resolve_view(self, tenant_id: uuid.UUID, view_name: str) -> dict[str, Any] | None:
        """
        Localiza os metadados de uma view analítica cadastrada no catálogo do tenant.
        """
        clean_name = view_name.upper().strip()
        logger.debug("[QueryResolver] Resolvendo view: %s para tenant %s", clean_name, tenant_id)
        
        async with get_db_context() as session:
            stmt = select(ViewCatalog).where(
                ViewCatalog.tenant_id == tenant_id,
                ViewCatalog.nome_view_oracle == clean_name
            )
            res = await session.execute(stmt)
            view = res.scalar_one_or_none()
            
            if not view:
                return None
                
            return {
                "id": view.id,
                "nome_view_oracle": view.nome_view_oracle,
                "descricao_para_ia": view.descricao_para_ia,
                "tipo_grafico_padrao": view.tipo_grafico_padrao,
                "parametros_schema": view.parametros_schema,
                "ativo": view.ativo,
            }

    async def resolve_dataset(self, tenant_id: uuid.UUID, dataset_id: uuid.UUID | str) -> dict[str, Any] | None:
        """
        Recupera um dataset persistido na Data Platform pelo ID.
        """
        key = uuid.UUID(str(dataset_id))
        logger.debug("[QueryResolver] Resolvendo dataset: %s", key)
        
        async with get_db_context() as session:
            stmt = select(Dataset).where(
                Dataset.tenant_id == tenant_id,
                Dataset.id == key
            )
            res = await session.execute(stmt)
            ds = res.scalar_one_or_none()
            
            if not ds:
                return None
                
            return {
                "id": ds.id,
                "dados_estruturados": ds.dados_estruturados,
                "tipagem_correta": ds.tipagem_correta,
                "version": ds.version,
                "origem": ds.origem,
                "metadados": ds.metadados,
                "criado_em": ds.criado_em,
            }

    async def resolve_kpi_metadata(self, tenant_id: uuid.UUID, kpi_name: str) -> dict[str, Any] | None:
        """
        Consulta os metadados e regras de agregação de um KPI específico cadastrado no catálogo.
        """
        clean_kpi = kpi_name.lower().strip()
        logger.debug("[QueryResolver] Resolvendo KPI: %s", clean_kpi)
        
        async with get_db_context() as session:
            # Varre o catálogo procurando por KPIs suportados
            stmt = select(MetadataCatalog).where(
                MetadataCatalog.tenant_id == tenant_id
            )
            res = await session.execute(stmt)
            catalogs = res.scalars().all()
            
            for cat in catalogs:
                kpis = cat.kpis_suportados or []
                if clean_kpi in [k.lower() for k in kpis]:
                    return {
                        "kpi": clean_kpi,
                        "view_name": cat.nome_view,
                        "campos_utilizados": cat.campos_utilizados,
                        "origem": cat.origem,
                        "categoria": cat.categoria,
                    }
        return None


# Singleton export
query_resolver = QueryResolver()
