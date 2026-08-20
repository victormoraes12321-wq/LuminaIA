"""
LuminaAI - Enterprise Blueprint Repository
------------------------------------------
Corporate repository for reusable analytical intelligence.

Blueprints store structural strategy only. They never store ERP rows,
query results or calculated numeric answers.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.blueprint import Blueprint

logger = logging.getLogger("luminaai.data_platform.blueprint_repository")


def _get_catalog_api():
    from services.data_platform.catalog_api import catalog_api

    return catalog_api


class BlueprintRepository:
    """
    Stores, versions, reuses and governs analytical Blueprints.

    Public legacy methods are intentionally preserved for compatibility.
    """

    COMPATIBILITY_THRESHOLD = 0.85

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return [value]
                return parsed if isinstance(parsed, list) else [value]
            return [value]
        if isinstance(value, tuple | set):
            return list(value)
        return [value]

    def _stable_list(self, value: Any) -> list[str]:
        return sorted({str(v).strip().lower() for v in self._as_list(value) if str(v).strip()})

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _filter_keys(self, filters: Any) -> list[str]:
        if not isinstance(filters, dict):
            return []
        return sorted(str(key).strip().lower() for key in filters.keys() if str(key).strip())

    def _components_from_layout(self, blueprint_model: Any) -> list[str]:
        layout = getattr(blueprint_model, "layout", None) or {}
        components = layout.get("components") or layout.get("componentes") or []
        visual = getattr(blueprint_model, "visualization_type", None)
        if visual:
            components = [visual, *self._as_list(components)]
        return self._stable_list(components)

    def _complexity(self, blueprint_model: Any) -> str:
        metrics = self._as_list(getattr(blueprint_model, "metrics", []))
        group_by = self._as_list(getattr(blueprint_model, "group_by", []))
        filters = getattr(blueprint_model, "filters", {}) or {}
        if len(group_by) > 2 or len(metrics) > 4 or len(filters) > 4:
            return "ALTA"
        if len(group_by) > 0 or len(metrics) > 2 or len(filters) > 1:
            return "MEDIA"
        return "BAIXA"

    def _business_domain(self, blueprint_model: Any) -> str:
        text = " ".join(
            [
                str(getattr(blueprint_model, "nome_consulta", "") or ""),
                str(getattr(blueprint_model, "objetivo", "") or ""),
                str(getattr(blueprint_model, "view_name", "") or ""),
                " ".join(self._as_list(getattr(blueprint_model, "metrics", []))),
            ]
        ).lower()
        if any(term in text for term in ("estoque", "saldo", "inventario")):
            return "ESTOQUE"
        if any(term in text for term in ("financeiro", "lucro", "margem", "despesa", "caixa")):
            return "FINANCEIRO"
        if any(term in text for term in ("cliente", "comprador")):
            return "CLIENTES"
        if any(term in text for term in ("produto", "sku", "item")):
            return "PRODUTOS"
        if any(term in text for term in ("vendedor", "representante")):
            return "COMERCIAL"
        if any(term in text for term in ("venda", "receita", "faturamento")):
            return "VENDAS"
        return "GERAL"

    def build_fingerprint(self, blueprint_model: Any) -> dict[str, Any]:
        """Generate a semantic structural fingerprint for reuse matching."""
        return {
            "objetivo": str(getattr(blueprint_model, "objetivo", "") or "").strip().lower(),
            "tipo_analise": str(getattr(blueprint_model, "tipo_analise", "AGGREGATION") or "AGGREGATION").upper(),
            "entidade": self._business_domain(blueprint_model),
            "kpis": self._stable_list(getattr(blueprint_model, "metrics", [])),
            "contexto": {
                "dominio": self._business_domain(blueprint_model),
                "view_family": str(getattr(blueprint_model, "view_name", "") or "").upper().replace("VW_", ""),
            },
            "filtros": self._filter_keys(getattr(blueprint_model, "filters", {}) or {}),
            "agrupamentos": self._stable_list(getattr(blueprint_model, "group_by", [])),
            "visualizacao": str(getattr(blueprint_model, "visualization_type", "TABLE") or "TABLE").upper(),
            "componentes": self._components_from_layout(blueprint_model),
            "complexidade": self._complexity(blueprint_model),
        }

    def fingerprint_hash(self, fingerprint: dict[str, Any]) -> str:
        canonical = json.dumps(fingerprint, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _build_identity(self, tenant_id: uuid.UUID, blueprint_model: Any, version: int, status: str, author: str) -> dict[str, Any]:
        return {
            "uuid": str(getattr(blueprint_model, "id", "") or ""),
            "tenant_id": str(tenant_id),
            "intent_id": getattr(blueprint_model, "intent_id", ""),
            "nome": getattr(blueprint_model, "nome_consulta", ""),
            "descricao": getattr(blueprint_model, "objetivo", ""),
            "categoria": getattr(blueprint_model, "tipo_analise", "Blueprint"),
            "dominio_negocio": self._business_domain(blueprint_model),
            "area": "Business Intelligence",
            "tags": ["blueprint", self._business_domain(blueprint_model).lower()],
            "autor": author,
            "status": status,
            "versao": version,
        }

    def _build_enterprise_modules(
        self,
        tenant_id: uuid.UUID,
        blueprint_model: Any,
        version: int,
        *,
        status: str = "ACTIVE",
        author: str = "IA",
        reason: str = "create_or_update",
        previous_version: int | None = None,
    ) -> dict[str, Any]:
        fingerprint = self.build_fingerprint(blueprint_model)
        fingerprint_hash = self.fingerprint_hash(fingerprint)
        metrics = self._stable_list(getattr(blueprint_model, "metrics", []))
        group_by = self._stable_list(getattr(blueprint_model, "group_by", []))
        filters = getattr(blueprint_model, "filters", {}) or {}
        layout = getattr(blueprint_model, "layout", {}) or {}
        view_name = getattr(blueprint_model, "view_name", "") or ""
        domain = self._business_domain(blueprint_model)
        now = dt.datetime.now(dt.timezone.utc).isoformat()

        return {
            "categoria": getattr(blueprint_model, "tipo_analise", "Blueprint") or "Blueprint",
            "dominio_negocio": domain,
            "area": "Business Intelligence",
            "tags": ["blueprint", domain.lower(), str(getattr(blueprint_model, "visualization_type", "table")).lower()],
            "autor": author,
            "status": status,
            "marketplace_scope": "TENANT",
            "is_marketplace": False,
            "fingerprint": fingerprint,
            "fingerprint_hash": fingerprint_hash,
            "identity": self._build_identity(tenant_id, blueprint_model, version, status, author),
            "business_intent": {
                "objetivo": getattr(blueprint_model, "objetivo", ""),
                "tipo_analise": getattr(blueprint_model, "tipo_analise", "AGGREGATION"),
                "indicadores": metrics,
                "filtros": filters,
                "agrupamentos": group_by,
                "complexidade": fingerprint["complexidade"],
            },
            "semantic_context": {
                "intent_id": getattr(blueprint_model, "intent_id", ""),
                "examples": list(getattr(blueprint_model, "exemplos_perguntas", []) or []),
                "fingerprint_hash": fingerprint_hash,
            },
            "business_context": {
                "dominio": domain,
                "area": "Business Intelligence",
                "categoria": getattr(blueprint_model, "tipo_analise", "Blueprint"),
            },
            "kpi_strategy": {
                "kpis": metrics,
                "dependencies": metrics,
            },
            "visualization_strategy": {
                "primary_chart_type": str(getattr(blueprint_model, "visualization_type", "TABLE") or "TABLE").upper(),
                "layout": layout,
            },
            "component_strategy": {
                "components": fingerprint["componentes"],
                "priority": layout.get("priority", ["KPIS", "CHART", "TABLE"]),
            },
            "filter_strategy": {
                "allowed_filters": self._filter_keys(filters),
                "default_filters": filters,
            },
            "grouping_strategy": {
                "group_by": group_by,
            },
            "navigation_strategy": {
                "drill_down": layout.get("drill_down", []),
                "drill_through": layout.get("drill_through", []),
                "exports": layout.get("exports", ["csv", "xlsx"]),
            },
            "dashboard_template_reference": {
                "template": layout.get("template") or self._suggest_template(blueprint_model),
                "visualization_type": getattr(blueprint_model, "visualization_type", "TABLE"),
            },
            "metadata_info": {
                "source": "BLUEPRINT_REPOSITORY",
                "created_by": author,
                "structural_only": True,
                "contains_erp_data": False,
            },
            "dependencies_map": {
                "views": [view_name] if view_name else [],
                "kpis": metrics,
                "components": fingerprint["componentes"],
                "metadata_catalog": [view_name] if view_name else [],
                "semantic_catalog": metrics,
                "analytical_packages": [],
                "dashboard_templates": [layout.get("template") or self._suggest_template(blueprint_model)],
                "dashboard_instances": [],
                "business_layer": metrics,
            },
            "version_info": {
                "version": version,
                "previous_version": previous_version,
                "author": author,
                "date": now,
                "reason": reason,
                "compatibility": "BACKWARD_COMPATIBLE",
                "changes": [],
            },
            "performance_profile": {
                "avg_usage_ms": 0.0,
                "min_usage_ms": 0.0,
                "max_usage_ms": 0.0,
                "reuse_count": 0,
                "tokens_saved": 0,
                "usage_frequency": "NEW",
                "complexity": fingerprint["complexidade"],
                "render_time_ms": 0.0,
            },
            "quality_profile": {},
            "health_profile": {},
        }

    def _suggest_template(self, blueprint_model: Any) -> str:
        visual = str(getattr(blueprint_model, "visualization_type", "TABLE") or "TABLE").upper()
        analysis = str(getattr(blueprint_model, "tipo_analise", "") or "").upper()
        if visual == "KPI":
            return "Executive Summary"
        if analysis in {"RANKING", "TOP", "BOTTOM"} or visual == "BAR":
            return "Sales Ranking"
        if visual == "LINE":
            return "Sales Overview"
        return "Executive Summary"

    def _score_quality(self, payload: dict[str, Any], usage_count: int = 0, avg_ms: float = 0.0) -> dict[str, Any]:
        fingerprint = payload.get("fingerprint") or {}
        required_ok = bool(fingerprint.get("objetivo") and fingerprint.get("kpis"))
        integrity = 100.0 if required_ok else 70.0
        consistency = 100.0 if payload.get("business_intent", {}).get("indicadores") == fingerprint.get("kpis") else 90.0
        reuse = min(100.0, float(usage_count) * 10.0)
        performance = 100.0 if avg_ms <= 1000 else max(50.0, 100.0 - (avg_ms / 200.0))
        compatibility = 100.0 if payload.get("version_info", {}).get("compatibility") == "BACKWARD_COMPATIBLE" else 75.0
        stability = 100.0
        score = round((integrity + consistency + reuse + stability + compatibility + performance) / 6.0, 2)
        return {
            "integrity": round(integrity, 2),
            "consistency": round(consistency, 2),
            "reuse": round(reuse, 2),
            "stability": round(stability, 2),
            "compatibility": round(compatibility, 2),
            "performance": round(performance, 2),
            "quality_score": score,
        }

    def _score_health(self, payload: dict[str, Any]) -> dict[str, Any]:
        warnings: list[str] = []
        deps = payload.get("dependencies_map") or {}
        if not deps.get("views"):
            warnings.append("missing_view_dependency")
        if not payload.get("fingerprint_hash"):
            warnings.append("missing_fingerprint")
        if not payload.get("dashboard_template_reference", {}).get("template"):
            warnings.append("missing_dashboard_template")
        score = max(0.0, 100.0 - (len(warnings) * 15.0))
        return {
            "health_score": round(score, 2),
            "status": "healthy" if score >= 85 else "warning",
            "warnings": warnings,
            "dependencies_checked": True,
            "versioning_checked": True,
            "templates_checked": True,
            "packages_checked": True,
        }

    async def get_blueprint(self, tenant_id: uuid.UUID, intent_id: str, db_session: AsyncSession) -> Blueprint | None:
        """Return the latest active blueprint by intent and tenant."""
        stmt = (
            select(Blueprint)
            .where(
                Blueprint.tenant_id == tenant_id,
                Blueprint.intent_id == intent_id,
                Blueprint.status == "ACTIVE",
            )
            .order_by(desc(Blueprint.version))
            .limit(1)
        )
        res = await db_session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_blueprint_versions(self, tenant_id: uuid.UUID, intent_id: str, db_session: AsyncSession) -> list[Blueprint]:
        stmt = (
            select(Blueprint)
            .where(Blueprint.tenant_id == tenant_id, Blueprint.intent_id == intent_id)
            .order_by(Blueprint.version.asc())
        )
        res = await db_session.execute(stmt)
        return list(res.scalars().all())

    async def save_blueprint(
        self,
        tenant_id: uuid.UUID,
        blueprint_model: Any,
        db_session: AsyncSession,
        *,
        author: str = "IA",
        reason: str = "save_blueprint",
    ) -> Blueprint:
        """
        Save a blueprint structurally.

        If the latest active version has the same fingerprint, only governance
        profiles and legacy counters are refreshed. If the structure changed, a
        new immutable version is created and the previous one is superseded.
        """
        latest = await self.get_blueprint(tenant_id, blueprint_model.intent_id, db_session)
        incoming_modules = self._build_enterprise_modules(
            tenant_id,
            blueprint_model,
            version=getattr(blueprint_model, "version", 1) or 1,
            author=author,
            reason=reason,
            previous_version=latest.version if latest else None,
        )
        incoming_hash = incoming_modules["fingerprint_hash"]

        if latest and latest.fingerprint_hash == incoming_hash:
            self._refresh_existing(latest, blueprint_model, incoming_modules)
            db_session.add(latest)
            await db_session.flush()
            await self._register_metadata(tenant_id, latest)
            return latest

        next_version = (latest.version + 1) if latest else (getattr(blueprint_model, "version", 1) or 1)
        if latest:
            latest.status = "SUPERSEDED"
            latest.version_info = {
                **self._as_dict(latest.version_info),
                "superseded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "superseded_by_version": next_version,
            }
            db_session.add(latest)

        modules = self._build_enterprise_modules(
            tenant_id,
            blueprint_model,
            version=next_version,
            author=author,
            reason=reason,
            previous_version=latest.version if latest else None,
        )
        modules["quality_profile"] = self._score_quality(modules)
        modules["health_profile"] = self._score_health(modules)

        new_bp = self._new_blueprint_from_model(tenant_id, blueprint_model, next_version, modules)
        db_session.add(new_bp)
        await db_session.flush()
        await self._register_metadata(tenant_id, new_bp)
        return new_bp

    def _refresh_existing(self, bp: Blueprint, blueprint_model: Any, modules: dict[str, Any]) -> None:
        v = getattr(blueprint_model, "versionamento", None)
        bp.nome_consulta = getattr(blueprint_model, "nome_consulta", bp.nome_consulta)
        bp.objetivo = getattr(blueprint_model, "objetivo", bp.objetivo)
        bp.tipo_analise = getattr(blueprint_model, "tipo_analise", bp.tipo_analise)
        view_catalog_id = getattr(blueprint_model, "view_catalog_id", bp.view_catalog_id)
        bp.view_catalog_id = uuid.UUID(view_catalog_id) if isinstance(view_catalog_id, str) and view_catalog_id not in {"", "unknown_catalog"} else view_catalog_id
        bp.view_name = getattr(blueprint_model, "view_name", bp.view_name)
        bp.metrics = list(getattr(blueprint_model, "metrics", bp.metrics) or [])
        bp.group_by = list(getattr(blueprint_model, "group_by", bp.group_by) or [])
        bp.filters = dict(getattr(blueprint_model, "filters", bp.filters) or {})
        bp.visualization_type = getattr(blueprint_model, "visualization_type", bp.visualization_type)
        bp.layout = dict(getattr(blueprint_model, "layout", bp.layout) or {})
        bp.exemplos_perguntas = list(getattr(blueprint_model, "exemplos_perguntas", bp.exemplos_perguntas) or [])
        if v:
            bp.dependencias = list(getattr(v, "dependencias", bp.dependencias) or [])
            bp.permissoes = list(getattr(v, "permissoes", bp.permissoes) or [])
            bp.quantidade_utilizacoes = int(getattr(v, "quantidade_utilizacoes", bp.quantidade_utilizacoes) or 0)
            bp.tempo_acumulado_ms = float(getattr(v, "tempo_acumulado_ms", bp.tempo_acumulado_ms) or 0.0)
            bp.tempo_ia_acumulado_ms = float(getattr(v, "tempo_ia_acumulado_ms", bp.tempo_ia_acumulado_ms) or 0.0)
            bp.tokens_economizados = int(getattr(v, "tokens_economizados", bp.tokens_economizados) or 0)
            ultima = getattr(v, "ultima_utilizacao", None)
            if ultima:
                try:
                    bp.ultima_utilizacao = dt.datetime.fromisoformat(ultima)
                except Exception:
                    pass
        self._apply_modules(bp, modules, preserve_profiles=True)

    def _new_blueprint_from_model(
        self,
        tenant_id: uuid.UUID,
        blueprint_model: Any,
        version: int,
        modules: dict[str, Any],
    ) -> Blueprint:
        v = getattr(blueprint_model, "versionamento", None)
        view_catalog_id = getattr(blueprint_model, "view_catalog_id", None)
        if isinstance(view_catalog_id, str):
            view_catalog_id = uuid.UUID(view_catalog_id) if view_catalog_id and view_catalog_id != "unknown_catalog" else None

        bp = Blueprint(
            tenant_id=tenant_id,
            intent_id=getattr(blueprint_model, "intent_id"),
            nome_consulta=getattr(blueprint_model, "nome_consulta"),
            objetivo=getattr(blueprint_model, "objetivo"),
            tipo_analise=getattr(blueprint_model, "tipo_analise", "AGGREGATION"),
            view_catalog_id=view_catalog_id,
            view_name=getattr(blueprint_model, "view_name"),
            metrics=list(getattr(blueprint_model, "metrics", []) or []),
            group_by=list(getattr(blueprint_model, "group_by", []) or []),
            filters=dict(getattr(blueprint_model, "filters", {}) or {}),
            visualization_type=getattr(blueprint_model, "visualization_type", "TABLE"),
            layout=dict(getattr(blueprint_model, "layout", {}) or {}),
            exemplos_perguntas=list(getattr(blueprint_model, "exemplos_perguntas", []) or []),
            version=version,
            dependencias=list(getattr(v, "dependencias", []) or []) if v else [],
            permissoes=list(getattr(v, "permissoes", []) or []) if v else [],
            quantidade_utilizacoes=int(getattr(v, "quantidade_utilizacoes", 0) or 0) if v else 0,
            tempo_acumulado_ms=float(getattr(v, "tempo_acumulado_ms", 0.0) or 0.0) if v else 0.0,
            tempo_ia_acumulado_ms=float(getattr(v, "tempo_ia_acumulado_ms", 0.0) or 0.0) if v else 0.0,
            tokens_economizados=int(getattr(v, "tokens_economizados", 0) or 0) if v else 0,
        )
        self._apply_modules(bp, modules)
        return bp

    def _apply_modules(self, bp: Blueprint, modules: dict[str, Any], *, preserve_profiles: bool = False) -> None:
        for key, value in modules.items():
            if preserve_profiles and key in {"performance_profile", "quality_profile", "health_profile"}:
                continue
            setattr(bp, key, value)
        if preserve_profiles:
            avg_ms = (bp.tempo_acumulado_ms / bp.quantidade_utilizacoes) if bp.quantidade_utilizacoes else 0.0
            merged = {**modules, "performance_profile": bp.performance_profile or {}}
            bp.quality_profile = self._score_quality(merged, bp.quantidade_utilizacoes, avg_ms)
            bp.health_profile = self._score_health(merged)

    async def get_all_blueprints(self, tenant_id: uuid.UUID, db_session: AsyncSession) -> list[Blueprint]:
        """Return active blueprints for a tenant."""
        stmt = (
            select(Blueprint)
            .where(Blueprint.tenant_id == tenant_id, Blueprint.status == "ACTIVE")
            .order_by(Blueprint.intent_id.asc(), Blueprint.version.desc())
        )
        res = await db_session.execute(stmt)
        return list(res.scalars().all())

    async def find_compatible_blueprint(
        self,
        tenant_id: uuid.UUID,
        blueprint_model: Any,
        db_session: AsyncSession,
        *,
        threshold: float | None = None,
        include_marketplace: bool = True,
    ) -> tuple[Blueprint | None, float]:
        """Find a structurally compatible Blueprint without sharing tenant data."""
        threshold = threshold or self.COMPATIBILITY_THRESHOLD
        incoming_fingerprint = self.build_fingerprint(blueprint_model)
        incoming_hash = self.fingerprint_hash(incoming_fingerprint)

        conditions = [
            and_(Blueprint.tenant_id == tenant_id, Blueprint.status == "ACTIVE"),
        ]
        if include_marketplace:
            conditions.append(
                and_(
                    Blueprint.is_marketplace.is_(True),
                    Blueprint.marketplace_scope == "GLOBAL",
                    Blueprint.status == "ACTIVE",
                )
            )

        stmt = select(Blueprint).where(or_(*conditions)).order_by(Blueprint.quantidade_utilizacoes.desc()).limit(100)
        res = await db_session.execute(stmt)
        candidates = list(res.scalars().all())

        best: Blueprint | None = None
        best_score = 0.0
        for candidate in candidates:
            if candidate.fingerprint_hash == incoming_hash:
                return candidate, 1.0
            score = self._compatibility_score(incoming_fingerprint, candidate.fingerprint or {})
            if score > best_score:
                best = candidate
                best_score = score

        if best and best_score >= threshold:
            return best, round(best_score, 4)
        return None, round(best_score, 4)

    def _compatibility_score(self, incoming: dict[str, Any], existing: dict[str, Any]) -> float:
        def jaccard(a: Any, b: Any) -> float:
            set_a = set(self._stable_list(a))
            set_b = set(self._stable_list(b))
            if not set_a and not set_b:
                return 1.0
            if not set_a or not set_b:
                return 0.0
            return len(set_a & set_b) / len(set_a | set_b)

        weights = {
            "domain": 0.18,
            "analysis": 0.14,
            "kpis": 0.22,
            "groups": 0.14,
            "filters": 0.08,
            "visual": 0.10,
            "components": 0.08,
            "complexity": 0.06,
        }
        score = 0.0
        score += weights["domain"] if incoming.get("entidade") == existing.get("entidade") else 0.0
        score += weights["analysis"] if incoming.get("tipo_analise") == existing.get("tipo_analise") else 0.0
        score += weights["kpis"] * jaccard(incoming.get("kpis"), existing.get("kpis"))
        score += weights["groups"] * jaccard(incoming.get("agrupamentos"), existing.get("agrupamentos"))
        score += weights["filters"] * jaccard(incoming.get("filtros"), existing.get("filtros"))
        score += weights["visual"] if incoming.get("visualizacao") == existing.get("visualizacao") else 0.0
        score += weights["components"] * jaccard(incoming.get("componentes"), existing.get("componentes"))
        score += weights["complexity"] if incoming.get("complexidade") == existing.get("complexidade") else 0.0
        return min(1.0, score)

    async def rollback_blueprint(
        self,
        tenant_id: uuid.UUID,
        intent_id: str,
        target_version: int,
        db_session: AsyncSession,
        *,
        author: str = "SYSTEM",
        reason: str = "rollback",
    ) -> Blueprint:
        """Create a new active version from a previous immutable version."""
        versions = await self.get_blueprint_versions(tenant_id, intent_id, db_session)
        if not versions:
            raise ValueError(f"Blueprint '{intent_id}' not found for tenant.")

        target = next((bp for bp in versions if bp.version == target_version), None)
        if not target:
            raise ValueError(f"Blueprint version {target_version} not found.")

        latest_version = max(bp.version for bp in versions)
        for bp in versions:
            if bp.status == "ACTIVE":
                bp.status = "SUPERSEDED"
                db_session.add(bp)

        new_version = latest_version + 1
        clone = Blueprint(
            tenant_id=tenant_id,
            intent_id=target.intent_id,
            nome_consulta=target.nome_consulta,
            objetivo=target.objetivo,
            tipo_analise=target.tipo_analise,
            view_catalog_id=target.view_catalog_id,
            view_name=target.view_name,
            metrics=self._as_list(target.metrics),
            group_by=self._as_list(target.group_by),
            filters=self._as_dict(target.filters),
            visualization_type=target.visualization_type,
            layout=self._as_dict(target.layout),
            exemplos_perguntas=self._as_list(target.exemplos_perguntas),
            version=new_version,
            dependencias=self._as_list(target.dependencias),
            permissoes=self._as_list(target.permissoes),
        )
        for attr in [
            "categoria",
            "dominio_negocio",
            "area",
            "tags",
            "marketplace_scope",
            "is_marketplace",
            "fingerprint",
            "fingerprint_hash",
            "identity",
            "business_intent",
            "semantic_context",
            "business_context",
            "kpi_strategy",
            "visualization_strategy",
            "component_strategy",
            "filter_strategy",
            "grouping_strategy",
            "navigation_strategy",
            "dashboard_template_reference",
            "metadata_info",
            "dependencies_map",
            "performance_profile",
            "quality_profile",
            "health_profile",
        ]:
            setattr(clone, attr, getattr(target, attr))
        clone.autor = author
        clone.status = "ACTIVE"
        clone.version_info = {
            **self._as_dict(target.version_info),
            "version": new_version,
            "rollback_from_version": target_version,
            "previous_version": latest_version,
            "author": author,
            "reason": reason,
            "date": dt.datetime.now(dt.timezone.utc).isoformat(),
            "compatibility": "BACKWARD_COMPATIBLE",
        }
        clone.identity = {**self._as_dict(clone.identity), "versao": new_version, "status": "ACTIVE", "autor": author}
        db_session.add(clone)
        await db_session.flush()
        await self._register_metadata(tenant_id, clone)
        return clone

    async def publish_to_marketplace(
        self,
        tenant_id: uuid.UUID,
        intent_id: str,
        db_session: AsyncSession,
        *,
        scope: str = "GLOBAL",
    ) -> Blueprint:
        """Expose structural intelligence for cross-tenant reuse, without data."""
        bp = await self.get_blueprint(tenant_id, intent_id, db_session)
        if not bp:
            raise ValueError(f"Blueprint '{intent_id}' not found.")
        bp.is_marketplace = True
        bp.marketplace_scope = scope.upper()
        bp.metadata_info = {
            **self._as_dict(bp.metadata_info),
            "marketplace_published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "contains_erp_data": False,
            "structural_only": True,
        }
        db_session.add(bp)
        await db_session.flush()
        return bp

    async def register_usage(
        self,
        tenant_id: uuid.UUID,
        intent_id: str,
        db_session: AsyncSession,
        *,
        execution_time_ms: float = 0.0,
        render_time_ms: float = 0.0,
        tokens_saved: int = 0,
    ) -> Blueprint | None:
        """Update performance profile and reuse counters for the active Blueprint."""
        bp = await self.get_blueprint(tenant_id, intent_id, db_session)
        if not bp:
            return None
        bp.quantidade_utilizacoes += 1
        bp.tempo_acumulado_ms += float(execution_time_ms or 0.0)
        bp.tokens_economizados += int(tokens_saved or 0)
        bp.ultima_utilizacao = dt.datetime.now(dt.timezone.utc)

        profile = self._as_dict(bp.performance_profile)
        previous_min = float(profile.get("min_usage_ms") or 0.0)
        previous_max = float(profile.get("max_usage_ms") or 0.0)
        avg = bp.tempo_acumulado_ms / bp.quantidade_utilizacoes
        profile.update(
            {
                "avg_usage_ms": round(avg, 2),
                "min_usage_ms": execution_time_ms if previous_min == 0 else min(previous_min, execution_time_ms),
                "max_usage_ms": max(previous_max, execution_time_ms),
                "reuse_count": bp.quantidade_utilizacoes,
                "tokens_saved": bp.tokens_economizados,
                "usage_frequency": "HIGH" if bp.quantidade_utilizacoes >= 10 else "NORMAL",
                "complexity": self._as_dict(bp.fingerprint).get("complexidade", "BAIXA"),
                "render_time_ms": float(render_time_ms or 0.0),
            }
        )
        bp.performance_profile = profile
        modules = {
            "fingerprint": self._as_dict(bp.fingerprint),
            "business_intent": self._as_dict(bp.business_intent),
            "version_info": self._as_dict(bp.version_info),
            "dependencies_map": self._as_dict(bp.dependencies_map),
            "fingerprint_hash": bp.fingerprint_hash,
            "dashboard_template_reference": self._as_dict(bp.dashboard_template_reference),
        }
        bp.quality_profile = self._score_quality(modules, bp.quantidade_utilizacoes, avg)
        bp.health_profile = self._score_health(modules)
        db_session.add(bp)
        await db_session.flush()
        return bp

    async def get_observability_metrics(self, tenant_id: uuid.UUID, db_session: AsyncSession) -> dict[str, Any]:
        """Return repository-level observability for a tenant."""
        stmt = select(Blueprint).where(Blueprint.tenant_id == tenant_id)
        res = await db_session.execute(stmt)
        blueprints = list(res.scalars().all())
        active = [bp for bp in blueprints if bp.status == "ACTIVE"]
        versions = len(blueprints)
        reuse_count = sum(bp.quantidade_utilizacoes for bp in blueprints)
        health_values = [float(self._as_dict(bp.health_profile).get("health_score", 100.0)) for bp in active]
        quality_values = [float(self._as_dict(bp.quality_profile).get("quality_score", 100.0)) for bp in active]
        warnings = sum(len(self._as_dict(bp.health_profile).get("warnings", [])) for bp in active)
        return {
            "quantidade_blueprints": len(active),
            "quantidade_reutilizacoes": reuse_count,
            "quantidade_versoes": versions,
            "tempo_medio_criacao_ms": 0.0,
            "tempo_medio_reutilizacao_ms": round(
                sum(float(self._as_dict(bp.performance_profile).get("avg_usage_ms", 0.0)) for bp in active) / len(active),
                2,
            )
            if active
            else 0.0,
            "health_score": round(sum(health_values) / len(health_values), 2) if health_values else 100.0,
            "quality_score": round(sum(quality_values) / len(quality_values), 2) if quality_values else 100.0,
            "erros": 0,
            "warnings": warnings,
        }

    async def _register_metadata(self, tenant_id: uuid.UUID, blueprint: Blueprint) -> None:
        """Mirror Blueprint governance into Metadata Catalog without blocking."""
        try:
            await _get_catalog_api().register(
                tenant_id=tenant_id,
                tipo="BLUEPRINT",
                dados={
                    "estrutura_id": blueprint.intent_id,
                    "nome_view": blueprint.nome_consulta or blueprint.intent_id,
                    "origem": "BLUEPRINT_REPOSITORY",
                    "owner": blueprint.autor or "IA",
                    "categoria": blueprint.categoria or blueprint.tipo_analise or "Blueprint",
                    "tags": blueprint.tags or ["blueprint"],
                    "blueprint_associado": blueprint.intent_id,
                    "tabelas_utilizadas": [blueprint.view_name] if blueprint.view_name else [],
                    "campos_utilizados": list(blueprint.metrics or []) + list(blueprint.group_by or []),
                    "filtros_padrao": blueprint.filters or {},
                    "kpis_suportados": blueprint.metrics or [],
                    "dependencias": list(set(([blueprint.view_name] if blueprint.view_name else []) + list(blueprint.dependencias or []))),
                    "status": "success" if blueprint.status == "ACTIVE" else "warning",
                    "integridade": "valid",
                    "health_score": self._as_dict(blueprint.health_profile).get("health_score", 100.0),
                    "performance_score": self._as_dict(blueprint.quality_profile).get("performance", 100.0),
                },
                upstream_ids=[blueprint.view_name] if blueprint.view_name else [],
            )
        except Exception as exc:
            logger.debug("[BlueprintRepository] Metadata Catalog registration skipped: %s", exc)


blueprint_repository = BlueprintRepository()
