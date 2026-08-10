from __future__ import annotations

import pytest
from pydantic import ValidationError

from contracts.security_rollout_v2 import (
    CONTRACT_VERSION,
    SecurityControlStatusV2,
    SecurityControlV2,
    SecuritySeverityV2,
    ThreatSurfaceKindV2,
)

pytestmark = pytest.mark.no_database


def test_contract_version_and_strict_frozen_contract() -> None:
    assert CONTRACT_VERSION == "lumina.security-migration-rollout/1.0"
    control = SecurityControlV2(
        control_id="AUTH-001",
        surface=ThreatSurfaceKindV2.AUTHORIZATION,
        status=SecurityControlStatusV2.PASS,
        severity=SecuritySeverityV2.CRITICAL,
        title="Server role authority",
        evidence="Role comes from authenticated PostgreSQL user",
    )
    with pytest.raises(ValidationError):
        SecurityControlV2.model_validate({**control.model_dump(), "unknown": True})
    with pytest.raises(ValidationError):
        control.status = SecurityControlStatusV2.FAIL  # type: ignore[misc]


def test_not_applicable_requires_justification() -> None:
    with pytest.raises(ValidationError):
        SecurityControlV2(
            control_id="CSRF-001",
            surface=ThreatSurfaceKindV2.HTTP,
            status=SecurityControlStatusV2.NOT_APPLICABLE,
            severity=SecuritySeverityV2.INFO,
            title="CSRF classification",
            evidence="Bearer only",
        )
