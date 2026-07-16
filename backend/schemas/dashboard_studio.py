from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DashboardStudioTarget = Literal["TEMPLATE", "INSTANCE"]


class GridItem(BaseModel):
    """Visual grid position for one dashboard component."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=120)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    w: int = Field(default=4, ge=1, le=12)
    h: int = Field(default=4, ge=1, le=48)
    min_w: int | None = Field(default=None, ge=1, le=12)
    min_h: int | None = Field(default=None, ge=1, le=48)
    hidden: bool = False


class ComponentConfig(BaseModel):
    """Visual component shell. It references existing analytical output only by id."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=120)
    type: str = Field(..., min_length=2, max_length=80)
    title: str | None = Field(default=None, max_length=255)
    source_id: str | None = Field(default=None, max_length=255)
    visual_config: dict[str, Any] = Field(default_factory=dict)
    allowed_interactions: list[str] = Field(default_factory=list)
    hidden: bool = False


class DashboardTemplateCreate(BaseModel):
    """Create a persistent dashboard template with visual-only metadata."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str = Field(default="CUSTOM", min_length=2, max_length=100)
    blueprint_id: uuid.UUID | None = None
    analytical_package_id: uuid.UUID | None = None
    layout: dict[str, Any] = Field(default_factory=dict)
    grid: dict[str, Any] | list[dict[str, Any]] = Field(default_factory=dict)
    components: list[dict[str, Any]] = Field(default_factory=list)
    component_order: list[str] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    tabs: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    responsive: dict[str, Any] = Field(default_factory=dict)
    theme: dict[str, Any] = Field(default_factory=dict)
    visual_config: dict[str, Any] = Field(default_factory=dict)
    default_state: dict[str, Any] = Field(default_factory=dict)
    available_components: list[dict[str, Any]] = Field(default_factory=list)
    permissions: dict[str, Any] = Field(default_factory=dict)


class DashboardTemplateUpdate(BaseModel):
    """Update only visual/template presentation fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    status: Literal["ACTIVE", "ARCHIVED"] | None = None
    layout: dict[str, Any] | None = None
    grid: dict[str, Any] | list[dict[str, Any]] | None = None
    components: list[dict[str, Any]] | None = None
    component_order: list[str] | None = None
    groups: list[dict[str, Any]] | None = None
    tabs: list[dict[str, Any]] | None = None
    sections: list[dict[str, Any]] | None = None
    responsive: dict[str, Any] | None = None
    theme: dict[str, Any] | None = None
    visual_config: dict[str, Any] | None = None
    default_state: dict[str, Any] | None = None
    available_components: list[dict[str, Any]] | None = None
    permissions: dict[str, Any] | None = None
    description_change: str | None = Field(default=None, max_length=500)


class DashboardTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    blueprint_id: uuid.UUID | None = None
    analytical_package_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    category: str
    status: str
    version: int
    layout: dict[str, Any]
    grid: dict[str, Any]
    components: list[dict[str, Any]]
    component_order: list[str]
    groups: list[dict[str, Any]]
    tabs: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    responsive: dict[str, Any]
    theme: dict[str, Any]
    visual_config: dict[str, Any]
    default_state: dict[str, Any]
    available_components: list[dict[str, Any]]
    permissions: dict[str, Any]
    created_by: uuid.UUID | None = None
    criado_em: datetime
    atualizado_em: datetime


class DashboardInstanceCreate(BaseModel):
    """Create an independent user dashboard instance from a template."""

    model_config = ConfigDict(extra="forbid")

    template_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255)
    current_filters: dict[str, Any] = Field(default_factory=dict)
    expanded_components: list[str] = Field(default_factory=list)
    panel_positions: dict[str, Any] = Field(default_factory=dict)
    favorites: list[str] = Field(default_factory=list)
    visible_columns: dict[str, Any] = Field(default_factory=dict)
    sort_orders: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    current_state: dict[str, Any] = Field(default_factory=dict)
    layout_override: dict[str, Any] = Field(default_factory=dict)


class DashboardInstanceUpdate(BaseModel):
    """Update user-specific state without changing the original template."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=255)
    status: Literal["ACTIVE", "ARCHIVED"] | None = None
    is_favorite: bool | None = None
    current_filters: dict[str, Any] | None = None
    expanded_components: list[str] | None = None
    panel_positions: dict[str, Any] | None = None
    favorites: list[str] | None = None
    visible_columns: dict[str, Any] | None = None
    sort_orders: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    current_state: dict[str, Any] | None = None
    layout_override: dict[str, Any] | None = None
    description_change: str | None = Field(default=None, max_length=500)


class DashboardInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    status: str
    is_favorite: bool
    version: int
    current_filters: dict[str, Any]
    expanded_components: list[str]
    panel_positions: dict[str, Any]
    favorites: list[str]
    visible_columns: dict[str, Any]
    sort_orders: dict[str, Any]
    preferences: dict[str, Any]
    current_state: dict[str, Any]
    layout_override: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime


class DashboardStudioVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID | None = None
    instance_id: uuid.UUID | None = None
    target_type: str
    version: int
    snapshot: dict[str, Any]
    author_id: uuid.UUID | None = None
    description: str | None = None
    criado_em: datetime


class DashboardDuplicateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=255)


class DashboardFavoriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_favorite: bool = True


class DashboardRollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=500)


class DashboardLayoutValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid: dict[str, Any] | list[dict[str, Any]] = Field(default_factory=dict)


class DashboardLayoutValidationResponse(BaseModel):
    is_valid: bool
    grid: dict[str, Any]
    adjustments: list[str] = Field(default_factory=list)


class DashboardExportResponse(BaseModel):
    target_type: DashboardStudioTarget
    schema_version: str = "dashboard-studio/v1"
    exported_at: datetime
    payload: dict[str, Any]


class DashboardImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: DashboardStudioTarget
    payload: dict[str, Any]
    name_override: str | None = Field(default=None, min_length=2, max_length=255)

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("Payload de importacao nao pode ser vazio.")
        return value
