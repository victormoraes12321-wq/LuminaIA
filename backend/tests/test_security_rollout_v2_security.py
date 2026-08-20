from __future__ import annotations

import pytest

from contracts.security_rollout_v2 import (
    SecurityControlStatusV2,
    SecurityControlV2,
    SecuritySeverityV2,
    TenantIsolationCheckV2,
    ThreatSurfaceKindV2,
)
from services.security_rollout_v2 import SecurityControlRegistryV2, SecurityPayloadSanitizerV2, SecurityReadinessServiceV2

pytestmark = pytest.mark.no_database


def _control(status: SecurityControlStatusV2, severity: SecuritySeverityV2 = SecuritySeverityV2.HIGH) -> SecurityControlV2:
    return SecurityControlV2(control_id="SEC-001", surface=ThreatSurfaceKindV2.SECRETS, status=status, severity=severity, title="Sensitive output control", evidence="Deterministic synthetic evidence")


def test_secret_sql_dataset_and_cot_are_redacted_recursively() -> None:
    sanitizer = SecurityPayloadSanitizerV2()
    value = sanitizer.sanitize({
        "authorization": "Bearer eyJabc.def.ghi",
        "sql": "SELECT * FROM users",
        "rows": [{"password": "secret"}],
        "chain_of_thought": "private reasoning",
        "message": "postgresql://user:password@db/prod",
        "internal_path": "C:\\runtime\\secret.txt",
        "safe": "bounded structural status",
    })
    rendered = repr(value)
    assert "SELECT" not in rendered and "postgresql://" not in rendered and "private reasoning" not in rendered and "runtime" not in rendered
    assert value["safe"] == "bounded structural status"
    assert sanitizer.sanitize("PASSWORD_CHANGE_REQUIRED") == "PASSWORD_CHANGE_REQUIRED"


def test_critical_failure_and_tenant_effect_block_readiness() -> None:
    critical = SecurityReadinessServiceV2.evaluate(controls=(_control(SecurityControlStatusV2.FAIL, SecuritySeverityV2.CRITICAL),))
    assert not critical.ready and critical.critical_failures == 1
    tenant = SecurityReadinessServiceV2.evaluate(
        controls=(_control(SecurityControlStatusV2.PASS),),
        tenant_checks=(TenantIsolationCheckV2(subsystem="DASH-001", disclosure_count=1, mutation_count=0, status=SecurityControlStatusV2.FAIL),),
    )
    assert not tenant.ready and tenant.critical_failures == 1


def test_passed_controls_certify_zero_critical_failures() -> None:
    result = SecurityReadinessServiceV2.evaluate(controls=(_control(SecurityControlStatusV2.PASS),))
    assert result.ready and result.critical_failures == 0


def test_consolidated_security_readiness_is_deterministic_and_green() -> None:
    first = SecurityControlRegistryV2.readiness()
    second = SecurityControlRegistryV2.readiness()
    assert first == second
    assert first.total_controls == first.passed_controls == 32
    assert first.failed_controls == first.critical_failures == 0
    assert first.ready
