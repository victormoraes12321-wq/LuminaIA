from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.analytical_v2 import (
    DimensionReference,
    EntityReference,
    ExecutionReadiness,
    MetricReference,
    QueryIntentV2,
    TimeWindow,
)


USER_ANALYTICAL_PROFILE_VERSION = "lumina.user-analytical-profile/1.0"


class StrictProfileModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class UserPreferenceType(str, Enum):
    PRESENTATION = "PRESENTATION"
    LOCALE = "LOCALE"
    ACCESSIBILITY = "ACCESSIBILITY"
    ANALYTICAL_DEFAULT = "ANALYTICAL_DEFAULT"
    FAVORITE_METRIC = "FAVORITE_METRIC"
    FAVORITE_DIMENSION = "FAVORITE_DIMENSION"
    FAVORITE_ENTITY = "FAVORITE_ENTITY"
    SAVED_FILTER_REFERENCE = "SAVED_FILTER_REFERENCE"
    SAVED_QUERY_REFERENCE = "SAVED_QUERY_REFERENCE"
    SAVED_DASHBOARD_REFERENCE = "SAVED_DASHBOARD_REFERENCE"
    INTERACTION = "INTERACTION"
    PRIVACY = "PRIVACY"
    RETENTION = "RETENTION"


class PreferenceRisk(str, Enum):
    SAFE_PRESENTATION = "SAFE_PRESENTATION"
    VISIBLE_ANALYTICAL_DEFAULT = "VISIBLE_ANALYTICAL_DEFAULT"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    RESTRICTED = "RESTRICTED"
    FORBIDDEN = "FORBIDDEN"


class PreferenceOrigin(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"
    ADMIN_POLICY = "ADMIN_POLICY"
    LEGACY_IMPORT = "LEGACY_IMPORT"
    MIGRATED = "MIGRATED"
    FEEDBACK_CANDIDATE = "FEEDBACK_CANDIDATE"
    INFERRED_UNCONFIRMED = "INFERRED_UNCONFIRMED"


class PreferenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    DELETED = "DELETED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"


class ProfileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETION_PENDING = "DELETION_PENDING"
    DELETED = "DELETED"


class ConsentStatus(str, Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    NOT_REQUIRED = "NOT_REQUIRED"
    MISSING = "MISSING"


class PreferenceDecision(str, Enum):
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"


class ProfilePermission(str, Enum):
    READ_OWN = "profile:read_own"
    UPDATE_OWN = "profile:update_own"
    EXPORT_OWN = "profile:export_own"
    DELETE_OWN = "profile:delete_own"
    MANAGE_POLICY = "profile:manage_policy"
    AUDIT_READ = "profile:audit_read"
    SUPPORT_READ_REDACTED = "profile:support_read_redacted"


class UserProfileRolloutMode(str, Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW = "SHADOW"
    V2_READ = "V2_READ"
    V2_READ_WRITE = "V2_READ_WRITE"


class ProfileAuditEventType(str, Enum):
    PROFILE_CREATED = "PROFILE_CREATED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PROFILE_DISABLED = "PROFILE_DISABLED"
    PROFILE_REACTIVATED = "PROFILE_REACTIVATED"
    PREFERENCE_CREATED = "PREFERENCE_CREATED"
    PREFERENCE_UPDATED = "PREFERENCE_UPDATED"
    PREFERENCE_DISABLED = "PREFERENCE_DISABLED"
    PREFERENCE_REACTIVATED = "PREFERENCE_REACTIVATED"
    PREFERENCE_REVOKED = "PREFERENCE_REVOKED"
    PREFERENCE_EXPIRED = "PREFERENCE_EXPIRED"
    PREFERENCE_DELETED = "PREFERENCE_DELETED"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    PREFERENCE_APPLIED = "PREFERENCE_APPLIED"
    PREFERENCE_SKIPPED = "PREFERENCE_SKIPPED"
    PREFERENCE_CONFLICT = "PREFERENCE_CONFLICT"
    EXPORT_REQUESTED = "EXPORT_REQUESTED"
    EXPORT_COMPLETED = "EXPORT_COMPLETED"
    DELETION_REQUESTED = "DELETION_REQUESTED"
    DELETION_COMPLETED = "DELETION_COMPLETED"
    IMPORT_DRY_RUN = "IMPORT_DRY_RUN"
    IMPORT_COMPLETED = "IMPORT_COMPLETED"
    ACCESS_DENIED = "ACCESS_DENIED"
    VERSION_CONFLICT = "VERSION_CONFLICT"


class PresentationPreferenceV2(StrictProfileModel):
    kind: Literal["PRESENTATION"] = "PRESENTATION"
    preferred_visualization: Literal[
        "AUTO", "TABLE", "BAR_CHART", "LINE_CHART", "PIE_CHART", "KPI_CARD"
    ] = "AUTO"
    table_first: bool = True
    table_density: Literal["COMPACT", "COMFORTABLE", "SPACIOUS"] = "COMFORTABLE"
    page_size: int = Field(default=25, ge=5, le=200)
    decimal_places: int = Field(default=2, ge=0, le=8)
    ordering: Literal["DEFAULT", "ASCENDING", "DESCENDING"] = "DEFAULT"
    chart_granularity: Literal["AUTO", "SUMMARY", "DETAILED"] = "AUTO"
    theme: Literal["SYSTEM", "LIGHT", "DARK"] = "SYSTEM"


class LocalePreferenceV2(StrictProfileModel):
    kind: Literal["LOCALE"] = "LOCALE"
    locale: str = Field(default="pt-BR", pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)
    currency_display: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    date_format: Literal["DD/MM/YYYY", "YYYY-MM-DD", "DD MMM YYYY"] = "DD/MM/YYYY"
    number_format: Literal["pt-BR", "en-US"] = "pt-BR"


class AccessibilityPreferenceV2(StrictProfileModel):
    kind: Literal["ACCESSIBILITY"] = "ACCESSIBILITY"
    reduced_motion: bool = False
    high_contrast: bool = False
    larger_text: bool = False
    accessible_labels: bool = True


class AnalyticalDefaultPreferenceV2(StrictProfileModel):
    kind: Literal["ANALYTICAL_DEFAULT"] = "ANALYTICAL_DEFAULT"
    target_field: Literal[
        "metric", "dimension", "entity", "filter", "period", "ordering", "limit"
    ]
    canonical_id: str = Field(min_length=1, max_length=128)
    display_label: str = Field(min_length=1, max_length=256)
    filter_field_id: str | None = Field(default=None, min_length=1, max_length=128)
    filter_operator: Literal["EQ", "IN"] | None = None
    filter_values: list[str | int | float | bool] = Field(default_factory=list, max_length=100)
    limit: int | None = Field(default=None, ge=1, le=1000)
    period_key: str | None = Field(default=None, min_length=1, max_length=64)
    knowledge_asset_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "AnalyticalDefaultPreferenceV2":
        if self.target_field == "filter":
            if not self.filter_field_id or not self.filter_operator or not self.filter_values:
                raise ValueError("filter default requires canonical field, operator and values")
        elif self.filter_field_id or self.filter_operator or self.filter_values:
            raise ValueError("filter fields are only accepted for filter defaults")
        if self.target_field == "limit" and self.limit is None:
            raise ValueError("limit default requires limit")
        if self.target_field != "limit" and self.limit is not None:
            raise ValueError("limit is only accepted for limit defaults")
        if self.target_field == "period" and self.period_key is None:
            raise ValueError("period default requires period_key")
        if self.target_field != "period" and self.period_key is not None:
            raise ValueError("period_key is only accepted for period defaults")
        return self


class FavoriteAssetPreferenceV2(StrictProfileModel):
    kind: Literal["FAVORITE_METRIC", "FAVORITE_DIMENSION", "FAVORITE_ENTITY"]
    canonical_id: str = Field(min_length=1, max_length=128)
    display_label: str = Field(min_length=1, max_length=256)
    knowledge_asset_id: uuid.UUID


class SavedReferencePreferenceV2(StrictProfileModel):
    kind: Literal[
        "SAVED_FILTER_REFERENCE",
        "SAVED_QUERY_REFERENCE",
        "SAVED_DASHBOARD_REFERENCE",
    ]
    reference_id: uuid.UUID
    reference_version: int = Field(ge=1)
    display_label: str = Field(min_length=1, max_length=256)
    canonical_scope: str = Field(min_length=1, max_length=128)


class InteractionPreferenceV2(StrictProfileModel):
    kind: Literal["INTERACTION"] = "INTERACTION"
    open_details_by_default: bool = False
    preserve_expanded_rows: bool = False
    confirmation_level: Literal["MINIMAL", "STANDARD", "STRICT"] = "STANDARD"


class PrivacyPreferenceV2(StrictProfileModel):
    kind: Literal["PRIVACY"] = "PRIVACY"
    profile_enabled: bool = True
    application_audit_enabled: bool = True
    allow_legacy_import: bool = False


class RetentionPreferenceV2(StrictProfileModel):
    kind: Literal["RETENTION"] = "RETENTION"
    expired_item_days: int = Field(default=90, ge=1, le=3650)
    export_days: int = Field(default=30, ge=1, le=365)
    deletion_request_days: int = Field(default=365, ge=30, le=3650)


UserPreferenceContentV2 = Annotated[
    PresentationPreferenceV2
    | LocalePreferenceV2
    | AccessibilityPreferenceV2
    | AnalyticalDefaultPreferenceV2
    | FavoriteAssetPreferenceV2
    | SavedReferencePreferenceV2
    | InteractionPreferenceV2
    | PrivacyPreferenceV2
    | RetentionPreferenceV2,
    Field(discriminator="kind"),
]


class PreferenceOriginV2(StrictProfileModel):
    kind: PreferenceOrigin
    source_label: str = Field(min_length=1, max_length=128)
    source_reference: str | None = Field(default=None, max_length=256)
    confirmed_at: datetime | None = None


class PreferenceConsentV2(StrictProfileModel):
    consent_id: uuid.UUID
    preference_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    purpose: str = Field(min_length=1, max_length=256)
    scope: str = Field(min_length=1, max_length=128)
    status: ConsentStatus
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    policy_version: str = Field(min_length=1, max_length=64)
    source: Literal["USER_ACTION", "SYSTEM_PRESENTATION_SETTING"]
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_timestamps(self) -> "PreferenceConsentV2":
        if self.status == ConsentStatus.GRANTED and self.granted_at is None:
            raise ValueError("granted consent requires granted_at")
        if self.status == ConsentStatus.REVOKED and self.revoked_at is None:
            raise ValueError("revoked consent requires revoked_at")
        if self.revoked_at and self.granted_at and self.revoked_at < self.granted_at:
            raise ValueError("revoked_at cannot precede granted_at")
        return self


class UserPreferenceItemV2(StrictProfileModel):
    preference_id: uuid.UUID
    profile_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    preference_type: UserPreferenceType
    preference_key: str = Field(min_length=1, max_length=128)
    content: UserPreferenceContentV2
    risk: PreferenceRisk
    origin: PreferenceOriginV2
    status: PreferenceStatus
    consent: PreferenceConsentV2 | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    expires_at: datetime | None = None
    version: int = Field(ge=1)
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION

    @model_validator(mode="after")
    def validate_item(self) -> "UserPreferenceItemV2":
        if self.schema_version != USER_ANALYTICAL_PROFILE_VERSION:
            raise ValueError("unsupported user profile contract version")
        if self.content.kind != self.preference_type.value:
            raise ValueError("preference type must match discriminated content kind")
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be later than effective_from")
        if self.status == PreferenceStatus.DELETED and self.deleted_at is None:
            raise ValueError("deleted preference requires deleted_at")
        if self.status != PreferenceStatus.DELETED and self.deleted_at is not None:
            raise ValueError("only deleted preference can have deleted_at")
        return self


class UserAnalyticalProfileV2(StrictProfileModel):
    profile_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    status: ProfileStatus
    profile_version: int = Field(ge=1)
    lock_version: int = Field(ge=0)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    preferences: list[UserPreferenceItemV2] = Field(default_factory=list, max_length=500)
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None
    deleted_at: datetime | None = None
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION

    @model_validator(mode="after")
    def validate_profile(self) -> "UserAnalyticalProfileV2":
        if self.schema_version != USER_ANALYTICAL_PROFILE_VERSION:
            raise ValueError("unsupported user profile contract version")
        if self.status == ProfileStatus.DISABLED and self.disabled_at is None:
            raise ValueError("disabled profile requires disabled_at")
        if self.status == ProfileStatus.DELETED and self.deleted_at is None:
            raise ValueError("deleted profile requires deleted_at")
        ids = [item.preference_id for item in self.preferences]
        if len(ids) != len(set(ids)):
            raise ValueError("profile preference IDs must be unique")
        if any(
            item.profile_id != self.profile_id
            or item.tenant_id != self.tenant_id
            or item.user_id != self.user_id
            for item in self.preferences
        ):
            raise ValueError("profile preferences must belong to the same tenant and user")
        return self


class UserAnalyticalProfileSummaryV2(StrictProfileModel):
    profile_id: uuid.UUID
    status: ProfileStatus
    profile_version: int = Field(ge=1)
    active_preferences: int = Field(ge=0)
    disabled_preferences: int = Field(ge=0)
    pending_confirmation: int = Field(ge=0)
    active_consents: int = Field(ge=0)
    categories: list[UserPreferenceType] = Field(default_factory=list)
    updated_at: datetime
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class PreferenceConflictV2(StrictProfileModel):
    preference_id: uuid.UUID
    field_path: str = Field(min_length=1, max_length=128)
    reason_code: str = Field(min_length=1, max_length=100)
    public_message: str = Field(min_length=1, max_length=500)
    blocks_application: bool


class PublicAppliedPreferenceItemV2(StrictProfileModel):
    preference_type: UserPreferenceType
    label: str = Field(min_length=1, max_length=256)
    value_label: str = Field(min_length=1, max_length=256)
    origin_label: str = Field(min_length=1, max_length=128)
    removable_this_turn: bool = True
    settings_path: str = "/dashboard/settings/profile"
    expires_at: datetime | None = None


class PublicAppliedPreferenceSummaryV2(StrictProfileModel):
    applied: list[PublicAppliedPreferenceItemV2] = Field(default_factory=list, max_length=50)
    ignored: list[str] = Field(default_factory=list, max_length=50)
    consent_required: list[str] = Field(default_factory=list, max_length=50)
    has_visible_analytical_default: bool = False
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class PreferenceApplicationDecisionV2(StrictProfileModel):
    preference_id: uuid.UUID
    preference_key: str
    field_path: str
    decision: PreferenceDecision
    reason_code: str
    risk: PreferenceRisk
    origin: PreferenceOrigin
    consent_status: ConsentStatus
    visible_to_user: bool


class PreferenceApplicationResultV2(StrictProfileModel):
    resolved_intent: QueryIntentV2
    readiness: ExecutionReadiness
    decisions: list[PreferenceApplicationDecisionV2] = Field(default_factory=list)
    conflicts: list[PreferenceConflictV2] = Field(default_factory=list)
    public_summary: PublicAppliedPreferenceSummaryV2
    applied_preference_ids: list[uuid.UUID] = Field(default_factory=list)
    profile_version: int = Field(ge=1)
    deterministic_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    shadow_only: bool = False
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class PreferenceAuditEventV2(StrictProfileModel):
    event_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    profile_id: uuid.UUID
    preference_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID
    event_type: ProfileAuditEventType
    reason_code: str
    request_id: str | None = Field(default=None, max_length=128)
    metadata_keys: list[str] = Field(default_factory=list, max_length=30)
    created_at: datetime
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class ProfileExportV2(StrictProfileModel):
    export_id: uuid.UUID
    profile: UserAnalyticalProfileV2
    consent_count: int = Field(ge=0)
    generated_at: datetime
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    format: Literal["JSON"] = "JSON"
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class ProfileDeletionRequestV2(StrictProfileModel):
    request_id: uuid.UUID
    profile_id: uuid.UUID
    status: Literal["PENDING", "COMPLETED", "REJECTED"]
    requested_at: datetime
    completed_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)
    idempotency_key_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class ProfileAccessDecisionV2(StrictProfileModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    permission: ProfilePermission
    allowed: bool
    redacted: bool = False
    reason_code: str
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class ProfilePatchV2(StrictProfileModel):
    expected_profile_lock_version: int = Field(ge=0)
    status: Literal["ACTIVE", "DISABLED"] | None = None


class PreferenceCreateV2(StrictProfileModel):
    preference_key: str = Field(min_length=1, max_length=128)
    content: UserPreferenceContentV2
    origin: PreferenceOrigin = PreferenceOrigin.USER_EXPLICIT
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    expires_at: datetime | None = None


class PreferenceUpdateV2(StrictProfileModel):
    expected_lock_version: int = Field(ge=0)
    content: UserPreferenceContentV2
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    expires_at: datetime | None = None


class ConsentGrantV2(StrictProfileModel):
    expected_preference_lock_version: int = Field(ge=0)
    purpose: str = Field(min_length=1, max_length=256)
    scope: str = Field(min_length=1, max_length=128)
    policy_version: str = Field(default="user-profile-consent/1.0", min_length=1, max_length=64)


class ConsentRevokeV2(StrictProfileModel):
    expected_lock_version: int = Field(ge=0)


class ProfileImportV2(StrictProfileModel):
    profile: UserAnalyticalProfileV2
    confirm: bool = False


class ProfileImportResultV2(StrictProfileModel):
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    dry_run: bool
    source_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION


class PreferenceApplicationContext(StrictProfileModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    request_id: str = Field(min_length=1, max_length=128)
    reference_datetime: datetime
    current_question: str = Field(min_length=1, max_length=1000)
    reset_explicit: bool = False
    removal_fields: list[str] = Field(default_factory=list, max_length=50)
    pending_clarification: bool = False
    allowed_canonical_ids: list[str] = Field(default_factory=list, max_length=1000)
    allowed_filter_fields: list[str] = Field(default_factory=list, max_length=500)
    governed_metric_refs: list[MetricReference] = Field(default_factory=list, max_length=200)
    governed_dimension_refs: list[DimensionReference] = Field(default_factory=list, max_length=200)
    governed_entity_refs: list[EntityReference] = Field(default_factory=list, max_length=200)
    governed_time_windows: list[TimeWindow] = Field(default_factory=list, max_length=100)
    rollout_mode: UserProfileRolloutMode = UserProfileRolloutMode.LEGACY_ONLY


class RetentionSelectionV2(StrictProfileModel):
    expired_preference_ids: list[uuid.UUID] = Field(default_factory=list)
    stale_export_ids: list[uuid.UUID] = Field(default_factory=list)
    stale_deletion_request_ids: list[uuid.UUID] = Field(default_factory=list)
    evaluated_at: datetime
    schema_version: str = USER_ANALYTICAL_PROFILE_VERSION
