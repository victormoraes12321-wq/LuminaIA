import logging
import time
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from services.data_platform.data_access_layer import DataAccessLayer
from models.tenant import Tenant

logger = logging.getLogger("luminaai.data_platform.execution_engine")

def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api
    return catalog_api

def _get_analytics_engines():
    from services.data_platform.query_resolver import query_resolver
    from services.data_platform.analytics_engine import analytics_engine
    from services.data_platform.dataset_builder import dataset_builder
    from services.data_platform.dashboard_payload_builder import dashboard_payload_builder
    return query_resolver, analytics_engine, dataset_builder, dashboard_payload_builder


class ExecutionEngine:
    """
    Execution Engine (Execution Engine).
    Responsável por executar o Blueprint.
    Monta o plano de execução físico, seleciona views e executa consultas
    estritamente de forma SEQUENCIAL usando a Data Access Layer.
    Nunca acessa o ERP.
    """

    def __init__(self, data_access_layer: DataAccessLayer):
        self.data_access_layer = data_access_layer

    async def execute_blueprint(
        self,
        tenant: Tenant,
        query_plan: Any,
        db_session: AsyncSession
    ) -> dict[str, Any]:
        """
        Executa os itens planejados no QueryPlan.
        Processa os itens em sequ?ncia para manter a AsyncSession consistente.
        """
        logger.info("[ExecutionEngine] Iniciando execu??o sequencial do blueprint...")
        resultados = {}
        
        # Mapeia itens planejados
        planejados = {}
        if hasattr(query_plan, "consulta_principal"):
            planejados[query_plan.consulta_principal.id] = query_plan.consulta_principal
        if hasattr(query_plan, "consultas_complementares") and query_plan.consultas_complementares:
            for item in query_plan.consultas_complementares:
                planejados[item.id] = item

        # Resolve a ordem de execu??o. A AsyncSession compartilhada n?o ? segura
        # para flush concorrente, ent?o os itens do plano rodam em sequ?ncia.
        if hasattr(query_plan, "ordem_execucao") and query_plan.ordem_execucao:
            for grupo in query_plan.ordem_execucao:
                for q_id in grupo:
                    item = planejados.get(q_id)
                    if not item or not item.view_name:
                        continue
                    await self._execute_single_item(tenant, item, db_session, query_plan, resultados)
        else:
            # Sequencial de fallback
            for q_id, item in planejados.items():
                if not item or not item.view_name:
                    continue
                await self._execute_single_item(tenant, item, db_session, query_plan, resultados)

        return resultados

    async def _execute_single_item(
        self,
        tenant: Tenant,
        item: Any,
        db_session: AsyncSession,
        query_plan: Any,
        resultados: dict[str, Any]
    ) -> None:
        """Executa de forma isolada um item do plano e grava seus metadados no analítico."""
        logger.info(
            "[ExecutionEngine] Iniciando execução da consulta: %s (view: %s)...",
            item.id,
            item.view_name
        )
        
        try:
            query_start_time = time.perf_counter()
            raw_rows = await self.data_access_layer.read_view_data(
                tenant=tenant,
                view_name=item.view_name,
                parameters=item.parametros,
                db_session=db_session
            )
            query_elapsed_ms = (time.perf_counter() - query_start_time) * 1000
            
            # Sanitiza Decimals e datetimes/dates para formatos serializáveis em JSON
            from decimal import Decimal
            from datetime import datetime, date
            def sanitize_decimals(val):
                if isinstance(val, list):
                    return [sanitize_decimals(x) for x in val]
                if isinstance(val, dict):
                    return {k: sanitize_decimals(v) for k, v in val.items()}
                if isinstance(val, Decimal):
                    return float(val) if val % 1 else int(val)
                if isinstance(val, (datetime, date)):
                    return val.isoformat()
                return val
            
            raw_rows = sanitize_decimals(raw_rows)
            
            # Persiste o dataset estruturado no banco analítico
            try:
                import uuid
                from datetime import datetime, date
                from models.dataset import Dataset
                
                # Detecta e infere tipos das colunas com base no primeiro registro
                col_types = {}
                if raw_rows:
                    first_row = raw_rows[0]
                    for col_name, val in first_row.items():
                        if isinstance(val, int):
                            col_types[col_name] = "integer"
                        elif isinstance(val, float):
                            col_types[col_name] = "float"
                        elif isinstance(val, bool):
                            col_types[col_name] = "boolean"
                        elif isinstance(val, (datetime, date)):
                            col_types[col_name] = "date"
                        else:
                            col_types[col_name] = "string"
                
                # Resolve versionamento: busca a versão atual do dataset para esta origem e tenant
                from sqlalchemy import select, func, and_
                stmt_v = select(func.max(Dataset.version)).where(
                    and_(
                        Dataset.tenant_id == tenant.id,
                        Dataset.origem == item.view_name
                    )
                )
                res_v = await db_session.execute(stmt_v)
                max_v = res_v.scalar() or 0
                dashboard_id = getattr(query_plan, "request_id", None) or uuid.uuid4()
                
                new_dataset = Dataset(
                    tenant_id=tenant.id,
                    dados_estruturados=raw_rows,
                    tipagem_correta=col_types,
                    metadados={
                        "objetivo": item.objetivo,
                        "prioridade": item.prioridade,
                        "sugestao_visualizacao": item.sugestao_visualizacao
                    },
                    version=max_v + 1,
                    origem=item.view_name,
                    blueprint_id=item.id,
                    dashboard_id=dashboard_id,
                    view_catalog_id=item.view_catalog_id
                )
                db_session.add(new_dataset)
                await db_session.flush()

                try:
                    api = _get_catalog_api()
                    dataset_id = str(new_dataset.id)
                    await api.register(
                        tenant_id=tenant.id,
                        tipo="DATASET",
                        dados={
                            "estrutura_id": dataset_id,
                            "nome_view": f"DS_{item.view_name}_{new_dataset.version}",
                            "origem": item.view_name,
                            "owner": "ExecutionEngine",
                            "categoria": "Dataset",
                            "tags": ["dataset", item.view_name.lower()],
                            "tabelas_utilizadas": [item.view_name],
                            "campos_utilizados": list(col_types.keys()),
                            "dependencias": [item.view_name],
                            "blueprint_associado": item.id,
                            "dashboard_associado": str(dashboard_id),
                            "status": "success",
                            "integridade": "valid",
                        },
                        upstream_ids=[item.view_name],
                    )
                    await api.register(
                        tenant_id=tenant.id,
                        tipo="DASHBOARD",
                        dados={
                            "estrutura_id": str(dashboard_id),
                            "nome_view": f"DASHBOARD_{str(dashboard_id)[:8]}",
                            "origem": "QUERY_ENGINE",
                            "owner": "DashboardBuilder",
                            "categoria": "Dashboard",
                            "tags": ["dashboard", "query"],
                            "dependencias": [dataset_id, item.view_name],
                            "blueprint_associado": item.id,
                            "dashboard_associado": str(dashboard_id),
                            "status": "success",
                            "integridade": "valid",
                        },
                        upstream_ids=[dataset_id],
                    )
                except Exception as catalog_exc:
                    logger.debug("[ExecutionEngine] Registro de Dataset/Dashboard no catalogo ignorado: %s", catalog_exc)
                
                # Registra a criação no histórico de auditoria
                from services.data_platform.history_service import history_service
                await history_service.log_change(
                    tenant_id=tenant.id,
                    estrutura_tipo="DATASET",
                    estrutura_id=str(new_dataset.id),
                    acao="CREATE" if max_v == 0 else "VERSION_UP",
                    detalhes={
                        "origem": item.view_name,
                        "version": new_dataset.version,
                        "total_registros": len(raw_rows)
                    }
                )
                logger.info("[ExecutionEngine] Dataset analítico persistido e auditado com sucesso!")
            except Exception as db_dataset_exc:
                logger.error("[ExecutionEngine] Falha ao persistir dataset analítico: %s", db_dataset_exc)

            resultados[item.id] = {
                "id": item.id,
                "view_name": item.view_name,
                "sugestao_visualizacao": item.sugestao_visualizacao,
                "raw_rows": raw_rows,
                "view_catalog_id": item.view_catalog_id
            }
            
            # Registra acesso no CatalogAPI para métricas de uso
            try:
                api = _get_catalog_api()
                await api.register_query(
                    tenant_id=tenant.id,
                    estrutura_id=item.view_name,
                    execution_time_ms=query_elapsed_ms,
                )
            except Exception as acc_exc:
                logger.debug("[ExecutionEngine] register_query ignorado: %s", acc_exc)

            logger.info(
                "[ExecutionEngine] Sucesso na execução de %s | Registros obtidos: %d",
                item.id,
                len(raw_rows)
            )
        except Exception as exc:
            logger.error("[ExecutionEngine] Falha ao executar %s: %s", item.id, exc)
            if getattr(item, "obrigatoria", True):
                raise exc
            else:
                logger.warning("[ExecutionEngine] Falha na consulta complementar opcional %s ignorada.", item.id)

        return resultados


from services.data_platform.analytical_storage import AnalyticalStorage
from services.data_platform.performance_layer import PerformanceLayer

execution_engine = ExecutionEngine(
    DataAccessLayer(AnalyticalStorage(), PerformanceLayer())
)


async def execute_blueprint(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility proxy for legacy package-level imports."""
    return await execution_engine.execute_blueprint(*args, **kwargs)
