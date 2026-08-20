"""Pure, non-persisting adapter from a narrow synthetic legacy shape."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence

from contracts.dashboard_blueprint_v2 import (
    LegacyDashboardAdaptationResultV2,
    LegacyDashboardAdaptationStatusV2,
)

from .fixtures import build_minimal_dashboard


_SUPPORTED_LEGACY_TYPES = {"KPI", "KPI_CARD", "TABLE", "DATA_TABLE", "BAR", "BAR_CHART"}
_SAFE_NAME = re.compile(r"[^a-z0-9.:-]+")


class LegacyDashboardBlueprintAdapter:
    """Create a V2 proposal without writing or mutating any legacy source."""

    @classmethod
    def adapt(cls, legacy: Mapping[str, object]) -> LegacyDashboardAdaptationResultV2:
        original = copy.deepcopy(dict(legacy))
        original_hash = cls._fingerprint(original)
        warnings: list[str] = ["legacy visual fields require governed V2 review"]
        unmapped = sorted(set(original) - {"name", "description", "components", "layout", "grid"})
        components = original.get("components")
        if not isinstance(components, Sequence) or isinstance(components, (str, bytes)) or not components:
            return LegacyDashboardAdaptationResultV2(
                status=LegacyDashboardAdaptationStatusV2.UNSUPPORTED,
                warnings=("legacy payload does not contain supported components",),
                unmapped_fields=tuple(unmapped),
                original_unchanged=original_hash == cls._fingerprint(dict(legacy)),
            )
        unsupported_types: list[str] = []
        for component in components:
            if not isinstance(component, Mapping):
                unsupported_types.append("NON_OBJECT")
                continue
            component_type = str(component.get("type", "")).upper()
            if component_type not in _SUPPORTED_LEGACY_TYPES:
                unsupported_types.append(component_type or "MISSING")
        if unsupported_types:
            warnings.append(f"unsupported component types: {','.join(sorted(set(unsupported_types)))}")
        raw_name = str(original.get("name") or "legacy-dashboard").lower()
        slug = _SAFE_NAME.sub(".", raw_name).strip(".") or "legacy.dashboard"
        if not slug.startswith("dashboard."):
            slug = f"dashboard.{slug}"
        proposal = build_minimal_dashboard(
            blueprint_id=slug[:120],
            title=str(original.get("name") or "Dashboard legado sintético")[:160],
        )
        if "layout" in original or "grid" in original:
            warnings.append("legacy layout was not copied; deterministic V2 layout was proposed")
        if unmapped:
            warnings.append("unmapped legacy fields were preserved only as warning names")
        status = (
            LegacyDashboardAdaptationStatusV2.PARTIAL
            if unsupported_types or unmapped
            else LegacyDashboardAdaptationStatusV2.COMPLETE_WITH_WARNINGS
        )
        return LegacyDashboardAdaptationResultV2(
            status=status,
            proposal=proposal,
            warnings=tuple(warnings),
            unmapped_fields=tuple(unmapped),
            original_unchanged=original_hash == cls._fingerprint(dict(legacy)),
        )

    @staticmethod
    def _fingerprint(value: object) -> str:
        return hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

