"""
LuminaAI — Analytical Package Service
----------------------------------------
Serviço central de lifecycle dos Analytical Packages.

Responsabilidades:
- Criar novos Packages a partir de resultados do pipeline QIE
- Reutilizar Packages existentes com novos parâmetros
- Persistir PackageDashboardInstances (snapshots de execução)
- Atualizar métricas de uso (usage_count, last_used_at, avg_execution_time)
- Calcular e atualizar quality_score e health_score
- Construir QueryResponse a partir de um Package (reuso HIT)

PRINCÍPIO: A primeira consulta cria conhecimento. As seguintes atualizam os dados.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import select, and_, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytical_package import AnalyticalPackage, PackageStatus
from models.package_dashboard_instance import PackageDashboardInstance
from services.data_platform.intent_fingerprint import intent_fingerprint_generator
from services.data_platform.package_cache import package_cache

if TYPE_CHECKING:
    pass

logger = logging.getLogger("luminaai.data_platform.analytical_package_service")


class AnalyticalPackageService:
    """
    Orquestra o ciclo de vida completo dos Analytical Packages.
    """

    # ── Criação ───────────────────────────────────────────────────────────────

    async def create_package(
        self,
        tenant_id: uuid.UUID,
        fingerprint: dict[str, Any],
        intention: Any,
        plan: Any,
        pipeline_result: dict[str, Any],
        db: AsyncSession,
    ) -> AnalyticalPackage:
        """
        Cria um novo Analytical Package a partir do resultado completo do pipeline.

        Chamado após um MISS no Package Layer (primeira execução de uma análise).

        Parâmetros:
            tenant_id        — ID do tenant
            fingerprint      — Fingerprint semântico gerado pelo IntentFingerprintGenerator
            intention        — IntentionResponse do pipeline
            plan             — QueryPlan gerado pelo Planner
            pipeline_result  — Dict com: dashboard_payload, datasets, analytics_results,
                               bi_intelligence, execution_time_ms, blueprint_snapshot,
                               visual_strategy, query_params
            db               — Sessão de banco de dados
        """
        structured = getattr(intention, "plano_estruturado", None)

        # Monta semantic_context
        semantic_context = self._build_semantic_context(intention, plan, fingerprint)

        # Monta visual_strategy
        visual_strategy = pipeline_result.get("visual_strategy") or self._build_visual_strategy(intention, plan)

        # Monta interaction_strategy
        interaction_strategy = self._build_interaction_strategy(intention, plan)

        # Monta analytical_structure
        analytical_structure = self._build_analytical_structure(intention, structured, plan)

        # Extrai view_names das dependências
        view_names = self._extract_view_names(plan, pipeline_result)

        # Monta dependencies
        dependencies = {
            "view_names": view_names,
            "blueprint_id": pipeline_result.get("blueprint_id"),
            "catalog_ids": pipeline_result.get("catalog_ids", []),
        }

        # Blueprint snapshot
        blueprint_snapshot = pipeline_result.get("blueprint_snapshot") or {}

        package = AnalyticalPackage(
            tenant_id=tenant_id,
            intent_fingerprint=fingerprint,
            intent_key=fingerprint.get("intent_key", ""),
            semantic_context=semantic_context,
            visual_strategy=visual_strategy,
            interaction_strategy=interaction_strategy,
            analytical_structure=analytical_structure,
            blueprint_id=pipeline_result.get("blueprint_id"),
            blueprint_snapshot=blueprint_snapshot,
            view_names=view_names,
            status=PackageStatus.ACTIVE,
            version=1,
            quality_score=1.0,
            health_score=1.0,
            usage_count=0,
            dependencies=dependencies,
            compatible_fingerprints=[fingerprint.get("intent_key", "")],
            created_by="AI_PIPELINE",
        )

        db.add(package)
        await db.flush()  # Obtém o ID sem commitar

        # Cria a primeira PackageDashboardInstance (criação)
        instance = await self._create_instance(
            package=package,
            tenant_id=tenant_id,
            fingerprint=fingerprint,
            pipeline_result=pipeline_result,
            was_reuse=False,
            compatibility_score=1.0,
            db=db,
        )

        logger.info(
            "[AnalyticalPackageService] Package CRIADO | id=%s domain=%s operation=%s entity=%s",
            package.id, fingerprint.get("domain"), fingerprint.get("operation"), fingerprint.get("entity"),
        )

        return package

    # ── Reuso ─────────────────────────────────────────────────────────────────

    async def reuse_package(
        self,
        package: AnalyticalPackage,
        tenant_id: uuid.UUID,
        fingerprint: dict[str, Any],
        pipeline_result: dict[str, Any],
        compatibility_score: float,
        db: AsyncSession,
    ) -> PackageDashboardInstance:
        """
        Reutiliza um Package existente: cria nova instância e atualiza métricas.

        Chamado após um HIT no Package Layer (análise compatível encontrada).

        Parâmetros:
            package            — Package ACTIVE a ser reutilizado
            tenant_id          — ID do tenant
            fingerprint        — Fingerprint da nova consulta
            pipeline_result    — Resultado do pipeline com dados frescos
                                 (apenas Execution + Analytics — sem NLU/Planner)
            compatibility_score — Score de compatibilidade que levou ao HIT
            db                 — Sessão de banco de dados
        """
        # Cria nova instância com os dados frescos
        instance = await self._create_instance(
            package=package,
            tenant_id=tenant_id,
            fingerprint=fingerprint,
            pipeline_result=pipeline_result,
            was_reuse=True,
            compatibility_score=compatibility_score,
            db=db,
        )

        # Atualiza métricas de uso do Package
        now = datetime.now(timezone.utc)
        execution_time = pipeline_result.get("execution_time_ms", 0)

        package.usage_count = (package.usage_count or 0) + 1
        package.last_used_at = now

        # Atualiza média de tempo de execução (média móvel exponencial simples)
        if package.avg_execution_time_ms > 0:
            package.avg_execution_time_ms = (
                0.8 * package.avg_execution_time_ms + 0.2 * execution_time
            )
        else:
            package.avg_execution_time_ms = float(execution_time)

        db.add(package)

        # Invalida cache L1 para forçar reload com métricas atualizadas
        package_cache.l1_invalidate(tenant_id, package.intent_key)

        logger.info(
            "[AnalyticalPackageService] Package REUTILIZADO | id=%s usage=%d score=%.3f",
            package.id, package.usage_count, compatibility_score,
        )

        return instance

    # ── Scores ────────────────────────────────────────────────────────────────

    async def update_quality_score(
        self,
        package: AnalyticalPackage,
        db: AsyncSession,
        days_since_last_refresh: int = 0,
    ) -> float:
        """Recalcula e persiste o quality_score do Package."""
        # Conta reusos recentes (proxy: usage_count total como base simplificada)
        recent_usage = min(package.usage_count, 100)
        total_usage = package.usage_count

        # Taxa de erro: erros / (uso total + erros)
        total_executions = max(1, total_usage + (package.error_count or 0))
        error_rate = (package.error_count or 0) / total_executions

        new_score = package.compute_quality_score(
            recent_usage=recent_usage,
            total_usage=total_usage,
            error_rate=error_rate,
            freshness_days=days_since_last_refresh,
        )

        package.quality_score = new_score
        db.add(package)

        return new_score

    async def update_health_score(
        self,
        package: AnalyticalPackage,
        db: AsyncSession,
        schema_valid: bool = True,
        views_available: bool = True,
        no_breaking_changes: bool = True,
    ) -> float:
        """Recalcula e persiste o health_score do Package."""
        new_score = package.compute_health_score(
            schema_valid=schema_valid,
            views_available=views_available,
            no_breaking_changes=no_breaking_changes,
            avg_time_ms=package.avg_execution_time_ms,
        )

        package.health_score = new_score
        db.add(package)

        # Se health score crítico (<0.3), depreca automaticamente
        if new_score < 0.3:
            package.status = PackageStatus.DEPRECATED
            package.deprecation_reason = f"Health score crítico: {new_score:.2f}"
            logger.warning(
                "[AnalyticalPackageService] Package AUTO-DEPRECADO por health score crítico | id=%s score=%.2f",
                package.id, new_score,
            )

        return new_score

    async def register_error(
        self,
        package: AnalyticalPackage,
        db: AsyncSession,
    ) -> None:
        """Registra um erro de execução no Package e atualiza scores."""
        package.error_count = (package.error_count or 0) + 1
        db.add(package)

    # ── Consultas ─────────────────────────────────────────────────────────────

    async def get_package_by_id(
        self,
        package_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> AnalyticalPackage | None:
        """Busca um Package específico por ID com isolamento de tenant."""
        stmt = select(AnalyticalPackage).where(
            and_(
                AnalyticalPackage.id == package_id,
                AnalyticalPackage.tenant_id == tenant_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_packages(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        status: PackageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalyticalPackage]:
        """Lista Packages do tenant com filtro opcional por status."""
        conditions = [AnalyticalPackage.tenant_id == tenant_id]
        if status:
            conditions.append(AnalyticalPackage.status == status)

        stmt = (
            select(AnalyticalPackage)
            .where(and_(*conditions))
            .order_by(AnalyticalPackage.usage_count.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_instances(
        self,
        package_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[PackageDashboardInstance]:
        """Lista as instâncias de um Package (histórico de execuções)."""
        stmt = (
            select(PackageDashboardInstance)
            .where(
                and_(
                    PackageDashboardInstance.package_id == package_id,
                    PackageDashboardInstance.tenant_id == tenant_id,
                )
            )
            .order_by(PackageDashboardInstance.criado_em.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_global_stats(
        self,
        tenant_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Retorna métricas globais de reuso de Packages do tenant."""
        # Total de Packages por status
        stmt_count = select(
            AnalyticalPackage.status,
            sql_func.count(AnalyticalPackage.id).label("count"),
        ).where(
            AnalyticalPackage.tenant_id == tenant_id
        ).group_by(AnalyticalPackage.status)

        result = await db.execute(stmt_count)
        counts_by_status = {row.status.value: row.count for row in result.all()}

        # Total de instâncias (reusos)
        stmt_instances = select(
            sql_func.count(PackageDashboardInstance.id)
        ).join(
            AnalyticalPackage,
            PackageDashboardInstance.package_id == AnalyticalPackage.id
        ).where(
            AnalyticalPackage.tenant_id == tenant_id
        )
        total_instances_result = await db.execute(stmt_instances)
        total_instances = total_instances_result.scalar() or 0

        # Reusos (instâncias com was_package_reuse=True)
        stmt_reuses = select(
            sql_func.count(PackageDashboardInstance.id)
        ).join(
            AnalyticalPackage,
            PackageDashboardInstance.package_id == AnalyticalPackage.id
        ).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                PackageDashboardInstance.was_package_reuse == True,
            )
        )
        total_reuses_result = await db.execute(stmt_reuses)
        total_reuses = total_reuses_result.scalar() or 0

        reuse_rate = round(total_reuses / total_instances, 4) if total_instances > 0 else 0.0

        # Scores médios
        stmt_scores = select(
            sql_func.avg(AnalyticalPackage.quality_score).label("avg_quality"),
            sql_func.avg(AnalyticalPackage.health_score).label("avg_health"),
        ).where(
            and_(
                AnalyticalPackage.tenant_id == tenant_id,
                AnalyticalPackage.status == PackageStatus.ACTIVE,
            )
        )
        scores_result = await db.execute(stmt_scores)
        scores_row = scores_result.one_or_none()

        return {
            "packages_by_status": counts_by_status,
            "total_packages": sum(counts_by_status.values()),
            "total_executions": total_instances,
            "total_reuses": total_reuses,
            "reuse_rate": reuse_rate,
            "avg_quality_score": round(float(scores_row.avg_quality or 0.0), 4) if scores_row else 0.0,
            "avg_health_score": round(float(scores_row.avg_health or 0.0), 4) if scores_row else 0.0,
            "cache_stats": package_cache.get_stats(),
        }

    # ── Serialização para QueryResponse ──────────────────────────────────────

    def serialize_package(self, package: AnalyticalPackage) -> dict[str, Any]:
        """Serializa um Package para resposta da API."""
        return {
            "id": str(package.id),
            "status": package.status.value,
            "version": package.version,
            "intent_fingerprint": package.intent_fingerprint,
            "semantic_context": package.semantic_context,
            "visual_strategy": package.visual_strategy,
            "analytical_structure": package.analytical_structure,
            "blueprint_id": package.blueprint_id,
            "view_names": package.view_names,
            "quality_score": package.quality_score,
            "health_score": package.health_score,
            "usage_count": package.usage_count,
            "last_used_at": package.last_used_at.isoformat() if package.last_used_at else None,
            "avg_execution_time_ms": package.avg_execution_time_ms,
            "dependencies": package.dependencies,
            "created_by": package.created_by,
            "criado_em": package.criado_em.isoformat() if package.criado_em else None,
            "atualizado_em": package.atualizado_em.isoformat() if package.atualizado_em else None,
        }

    # ── Helpers Privados ──────────────────────────────────────────────────────

    async def _create_instance(
        self,
        package: AnalyticalPackage,
        tenant_id: uuid.UUID,
        fingerprint: dict[str, Any],
        pipeline_result: dict[str, Any],
        was_reuse: bool,
        compatibility_score: float,
        db: AsyncSession,
    ) -> PackageDashboardInstance:
        """Cria e persiste uma PackageDashboardInstance."""
        instance = PackageDashboardInstance(
            package_id=package.id,
            tenant_id=tenant_id,
            dashboard_payload=pipeline_result.get("dashboard_payload") or {},
            datasets_snapshot=pipeline_result.get("datasets") or {},
            analytics_snapshot=pipeline_result.get("analytics_results") or {},
            bi_intelligence_snapshot=pipeline_result.get("bi_intelligence") or {},
            query_params=pipeline_result.get("query_params") or {},
            intent_fingerprint_used=fingerprint,
            pergunta_original=pipeline_result.get("pergunta_original"),
            execution_time_ms=pipeline_result.get("execution_time_ms", 0),
            was_package_reuse=was_reuse,
            compatibility_score=compatibility_score,
            data_freshness_at=datetime.now(timezone.utc),
        )

        db.add(instance)
        return instance

    def _build_semantic_context(
        self,
        intention: Any,
        plan: Any,
        fingerprint: dict[str, Any],
    ) -> dict[str, Any]:
        """Constrói o semantic_context rico a partir da intenção e plano."""
        return {
            "domain": fingerprint.get("domain", "GERAL"),
            "operation": fingerprint.get("operation", "AGGREGATION"),
            "entity": fingerprint.get("entity", "GERAL"),
            "granularity": fingerprint.get("granularity", "GERAL"),
            "analysis_type": fingerprint.get("analysis_type", "AGGREGATION"),
            "ia_confianca": getattr(intention, "confianca", 0.0),
            "ia_justificativa": getattr(intention, "justificativa", ""),
            "operacao_raw": getattr(intention, "operacao", ""),
            "entidade_raw": getattr(intention, "entidade_alvo", ""),
            "is_comparacao": getattr(intention, "is_comparacao", False),
        }

    def _build_visual_strategy(
        self,
        intention: Any,
        plan: Any,
    ) -> dict[str, Any]:
        """Constrói a estratégia visual a partir da intenção."""
        vis_type = getattr(intention, "visualizacao_preferida", "TABLE") or "TABLE"
        structured = getattr(intention, "plano_estruturado", None)
        if structured:
            vis = getattr(structured, "visualization", None)
            if vis:
                vis_type = getattr(vis, "type", vis_type) or vis_type

        return {
            "primary_chart_type": vis_type,
            "layout_order": ["kpi_cards", "chart", "data_table"],
            "show_insights": True,
            "show_trend": True,
            "layout_priority": "ALTA",
        }

    def _build_interaction_strategy(
        self,
        intention: Any,
        plan: Any,
    ) -> dict[str, Any]:
        """Constrói a estratégia de interação."""
        return {
            "filters_available": ["date_range", "produto", "cliente", "regiao"],
            "drill_down_enabled": True,
            "export_enabled": True,
            "refresh_enabled": True,
        }

    def _build_analytical_structure(
        self,
        intention: Any,
        structured: Any | None,
        plan: Any,
    ) -> dict[str, Any]:
        """Constrói a estrutura analítica a partir do plano estruturado."""
        metrics = []
        group_by = []
        filters = {}

        if structured:
            metrics = list(getattr(structured, "metrics", []) or [])
            group_by = list(getattr(structured, "group_by", []) or [])
            plan_filters = getattr(structured, "filters", None)
            if plan_filters:
                filters = {
                    "date_range": getattr(plan_filters, "date_range", ""),
                    "products": getattr(plan_filters, "products", []),
                    "customers": getattr(plan_filters, "customers", []),
                    "regions": getattr(plan_filters, "regions", []),
                }

        return {
            "metrics": metrics,
            "group_by": group_by,
            "filters_template": filters,
            "query_type": getattr(structured, "query_type", "AGGREGATION") if structured else "AGGREGATION",
        }

    def _extract_view_names(self, plan: Any, pipeline_result: dict[str, Any]) -> list[str]:
        """Extrai os nomes de views do plano ou do resultado."""
        view_names = []

        if plan:
            vn = getattr(plan.consulta_principal, "view_name", None)
            if vn:
                view_names.append(vn)

        # Complementa com views do resultado da execução
        datasets = pipeline_result.get("datasets") or {}
        for ds in datasets.values():
            if isinstance(ds, dict):
                vn = ds.get("metadata", {}).get("view_name") or ds.get("view_name")
                if vn and vn not in view_names:
                    view_names.append(vn)

        return view_names


# ── Singleton ─────────────────────────────────────────────────────────────────
analytical_package_service = AnalyticalPackageService()
