"""Identity, lifecycle, governance, and compatibility contracts for Dashboard Blueprint V2."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DASHBOARD_BLUEPRINT_CONTRACT_ID = "lumina.dashboard-blueprint"
DASHBOARD_BLUEPRINT_CONTRACT_VERSION = "lumina.dashboard-blueprint/2.0"
CANONICAL_ID_PATTERN = r"^[a-z][a-z0-9_.:-]{2,127}$"
SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"


class StrictDashboardModel(BaseModel):
    """Fail-closed base for every public Prompt 19 contract."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


class DashboardLifecycleV2(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"


class DashboardOriginV2(str, Enum):
    HUMAN_AUTHORED = "HUMAN_AUTHORED"
    TEMPLATE = "TEMPLATE"
    MIGRATED_LEGACY = "MIGRATED_LEGACY"
    AI_PROPOSED = "AI_PROPOSED"
    AI_ASSISTED = "AI_ASSISTED"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"


class DashboardClassificationV2(str, Enum):
    PUBLIC_METADATA = "PUBLIC_METADATA"
    TENANT_METADATA = "TENANT_METADATA"
    TENANT_BUSINESS_DATA = "TENANT_BUSINESS_DATA"
    RESTRICTED_BUSINESS_DATA = "RESTRICTED_BUSINESS_DATA"
    PERSONAL_DATA = "PERSONAL_DATA"
    SENSITIVE_PERSONAL_DATA = "SENSITIVE_PERSONAL_DATA"
    SECRET = "SECRET"
    FORBIDDEN = "FORBIDDEN"


class DashboardCapabilityV2(str, Enum):
    VIEW = "dashboard:view"
    FILTER = "dashboard:filter"
    DRILLDOWN = "dashboard:drilldown"
    EXPORT = "dashboard:export"
    EDIT_VISUAL = "dashboard:edit_visual"
    EDIT_SEMANTIC = "dashboard:edit_semantic"
    REVIEW = "dashboard:review"
    PUBLISH = "dashboard:publish"
    ARCHIVE = "dashboard:archive"
    VIEW_PROVENANCE = "dashboard:view_provenance"


class DashboardRevisionV2(StrictDashboardModel):
    visual_revision: int = Field(default=1, ge=1, le=1_000_000)
    semantic_revision: int = Field(default=1, ge=1, le=1_000_000)


class DashboardVersionV2(StrictDashboardModel):
    contract_id: Literal["lumina.dashboard-blueprint"] = DASHBOARD_BLUEPRINT_CONTRACT_ID
    contract_version: Literal["lumina.dashboard-blueprint/2.0"] = (
        DASHBOARD_BLUEPRINT_CONTRACT_VERSION
    )
    blueprint_version: str = Field(default="1.0.0", pattern=SEMVER_PATTERN)
    revision: DashboardRevisionV2 = Field(default_factory=DashboardRevisionV2)
    publication_version: str | None = Field(default=None, pattern=SEMVER_PATTERN)


class DashboardIdentityV2(StrictDashboardModel):
    blueprint_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    canonical_name: str = Field(pattern=CANONICAL_ID_PATTERN)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=8, max_length=1_000)
    locale: Literal["pt-BR"] = "pt-BR"
    timezone_policy: Literal[
        "TENANT_AUTHORITY",
        "USER_THEN_TENANT",
        "APPLICATION_DEFAULT",
    ] = "TENANT_AUTHORITY"


class DashboardPurposeV2(StrictDashboardModel):
    purpose_id: str = Field(pattern=CANONICAL_ID_PATTERN)
    summary: str = Field(min_length=8, max_length=500)
    analytical_domains: tuple[str, ...] = Field(min_length=1, max_length=12)
    intended_decisions: tuple[str, ...] = Field(default=(), max_length=20)


class DashboardAudienceV2(StrictDashboardModel):
    audience_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    minimum_role: Literal["CONSULTA", "GESTOR", "ADMIN"] = "CONSULTA"


class DashboardPermissionRequirementV2(StrictDashboardModel):
    capability: DashboardCapabilityV2
    required: bool = True
    reason: str = Field(min_length=3, max_length=240)


class DashboardGovernanceV2(StrictDashboardModel):
    classification: DashboardClassificationV2 = (
        DashboardClassificationV2.TENANT_BUSINESS_DATA
    )
    contains_personal_data: bool = False
    template_eligible: bool = True
    permissions: tuple[DashboardPermissionRequirementV2, ...] = Field(
        default_factory=lambda: (
            DashboardPermissionRequirementV2(
                capability=DashboardCapabilityV2.VIEW,
                reason="Visualização do dashboard",
            ),
        ),
        min_length=1,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_classification(self) -> "DashboardGovernanceV2":
        if self.classification in {
            DashboardClassificationV2.SECRET,
            DashboardClassificationV2.FORBIDDEN,
        }:
            raise ValueError("SECRET and FORBIDDEN dashboards are not contractually allowed")
        if self.contains_personal_data and self.template_eligible:
            raise ValueError("dashboards containing personal data cannot be default templates")
        capabilities = [permission.capability for permission in self.permissions]
        if len(capabilities) != len(set(capabilities)):
            raise ValueError("permission requirements must be unique by capability")
        return self


class DashboardCompatibilityV2(StrictDashboardModel):
    minimum_contract_version: Literal["2.0"] = "2.0"
    maximum_contract_version_exclusive: Literal["3.0"] = "3.0"
    required_features: tuple[str, ...] = Field(default=(), max_length=32)
    deprecated_features: tuple[str, ...] = Field(default=(), max_length=32)


class DashboardBlueprintExecutionContextV2(StrictDashboardModel):
    """Future server-controlled envelope. It is never embedded in a blueprint."""

    authority: Literal["TRUSTED_BACKEND"] = "TRUSTED_BACKEND"
    tenant_id: str = Field(min_length=3, max_length=128)
    user_id: str = Field(min_length=3, max_length=128)
    roles: tuple[Literal["CONSULTA", "GESTOR", "ADMIN"], ...] = Field(
        min_length=1, max_length=3
    )
    permissions: tuple[DashboardCapabilityV2, ...] = Field(default=(), max_length=10)
    classification_ceiling: DashboardClassificationV2

