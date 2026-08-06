"""Export Prompt 22 schemas and reviewed synthetic goldens deterministically."""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import contracts.dashboard_ai_assistance_v2 as contracts

_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "dashboard_ai_assistance_v2_fixtures",
    BACKEND / "services" / "dashboard_ai_assistance_v2" / "fixtures.py",
)
if _FIXTURE_SPEC is None or _FIXTURE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("Prompt 22 fixture module not found")
_FIXTURES = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_FIXTURES)
golden_cases = _FIXTURES.golden_cases


BASE = ROOT / "docs" / "contracts" / "dashboard_ai_assistance_v2"
SCHEMAS = BASE / "schemas.json"
GOLDENS = ROOT / "backend" / "tests" / "golden" / "dashboard_ai_assistance_v2.json"


def _content(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export() -> dict[str, object]:
    models = {
        name: value.model_json_schema()
        for name, value in inspect.getmembers(contracts, inspect.isclass)
        if issubclass(value, BaseModel) and value not in {BaseModel, contracts.StrictDashboardAiModel}
    }
    schema_payload = {
        "contract_version": contracts.DASHBOARD_AI_ASSISTANCE_CONTRACT_VERSION,
        "schema_count": len(models),
        "schemas": dict(sorted(models.items())),
    }
    outputs = {SCHEMAS: schema_payload, GOLDENS: golden_cases()}
    hashes: dict[str, str] = {}
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        content = _content(payload)
        path.write_text(content, encoding="utf-8", newline="\n")
        key = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        hashes[key] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"contract_version": contracts.DASHBOARD_AI_ASSISTANCE_CONTRACT_VERSION, "hashes": hashes}


def main() -> None:
    first = export()
    second = export()
    if first != second:
        raise SystemExit("Prompt 22 schemas or goldens are not deterministic")
    print(_content({"status": "SUCCESS", "run_1": first, "run_2": second}), end="")


if __name__ == "__main__":
    main()
