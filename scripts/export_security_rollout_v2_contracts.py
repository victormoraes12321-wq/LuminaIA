"""Deterministically export Prompt 26 schemas and structural goldens."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from contracts.security_rollout_v2 import (  # noqa: E402
    CanaryAssignmentV2, CanaryPolicyV2, CapabilityCheckV2,
    ConfigurationReadinessV2, ConfigurationSnapshotV2, DeploymentCompatibilityV2,
    FeatureConfigurationV2, FeatureDependencyV2, FeatureRolloutPolicyV2,
    IncidentReadinessV2, KillSwitchV2, MigrationCompatibilityV2, MigrationReadinessV2,
    OperationalReadinessV2, RollbackPlanV2, RollbackReadinessV2, RolloutEvidenceV2,
    RolloutGateV2, RolloutReadinessV2, SchemaManifestV2, SecurityCertificationV2,
    SecurityControlV2, SecurityFindingV2, SecurityReadinessV2, TenantIsolationCheckV2,
    ThreatSurfaceV2,
)
from services.security_rollout_v2 import (  # noqa: E402
    AuthorizationMatrixServiceV2, GovernedFeatureRegistryV2, RollbackReadinessServiceV2,
    SecurityControlRegistryV2,
)

MODELS = (
    CanaryAssignmentV2, CanaryPolicyV2, CapabilityCheckV2,
    ConfigurationReadinessV2, ConfigurationSnapshotV2, DeploymentCompatibilityV2,
    FeatureConfigurationV2, FeatureDependencyV2, FeatureRolloutPolicyV2,
    IncidentReadinessV2, KillSwitchV2, MigrationCompatibilityV2, MigrationReadinessV2,
    OperationalReadinessV2, RollbackPlanV2, RollbackReadinessV2, RolloutEvidenceV2,
    RolloutGateV2, RolloutReadinessV2, SchemaManifestV2, SecurityCertificationV2,
    SecurityControlV2, SecurityFindingV2, SecurityReadinessV2, TenantIsolationCheckV2,
    ThreatSurfaceV2,
)
OUTPUT = ROOT / "docs" / "contracts" / "security_rollout_v2"
SCHEMAS = OUTPUT / "schemas"
GOLDENS = OUTPUT / "goldens"


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def export() -> dict[str, Any]:
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    GOLDENS.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        _write(SCHEMAS / f"{model.__name__}.json", model.model_json_schema())
    _write(GOLDENS / "feature_inventory.json", [item.model_dump(mode="json") for item in GovernedFeatureRegistryV2.list_policies()])
    _write(GOLDENS / "authorization_matrix.json", [item.model_dump(mode="json") for item in AuthorizationMatrixServiceV2.matrix()])
    _write(GOLDENS / "rollback_matrix.json", RollbackReadinessServiceV2.evaluate().model_dump(mode="json"))
    _write(GOLDENS / "security_readiness.json", SecurityControlRegistryV2.readiness().model_dump(mode="json"))
    files = tuple(sorted((*SCHEMAS.glob("*.json"), *GOLDENS.glob("*.json"))))
    digest = hashlib.sha256(b"".join(path.relative_to(OUTPUT).as_posix().encode() + b"\0" + path.read_bytes() for path in files)).hexdigest()
    manifest = {"contract_version": "lumina.security-migration-rollout/1.0", "schema_count": len(MODELS), "golden_count": 4, "aggregate_sha256": digest}
    _write(OUTPUT / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(export(), sort_keys=True))
