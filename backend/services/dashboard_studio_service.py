from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dashboard_instance import DashboardInstance
from models.dashboard_studio_version import DashboardStudioVersion
from models.dashboard_template import DashboardTemplate
from models.user import User
from schemas.dashboard_studio import (
    DashboardDuplicateRequest,
    DashboardExportResponse,
    DashboardFavoriteRequest,
    DashboardImportRequest,
    DashboardInstanceCreate,
    DashboardInstanceUpdate,
    DashboardLayoutValidationResponse,
    DashboardTemplateCreate,
    DashboardTemplateUpdate,
)


class DashboardStudioService:
    """Visual-only service for Dashboard Templates and user Instances."""

    FORBIDDEN_KEYS = {
        "blueprint",
        "business_layer",
        "business_rules",
        "data_platform",
        "analytics_engine",
        "kpi",
        "kpis",
        "metric",
        "metrics",
        "formula",
        "formulas",
        "calculation",
        "calculations",
        "sql",
        "query",
        "queries",
        "view",
        "views",
        "dataset",
        "datasets",
        "raw_data",
        "raw_rows",
        "records",
        "rows",
        "chart_data",
        "analytics_results",
        "dashboard_payload",
        "dados_estruturados",
    }

    TEMPLATE_VISUAL_FIELDS = {
        "name",
        "description",
        "category",
        "status",
        "layout",
        "grid",
        "components",
        "component_order",
        "groups",
        "tabs",
        "sections",
        "responsive",
        "theme",
        "visual_config",
        "default_state",
        "available_components",
        "permissions",
    }

    INSTANCE_STATE_FIELDS = {
        "name",
        "status",
        "is_favorite",
        "current_filters",
        "expanded_components",
        "panel_positions",
        "favorites",
        "visible_columns",
        "sort_orders",
        "preferences",
        "current_state",
        "layout_override",
    }

    TEMPLATE_SNAPSHOT_FIELDS = {
        "id",
        "tenant_id",
        "blueprint_id",
        "analytical_package_id",
        "name",
        "description",
        "category",
        "status",
        "version",
        "layout",
        "grid",
        "components",
        "component_order",
        "groups",
        "tabs",
        "sections",
        "responsive",
        "theme",
        "visual_config",
        "default_state",
        "available_components",
        "permissions",
        "created_by",
        "criado_em",
        "atualizado_em",
    }

    INSTANCE_SNAPSHOT_FIELDS = {
        "id",
        "tenant_id",
        "template_id",
        "user_id",
        "name",
        "status",
        "is_favorite",
        "version",
        "current_filters",
        "expanded_components",
        "panel_positions",
        "favorites",
        "visible_columns",
        "sort_orders",
        "preferences",
        "current_state",
        "layout_override",
        "criado_em",
        "atualizado_em",
    }

    DEFAULT_AVAILABLE_COMPONENTS = [
        {"type": "KPI", "label": "KPI card", "category": "indicator"},
        {"type": "CARD", "label": "Metric card", "category": "indicator"},
        {"type": "BAR", "label": "Bar chart", "category": "chart"},
        {"type": "LINE", "label": "Line chart", "category": "chart"},
        {"type": "TABLE", "label": "Data table shell", "category": "table"},
        {"type": "FILTERS", "label": "Filter panel", "category": "control"},
        {"type": "SUMMARY", "label": "Executive summary", "category": "insight"},
    ]

    async def create_template(
        self,
        db: AsyncSession,
        payload: DashboardTemplateCreate,
        current_user: User,
    ) -> DashboardTemplate:
        data = payload.model_dump()
        self._assert_visual_only(data)

        grid, _ = self.normalize_grid(data.get("grid") or {})
        components = data.get("components") or []
        component_order = data.get("component_order") or self._component_order(components, grid)

        template = DashboardTemplate(
            tenant_id=current_user.tenant_id,
            created_by=current_user.id,
            blueprint_id=data.get("blueprint_id"),
            analytical_package_id=data.get("analytical_package_id"),
            name=data["name"],
            description=data.get("description"),
            category=data.get("category") or "CUSTOM",
            layout=data.get("layout") or self._default_layout(),
            grid=grid,
            components=components,
            component_order=component_order,
            groups=data.get("groups") or [],
            tabs=data.get("tabs") or [],
            sections=data.get("sections") or [],
            responsive=data.get("responsive") or self._default_responsive(),
            theme=data.get("theme") or self._default_theme(),
            visual_config=data.get("visual_config") or {},
            default_state=data.get("default_state") or {},
            available_components=data.get("available_components") or copy.deepcopy(self.DEFAULT_AVAILABLE_COMPONENTS),
            permissions=data.get("permissions") or self._default_permissions(),
        )

        db.add(template)
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        await self._record_template_version(db, template, current_user.id, "Template created")
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        return template

    async def list_templates(
        self,
        db: AsyncSession,
        current_user: User,
        include_archived: bool = False,
    ) -> list[DashboardTemplate]:
        stmt = select(DashboardTemplate).where(DashboardTemplate.tenant_id == current_user.tenant_id)
        if not include_archived:
            stmt = stmt.where(DashboardTemplate.status == "ACTIVE")
        stmt = stmt.order_by(DashboardTemplate.atualizado_em.desc())
        result = await db.execute(stmt)
        templates = list(result.scalars().all())
        for template in templates:
            self._coerce_template_json(template)
        return templates

    async def get_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        current_user: User,
    ) -> DashboardTemplate:
        return await self._get_template(db, template_id, current_user.tenant_id)

    async def update_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        payload: DashboardTemplateUpdate,
        current_user: User,
    ) -> DashboardTemplate:
        template = await self._get_template(db, template_id, current_user.tenant_id)
        changes = payload.model_dump(exclude_unset=True)
        description = changes.pop("description_change", None) or "Template updated"
        self._assert_visual_only(changes)

        if "grid" in changes:
            changes["grid"], _ = self.normalize_grid(changes["grid"] or {})
        if "components" in changes and "component_order" not in changes:
            changes["component_order"] = self._component_order(changes["components"], changes.get("grid", template.grid))

        for field, value in changes.items():
            if field in self.TEMPLATE_VISUAL_FIELDS:
                setattr(template, field, value)

        template.version += 1
        db.add(template)
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        await self._record_template_version(db, template, current_user.id, description)
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        return template

    async def create_instance(
        self,
        db: AsyncSession,
        payload: DashboardInstanceCreate,
        current_user: User,
    ) -> DashboardInstance:
        data = payload.model_dump()
        self._assert_visual_only(data)
        await self._get_template(db, data["template_id"], current_user.tenant_id)

        data["panel_positions"] = self.normalize_panel_positions(data.get("panel_positions") or {})
        data["layout_override"] = self.normalize_layout_override(data.get("layout_override") or {})

        instance = DashboardInstance(
            tenant_id=current_user.tenant_id,
            template_id=data["template_id"],
            user_id=current_user.id,
            name=data["name"],
            current_filters=data.get("current_filters") or {},
            expanded_components=data.get("expanded_components") or [],
            panel_positions=data.get("panel_positions") or {},
            favorites=data.get("favorites") or [],
            visible_columns=data.get("visible_columns") or {},
            sort_orders=data.get("sort_orders") or {},
            preferences=data.get("preferences") or {},
            current_state=data.get("current_state") or {},
            layout_override=data.get("layout_override") or {},
        )

        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        await self._record_instance_version(db, instance, current_user.id, "Instance created")
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        return instance

    async def list_instances(
        self,
        db: AsyncSession,
        current_user: User,
        include_archived: bool = False,
        favorites_only: bool = False,
    ) -> list[DashboardInstance]:
        stmt = select(DashboardInstance).where(
            DashboardInstance.tenant_id == current_user.tenant_id,
            DashboardInstance.user_id == current_user.id,
        )
        if not include_archived:
            stmt = stmt.where(DashboardInstance.status == "ACTIVE")
        if favorites_only:
            stmt = stmt.where(DashboardInstance.is_favorite.is_(True))
        stmt = stmt.order_by(DashboardInstance.atualizado_em.desc())
        result = await db.execute(stmt)
        instances = list(result.scalars().all())
        for instance in instances:
            self._coerce_instance_json(instance)
        return instances

    async def get_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        current_user: User,
    ) -> DashboardInstance:
        return await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)

    async def update_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        payload: DashboardInstanceUpdate,
        current_user: User,
    ) -> DashboardInstance:
        instance = await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        template_version_before = await self._template_version(db, instance.template_id, current_user.tenant_id)

        changes = payload.model_dump(exclude_unset=True)
        description = changes.pop("description_change", None) or "Instance updated"
        self._assert_visual_only(changes)

        if "panel_positions" in changes:
            changes["panel_positions"] = self.normalize_panel_positions(changes["panel_positions"] or {})
        if "layout_override" in changes:
            changes["layout_override"] = self.normalize_layout_override(changes["layout_override"] or {})

        for field, value in changes.items():
            if field in self.INSTANCE_STATE_FIELDS:
                setattr(instance, field, value)

        instance.version += 1
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)

        template_version_after = await self._template_version(db, instance.template_id, current_user.tenant_id)
        if template_version_after != template_version_before:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Template alterado durante a edicao. Recarregue o Studio antes de salvar.",
            )

        await self._record_instance_version(db, instance, current_user.id, description)
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        return instance

    async def duplicate_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        payload: DashboardDuplicateRequest,
        current_user: User,
    ) -> DashboardInstance:
        source = await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        new_instance = DashboardInstance(
            tenant_id=source.tenant_id,
            template_id=source.template_id,
            user_id=current_user.id,
            name=payload.name or f"{source.name} - Copy",
            is_favorite=False,
            current_filters=copy.deepcopy(source.current_filters),
            expanded_components=copy.deepcopy(source.expanded_components),
            panel_positions=copy.deepcopy(source.panel_positions),
            favorites=copy.deepcopy(source.favorites),
            visible_columns=copy.deepcopy(source.visible_columns),
            sort_orders=copy.deepcopy(source.sort_orders),
            preferences=copy.deepcopy(source.preferences),
            current_state=copy.deepcopy(source.current_state),
            layout_override=copy.deepcopy(source.layout_override),
        )
        db.add(new_instance)
        await db.flush()
        await db.refresh(new_instance)
        self._coerce_instance_json(new_instance)
        await self._record_instance_version(db, new_instance, current_user.id, f"Duplicated from {source.id}")
        await db.flush()
        await db.refresh(new_instance)
        self._coerce_instance_json(new_instance)
        return new_instance

    async def set_favorite(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        payload: DashboardFavoriteRequest,
        current_user: User,
    ) -> DashboardInstance:
        instance = await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        instance.is_favorite = payload.is_favorite
        instance.version += 1
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        await self._record_instance_version(db, instance, current_user.id, "Favorite changed")
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        return instance

    async def list_template_versions(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        current_user: User,
    ) -> list[DashboardStudioVersion]:
        await self._get_template(db, template_id, current_user.tenant_id)
        result = await db.execute(
            select(DashboardStudioVersion)
            .where(
                DashboardStudioVersion.tenant_id == current_user.tenant_id,
                DashboardStudioVersion.template_id == template_id,
                DashboardStudioVersion.target_type == "TEMPLATE",
            )
            .order_by(DashboardStudioVersion.version.desc())
        )
        versions = list(result.scalars().all())
        for version in versions:
            self._coerce_version_json(version)
        return versions

    async def list_instance_versions(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        current_user: User,
    ) -> list[DashboardStudioVersion]:
        await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        result = await db.execute(
            select(DashboardStudioVersion)
            .where(
                DashboardStudioVersion.tenant_id == current_user.tenant_id,
                DashboardStudioVersion.instance_id == instance_id,
                DashboardStudioVersion.target_type == "INSTANCE",
            )
            .order_by(DashboardStudioVersion.version.desc())
        )
        versions = list(result.scalars().all())
        for version in versions:
            self._coerce_version_json(version)
        return versions

    async def rollback_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        version: int,
        current_user: User,
        description: str | None = None,
    ) -> DashboardTemplate:
        template = await self._get_template(db, template_id, current_user.tenant_id)
        version_row = await self._get_version(db, current_user.tenant_id, "TEMPLATE", version, template_id=template_id)
        snapshot = dict(self._coerce_json_value(version_row.snapshot, {}))
        self._assert_visual_only(snapshot)

        for field in self.TEMPLATE_VISUAL_FIELDS:
            if field in snapshot:
                setattr(template, field, copy.deepcopy(snapshot[field]))

        template.version += 1
        db.add(template)
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        await self._record_template_version(
            db,
            template,
            current_user.id,
            description or f"Rollback to template version {version}",
        )
        await db.flush()
        await db.refresh(template)
        self._coerce_template_json(template)
        return template

    async def rollback_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        version: int,
        current_user: User,
        description: str | None = None,
    ) -> DashboardInstance:
        instance = await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        version_row = await self._get_version(db, current_user.tenant_id, "INSTANCE", version, instance_id=instance_id)
        snapshot = dict(self._coerce_json_value(version_row.snapshot, {}))
        self._assert_visual_only(snapshot)

        for field in self.INSTANCE_STATE_FIELDS:
            if field in snapshot:
                setattr(instance, field, copy.deepcopy(snapshot[field]))

        instance.version += 1
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        await self._record_instance_version(
            db,
            instance,
            current_user.id,
            description or f"Rollback to instance version {version}",
        )
        await db.flush()
        await db.refresh(instance)
        self._coerce_instance_json(instance)
        return instance

    async def export_template(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        current_user: User,
    ) -> DashboardExportResponse:
        template = await self._get_template(db, template_id, current_user.tenant_id)
        return DashboardExportResponse(
            target_type="TEMPLATE",
            exported_at=datetime.now(timezone.utc),
            payload=self._template_snapshot(template),
        )

    async def export_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        current_user: User,
    ) -> DashboardExportResponse:
        instance = await self._get_instance(db, instance_id, current_user.tenant_id, current_user.id)
        return DashboardExportResponse(
            target_type="INSTANCE",
            exported_at=datetime.now(timezone.utc),
            payload=self._instance_snapshot(instance),
        )

    async def import_layout(
        self,
        db: AsyncSession,
        payload: DashboardImportRequest,
        current_user: User,
    ) -> DashboardTemplate | DashboardInstance:
        self._assert_visual_only(payload.payload)
        imported = dict(payload.payload)

        if payload.target_type == "TEMPLATE":
            create_payload = DashboardTemplateCreate(
                name=payload.name_override or imported.get("name") or "Imported Dashboard Template",
                description=imported.get("description"),
                category=imported.get("category") or "IMPORTED",
                layout=imported.get("layout") or {},
                grid=imported.get("grid") or {},
                components=imported.get("components") or [],
                component_order=imported.get("component_order") or [],
                groups=imported.get("groups") or [],
                tabs=imported.get("tabs") or [],
                sections=imported.get("sections") or [],
                responsive=imported.get("responsive") or {},
                theme=imported.get("theme") or {},
                visual_config=imported.get("visual_config") or {},
                default_state=imported.get("default_state") or {},
                available_components=imported.get("available_components") or [],
                permissions=imported.get("permissions") or {},
            )
            return await self.create_template(db, create_payload, current_user)

        template_id_raw = imported.get("template_id")
        if not template_id_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importacao de instancia exige template_id existente no tenant.",
            )
        create_instance = DashboardInstanceCreate(
            template_id=uuid.UUID(str(template_id_raw)),
            name=payload.name_override or imported.get("name") or "Imported Dashboard Instance",
            current_filters=imported.get("current_filters") or {},
            expanded_components=imported.get("expanded_components") or [],
            panel_positions=imported.get("panel_positions") or {},
            favorites=imported.get("favorites") or [],
            visible_columns=imported.get("visible_columns") or {},
            sort_orders=imported.get("sort_orders") or {},
            preferences=imported.get("preferences") or {},
            current_state=imported.get("current_state") or {},
            layout_override=imported.get("layout_override") or {},
        )
        return await self.create_instance(db, create_instance, current_user)

    def validate_layout(self, grid: dict[str, Any] | list[dict[str, Any]]) -> DashboardLayoutValidationResponse:
        normalized, adjustments = self.normalize_grid(grid)
        return DashboardLayoutValidationResponse(
            is_valid=len(adjustments) == 0,
            grid=normalized,
            adjustments=adjustments,
        )

    def normalize_grid(self, grid: dict[str, Any] | list[dict[str, Any]] | None) -> tuple[dict[str, Any], list[str]]:
        adjustments: list[str] = []
        if grid is None:
            grid = {}
        if isinstance(grid, list):
            grid = {"columns": 12, "gap": 16, "items": grid}
        if not isinstance(grid, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grid invalido.")

        columns = self._int_between(grid.get("columns", 12), 1, 24, 12)
        items_raw = grid.get("items", [])
        if not isinstance(items_raw, list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grid.items deve ser uma lista.")

        normalized_items: list[dict[str, Any]] = []
        occupied: list[dict[str, Any]] = []
        for index, item in enumerate(items_raw):
            if not isinstance(item, dict):
                adjustments.append(f"Item {index} ignorado por nao ser objeto.")
                continue
            item_id = str(item.get("id") or f"component-{index + 1}")
            w = self._int_between(item.get("w", 4), 1, columns, 4)
            h = self._int_between(item.get("h", 4), 1, 48, 4)
            x = self._int_between(item.get("x", 0), 0, columns - 1, 0)
            y = self._int_between(item.get("y", 0), 0, 10_000, 0)
            if x + w > columns:
                x = max(0, columns - w)
                adjustments.append(f"{item_id}: ajustado para caber no grid.")

            normalized = {**item, "id": item_id, "x": x, "y": y, "w": w, "h": h}
            original_y = normalized["y"]
            while any(self._overlaps(normalized, other) for other in occupied):
                normalized["y"] += 1
            if normalized["y"] != original_y:
                adjustments.append(f"{item_id}: reposicionado para evitar sobreposicao.")
            occupied.append(normalized)
            normalized_items.append(normalized)

        normalized_items.sort(key=lambda i: (i.get("y", 0), i.get("x", 0), i.get("id", "")))
        normalized = {**grid, "columns": columns, "items": normalized_items, "no_overlap": True}
        normalized.setdefault("gap", 16)
        normalized.setdefault("row_height", 88)
        normalized.setdefault("snap", True)
        normalized.setdefault("auto_spacing", True)
        normalized.setdefault("auto_balance", True)
        normalized.setdefault("responsive", True)
        return normalized, adjustments

    def normalize_panel_positions(self, panel_positions: dict[str, Any]) -> dict[str, Any]:
        if not panel_positions:
            return {}
        items = []
        passthrough: dict[str, Any] = {}
        for key, value in panel_positions.items():
            if isinstance(value, dict) and {"x", "y", "w", "h"}.issubset(value.keys()):
                items.append({"id": key, **value})
            else:
                passthrough[key] = value
        if not items:
            return panel_positions
        normalized, _ = self.normalize_grid({"items": items})
        return {**passthrough, **{item["id"]: item for item in normalized["items"]}}

    def normalize_layout_override(self, layout_override: dict[str, Any]) -> dict[str, Any]:
        if not layout_override:
            return {}
        normalized = dict(layout_override)
        if "grid" in normalized:
            normalized["grid"], _ = self.normalize_grid(normalized.get("grid") or {})
        elif "items" in normalized:
            grid, _ = self.normalize_grid(normalized)
            normalized = {"grid": grid}
        return normalized

    async def _get_template(self, db: AsyncSession, template_id: uuid.UUID, tenant_id: uuid.UUID) -> DashboardTemplate:
        result = await db.execute(
            select(DashboardTemplate).where(
                DashboardTemplate.id == template_id,
                DashboardTemplate.tenant_id == tenant_id,
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard Template nao encontrado.")
        self._coerce_template_json(template)
        return template

    async def _get_instance(
        self,
        db: AsyncSession,
        instance_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DashboardInstance:
        result = await db.execute(
            select(DashboardInstance).where(
                DashboardInstance.id == instance_id,
                DashboardInstance.tenant_id == tenant_id,
                DashboardInstance.user_id == user_id,
            )
        )
        instance = result.scalar_one_or_none()
        if instance is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard Instance nao encontrada.")
        self._coerce_instance_json(instance)
        return instance

    async def _template_version(self, db: AsyncSession, template_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        template = await self._get_template(db, template_id, tenant_id)
        return template.version

    async def _get_version(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        target_type: str,
        version: int,
        template_id: uuid.UUID | None = None,
        instance_id: uuid.UUID | None = None,
    ) -> DashboardStudioVersion:
        stmt = select(DashboardStudioVersion).where(
            DashboardStudioVersion.tenant_id == tenant_id,
            DashboardStudioVersion.target_type == target_type,
            DashboardStudioVersion.version == version,
        )
        if target_type == "TEMPLATE":
            stmt = stmt.where(DashboardStudioVersion.template_id == template_id)
        else:
            stmt = stmt.where(DashboardStudioVersion.instance_id == instance_id)
        result = await db.execute(stmt)
        version_row = result.scalar_one_or_none()
        if version_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versao nao encontrada.")
        self._coerce_version_json(version_row)
        return version_row

    async def _record_template_version(
        self,
        db: AsyncSession,
        template: DashboardTemplate,
        author_id: uuid.UUID | None,
        description: str,
    ) -> DashboardStudioVersion:
        row = DashboardStudioVersion(
            tenant_id=template.tenant_id,
            template_id=template.id,
            target_type="TEMPLATE",
            version=template.version,
            snapshot=self._template_snapshot(template),
            author_id=author_id,
            description=description,
        )
        db.add(row)
        return row

    async def _record_instance_version(
        self,
        db: AsyncSession,
        instance: DashboardInstance,
        author_id: uuid.UUID | None,
        description: str,
    ) -> DashboardStudioVersion:
        row = DashboardStudioVersion(
            tenant_id=instance.tenant_id,
            instance_id=instance.id,
            target_type="INSTANCE",
            version=instance.version,
            snapshot=self._instance_snapshot(instance),
            author_id=author_id,
            description=description,
        )
        db.add(row)
        return row

    def _template_snapshot(self, template: DashboardTemplate) -> dict[str, Any]:
        self._coerce_template_json(template)
        return self._snapshot(template, self.TEMPLATE_SNAPSHOT_FIELDS)

    def _instance_snapshot(self, instance: DashboardInstance) -> dict[str, Any]:
        self._coerce_instance_json(instance)
        return self._snapshot(instance, self.INSTANCE_SNAPSHOT_FIELDS)

    def _coerce_template_json(self, template: DashboardTemplate) -> None:
        for field in {
            "layout",
            "grid",
            "components",
            "component_order",
            "groups",
            "tabs",
            "sections",
            "responsive",
            "theme",
            "visual_config",
            "default_state",
            "available_components",
            "permissions",
        }:
            fallback: Any = [] if field in {"components", "component_order", "groups", "tabs", "sections", "available_components"} else {}
            setattr(template, field, self._coerce_json_value(getattr(template, field), fallback))

    def _coerce_instance_json(self, instance: DashboardInstance) -> None:
        for field in {
            "current_filters",
            "expanded_components",
            "panel_positions",
            "favorites",
            "visible_columns",
            "sort_orders",
            "preferences",
            "current_state",
            "layout_override",
        }:
            fallback: Any = [] if field in {"expanded_components", "favorites"} else {}
            setattr(instance, field, self._coerce_json_value(getattr(instance, field), fallback))

    def _coerce_version_json(self, version: DashboardStudioVersion) -> None:
        version.snapshot = self._coerce_json_value(version.snapshot, {})

    def _coerce_json_value(self, value: Any, fallback: Any) -> Any:
        if value is None:
            return copy.deepcopy(fallback)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return copy.deepcopy(fallback)
        return value

    def _snapshot(self, obj: Any, fields: set[str]) -> dict[str, Any]:
        return {field: self._json_safe(copy.deepcopy(getattr(obj, field))) for field in fields if hasattr(obj, field)}

    def _json_safe(self, value: Any) -> Any:
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._json_safe(val) for key, val in value.items()}
        return value

    def _assert_visual_only(self, payload: Any, path: str = "payload") -> None:
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key).strip().lower()
                if normalized_key in self.FORBIDDEN_KEYS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Dashboard Studio aceita apenas personalizacao visual. "
                            f"Campo proibido: {path}.{key}"
                        ),
                    )
                self._assert_visual_only(value, f"{path}.{key}")
        elif isinstance(payload, list):
            for index, item in enumerate(payload):
                self._assert_visual_only(item, f"{path}[{index}]")

    def _component_order(self, components: list[dict[str, Any]], grid: dict[str, Any] | list[dict[str, Any]] | None) -> list[str]:
        ordered: list[str] = []
        if isinstance(grid, dict):
            grid_items = grid.get("items") or []
            if isinstance(grid_items, list):
                ordered.extend([str(item.get("id")) for item in grid_items if isinstance(item, dict) and item.get("id")])
        ordered.extend([str(item.get("id")) for item in components if isinstance(item, dict) and item.get("id")])
        deduped: list[str] = []
        for item_id in ordered:
            if item_id not in deduped:
                deduped.append(item_id)
        return deduped

    def _default_layout(self) -> dict[str, Any]:
        return {
            "type": "enterprise-grid",
            "density": "comfortable",
            "hierarchy": ["kpis", "primary_visual", "details", "summary"],
        }

    def _default_responsive(self) -> dict[str, Any]:
        return {
            "desktop": {"columns": 12},
            "notebook": {"columns": 10},
            "tablet": {"columns": 6},
            "mobile": {"columns": 1, "stack": True},
        }

    def _default_theme(self) -> dict[str, Any]:
        return {
            "mode": "corporate",
            "palette": {"primary": "#14b8a6", "accent": "#f59e0b", "surface": "#0f172a"},
            "typography": {"heading": "Manrope", "body": "Source Sans 3"},
            "spacing": "balanced",
            "radius": "xl",
            "shadows": "soft",
        }

    def _default_permissions(self) -> dict[str, Any]:
        return {
            "can_move": True,
            "can_resize": True,
            "can_hide": True,
            "can_duplicate": True,
            "can_export_layout": True,
            "can_change_analytics": False,
        }

    def _int_between(self, value: Any, minimum: int, maximum: int, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(maximum, parsed))

    def _overlaps(self, a: dict[str, Any], b: dict[str, Any]) -> bool:
        return not (
            a["x"] + a["w"] <= b["x"]
            or b["x"] + b["w"] <= a["x"]
            or a["y"] + a["h"] <= b["y"]
            or b["y"] + b["h"] <= a["y"]
        )


dashboard_studio_service = DashboardStudioService()
