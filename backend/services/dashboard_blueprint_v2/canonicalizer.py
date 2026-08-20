"""Deterministic Unicode-aware canonicalization and checksum computation."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import cast

from pydantic import JsonValue

from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardCanonicalizationResultV2,
    DashboardChecksumSetV2,
)


_WHITESPACE = re.compile(r"\s+")
_SEMANTIC_INTERACTIONS = {"CROSS_FILTER", "DRILLDOWN", "INTERNAL_NAVIGATION"}
_VISUAL_EXCLUDED_KEYS = {
    "binding_id",
    "metric_id",
    "dimension_id",
    "source_binding_id",
    "expected_result_shape",
    "ranking_dimension_id",
}


class DashboardBlueprintCanonicalizer:
    """Pure canonicalizer. It never repairs an invalid blueprint."""

    @classmethod
    def canonicalize(cls, blueprint: DashboardBlueprintV2) -> DashboardCanonicalizationResultV2:
        payload = blueprint.model_dump(mode="json", exclude_none=True, exclude={"checksum"})
        normalized = cast(dict[str, JsonValue], cls._normalize(payload))
        semantic = cls._semantic_projection(normalized)
        visual = cls._visual_projection(normalized)
        canonical_json = cls._json(normalized)
        checksums = DashboardChecksumSetV2(
            blueprint_checksum=cls._hash_json(normalized),
            semantic_checksum=cls._hash_json(semantic),
            visual_checksum=cls._hash_json(visual),
            layout_checksum=cls._hash_json(normalized["layout"]),
            widgets_checksum=cls._hash_json(normalized["widgets"]),
            bindings_checksum=cls._hash_json(normalized["data_bindings"]),
            filters_checksum=cls._hash_json(
                {"filters": normalized["filters"], "groups": normalized["filter_groups"]}
            ),
            interactions_checksum=cls._hash_json(normalized["interactions"]),
            accessibility_checksum=cls._hash_json(normalized["accessibility"]),
        )
        return DashboardCanonicalizationResultV2(
            canonical_json=canonical_json,
            checksums=checksums,
        )

    @classmethod
    def _normalize(cls, value: object) -> JsonValue:
        if isinstance(value, str):
            return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()
        if isinstance(value, Mapping):
            return {
                str(key): cls._normalize(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return [cls._normalize(item) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise TypeError(f"unsupported canonical value: {type(value).__name__}")

    @classmethod
    def _semantic_projection(cls, payload: dict[str, JsonValue]) -> JsonValue:
        version = cast(dict[str, JsonValue], payload["version"])
        identity = cast(dict[str, JsonValue], payload["identity"])
        widgets = cast(list[dict[str, JsonValue]], payload["widgets"])
        interactions = cast(list[dict[str, JsonValue]], payload["interactions"])
        return {
            "version": {
                "contract_id": version["contract_id"],
                "contract_version": version["contract_version"],
                "blueprint_version": version["blueprint_version"],
                "semantic_revision": cast(dict[str, JsonValue], version["revision"])[
                    "semantic_revision"
                ],
            },
            "identity": {
                "blueprint_id": identity["blueprint_id"],
                "canonical_name": identity["canonical_name"],
                "locale": identity["locale"],
                "timezone_policy": identity["timezone_policy"],
            },
            "purpose": payload["purpose"],
            "lifecycle": payload["lifecycle"],
            "created_origin": payload["created_origin"],
            "audience": payload["audience"],
            "governance": payload["governance"],
            "widget_bindings": [
                {
                    key: widget[key]
                    for key in ("widget_type", "binding_id", "expected_result_shape")
                    if key in widget
                }
                | {"widget_id": cast(dict[str, JsonValue], widget["identity"])["widget_id"]}
                for widget in widgets
            ],
            "data_bindings": payload["data_bindings"],
            "filters": payload["filters"],
            "filter_groups": payload["filter_groups"],
            "interactions": [
                item for item in interactions if item.get("interaction_type") in _SEMANTIC_INTERACTIONS
            ],
            "refresh_policy": payload["refresh_policy"],
            "compatibility": payload["compatibility"],
        }

    @classmethod
    def _visual_projection(cls, payload: dict[str, JsonValue]) -> JsonValue:
        def strip_semantic(value: JsonValue) -> JsonValue:
            if isinstance(value, dict):
                return {
                    key: strip_semantic(item)
                    for key, item in value.items()
                    if key not in _VISUAL_EXCLUDED_KEYS
                }
            if isinstance(value, list):
                return [strip_semantic(item) for item in value]
            return value

        identity = cast(dict[str, JsonValue], payload["identity"])
        version = cast(dict[str, JsonValue], payload["version"])
        revision = cast(dict[str, JsonValue], version["revision"])
        return {
            "visual_revision": revision["visual_revision"],
            "title": identity["title"],
            "description": identity["description"],
            "layout": payload["layout"],
            "widgets": strip_semantic(payload["widgets"]),
            "accessibility": payload["accessibility"],
        }

    @staticmethod
    def _json(value: JsonValue) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _hash_json(cls, value: JsonValue) -> str:
        return hashlib.sha256(cls._json(value).encode("utf-8")).hexdigest()
