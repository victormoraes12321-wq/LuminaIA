"""
LuminaAI — Live Dashboard Runtime
----------------------------------
Camada de execução dinâmica que gerencia o ciclo de vida dos painéis
de forma reativa. Separa de forma definitiva Blueprint, Template,
Runtime Dataset, Dashboard Instance e Renderização, aplicando
Change Detection e Diff Rendering.
"""
from __future__ import annotations

import logging
import uuid
import time
import json
import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tenant import Tenant
from models.analytical_package import AnalyticalPackage, PackageStatus
from models.package_dashboard_instance import PackageDashboardInstance
from models.view_catalog import ChartType
from services.query_planner import QueryPlan
from services.data_platform.dataset_builder import dataset_builder
from services.data_platform.analytics_engine import analytics_engine
from services.data_platform.dashboard_payload_builder import dashboard_payload_builder
from services.data_platform.event_engine import event_engine

logger = logging.getLogger("luminaai.data_platform.live_dashboard_runtime")


class LiveDashboardRuntime:
    """
    Garante o Smart Refresh do Runtime Dataset mantendo a estrutura lógica (Blueprint, Template).
    Implementa caches por componente, Change Detection (Diff) e monitoramento de performance.
    """

    def __init__(self):
        # Cache em memória por componente: {component_key: {"hash": str, "data": Any, "timestamp": datetime}}
        self._component_cache: Dict[str, Dict[str, Any]] = {}
        # Histórico de telemetria de atualizações para observabilidade
        self._telemetry_history: List[Dict[str, Any]] = []

    def _get_component_cache_key(self, tenant_id: uuid.UUID, package_id: uuid.UUID, widget_type: str, widget_title: str) -> str:
        """Gera uma chave única de cache por componente isolada por Tenant."""
        title_slug = "".join(c for c in widget_title if c.isalnum()).lower()
        return f"{tenant_id}:{package_id}:{widget_type.lower()}:{title_slug}"

    def get_cached_component(self, tenant_id: uuid.UUID, package_id: uuid.UUID, widget_type: str, widget_title: str) -> Any | None:
        """Recupera o estado de cache individual do componente."""
        key = self._get_component_cache_key(tenant_id, package_id, widget_type, widget_title)
        cache_entry = self._component_cache.get(key)
        if cache_entry:
            # TTL de 15 minutos para cache de componente
            if (datetime.now(timezone.utc) - cache_entry["timestamp"]).total_seconds() < 900:
                logger.debug("[LiveDashboardRuntime] Cache HIT para componente: %s", key)
                return cache_entry["data"]
            else:
                del self._component_cache[key]
        return None

    def set_component_cache(self, tenant_id: uuid.UUID, package_id: uuid.UUID, widget_type: str, widget_title: str, data: Any) -> None:
        """Salva no cache individual o estado do componente."""
        key = self._get_component_cache_key(tenant_id, package_id, widget_type, widget_title)
        self._component_cache[key] = {
            "data": copy.deepcopy(data),
            "timestamp": datetime.now(timezone.utc)
        }
        logger.debug("[LiveDashboardRuntime] Cache set para componente: %s", key)

    def clear_package_caches(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> None:
        """Limpa todos os caches de componentes associados a um pacote analítico."""
        prefix = f"{tenant_id}:{package_id}:"
        to_delete = [k for k in self._component_cache if k.startswith(prefix)]
        for k in to_delete:
            del self._component_cache[k]
        logger.info("[LiveDashboardRuntime] Limpos %d caches de componentes do pacote %s", len(to_delete), package_id)

    def detect_changes(self, prev_widgets: List[Dict[str, Any]], new_widgets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Algoritmo de Change Detection (Diff Rendering).
        Compara a lista de widgets anteriores com os novos e retorna uma tupla:
        (componentes_atualizados, componentes_reutilizados).
        """
        updated = []
        reused = []

        # Indexa os widgets anteriores pelo par chave (type, title) para matching rápido
        prev_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for w in prev_widgets:
            prev_map[(w.get("type", ""), w.get("title", ""))] = w

        for new_w in new_widgets:
            key = (new_w.get("type", ""), new_w.get("title", ""))
            prev_w = prev_map.get(key)

            if not prev_w:
                # Componente novo no layout
                updated.append(new_w)
            else:
                # Compara dados mutáveis do componente (valores, dados do gráfico, rows de tabela)
                is_changed = False
                w_type = new_w.get("type")

                if w_type == "KPI_CARD":
                    # Compara valor numérico e variação
                    is_changed = (
                        prev_w.get("value") != new_w.get("value") or
                        prev_w.get("diff_value") != new_w.get("diff_value") or
                        prev_w.get("direction") != new_w.get("direction")
                    )
                elif w_type == "TABLE":
                    # Compara total de linhas e rows
                    is_changed = (
                        prev_w.get("total_rows") != new_w.get("total_rows") or
                        prev_w.get("rows") != new_w.get("rows")
                    )
                else:
                    # Gráficos (BAR, LINE, PIE, etc.) — compara dados em formato de lista
                    is_changed = prev_w.get("data") != new_w.get("data")

                if is_changed:
                    updated.append(new_w)
                else:
                    reused.append(new_w)

        return updated, reused

    async def refresh_runtime(
        self,
        tenant_id: uuid.UUID,
        package_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Smart Refresh: Atualiza apenas o Runtime Dataset e reconstrói a Dashboard Instance.
        Reutiliza Blueprint, Template e as views associadas sem reprocessar IA (NLU/Planner).
        Garante isolamento Multi-Tenant e registra telemetria.
        """
        start_time = time.perf_counter()
        logger.info("[LiveDashboardRuntime] Iniciando Smart Refresh para package=%s", package_id)

        # 1. Carrega o pacote analítico ativamente e isolado por Tenant
        stmt_pkg = select(AnalyticalPackage).where(
            AnalyticalPackage.id == package_id,
            AnalyticalPackage.tenant_id == tenant_id
        )
        res_pkg = await db.execute(stmt_pkg)
        package = res_pkg.scalar_one_or_none()

        if not package:
            logger.error("[LiveDashboardRuntime] AnalyticalPackage %s não encontrado para tenant=%s", package_id, tenant_id)
            raise ValueError("Pacote Analítico não encontrado ou acesso não autorizado.")

        if package.status == PackageStatus.DEPRECATED:
            logger.warning("[LiveDashboardRuntime] Smart Refresh rodando sobre pacote DEPRECATED %s", package_id)

        # 2. Carrega dados do Tenant
        stmt_t = select(Tenant).where(Tenant.id == tenant_id)
        res_t = await db.execute(stmt_t)
        tenant = res_t.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant não cadastrado.")

        # Recompõe o QueryPlan original a partir do snapshot do Blueprint
        try:
            blueprint_snap = package.blueprint_snapshot
            # Trata conversão manual do schema de snapshot para o objeto QueryPlan
            query_plan = QueryPlan(**blueprint_snap)
        except Exception as err:
            logger.exception("[LiveDashboardRuntime] Erro ao deserializar blueprint_snapshot: %s", err)
            raise RuntimeError(f"Falha na integridade estrutural do Blueprint: {err}")

        # 3. Executa consultas de Runtime Dataset de forma direta (Execution Engine)
        from services.data_platform import execution_engine
        query_results = await execution_engine.execute_blueprint(tenant, query_plan, db)

        # 4. Reconstrói o Runtime Dataset
        builder_datasets = {}
        for q_id, res_item in query_results.items():
            builder_datasets[q_id] = dataset_builder.build_dataset(
                tenant_id=tenant_id,
                raw_rows=res_item["raw_rows"],
                view_name=res_item["view_name"]
            )

        # 5. Processa cálculos e estatísticas determinísticas no Analytics Engine
        analytics_results = await analytics_engine.process_analytics(
            tenant_id=tenant_id,
            datasets=builder_datasets,
            blueprint=query_plan
        )

        # 6. Cria nova Dashboard Instance aplicando a estratégia de visualização
        class MockIntention:
            def __init__(self, chart_type: str | None):
                self.chart_type_sobrescrever = chart_type
                self.chart_types_solicitados = None

        mock_intent = MockIntention(package.visual_strategy.get("primary_chart_type"))
        new_payload = dashboard_payload_builder.build_payload(
            tenant_id=tenant_id,
            datasets=builder_datasets,
            primary_intention=mock_intent,
            analytics_results=analytics_results
        )

        # 7. Change Detection (Diff Rendering) contra a última instância salva
        prev_widgets = []
        stmt_prev = select(PackageDashboardInstance).where(
            PackageDashboardInstance.package_id == package_id,
            PackageDashboardInstance.tenant_id == tenant_id
        ).order_by(PackageDashboardInstance.criado_em.desc()).limit(1)
        res_prev = await db.execute(stmt_prev)
        prev_instance = res_prev.scalar_one_or_none()

        if prev_instance:
            prev_widgets = prev_instance.dashboard_payload.get("widgets", [])

        # Compara componentes novos e anteriores
        new_widgets = new_payload.get("widgets", [])
        updated_widgets, reused_widgets = self.detect_changes(prev_widgets, new_widgets)

        # Atualiza caches dos componentes alterados
        for w in updated_widgets:
            self.set_component_cache(tenant_id, package_id, w["type"], w["title"], w)
        # Tenta hidratação de cache para reutilizados se faltar memória local
        for w in reused_widgets:
            cached = self.get_cached_component(tenant_id, package_id, w["type"], w["title"])
            if not cached:
                self.set_component_cache(tenant_id, package_id, w["type"], w["title"], w)

        # 8. Persiste a nova Dashboard Instance no banco de dados
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Estima tempo que seria gasto re-analisando por IA (NLU + Planner + Validator) - mínimo 1800ms
        tempo_economizado_ms = max(0, 1800 - elapsed_ms)

        bi_snap = prev_instance.bi_intelligence_snapshot if prev_instance else {}

        new_instance = PackageDashboardInstance(
            id=uuid.uuid4(),
            package_id=package_id,
            tenant_id=tenant_id,
            dashboard_payload=new_payload,
            datasets_snapshot=builder_datasets,
            analytics_snapshot=analytics_results,
            bi_intelligence_snapshot=bi_snap,
            query_params=package.analytical_structure.get("filters", {}),
            intent_fingerprint_used=package.intent_fingerprint,
            pergunta_original=f"Live Runtime Refresh (Scheduler)",
            execution_time_ms=elapsed_ms,
            was_package_reuse=True,
            compatibility_score=1.0,
            data_freshness_at=datetime.now(timezone.utc)
        )
        db.add(new_instance)

        # Incrementa contador de reuso do pacote
        package.usage_count += 1
        package.last_used_at = datetime.now(timezone.utc)
        package.avg_execution_time_ms = (
            (package.avg_execution_time_ms * (package.usage_count - 1) + elapsed_ms) / package.usage_count
        )
        db.add(package)
        await db.commit()

        # 9. Registra Métricas de Telemetria e Observabilidade
        telemetry = {
            "update_time_ms": elapsed_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "package_id": str(package_id),
            "tenant_id": str(tenant_id),
            "updated_components": [w["title"] for w in updated_widgets],
            "reused_components": [w["title"] for w in reused_widgets],
            "tempo_economizado_ms": tempo_economizado_ms,
            "renderizacoes_evitadas_count": len(reused_widgets),
            "cache_usage_hits": len(reused_widgets),
            "memory_usage_bytes": len(json.dumps(new_payload).encode("utf-8"))
        }
        self._telemetry_history.append(telemetry)
        if len(self._telemetry_history) > 500:
            self._telemetry_history.pop(0)

        # 10. Despacha atualizações no Event Engine para sincronizar telas abertas
        event_data = {
            "package_id": str(package_id),
            "dashboard_instance_id": str(new_instance.id),
            "updated_widgets": updated_widgets, # Envia apenas a parte modificada (Diff Rendering)
            "reused_widgets_titles": [w["title"] for w in reused_widgets],
            "telemetry": telemetry
        }
        
        # Dispara eventos sucessivos no pub/sub
        await event_engine.publish(tenant_id, "DATASET_UPDATED", {"package_id": str(package_id)})
        await event_engine.publish(tenant_id, "RUNTIME_UPDATED", {"instance_id": str(new_instance.id)})
        await event_engine.publish(tenant_id, "DASHBOARD_UPDATED", event_data)

        logger.info(
            "[LiveDashboardRuntime] Smart Refresh finalizado | total_widgets=%d | atualizados=%d | economizado=%dms",
            len(new_widgets),
            len(updated_widgets),
            tempo_economizado_ms
        )

        return event_data

    def get_telemetry_report(self, tenant_id: uuid.UUID | None = None) -> List[Dict[str, Any]]:
        """Retorna logs de performance de renderização."""
        if tenant_id:
            t_str = str(tenant_id)
            return [t for t in self._telemetry_history if t["tenant_id"] == t_str]
        return list(self._telemetry_history)


# Export singleton
live_dashboard_runtime = LiveDashboardRuntime()
