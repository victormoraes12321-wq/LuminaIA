"""Tests for Observability V2 contract schema exporters and reproducibilty."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from contracts.observability_v2 import (
    ObservabilityContextV2,
    OperationalEventV2,
    SloEvaluationV2,
    TraceSummaryV2,
)

pytestmark = pytest.mark.no_database

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = ROOT_DIR / "docs" / "contracts" / "observability_v2" / "schemas"


def test_observability_v2_json_schemas_exist_and_valid():
    schema_file = SCHEMAS_DIR / "ObservabilityContextV2.json"
    assert schema_file.exists()

    data = json.loads(schema_file.read_text(encoding="utf-8"))
    assert data["title"] == "ObservabilityContextV2"
    assert "contract_version" in data["properties"]
