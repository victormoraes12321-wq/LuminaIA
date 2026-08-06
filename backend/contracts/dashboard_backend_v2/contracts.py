"""Strict public contracts for the governed dashboard backend.

The backend contract deliberately carries canonical identifiers and certified
metadata only.  SQL, physical identifiers, credentials and tenant authority
from clients are not part of this surface.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardLifecycleV2,
    DashboardOriginV2,
    DashboardSemanticPatchV2,
    DashboardVisualPatchV2,
)


DASHBOARD_BACKEND_CONTRACT_VERSION = "lumina.dashboard-backend/1.0"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}$"
CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StrictDashboardBackendModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class DashboardOwnershipTypeV2(str, Enum):
    USER = "USER"
    TEAM = "TEAM"
    TENANT = "TENANT"
    SYSTEM_TEMPLATE = "SYSTEM_TEMPLATE"


class DashboardCollaboratorRoleV2(str, Enum):
    VIEWER = "VIEWER"
    EDITOR_VISUAL = "EDITOR_VISUAL"
    EDITOR_SEMANTIC = "EDITOR_SEMANTIC"
    REVIEWER = "REVIEWER"
    PUBLISHER = "PUBLISHER"
    ADMINISTRATOR = "ADMINISTRATOR"


class DashboardReviewDecisionKindV2(str, Enum):
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DashboardRuntimeStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"


class DashboardWidgetResultStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


class DashboardCacheIndicatorV2(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    BYPASS = "BYPASS"
    MATERIALIZATION_HIT = "MATERIALIZATION_HIT"


class DashboardCapabilityBackendV2(str, Enum):
    CREATE = "dashboard:create"
    VIEW = "dashboard:view"
    LIST = "dashboard:list"
    EDIT_VISUAL = "dashboard:edit_visual"
    EDIT_SEMANTIC = "dashboard:edit_semantic"
    REVIEW = "dashboard:review"
    APPROVE = "dashboard:approve"
    PUBLISH = "dashboard:publish"
    ROLLBACK = "dashboard:rollback"
    ARCHIVE = "dashboard:archive"
    CLONE = "dashboard:clone"
    MANAGE_COLLABORATORS = "dashboard:manage_collaborators"
    EXECUTE = "dashboard:execute"
    VIEW_PROVENANCE = "dashboard:view_provenance"
    VIEW_AUDIT = "dashboard:view_audit"


class DashboardIdentityRecordV2(StrictDashboardBackendModel):
    dashboard_id: str = Field(pattern=ID_PATTERN)
    canonical_name: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=8, max_length=1_000)


class DashboardOwnershipV2(StrictDashboardBackendModel):
    ownership_type: DashboardOwnershipTypeV2
    owner_reference: str = Field(pattern=ID_PATTERN)


class DashboardCollaboratorV2(StrictDashboardBackendModel):
    collaborator_id: str = Field(pattern=ID_PATTERN)
    user_reference: str = Field(pattern=ID_PATTERN)
    role: DashboardCollaboratorRoleV2
    lock_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class DashboardCollaboratorCreateRequestV2(StrictDashboardBackendModel):
    user_reference: str = Field(pattern=ID_PATTERN)
    role: DashboardCollaboratorRoleV2


class DashboardCollaboratorUpdateRequestV2(StrictDashboardBackendModel):
    role: DashboardCollaboratorRoleV2
    expected_lock_version: int = Field(ge=1)


class DashboardAccessPolicyV2(StrictDashboardBackendModel):
    minimum_role: Literal["CONSULTA", "GESTOR", "ADMIN"] = "CONSULTA"
    capabilities: tuple[DashboardCapabilityBackendV2, ...] = Field(default=(), max_length=15)
    classification_ceiling: str = Field(min_length=3, max_length=64)
    allow_partial_runtime: bool = True


class DashboardLifecyclePolicyV2(StrictDashboardBackendModel):
    current: DashboardLifecycleV2
    permitted_transitions: tuple[DashboardLifecycleV2, ...]
    runtime_eligible: bool


class DashboardRecordV2(StrictDashboardBackendModel):
    contract_version: Literal["lumina.dashboard-backend/1.0"] = DASHBOARD_BACKEND_CONTRACT_VERSION
    identity: DashboardIdentityRecordV2
    ownership: DashboardOwnershipV2
    lifecycle: DashboardLifecycleV2
    head_lifecycle: DashboardLifecycleV2
    origin: DashboardOriginV2
    classification: str = Field(min_length=3, max_length=64)
    head_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    active_publication_id: str | None = Field(default=None, pattern=ID_PATTERN)
    lock_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class DashboardCreateRequestV2(StrictDashboardBackendModel):
    canonical_name: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=8, max_length=1_000)
    blueprint: DashboardBlueprintV2
    origin: DashboardOriginV2 = DashboardOriginV2.HUMAN_AUTHORED
    reason: str = Field(min_length=3, max_length=500)


class DashboardCreateResultV2(StrictDashboardBackendModel):
    dashboard: DashboardRecordV2
    revision: "DashboardRevisionV2"
    replayed: bool = False


class DashboardUpdateDraftRequestV2(StrictDashboardBackendModel):
    expected_lock_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=8, max_length=1_000)
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def require_change(self) -> "DashboardUpdateDraftRequestV2":
        if self.title is None and self.description is None:
            raise ValueError("at least one metadata field must change")
        return self


class DashboardRevisionReferenceV2(StrictDashboardBackendModel):
    revision_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    blueprint_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    semantic_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    visual_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardVisualRevisionV2(StrictDashboardBackendModel):
    number: int = Field(ge=1)
    checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardSemanticRevisionV2(StrictDashboardBackendModel):
    number: int = Field(ge=1)
    checksum: str = Field(pattern=CHECKSUM_PATTERN)
    validation_status: Literal["VALID", "BLOCKED"]


class DashboardRevisionV2(StrictDashboardBackendModel):
    contract_version: Literal["lumina.dashboard-backend/1.0"] = DASHBOARD_BACKEND_CONTRACT_VERSION
    revision_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    parent_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    blueprint_contract_version: Literal["lumina.dashboard-blueprint/2.0"]
    blueprint_version: str = Field(min_length=5, max_length=32)
    semantic: DashboardSemanticRevisionV2
    visual: DashboardVisualRevisionV2
    blueprint: DashboardBlueprintV2
    blueprint_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    validation_reference: str = Field(min_length=3, max_length=160)
    author_reference: str = Field(pattern=ID_PATTERN)
    created_at: datetime
    reason: str = Field(min_length=3, max_length=500)
    origin: DashboardOriginV2
    lock_version: int = Field(ge=1)


class DashboardRevisionCreateRequestV2(StrictDashboardBackendModel):
    blueprint: DashboardBlueprintV2
    base_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    expected_dashboard_lock_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class DashboardVisualPatchRequestV2(StrictDashboardBackendModel):
    patch: DashboardVisualPatchV2
    expected_dashboard_lock_version: int = Field(ge=1)
    expected_revision_lock_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class DashboardSemanticPatchRequestV2(StrictDashboardBackendModel):
    patch: DashboardSemanticPatchV2
    expected_dashboard_lock_version: int = Field(ge=1)
    expected_revision_lock_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class DashboardReviewRequestV2(StrictDashboardBackendModel):
    action: Literal["SUBMITTED", "CHANGES_REQUESTED"] = "SUBMITTED"
    revision_id: str = Field(pattern=ID_PATTERN)
    expected_dashboard_lock_version: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=1_000)


class DashboardReviewDecisionV2(StrictDashboardBackendModel):
    decision: DashboardReviewDecisionKindV2
    revision_id: str = Field(pattern=ID_PATTERN)
    expected_dashboard_lock_version: int = Field(ge=1)
    comment: str = Field(min_length=3, max_length=1_000)


class DashboardApprovalV2(StrictDashboardBackendModel):
    approval_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    revision: DashboardRevisionReferenceV2
    approved_by: str = Field(pattern=ID_PATTERN)
    approved_at: datetime


class DashboardPublicationV2(StrictDashboardBackendModel):
    publication_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    revision: DashboardRevisionReferenceV2
    publication_version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    generation: int = Field(ge=1)
    status: Literal["PUBLISHED", "SUPERSEDED"]
    supersedes_publication_id: str | None = Field(default=None, pattern=ID_PATTERN)
    published_by: str = Field(pattern=ID_PATTERN)
    published_at: datetime


class DashboardPublicationRequestV2(StrictDashboardBackendModel):
    revision_id: str = Field(pattern=ID_PATTERN)
    expected_dashboard_lock_version: int = Field(ge=1)
    expected_active_generation: int = Field(ge=0)
    publication_version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    confirmation: Literal["PUBLISH_APPROVED_REVISION"]


class DashboardPublicationResultV2(StrictDashboardBackendModel):
    publication: DashboardPublicationV2
    superseded_publication_id: str | None = Field(default=None, pattern=ID_PATTERN)
    replayed: bool = False


class DashboardSupersessionV2(StrictDashboardBackendModel):
    previous_publication_id: str = Field(pattern=ID_PATTERN)
    replacement_publication_id: str = Field(pattern=ID_PATTERN)
    generation: int = Field(ge=2)
    occurred_at: datetime


class DashboardRollbackRequestV2(StrictDashboardBackendModel):
    target_publication_id: str = Field(pattern=ID_PATTERN)
    expected_dashboard_lock_version: int = Field(ge=1)
    expected_active_generation: int = Field(ge=1)
    publication_version: str = Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    confirmation: Literal["CREATE_ROLLBACK_PUBLICATION"]
    reason: str = Field(min_length=3, max_length=500)


class DashboardRollbackResultV2(StrictDashboardBackendModel):
    publication: DashboardPublicationV2
    source_publication_id: str = Field(pattern=ID_PATTERN)
    superseded_publication_id: str = Field(pattern=ID_PATTERN)
    replayed: bool = False


class DashboardArchiveRequestV2(StrictDashboardBackendModel):
    expected_dashboard_lock_version: int = Field(ge=1)
    confirmation: Literal["ARCHIVE_DASHBOARD"]
    reason: str = Field(min_length=3, max_length=500)


class DashboardCloneRequestV2(StrictDashboardBackendModel):
    canonical_name: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=8, max_length=1_000)
    source_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    reason: str = Field(min_length=3, max_length=500)


class DashboardListRequestV2(StrictDashboardBackendModel):
    lifecycle: DashboardLifecycleV2 | None = None
    cursor: str | None = Field(default=None, max_length=256)
    limit: int = Field(default=50, ge=1, le=100)


class DashboardListItemV2(StrictDashboardBackendModel):
    dashboard: DashboardRecordV2
    effective_capabilities: tuple[DashboardCapabilityBackendV2, ...]


class DashboardDetailV2(StrictDashboardBackendModel):
    dashboard: DashboardRecordV2
    head_revision: DashboardRevisionV2 | None
    active_publication: DashboardPublicationV2 | None
    collaborators: tuple[DashboardCollaboratorV2, ...] = ()
    effective_capabilities: tuple[DashboardCapabilityBackendV2, ...] = ()


class DashboardRuntimeFilterValueV2(StrictDashboardBackendModel):
    filter_id: str = Field(pattern=ID_PATTERN)
    values: tuple[str | int | Decimal | bool, ...] = Field(min_length=1, max_length=100)


class DashboardRuntimeInteractionV2(StrictDashboardBackendModel):
    interaction_id: str = Field(pattern=ID_PATTERN)
    action: Literal["CROSS_FILTER", "DRILLDOWN", "RESET", "SORTING", "PAGINATION", "PROVENANCE", "EXPAND"]
    source_widget_id: str = Field(pattern=ID_PATTERN)
    target_widget_id: str | None = Field(default=None, pattern=ID_PATTERN)


class DashboardRuntimeRequestV2(StrictDashboardBackendModel):
    publication_id: str | None = Field(default=None, pattern=ID_PATTERN)
    blueprint_checksum: str | None = Field(default=None, pattern=CHECKSUM_PATTERN)
    filters: tuple[DashboardRuntimeFilterValueV2, ...] = Field(default=(), max_length=32)
    interactions: tuple[DashboardRuntimeInteractionV2, ...] = Field(default=(), max_length=64)
    requested_widget_ids: tuple[str, ...] = Field(default=(), max_length=64)
    deadline_ms: int = Field(default=15_000, ge=100, le=60_000)
    allow_partial: bool = True


class DashboardEffectiveFilterV2(StrictDashboardBackendModel):
    filter_id: str = Field(pattern=ID_PATTERN)
    canonical_target_id: str = Field(pattern=ID_PATTERN)
    canonical_values: tuple[str, ...] = Field(min_length=1, max_length=100)


class DashboardWidgetRuntimePlanV2(StrictDashboardBackendModel):
    widget_id: str = Field(pattern=ID_PATTERN)
    binding_id: str = Field(pattern=ID_PATTERN)
    analytical_dataset_id: str = Field(pattern=ID_PATTERN)
    widget_type: str = Field(min_length=3, max_length=64)
    expected_result_shape: str = Field(min_length=3, max_length=64)
    metric_ids: tuple[str, ...] = Field(default=(), max_length=12)
    dimension_ids: tuple[str, ...] = Field(default=(), max_length=12)
    entity_ids: tuple[str, ...] = Field(default=(), max_length=100)
    canonical_period: JsonValue
    comparison: JsonValue | None = None
    effective_filters: tuple[DashboardEffectiveFilterV2, ...] = ()
    completeness: str = Field(min_length=3, max_length=64)
    freshness: str = Field(min_length=3, max_length=64)
    classification_ceiling: str = Field(min_length=3, max_length=64)
    permission_scope: str = Field(min_length=3, max_length=128)
    cache_preference: str = Field(min_length=3, max_length=64)
    materialization_preference: str = Field(min_length=3, max_length=64)
    execution_group: str = Field(pattern=ID_PATTERN)
    analytical_cache_fingerprint: str = Field(pattern=CHECKSUM_PATTERN)
    plan_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardRuntimePlanV2(StrictDashboardBackendModel):
    dashboard_id: str = Field(pattern=ID_PATTERN)
    publication_id: str = Field(pattern=ID_PATTERN)
    revision_id: str = Field(pattern=ID_PATTERN)
    blueprint_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    tenant_reference: str = Field(pattern=ID_PATTERN)
    user_access_scope: str = Field(min_length=3, max_length=128)
    effective_filters: tuple[DashboardEffectiveFilterV2, ...] = ()
    effective_period: JsonValue | None = None
    widget_plans: tuple[DashboardWidgetRuntimePlanV2, ...] = Field(max_length=64)
    execution_groups: tuple[str, ...] = Field(max_length=64)
    cache_decisions: tuple[str, ...] = Field(max_length=64)
    dependencies: tuple[str, ...] = Field(max_length=128)
    deadline_at: datetime
    maximum_widgets: int = Field(ge=1, le=64)
    maximum_result_size: int = Field(ge=1, le=100_000)
    provenance_required: bool = True
    plan_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardRuntimeWarningV2(StrictDashboardBackendModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    message: str = Field(min_length=3, max_length=500)
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    widget_id: str | None = Field(default=None, pattern=ID_PATTERN)


class DashboardRuntimeProvenanceV2(StrictDashboardBackendModel):
    publication_id: str = Field(pattern=ID_PATTERN)
    blueprint_version: str = Field(min_length=5, max_length=32)
    revision_id: str = Field(pattern=ID_PATTERN)
    binding_id: str | None = Field(default=None, pattern=ID_PATTERN)
    effective_filters: tuple[DashboardEffectiveFilterV2, ...] = ()
    period_summary: str | None = Field(default=None, max_length=240)
    metric_definition_references: tuple[str, ...] = Field(default=(), max_length=12)
    validation_status: Literal["CERTIFIED", "PARTIAL", "BLOCKED"]
    source_freshness: str = Field(min_length=3, max_length=120)
    cache_indicator: DashboardCacheIndicatorV2
    warnings: tuple[DashboardRuntimeWarningV2, ...] = ()


class DashboardScalarDataV2(StrictDashboardBackendModel):
    data_type: Literal["SCALAR"] = "SCALAR"
    value: Decimal
    unit: str = Field(min_length=1, max_length=32)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class DashboardTabularCellV2(StrictDashboardBackendModel):
    column_id: str = Field(pattern=ID_PATTERN)
    text_value: str | None = Field(default=None, max_length=500)
    decimal_value: Decimal | None = None
    unit: str | None = Field(default=None, max_length=32)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class DashboardTabularRowV2(StrictDashboardBackendModel):
    cells: tuple[DashboardTabularCellV2, ...] = Field(min_length=1, max_length=64)


class DashboardTabularDataV2(StrictDashboardBackendModel):
    data_type: Literal["TABULAR"] = "TABULAR"
    rows: tuple[DashboardTabularRowV2, ...] = Field(max_length=500)


DashboardTypedDataV2 = Annotated[DashboardScalarDataV2 | DashboardTabularDataV2, Field(discriminator="data_type")]


class DashboardWidgetRuntimeResultV2(StrictDashboardBackendModel):
    widget_id: str = Field(pattern=ID_PATTERN)
    binding_id: str = Field(pattern=ID_PATTERN)
    status: DashboardWidgetResultStatusV2
    expected_result_shape: str = Field(min_length=3, max_length=64)
    data: DashboardTypedDataV2 | None = None
    fact_references: tuple[str, ...] = Field(default=(), max_length=100)
    certification_reference: str | None = Field(default=None, max_length=160)
    provenance: DashboardRuntimeProvenanceV2
    completeness: str = Field(min_length=3, max_length=64)
    freshness: str = Field(min_length=3, max_length=64)
    truncated: bool = False
    partial: bool = False
    warnings: tuple[DashboardRuntimeWarningV2, ...] = ()
    cache_indicator: DashboardCacheIndicatorV2
    generated_at: datetime
    checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardRuntimeResultV2(StrictDashboardBackendModel):
    execution_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    publication_id: str = Field(pattern=ID_PATTERN)
    status: DashboardRuntimeStatusV2
    widgets: tuple[DashboardWidgetRuntimeResultV2, ...] = Field(max_length=64)
    provenance: DashboardRuntimeProvenanceV2
    warnings: tuple[DashboardRuntimeWarningV2, ...] = ()
    started_at: datetime
    completed_at: datetime
    checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAuditEventV2(StrictDashboardBackendModel):
    event_id: str = Field(pattern=ID_PATTERN)
    dashboard_id: str = Field(pattern=ID_PATTERN)
    event_type: str = Field(pattern=r"^DASHBOARD_[A-Z0-9_]{2,63}$")
    actor_reference: str = Field(pattern=ID_PATTERN)
    resource_reference: str | None = Field(default=None, pattern=ID_PATTERN)
    outcome: Literal["SUCCESS", "DENIED", "CONFLICT", "FAILED"]
    metadata_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    occurred_at: datetime


class DashboardEvaluationCaseV2(StrictDashboardBackendModel):
    case_id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=3, max_length=160)
    category: str = Field(min_length=3, max_length=64)
    fixture_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    expected_status: DashboardRuntimeStatusV2


class DashboardEvaluationResultV2(StrictDashboardBackendModel):
    result_id: str = Field(pattern=ID_PATTERN)
    case_id: str = Field(pattern=ID_PATTERN)
    passed: bool
    actual_status: DashboardRuntimeStatusV2
    evidence_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    executed_at: datetime


class DashboardBackupTableV2(StrictDashboardBackendModel):
    table_name: str = Field(pattern=r"^dashboard[a-z0-9_]+_v2$")
    row_count: int = Field(ge=0)
    content_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardBackupManifestV2(StrictDashboardBackendModel):
    contract_version: Literal["lumina.dashboard-backend/1.0"] = DASHBOARD_BACKEND_CONTRACT_VERSION
    backup_id: str = Field(pattern=ID_PATTERN)
    source: Literal["DISPOSABLE_POSTGRESQL"] = "DISPOSABLE_POSTGRESQL"
    sanitized: Literal[True] = True
    tables: tuple[DashboardBackupTableV2, ...] = Field(min_length=1, max_length=13)
    created_at: datetime
    checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardRestoreValidationV2(StrictDashboardBackendModel):
    backup_id: str = Field(pattern=ID_PATTERN)
    restored: bool
    row_counts_match: bool
    checksums_match: bool
    active_publication_valid: bool
    tenant_isolation_valid: bool
    constraints_valid: bool
    indexes_valid: bool
    validated_at: datetime
