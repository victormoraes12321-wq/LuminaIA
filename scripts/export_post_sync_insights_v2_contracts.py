"""Export JSON Schemas and Golden Samples for Post-Sync Insights V2."""
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

from contracts.post_sync_insights_v2 import (
    PostSyncInsightCandidateV2,
    PostSyncInsightDetailV2,
    PostSyncInsightEvidenceV2,
    PostSyncInsightListItemV2,
    PostSyncInsightPolicyV2,
    PostSyncInsightRunRequestV2,
    PostSyncInsightRunResultV2,
    PostSyncInsightRunV2,
    PostSyncInsightV2,
)
from services.post_sync_insights_v2.policy import get_default_post_sync_policy

MODELS = [
    ("PostSyncInsightPolicyV2", PostSyncInsightPolicyV2),
    ("PostSyncInsightRunRequestV2", PostSyncInsightRunRequestV2),
    ("PostSyncInsightCandidateV2", PostSyncInsightCandidateV2),
    ("PostSyncInsightV2", PostSyncInsightV2),
    ("PostSyncInsightEvidenceV2", PostSyncInsightEvidenceV2),
    ("PostSyncInsightRunV2", PostSyncInsightRunV2),
    ("PostSyncInsightRunResultV2", PostSyncInsightRunResultV2),
    ("PostSyncInsightListItemV2", PostSyncInsightListItemV2),
    ("PostSyncInsightDetailV2", PostSyncInsightDetailV2),
]

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT_DIR / "docs" / "contracts" / "post_sync_insights_v2" / "schemas"
GOLDENS_DIR = ROOT_DIR / "docs" / "contracts" / "post_sync_insights_v2" / "goldens"


def export_schemas_and_goldens() -> None:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    GOLDENS_DIR.mkdir(parents=True, exist_ok=True)

    for name, model_cls in MODELS:
        schema_file = SCHEMAS_DIR / f"{name}.json"
        schema_data = model_cls.model_json_schema()
        schema_file.write_text(json.dumps(schema_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Golden sample: Default policy
    policy = get_default_post_sync_policy("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    golden_policy_file = GOLDENS_DIR / "DefaultPolicyGoldenV2.json"
    golden_policy_file.write_text(json.dumps(policy.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Exported {len(MODELS)} schemas and goldens successfully.")


if __name__ == "__main__":
    export_schemas_and_goldens()
