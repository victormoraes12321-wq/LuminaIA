"""Export JSON Schemas and Golden Samples for Observability, Metrics, and Evaluations V2."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LUMINA_TESTING", "true")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://lumina_user:lumina_password@127.0.0.1:55432/luminaai_test")
os.environ.setdefault("SECRET_KEY", "01234567890123456789012345678901")
os.environ.setdefault("ENCRYPTION_KEY", "gAAAAABk" + "0"*36 + "=")
os.environ.setdefault("OPENAI_API_KEY", "sk-proj-01234567890123456789")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from contracts.observability_v2 import (
    ErrorBudgetV2,
    EvaluationCaseV2,
    EvaluationEvidenceV2,
    EvaluationRegressionV2,
    EvaluationResultV2,
    EvaluationRunV2,
    EvaluationSuiteV2,
    ObservabilityContextV2,
    OperationalEventV2,
    OperationalMetricDefinitionV2,
    OperationalMetricPointV2,
    OperationalMetricRollupV2,
    SloDefinitionV2,
    SloEvaluationV2,
    SpanSummaryV2,
    TraceSummaryV2,
)

MODELS = [
    ("ObservabilityContextV2", ObservabilityContextV2),
    ("SpanSummaryV2", SpanSummaryV2),
    ("TraceSummaryV2", TraceSummaryV2),
    ("OperationalEventV2", OperationalEventV2),
    ("OperationalMetricDefinitionV2", OperationalMetricDefinitionV2),
    ("OperationalMetricPointV2", OperationalMetricPointV2),
    ("OperationalMetricRollupV2", OperationalMetricRollupV2),
    ("SloDefinitionV2", SloDefinitionV2),
    ("ErrorBudgetV2", ErrorBudgetV2),
    ("SloEvaluationV2", SloEvaluationV2),
    ("EvaluationCaseV2", EvaluationCaseV2),
    ("EvaluationEvidenceV2", EvaluationEvidenceV2),
    ("EvaluationResultV2", EvaluationResultV2),
    ("EvaluationRegressionV2", EvaluationRegressionV2),
    ("EvaluationSuiteV2", EvaluationSuiteV2),
    ("EvaluationRunV2", EvaluationRunV2),
]

SCHEMAS_DIR = ROOT_DIR / "docs" / "contracts" / "observability_v2" / "schemas"
GOLDENS_DIR = ROOT_DIR / "docs" / "contracts" / "observability_v2" / "goldens"


def export_schemas_and_goldens() -> None:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    GOLDENS_DIR.mkdir(parents=True, exist_ok=True)

    for name, model_cls in MODELS:
        schema_file = SCHEMAS_DIR / f"{name}.json"
        schema_data = model_cls.model_json_schema()
        schema_file.write_text(json.dumps(schema_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Successfully exported {len(MODELS)} schemas to {SCHEMAS_DIR}")


if __name__ == "__main__":
    export_schemas_and_goldens()
