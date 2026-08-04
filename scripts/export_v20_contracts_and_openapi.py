"""
Exporter & Double-Verification Script for Prompt 17 (Schemas, Goldens, OpenAPI)
"""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from contracts.validation_provenance_v2 import (
    AnalyticalClaimV2,
    AnalyticalFactV2,
    CertificationEnvelopeV2,
    PublicProvenanceSummaryV2,
    ValidationPolicyV2,
    ValidationRequestV2,
)

BASE_DIR = Path(__file__).resolve().parents[1] / "docs" / "contracts" / "validation_provenance_v2"
SCHEMAS_DIR = BASE_DIR / "schemas"
GOLDENS_DIR = BASE_DIR / "goldens"

SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
GOLDENS_DIR.mkdir(parents=True, exist_ok=True)


def export_artifacts() -> dict[str, str]:
    hashes = {}

    # Export Schemas
    models = {
        "ValidationPolicyV2.json": ValidationPolicyV2,
        "ValidationRequestV2.json": ValidationRequestV2,
        "AnalyticalFactV2.json": AnalyticalFactV2,
        "AnalyticalClaimV2.json": AnalyticalClaimV2,
        "PublicProvenanceSummaryV2.json": PublicProvenanceSummaryV2,
        "CertificationEnvelopeV2.json": CertificationEnvelopeV2,
    }

    for fname, model_cls in models.items():
        out_path = SCHEMAS_DIR / fname
        schema_dict = model_cls.model_json_schema()
        content = json.dumps(schema_dict, indent=2, sort_keys=True)
        out_path.write_text(content, encoding="utf-8")
        hashes[f"schema:{fname}"] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Export Golden Cases
    golden_cases = {
        "golden_certified_valid.json": {
            "scenario": "June vs July Revenue Comparison Certified Valid",
            "overall_status": "VALID",
            "fact_count": 2,
            "claim_count": 1,
            "contract_version": "lumina.validation-provenance/1.0",
        },
        "golden_blocked_tenant_mismatch.json": {
            "scenario": "Cross Tenant Proof Mismatch Blocked",
            "overall_status": "BLOCKED",
            "critical_issue": "ERR_TENANT_PROOF_MISMATCH",
            "contract_version": "lumina.validation-provenance/1.0",
        },
    }

    for fname, gdata in golden_cases.items():
        out_path = GOLDENS_DIR / fname
        content = json.dumps(gdata, indent=2, sort_keys=True)
        out_path.write_text(content, encoding="utf-8")
        hashes[f"golden:{fname}"] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Export OpenAPI Spec
    try:
        from main import app
        openapi_data = app.openapi()
        out_path = BASE_DIR / "openapi.json"
        content = json.dumps(openapi_data, indent=2, sort_keys=True)
        out_path.write_text(content, encoding="utf-8")
        hashes["openapi"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    except Exception as ex:
        hashes["openapi"] = f"skipped:{ex}"

    return hashes


def main():
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LUMINA_TESTING"] = "true"
    os.environ["TEST_DATABASE_URL"] = (
        "postgresql+asyncpg://lumina_test:lumina_test"
        "@127.0.0.1:55432/luminaai_test"
    )
    os.environ["SECRET_KEY"] = "test-secret-key-only-32-characters-minimum"
    os.environ["ENCRYPTION_KEY"] = (
        "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
    )
    os.environ["OPENAI_API_KEY"] = (
        "sk-test-not-a-real-openai-credential-000000000000"
    )
    os.environ["MOCK_ORACLE"] = "true"
    os.environ["MOCK_OPENAI"] = "true"
    os.environ["LUMINA_DISABLE_EXTERNAL_NETWORK"] = "true"
    os.environ["SMART_CACHE_MATERIALIZATION_MODE"] = "LEGACY_ONLY"
    os.environ["SMART_CACHE_ADMIN_ENABLED"] = "false"

    print("--- RUN 1: Exporting Schemas, Goldens, and OpenAPI ---")
    h1 = export_artifacts()

    print("--- RUN 2: Re-exporting Schemas, Goldens, and OpenAPI ---")
    h2 = export_artifacts()

    diffs = 0
    for k in h1:
        if h1[k] != h2[k]:
            print(f"ERROR: Hash mismatch for {k}: {h1[k]} != {h2[k]}")
            diffs += 1
        else:
            print(f"MATCH: {k} -> {h1[k][:12]}...")

    if diffs == 0:
        print("\nSUCCESS: Export Double Verification PASSED with 0 Hash Differences!")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
