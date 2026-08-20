"""Critical-first security readiness aggregation."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    SecurityControlStatusV2,
    SecurityControlV2,
    SecurityFindingV2,
    SecurityReadinessV2,
    SecuritySeverityV2,
    TenantIsolationCheckV2,
)

_FAIL_STATES = {
    SecurityControlStatusV2.FAIL,
    SecurityControlStatusV2.BLOCKED,
    SecurityControlStatusV2.NOT_CONFIGURED,
    SecurityControlStatusV2.MANUAL_REVIEW_REQUIRED,
}


class SecurityReadinessServiceV2:
    @staticmethod
    def evaluate(*, controls: tuple[SecurityControlV2, ...], findings: tuple[SecurityFindingV2, ...] = (), tenant_checks: tuple[TenantIsolationCheckV2, ...] = ()) -> SecurityReadinessV2:
        passed = sum(control.status in {SecurityControlStatusV2.PASS, SecurityControlStatusV2.NOT_APPLICABLE} for control in controls)
        failed = sum(control.status in _FAIL_STATES for control in controls)
        critical = sum(control.severity is SecuritySeverityV2.CRITICAL and control.status in _FAIL_STATES for control in controls)
        critical += sum(finding.severity is SecuritySeverityV2.CRITICAL and finding.status in _FAIL_STATES for finding in findings)
        tenant_failure = any(check.disclosure_count or check.mutation_count or check.status is not SecurityControlStatusV2.PASS for check in tenant_checks)
        if tenant_failure:
            critical += 1
        return SecurityReadinessV2(
            controls=controls,
            findings=findings,
            tenant_checks=tenant_checks,
            total_controls=len(controls),
            passed_controls=passed,
            failed_controls=failed,
            critical_failures=critical,
            ready=failed == 0 and critical == 0 and not tenant_failure,
        )
