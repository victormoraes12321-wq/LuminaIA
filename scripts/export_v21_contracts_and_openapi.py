"""Deterministic Prompt 18 schema, golden, and OpenAPI exporter."""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
BASE = ROOT / "docs" / "contracts" / "smart_cache_materialization_v2"
SCHEMAS = BASE / "schemas"
GOLDENS = BASE / "goldens"


def _content(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write(path: Path, value: object, hashes: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _content(value)
    path.write_text(content, encoding="utf-8", newline="\n")
    hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def export_artifacts() -> dict[str, str]:
    from contracts import smart_cache_materialization_v2 as contracts

    hashes: dict[str, str] = {}
    models = {
        name: value
        for name, value in inspect.getmembers(contracts, inspect.isclass)
        if issubclass(value, BaseModel) and value is not BaseModel
    }
    for name, model in sorted(models.items()):
        _write(SCHEMAS / f"{name}.json", model.model_json_schema(), hashes)

    _write(
        GOLDENS / "certified_cache_hit.json",
        {
            "cache_type": "CERTIFIED_ANALYTICAL_RESULT",
            "certification_status": "VALID",
            "decision": "HIT",
            "freshness": "FRESH",
            "result_complete": True,
            "tenant_isolation": "VERIFIED",
        },
        hashes,
    )
    _write(
        GOLDENS / "governed_materialization_ready.json",
        {
            "auto_published": False,
            "build_status": "READY",
            "certification_status": "VALID",
            "lifecycle": "READY",
            "publication_requires_cas": True,
            "source": "SAFE_ANALYTICAL_POSTGRESQL",
        },
        hashes,
    )

    from main import app as legacy_app

    _write(BASE / "openapi_legacy.json", legacy_app.openapi(), hashes)

    from routers.smart_cache_materialization import router

    experimental = FastAPI(title="LuminaAI Prompt 18 Experimental Contract")
    experimental.include_router(router)
    _write(BASE / "openapi_experimental.json", experimental.openapi(), hashes)
    return hashes


def main() -> None:
    os.environ.update(
        {
            "ENVIRONMENT": "test",
            "LUMINA_TESTING": "true",
            "TEST_DATABASE_URL": (
                "postgresql+asyncpg://lumina_test:lumina_test@127.0.0.1:55432/luminaai_test"
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
    first = export_artifacts()
    second = export_artifacts()
    if first != second:
        mismatches = sorted(key for key in first if first.get(key) != second.get(key))
        raise SystemExit(f"non-deterministic Prompt 18 artifacts: {mismatches}")
    legacy = json.loads((BASE / "openapi_legacy.json").read_text(encoding="utf-8"))
    if any(path.startswith("/api/v2/cache") for path in legacy["paths"]):
        raise SystemExit("LEGACY_ONLY OpenAPI unexpectedly exposes Prompt 18")
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "artifacts": len(first),
                "schemas": sum("/schemas/" in key for key in first),
                "goldens": sum("/goldens/" in key for key in first),
                "legacy_paths": len(legacy["paths"]),
                "hashes": first,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
