"""Deterministic, fail-closed Dashboard Blueprint V2 validation pipeline."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from contracts.dashboard_blueprint_v2 import (
    DASHBOARD_BLUEPRINT_CONTRACT_VERSION,
    DashboardBlueprintV2,
    DashboardClassificationV2,
    DashboardSemanticPatchV2,
    DashboardValidationIssueV2,
    DashboardValidationResultV2,
    DashboardValidationSeverityV2,
    DashboardValidationStageV2,
    DashboardValidationStatusV2,
    DashboardVisualPatchV2,
)
from contracts.dashboard_blueprint_v2.interactions import DashboardCrossFilterV2
from contracts.dashboard_blueprint_v2.widgets import (
    DashboardChartWidgetBaseV2,
    DashboardPieChartWidgetV2,
    DashboardTableWidgetV2,
)

from .canonicalizer import DashboardBlueprintCanonicalizer
from .compatibility import DashboardBlueprintCompatibilityService
from .registries import FEATURE_REGISTRY, WIDGET_REGISTRY


MAX_PAYLOAD_BYTES = 1_000_000
MAX_JSON_DEPTH = 20
_BLOCKED_TEXT_PATTERNS = (
    re.compile(r"<\s*(?:script|iframe|object|embed|style)\b", re.IGNORECASE),
    re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE),
    re.compile(r"(?:javascript|data\s*:\s*text/html)\s*:", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"(?:postgres(?:ql)?|oracle|mysql|mssql)://", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:select\s+.+\s+from|insert\s+into|update\s+.+\s+set|delete\s+from|drop\s+(?:table|database|schema)|alter\s+table)\b", re.IGNORECASE),
    re.compile(r"(?:--|/\*|\*/|;\s*(?:select|drop|insert|update|delete)\b)", re.IGNORECASE),
    re.compile(r"(?:\.{2}[\\/]|[A-Za-z]:\\|/etc/|/proc/)", re.IGNORECASE),
    re.compile(r"(?:\{\{|\}\}|\$\{|<%)"),
    re.compile(r"(?:^|\s)(?:import\s+[a-z_]|from\s+[a-z_.]+\s+import|eval\s*\(|exec\s*\()", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:rm\s+-rf|curl\s+|wget\s+|powershell\s+|cmd\.exe|/bin/sh)", re.IGNORECASE),
    re.compile(r"https?://", re.IGNORECASE),
)


def _issue(
    code: str,
    stage: DashboardValidationStageV2,
    severity: DashboardValidationSeverityV2,
    message: str,
    field_path: str | None = None,
    *,
    blocking: bool = False,
) -> DashboardValidationIssueV2:
    return DashboardValidationIssueV2(
        code=code,
        stage=stage,
        severity=severity,
        message=message,
        field_path=field_path,
        blocking=blocking,
    )


class DashboardValidator(ABC):
    stage: DashboardValidationStageV2

    @abstractmethod
    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        raise NotImplementedError


class DashboardContractValidator(DashboardValidator):
    stage = DashboardValidationStageV2.CONTRACT

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return ()


class DashboardIdentityValidator(DashboardValidator):
    stage = DashboardValidationStageV2.IDENTITY

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if blueprint.identity.blueprint_id == blueprint.identity.canonical_name:
            return ()
        return (
            _issue(
                "IDENTITY_NAMES_DISTINCT",
                self.stage,
                DashboardValidationSeverityV2.INFO,
                "blueprint ID and canonical name are intentionally distinct",
            ),
        )


class DashboardVersionValidator(DashboardValidator):
    stage = DashboardValidationStageV2.VERSION

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if blueprint.version.contract_version == DASHBOARD_BLUEPRINT_CONTRACT_VERSION:
            return ()
        return (
            _issue(
                "UNSUPPORTED_CONTRACT_VERSION",
                self.stage,
                DashboardValidationSeverityV2.CRITICAL,
                "dashboard contract major version is unsupported",
                blocking=True,
            ),
        )


class DashboardLifecycleValidator(DashboardValidator):
    stage = DashboardValidationStageV2.LIFECYCLE

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if blueprint.lifecycle.value in {"REJECTED", "ARCHIVED"}:
            return (
                _issue(
                    "LIFECYCLE_NOT_RUNTIME_AUTHORITY",
                    self.stage,
                    DashboardValidationSeverityV2.WARNING,
                    "this lifecycle state is not eligible for future runtime authority",
                ),
            )
        return ()


class DashboardSecurityValidator(DashboardValidator):
    stage = DashboardValidationStageV2.SECURITY

    @classmethod
    def validate_raw(cls, payload: object) -> tuple[DashboardValidationIssueV2, ...]:
        issues: list[DashboardValidationIssueV2] = []
        try:
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            return (
                _issue(
                    "PAYLOAD_NOT_JSON",
                    cls.stage,
                    DashboardValidationSeverityV2.CRITICAL,
                    "dashboard payload must be finite JSON",
                    blocking=True,
                ),
            )
        if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            issues.append(
                _issue(
                    "PAYLOAD_TOO_LARGE",
                    cls.stage,
                    DashboardValidationSeverityV2.CRITICAL,
                    "dashboard payload exceeds the governed size limit",
                    blocking=True,
                )
            )

        def walk(value: object, path: str, depth: int) -> None:
            if depth > MAX_JSON_DEPTH:
                issues.append(
                    _issue(
                        "PAYLOAD_TOO_DEEP",
                        cls.stage,
                        DashboardValidationSeverityV2.CRITICAL,
                        "dashboard payload exceeds the governed nesting depth",
                        path,
                        blocking=True,
                    )
                )
                return
            if isinstance(value, str):
                if "\x00" in value or any(ord(char) < 32 and char not in "\n\r\t" for char in value):
                    issues.append(
                        _issue(
                            "CONTROL_CHARACTER_BLOCKED",
                            cls.stage,
                            DashboardValidationSeverityV2.CRITICAL,
                            "control characters are prohibited",
                            path,
                            blocking=True,
                        )
                    )
                if any(pattern.search(value) for pattern in _BLOCKED_TEXT_PATTERNS):
                    issues.append(
                        _issue(
                            "EXECUTABLE_OR_UNSAFE_CONTENT",
                            cls.stage,
                            DashboardValidationSeverityV2.CRITICAL,
                            "executable, query, external URL, or unsafe content is prohibited",
                            path,
                            blocking=True,
                        )
                    )
            elif isinstance(value, Mapping):
                for key, item in value.items():
                    walk(item, f"{path}/{key}", depth + 1)
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                for index, item in enumerate(value):
                    walk(item, f"{path}/{index}", depth + 1)

        walk(payload, "", 0)
        unique = {(issue.code, issue.field_path): issue for issue in issues}
        return tuple(unique.values())

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return self.validate_raw(blueprint.model_dump(mode="json", exclude_none=True))


class DashboardClassificationValidator(DashboardValidator):
    stage = DashboardValidationStageV2.CLASSIFICATION

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if blueprint.governance.classification in {
            DashboardClassificationV2.SECRET,
            DashboardClassificationV2.FORBIDDEN,
        }:
            return (
                _issue(
                    "CLASSIFICATION_BLOCKED",
                    self.stage,
                    DashboardValidationSeverityV2.CRITICAL,
                    "dashboard classification is prohibited",
                    blocking=True,
                ),
            )
        return ()


class DashboardPermissionValidator(DashboardValidator):
    stage = DashboardValidationStageV2.PERMISSIONS

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if all(permission.required for permission in blueprint.governance.permissions):
            return ()
        return (
            _issue(
                "OPTIONAL_PERMISSION_REQUIREMENT",
                self.stage,
                DashboardValidationSeverityV2.INFO,
                "optional capabilities are requirements only and never grants",
            ),
        )


class DashboardLayoutValidator(DashboardValidator):
    stage = DashboardValidationStageV2.LAYOUT

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return ()


class DashboardWidgetValidator(DashboardValidator):
    stage = DashboardValidationStageV2.WIDGETS

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        issues: list[DashboardValidationIssueV2] = []
        for widget in blueprint.widgets:
            entry = WIDGET_REGISTRY.get(widget.widget_type)
            if entry is None:
                issues.append(
                    _issue(
                        "WIDGET_UNSUPPORTED",
                        self.stage,
                        DashboardValidationSeverityV2.ERROR,
                        "widget type is not statically registered",
                        blocking=True,
                    )
                )
                continue
            if entry.binding_required and widget.binding_id is None:
                issues.append(
                    _issue(
                        "WIDGET_BINDING_REQUIRED",
                        self.stage,
                        DashboardValidationSeverityV2.ERROR,
                        "analytical widget requires a binding",
                        blocking=True,
                    )
                )
            if isinstance(widget, DashboardChartWidgetBaseV2) and len(widget.series) > entry.maximum_series:
                issues.append(
                    _issue(
                        "CHART_SERIES_LIMIT",
                        self.stage,
                        DashboardValidationSeverityV2.ERROR,
                        "chart exceeds registry series limit",
                        blocking=True,
                    )
                )
            if isinstance(widget, DashboardPieChartWidgetV2) and widget.maximum_points > widget.maximum_slices:
                issues.append(
                    _issue(
                        "PIE_CARDINALITY_REQUIRES_BACKEND_LIMIT",
                        self.stage,
                        DashboardValidationSeverityV2.WARNING,
                        "pie chart points must be limited by the certified backend result",
                    )
                )
            if isinstance(widget, DashboardTableWidgetV2) and widget.truncation_indicator != "REQUIRED":
                issues.append(
                    _issue(
                        "TABLE_TRUNCATION_HIDDEN",
                        self.stage,
                        DashboardValidationSeverityV2.ERROR,
                        "table truncation indicator is mandatory",
                        blocking=True,
                    )
                )
        return tuple(issues)


class DashboardBindingValidator(DashboardValidator):
    stage = DashboardValidationStageV2.DATA_BINDINGS

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return ()


class DashboardFilterValidator(DashboardValidator):
    stage = DashboardValidationStageV2.FILTERS

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return ()


class DashboardInteractionValidator(DashboardValidator):
    stage = DashboardValidationStageV2.INTERACTIONS

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        cross_filters = [item for item in blueprint.interactions if isinstance(item, DashboardCrossFilterV2)]
        if len(cross_filters) > 64:
            return (
                _issue(
                    "CROSS_FILTER_LIMIT",
                    self.stage,
                    DashboardValidationSeverityV2.ERROR,
                    "cross-filter count exceeds governed limit",
                    blocking=True,
                ),
            )
        return ()


class DashboardFormattingValidator(DashboardValidator):
    stage = DashboardValidationStageV2.FORMATTING

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        return ()


class DashboardAccessibilityValidator(DashboardValidator):
    stage = DashboardValidationStageV2.ACCESSIBILITY

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if blueprint.accessibility.color_independent_status and blueprint.accessibility.textual_fallback_required:
            return ()
        return (
            _issue(
                "ACCESSIBILITY_MINIMUM_MISSING",
                self.stage,
                DashboardValidationSeverityV2.ERROR,
                "textual fallback and color-independent status are mandatory",
                blocking=True,
            ),
        )


class DashboardProvenanceValidator(DashboardValidator):
    stage = DashboardValidationStageV2.PROVENANCE

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        if all(binding.provenance.public_summary_required for binding in blueprint.data_bindings):
            return ()
        return (
            _issue(
                "PUBLIC_PROVENANCE_REQUIRED",
                self.stage,
                DashboardValidationSeverityV2.ERROR,
                "analytical bindings require public provenance",
                blocking=True,
            ),
        )


class DashboardCompatibilityValidator(DashboardValidator):
    stage = DashboardValidationStageV2.COMPATIBILITY

    def validate(self, blueprint: DashboardBlueprintV2) -> tuple[DashboardValidationIssueV2, ...]:
        check = DashboardBlueprintCompatibilityService.check(blueprint)
        issues = [
            _issue(
                "COMPATIBILITY_ERROR",
                self.stage,
                DashboardValidationSeverityV2.ERROR,
                message,
                blocking=True,
            )
            for message in check.errors
        ]
        issues.extend(
            _issue(
                "DEPRECATED_FEATURE",
                self.stage,
                DashboardValidationSeverityV2.WARNING,
                message,
            )
            for message in check.warnings
        )
        return tuple(issues)


class DashboardPatchValidator:
    _VISUAL_ALLOWED = (
        re.compile(r"^/identity/(?:title|description)$"),
        re.compile(r"^/layout/breakpoints/\d+/(?:items|grid)(?:/.*)?$"),
        re.compile(r"^/widgets/\d+/(?:title|formatting|theme_token|visible)(?:/.*)?$"),
    )
    _SEMANTIC_ALLOWED = (
        re.compile(r"^/data_bindings(?:/.*)?$"),
        re.compile(r"^/filters(?:/.*)?$"),
        re.compile(r"^/filter_groups(?:/.*)?$"),
        re.compile(r"^/interactions(?:/.*)?$"),
        re.compile(r"^/governance/classification$"),
        re.compile(r"^/widgets/\d+/(?:binding_id|expected_result_shape)$"),
    )
    _VISUAL_FORBIDDEN_SEGMENTS = {
        "metric_id", "dimension_id", "binding_id", "data_bindings", "filters",
        "classification", "permissions", "provenance", "expected_result_shape",
    }

    @classmethod
    def validate_visual(cls, patch: DashboardVisualPatchV2) -> tuple[DashboardValidationIssueV2, ...]:
        issues: list[DashboardValidationIssueV2] = []
        for operation in patch.operations:
            segments = set(operation.path.strip("/").split("/"))
            if segments & cls._VISUAL_FORBIDDEN_SEGMENTS or not any(
                pattern.match(operation.path) for pattern in cls._VISUAL_ALLOWED
            ):
                issues.append(
                    _issue(
                        "VISUAL_PATCH_SEMANTIC_MUTATION",
                        DashboardValidationStageV2.WIDGETS,
                        DashboardValidationSeverityV2.ERROR,
                        "visual patch cannot alter semantic content",
                        operation.path,
                        blocking=True,
                    )
                )
        return tuple(issues)

    @classmethod
    def validate_semantic(cls, patch: DashboardSemanticPatchV2) -> tuple[DashboardValidationIssueV2, ...]:
        return tuple(
            _issue(
                "SEMANTIC_PATCH_PATH_UNSUPPORTED",
                DashboardValidationStageV2.DATA_BINDINGS,
                DashboardValidationSeverityV2.ERROR,
                "semantic patch path is not allowlisted",
                operation.path,
                blocking=True,
            )
            for operation in patch.operations
            if not any(pattern.match(operation.path) for pattern in cls._SEMANTIC_ALLOWED)
        )


VALIDATOR_REGISTRY: tuple[DashboardValidator, ...] = (
    DashboardContractValidator(),
    DashboardIdentityValidator(),
    DashboardVersionValidator(),
    DashboardLifecycleValidator(),
    DashboardSecurityValidator(),
    DashboardClassificationValidator(),
    DashboardPermissionValidator(),
    DashboardLayoutValidator(),
    DashboardWidgetValidator(),
    DashboardBindingValidator(),
    DashboardFilterValidator(),
    DashboardInteractionValidator(),
    DashboardFormattingValidator(),
    DashboardAccessibilityValidator(),
    DashboardProvenanceValidator(),
    DashboardCompatibilityValidator(),
)


class DashboardBlueprintValidationService:
    """Validate an untrusted JSON payload or an already parsed immutable blueprint."""

    @classmethod
    def validate_payload(cls, payload: object) -> DashboardValidationResultV2:
        raw = payload.model_dump(mode="json", exclude_none=True) if isinstance(payload, DashboardBlueprintV2) else payload
        security_issues = DashboardSecurityValidator.validate_raw(raw)
        if any(issue.blocking for issue in security_issues):
            return DashboardValidationResultV2(
                status=DashboardValidationStatusV2.BLOCKED,
                issues=security_issues,
                completed_stages=(DashboardValidationStageV2.SECURITY,),
            )
        if isinstance(raw, Mapping):
            version = raw.get("version")
            if isinstance(version, Mapping):
                contract_version = version.get("contract_version")
                if contract_version not in {None, DASHBOARD_BLUEPRINT_CONTRACT_VERSION}:
                    return DashboardValidationResultV2(
                        status=DashboardValidationStatusV2.UNSUPPORTED_VERSION,
                        issues=(
                            _issue(
                                "UNSUPPORTED_CONTRACT_VERSION",
                                DashboardValidationStageV2.VERSION,
                                DashboardValidationSeverityV2.CRITICAL,
                                "dashboard contract version is unsupported",
                                "/version/contract_version",
                                blocking=True,
                            ),
                        ),
                        completed_stages=(DashboardValidationStageV2.VERSION,),
                    )
        try:
            if isinstance(payload, DashboardBlueprintV2):
                blueprint = payload
            else:
                blueprint = DashboardBlueprintV2.model_validate_json(
                    json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
                )
        except (ValidationError, TypeError, ValueError):
            return DashboardValidationResultV2(
                status=DashboardValidationStatusV2.INVALID,
                issues=(
                    _issue(
                        "CONTRACT_VALIDATION_FAILED",
                        DashboardValidationStageV2.CONTRACT,
                        DashboardValidationSeverityV2.ERROR,
                        "dashboard payload does not satisfy the strict V2 contract",
                        blocking=True,
                    ),
                ),
                completed_stages=(DashboardValidationStageV2.CONTRACT,),
            )

        issues: list[DashboardValidationIssueV2] = list(security_issues)
        completed: list[DashboardValidationStageV2] = []
        for validator in VALIDATOR_REGISTRY:
            stage_issues = validator.validate(blueprint)
            issues.extend(stage_issues)
            completed.append(validator.stage)
            if any(
                issue.blocking and issue.severity is DashboardValidationSeverityV2.CRITICAL
                for issue in stage_issues
            ):
                break

        blocking = any(issue.blocking for issue in issues)
        critical = any(issue.severity is DashboardValidationSeverityV2.CRITICAL for issue in issues)
        errors = any(issue.severity is DashboardValidationSeverityV2.ERROR for issue in issues)
        warnings = any(issue.severity is DashboardValidationSeverityV2.WARNING for issue in issues)
        if critical:
            status = DashboardValidationStatusV2.BLOCKED
        elif blocking or errors:
            status = DashboardValidationStatusV2.INVALID
        elif warnings:
            status = DashboardValidationStatusV2.VALID_WITH_WARNINGS
        else:
            status = DashboardValidationStatusV2.VALID
        canonicalization = None
        if status in {
            DashboardValidationStatusV2.VALID,
            DashboardValidationStatusV2.VALID_WITH_WARNINGS,
        }:
            canonicalization = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
            completed.append(DashboardValidationStageV2.CANONICALIZATION)
        return DashboardValidationResultV2(
            status=status,
            issues=tuple(issues),
            completed_stages=tuple(dict.fromkeys(completed)),
            canonicalization=canonicalization,
        )

