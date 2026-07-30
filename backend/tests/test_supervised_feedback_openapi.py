from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from main import app
from schemas.query import QueryResponse


pytestmark = pytest.mark.unit
ROOT = Path(__file__).parents[2]


def load_exporter():
    path = ROOT / "scripts" / "export_analytical_contract_schemas.py"
    spec = importlib.util.spec_from_file_location("lumina_schema_export_prompt12", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.glob("*.schema.json"))
    }


def test_prompt12_schemas_are_reproducible(tmp_path: Path) -> None:
    exporter = load_exporter()
    first = tmp_path / "first"
    second = tmp_path / "second"
    exporter.export_schemas(first)
    exporter.export_schemas(second)
    assert hashes(first) == hashes(second)
    required = {
        "FeedbackSubmissionV2.schema.json",
        "FeedbackRecordV2.schema.json",
        "StructuredCorrectionV2.schema.json",
        "FeedbackReviewDecisionV2.schema.json",
        "ApprovedTrainingExampleV2.schema.json",
        "TrainingDatasetSnapshotV2.schema.json",
        "EvaluationCaseV2.schema.json",
        "FeedbackDeletionRequestV2.schema.json",
        "GovernedImportDryRunRequestV2.schema.json",
        "GovernedImportDryRunResultV2.schema.json",
        "FeedbackShadowEvaluationV2.schema.json",
    }
    assert required.issubset(hashes(first))


def test_openapi_exposes_versioned_routes_without_client_identity_authority() -> None:
    schema = app.openapi()
    operation_count = sum(
        method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}
        for operations in schema["paths"].values()
        for method in operations
    )
    feedback_paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if path.startswith("/api/v2/feedback") or path.startswith("/api/v2/me/feedback")
    }
    # Prompt 12 owns the feedback surface, while later prompts add versioned
    # APIs without changing the 29 feedback paths certified here.
    assert len(schema["paths"]) >= 149
    assert operation_count >= 173
    assert len(feedback_paths) == 29
    submission = schema["components"]["schemas"]["FeedbackSubmissionV2"]
    serialized = json.dumps(submission)
    assert '"tenant_id"' not in serialized
    assert '"user_id"' not in serialized
    assert '"reviewer_user_id"' not in serialized


def test_query_response_exposes_only_structural_feedback_target_checksum() -> None:
    schema = QueryResponse.model_json_schema()
    properties = schema["properties"]
    assert properties["feedback_target_checksum"]["anyOf"][0]["pattern"] == "^[a-f0-9]{64}$"
    forbidden = {"feedback_payload", "raw_response", "sql", "binds", "dataset_rows"}
    assert forbidden.isdisjoint(properties)
