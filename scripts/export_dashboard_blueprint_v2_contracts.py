"""Deterministic Dashboard Blueprint V2 schema, golden, and OpenAPI verifier."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

from pydantic import BaseModel, TypeAdapter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
BASE = ROOT / "docs" / "contracts" / "dashboard_blueprint_v2"
SCHEMAS = BASE / "schemas"
GOLDENS = BASE / "goldens"
EXPECTED_OPENAPI_PATHS = 190
EXPECTED_OPENAPI_OPERATIONS = 216


def _content(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write(path: Path, value: object, hashes: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _content(value)
    path.write_text(content, encoding="utf-8", newline="\n")
    hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(content.encode("utf-8")).hexdigest()


def _aggregate(hashes: dict[str, str]) -> str:
    serialized = "\n".join(f"{path}:{digest}" for path, digest in sorted(hashes.items()))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _openapi_summary() -> dict[str, object]:
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "LUMINA_TESTING": "true",
            "TEST_DATABASE_URL": (
                "postgresql+asyncpg://lumina_test:lumina_test@127.0.0.1:55432/"
                "luminaai_test_prompt19"
            ),
            "SECRET_KEY": "test-secret-key-only-32-characters-minimum",
            "ENCRYPTION_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
            "OPENAI_API_KEY": "sk-test-not-a-real-openai-credential-000000000000",
            "MOCK_ORACLE": "true",
            "MOCK_OPENAI": "true",
            "LUMINA_DISABLE_EXTERNAL_NETWORK": "true",
            "SMART_CACHE_MATERIALIZATION_MODE": "LEGACY_ONLY",
            "SMART_CACHE_ADMIN_ENABLED": "false",
        }
    )
    os.environ.pop("DATABASE_URL", None)
    from main import app

    document = app.openapi()
    paths = document.get("paths", {})
    operations = sum(
        1
        for path_item in paths.values()
        for method in path_item
        if method.lower() in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    )
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(paths) != EXPECTED_OPENAPI_PATHS or operations != EXPECTED_OPENAPI_OPERATIONS:
        raise SystemExit(
            f"OpenAPI changed: paths={len(paths)} operations={operations}; "
            f"expected {EXPECTED_OPENAPI_PATHS}/{EXPECTED_OPENAPI_OPERATIONS}"
        )
    if any("dashboard-blueprint" in path for path in paths):
        raise SystemExit("Prompt 19 unexpectedly exposed an OpenAPI path")
    return {
        "paths": len(paths),
        "operations": operations,
        "logical_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "prompt18_default_paths": sum(1 for path in paths if path.startswith("/api/v2/cache")),
        "prompt19_paths": sum(1 for path in paths if "dashboard-blueprint" in path),
    }


def export_artifacts() -> tuple[dict[str, str], dict[str, object]]:
    from contracts import dashboard_blueprint_v2 as contracts
    from services.dashboard_blueprint_v2.fixtures import golden_cases

    hashes: dict[str, str] = {}
    models = {
        name: value
        for name, value in inspect.getmembers(contracts, inspect.isclass)
        if issubclass(value, BaseModel)
        and value is not BaseModel
        and name not in {"StrictDashboardModel", "DashboardWidgetBaseV2", "DashboardChartWidgetBaseV2", "DashboardFilterBaseV2", "DashboardInteractionBaseV2"}
    }
    for name, model in sorted(models.items()):
        _write(SCHEMAS / f"{name}.json", model.model_json_schema(), hashes)
    union_exports = {
        "DashboardWidgetV2": contracts.DashboardWidgetV2,
        "DashboardFilterV2": contracts.DashboardFilterV2,
        "DashboardInteractionV2": contracts.DashboardInteractionV2,
        "DashboardPeriodBindingV2": contracts.DashboardPeriodBindingV2,
    }
    for name, annotation in union_exports.items():
        _write(SCHEMAS / f"{name}.json", TypeAdapter(annotation).json_schema(), hashes)
    for name, case in sorted(golden_cases().items()):
        _write(GOLDENS / f"{name}.json", case, hashes)
    return hashes, _openapi_summary()


def main() -> None:
    first, first_openapi = export_artifacts()
    second, second_openapi = export_artifacts()
    if first != second:
        raise SystemExit("Dashboard Blueprint V2 schemas or goldens are not deterministic")
    if first_openapi != second_openapi:
        raise SystemExit("default OpenAPI is not deterministic")
    schema_count = sum("/schemas/" in path for path in first)
    golden_count = sum("/goldens/" in path for path in first)
    result = {
        "status": "SUCCESS",
        "contract_version": "lumina.dashboard-blueprint/2.0",
        "artifacts": len(first),
        "schemas": schema_count,
        "goldens": golden_count,
        "aggregate_sha256_run_1": _aggregate(first),
        "aggregate_sha256_run_2": _aggregate(second),
        "openapi_run_1": first_openapi,
        "openapi_run_2": second_openapi,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

