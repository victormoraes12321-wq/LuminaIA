"""Export deterministic JSON Schemas for Dashboard Backend V2."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import contracts.dashboard_backend_v2 as contracts


OUTPUT = ROOT / "docs" / "contracts" / "dashboard_backend_v2" / "schemas.json"


def export() -> Path:
    schemas: dict[str, object] = {}
    for name in sorted(contracts.__all__):
        candidate = getattr(contracts, name, None)
        if isinstance(candidate, type) and hasattr(candidate, "model_json_schema"):
            schemas[name] = candidate.model_json_schema()
    payload = {
        "contract_version": contracts.DASHBOARD_BACKEND_CONTRACT_VERSION,
        "schema_count": len(schemas),
        "schemas": schemas,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    print(export())
