"""Typed validation, canonicalization, and evaluation results."""
from __future__ import annotations

from enum import Enum

from pydantic import Field, JsonValue

from .identity import StrictDashboardModel


class DashboardValidationStageV2(str, Enum):
    CONTRACT = "CONTRACT"
    IDENTITY = "IDENTITY"
    VERSION = "VERSION"
    LIFECYCLE = "LIFECYCLE"
    SECURITY = "SECURITY"
    CLASSIFICATION = "CLASSIFICATION"
    PERMISSIONS = "PERMISSIONS"
    LAYOUT = "LAYOUT"
    WIDGETS = "WIDGETS"
    DATA_BINDINGS = "DATA_BINDINGS"
    FILTERS = "FILTERS"
    INTERACTIONS = "INTERACTIONS"
    FORMATTING = "FORMATTING"
    ACCESSIBILITY = "ACCESSIBILITY"
    PROVENANCE = "PROVENANCE"
    COMPATIBILITY = "COMPATIBILITY"
    CANONICALIZATION = "CANONICALIZATION"


class DashboardValidationStatusV2(str, Enum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"


class DashboardValidationSeverityV2(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DashboardValidationIssueV2(StrictDashboardModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,79}$")
    stage: DashboardValidationStageV2
    severity: DashboardValidationSeverityV2
    message: str = Field(min_length=3, max_length=500)
    field_path: str | None = Field(default=None, max_length=240)
    blocking: bool = False


class DashboardChecksumSetV2(StrictDashboardModel):
    blueprint_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    semantic_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    visual_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    layout_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    widgets_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    bindings_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    filters_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    interactions_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    accessibility_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class DashboardCanonicalizationResultV2(StrictDashboardModel):
    contract_version: str = "lumina.dashboard-blueprint/2.0"
    canonical_json: str = Field(min_length=2, max_length=1_000_000)
    checksums: DashboardChecksumSetV2


class DashboardValidationResultV2(StrictDashboardModel):
    status: DashboardValidationStatusV2
    issues: tuple[DashboardValidationIssueV2, ...] = Field(default=(), max_length=256)
    completed_stages: tuple[DashboardValidationStageV2, ...] = Field(default=(), max_length=17)
    canonicalization: DashboardCanonicalizationResultV2 | None = None


class DashboardEvaluationCaseV2(StrictDashboardModel):
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_.:-]{2,127}$")
    description: str = Field(min_length=4, max_length=300)
    payload: JsonValue
    expected_status: DashboardValidationStatusV2


class DashboardEvaluationResultV2(StrictDashboardModel):
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_.:-]{2,127}$")
    actual_status: DashboardValidationStatusV2
    passed: bool
    issue_codes: tuple[str, ...] = Field(default=(), max_length=64)

