from __future__ import annotations

import pytest

from contracts.security_rollout_v2 import (
    CanaryPolicyV2,
    FeatureRolloutStageV2,
    GovernedFeatureV2,
    RolloutDecisionV2,
    RolloutEvidenceV2,
    RolloutReadinessStateV2,
)
from services.security_rollout_v2 import (
    AuthorizationMatrixServiceV2,
    CanaryPolicyServiceV2,
    GovernedFeatureRegistryV2,
    GovernedRolloutPolicyV2,
    RollbackReadinessServiceV2,
    RolloutReadinessServiceV2,
)

pytestmark = pytest.mark.no_database


def _evidence(stage: FeatureRolloutStageV2, **overrides: bool | str) -> RolloutEvidenceV2:
    values: dict[str, bool | str | FeatureRolloutStageV2] = {
        "environment": "staging",
        "requested_stage": stage,
        "migration_compatible": True,
        "security_ready": True,
        "tenant_isolation_pass": True,
        "openapi_reproducible": True,
        "evaluations_pass": True,
        "observability_ready": True,
        "error_budget_available": True,
        "error_budget_exhausted": False,
        "performance_structural_pass": True,
        "queue_healthy": True,
        "rollback_ready": True,
        "dependencies_satisfied": True,
        "full_regression_pass": True,
        "runbook_ready": True,
        "global_kill_switch_active": False,
        "feature_kill_switch_active": False,
        "tenant_eligible": True,
        "user_capability_allowed": True,
        "critical_security_failure": False,
    }
    values.update(overrides)
    return RolloutEvidenceV2.model_validate(values)


def test_static_inventory_is_complete_and_unique() -> None:
    policies = GovernedFeatureRegistryV2.list_policies()
    assert len(policies) == len(GovernedFeatureV2) == 8
    assert {p.feature for p in policies} == set(GovernedFeatureV2)
    assert all(p.kill_switch_required and p.rollback_types for p in policies)


def test_authorization_matrix_is_deny_by_default() -> None:
    assert AuthorizationMatrixServiceV2.decide(server_role="CONSULTA", capability="dashboard.read").decision.value == "ALLOW"
    assert AuthorizationMatrixServiceV2.decide(server_role="CONSULTA", capability="dashboard.publish").decision.value == "DENY"
    assert AuthorizationMatrixServiceV2.decide(server_role="ADMIN", capability="unknown.capability").decision.value == "DENY"


def test_closed_stage_transitions_and_canary_readiness() -> None:
    assert GovernedRolloutPolicyV2.can_transition(FeatureRolloutStageV2.DISABLED, FeatureRolloutStageV2.AUDIT_ONLY)
    assert not GovernedRolloutPolicyV2.can_transition(FeatureRolloutStageV2.DISABLED, FeatureRolloutStageV2.CANARY)
    result = RolloutReadinessServiceV2.evaluate(GovernedFeatureV2.DASHBOARD_V2_READ, _evidence(FeatureRolloutStageV2.CANARY))
    assert result.state is RolloutReadinessStateV2.READY_FOR_CANARY
    assert result.decision is RolloutDecisionV2.ALLOW_CANARY


def test_kill_switch_and_critical_failure_take_precedence() -> None:
    blocked = RolloutReadinessServiceV2.evaluate(
        GovernedFeatureV2.WORK_QUEUE_V2,
        _evidence(FeatureRolloutStageV2.CANARY, global_kill_switch_active=True),
    )
    assert blocked.state is RolloutReadinessStateV2.BLOCKED
    assert "GLOBAL_EMERGENCY_DISABLE" in blocked.blocking_reasons
    rollback = RolloutReadinessServiceV2.evaluate(
        GovernedFeatureV2.WORK_QUEUE_V2,
        _evidence(FeatureRolloutStageV2.CANARY, critical_security_failure=True),
    )
    assert rollback.decision is RolloutDecisionV2.ROLLBACK


def test_full_rollout_is_deliberately_not_certifiable_here() -> None:
    result = RolloutReadinessServiceV2.evaluate(GovernedFeatureV2.DASHBOARD_AI, _evidence(FeatureRolloutStageV2.FULL))
    assert result.state is RolloutReadinessStateV2.BLOCKED
    assert "PRODUCTION_EVIDENCE" in result.blocking_reasons


def test_canary_is_stable_server_side_and_production_denied() -> None:
    policy = CanaryPolicyV2(policy_version="canary-v1", percentage=25, explicit_internal_tenants=("internal-a",))
    first = CanaryPolicyServiceV2.assign(trusted_tenant_identifier="tenant-a", environment="staging", policy=policy)
    second = CanaryPolicyServiceV2.assign(trusted_tenant_identifier="tenant-a", environment="staging", policy=policy)
    assert first == second
    assert CanaryPolicyServiceV2.assign(trusted_tenant_identifier="internal-a", environment="staging", policy=policy).eligible
    assert not CanaryPolicyServiceV2.assign(trusted_tenant_identifier="tenant-a", environment="production", policy=policy).eligible


def test_every_feature_has_rollback_first_plan() -> None:
    readiness = RollbackReadinessServiceV2.evaluate()
    assert readiness.ready
    assert {p.feature for p in readiness.plans} == set(GovernedFeatureV2)
    assert all(not p.database_down_automatic and p.previous_app_compatible for p in readiness.plans)
