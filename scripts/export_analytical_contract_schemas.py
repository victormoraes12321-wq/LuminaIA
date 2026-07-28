from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "contracts" / "schemas"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from contracts.analytical_v2 import (  # noqa: E402
    AnalyticalResponseV2,
    ComparisonSpecification,
    QueryIntentV2,
    QueryPlanV2,
    VisualizationSpecification,
)


ContractModel: TypeAlias = type[BaseModel]
SCHEMA_MODELS: tuple[ContractModel, ...] = (
    QueryIntentV2,
    QueryPlanV2,
    ComparisonSpecification,
    VisualizationSpecification,
    AnalyticalResponseV2,
)


def render_schema(model: ContractModel) -> str:
    payload = model.model_json_schema()
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_schemas(output_directory: Path = OUTPUT_DIRECTORY) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in SCHEMA_MODELS:
        target = output_directory / f"{model.__name__}.schema.json"
        target.write_text(render_schema(model), encoding="utf-8", newline="\n")
        written.append(target)
    return written


def main() -> int:
    try:
        for path in export_schemas():
            print(path.relative_to(REPOSITORY_ROOT))
    except Exception as exc:
        print(f"schema export failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
