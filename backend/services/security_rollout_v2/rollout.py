"""Fail-closed rollout stage transitions and readiness gates."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    FeatureRolloutStageV2,
    GateOutcomeV2,
    GovernedFeatureV2,
    RolloutDecisionV2,
    RolloutEvidenceV2,
    RolloutGateV2,
    RolloutReadinessStateV2,
    RolloutReadinessV2,
)

_TRANSITIONS: dict[FeatureRolloutStageV2, frozenset[FeatureRolloutStageV2]] = {
    FeatureRolloutStageV2.DISABLED: frozenset({FeatureRolloutStageV2.AUDIT_ONLY}),
    FeatureRolloutStageV2.AUDIT_ONLY: frozenset({FeatureRolloutStageV2.SHADOW, FeatureRolloutStageV2.PAUSED}),
    FeatureRolloutStageV2.SHADOW: frozenset({FeatureRolloutStageV2.INTERNAL, FeatureRolloutStageV2.PAUSED, FeatureRolloutStageV2.ROLLED_BACK}),
    FeatureRolloutStageV2.INTERNAL: frozenset({FeatureRolloutStageV2.CANARY, FeatureRolloutStageV2.PAUSED, FeatureRolloutStageV2.ROLLED_BACK}),
    FeatureRolloutStageV2.CANARY: frozenset({FeatureRolloutStageV2.EXPANDED, FeatureRolloutStageV2.PAUSED, FeatureRolloutStageV2.ROLLED_BACK}),
    FeatureRolloutStageV2.EXPANDED: frozenset({FeatureRolloutStageV2.FULL, FeatureRolloutStageV2.PAUSED, FeatureRolloutStageV2.ROLLED_BACK}),
    FeatureRolloutStageV2.FULL: frozenset({FeatureRolloutStageV2.PAUSED, FeatureRolloutStageV2.ROLLED_BACK}),
    FeatureRolloutStageV2.PAUSED: frozenset({FeatureRolloutStageV2.ROLLED_BACK, FeatureRolloutStageV2.DISABLED}),
    FeatureRolloutStageV2.ROLLED_BACK: frozenset({FeatureRolloutStageV2.DISABLED, FeatureRolloutStageV2.AUDIT_ONLY}),
}


class GovernedRolloutPolicyV2:
    @staticmethod
    def can_transition(current: FeatureRolloutStageV2, target: FeatureRolloutStageV2) -> bool:
        return target in _TRANSITIONS[current]


class RolloutReadinessServiceV2:
    _ORDERED_GATES = (
        ("GLOBAL_EMERGENCY_DISABLE", "global_kill_switch_active", True),
        ("FEATURE_KILL_SWITCH", "feature_kill_switch_active", True),
        ("ENVIRONMENT_ALLOW", None, True),
        ("MIGRATION_READINESS", "migration_compatible", True),
        ("SECURITY_READINESS", "security_ready", True),
        ("TENANT_ISOLATION", "tenant_isolation_pass", True),
        ("OPENAPI_REPRODUCIBILITY", "openapi_reproducible", False),
        ("EVALUATIONS", "evaluations_pass", True),
        ("OBSERVABILITY", "observability_ready", True),
        ("ERROR_BUDGET", "error_budget_available", False),
        ("PERFORMANCE", "performance_structural_pass", False),
        ("QUEUE_HEALTH", "queue_healthy", False),
        ("ROLLBACK_READINESS", "rollback_ready", True),
        ("DEPENDENCIES", "dependencies_satisfied", True),
        ("TENANT_ELIGIBILITY", "tenant_eligible", False),
        ("USER_CAPABILITY", "user_capability_allowed", True),
    )

    @staticmethod
    def _required_for_stage(stage: FeatureRolloutStageV2, gate_id: str) -> bool:
        base = {"GLOBAL_EMERGENCY_DISABLE", "FEATURE_KILL_SWITCH", "ENVIRONMENT_ALLOW", "MIGRATION_READINESS", "SECURITY_READINESS", "TENANT_ISOLATION", "OBSERVABILITY", "DEPENDENCIES", "ROLLBACK_READINESS"}
        if stage in {FeatureRolloutStageV2.INTERNAL, FeatureRolloutStageV2.CANARY, FeatureRolloutStageV2.EXPANDED, FeatureRolloutStageV2.FULL}:
            base |= {"OPENAPI_REPRODUCIBILITY", "EVALUATIONS", "USER_CAPABILITY"}
        if stage in {FeatureRolloutStageV2.CANARY, FeatureRolloutStageV2.EXPANDED, FeatureRolloutStageV2.FULL}:
            base |= {"ERROR_BUDGET", "PERFORMANCE", "TENANT_ELIGIBILITY"}
        return gate_id in base

    @classmethod
    def evaluate(cls, feature: GovernedFeatureV2, evidence: RolloutEvidenceV2) -> RolloutReadinessV2:
        gates: list[RolloutGateV2] = []
        for gate_id, attribute, critical in cls._ORDERED_GATES:
            if gate_id == "GLOBAL_EMERGENCY_DISABLE":
                passed = not evidence.global_kill_switch_active
            elif gate_id == "FEATURE_KILL_SWITCH":
                passed = not evidence.feature_kill_switch_active
            elif gate_id == "ENVIRONMENT_ALLOW":
                passed = evidence.environment in {"test", "staging", "production"}
            else:
                passed = bool(getattr(evidence, str(attribute)))
            if gate_id == "ERROR_BUDGET" and evidence.error_budget_exhausted:
                passed = False
            if evidence.critical_security_failure and gate_id == "SECURITY_READINESS":
                passed = False
            required = cls._required_for_stage(evidence.requested_stage, gate_id)
            outcome = GateOutcomeV2.PASS if passed or not required else GateOutcomeV2.BLOCKED
            gates.append(RolloutGateV2(gate_id=gate_id, outcome=outcome, reason_code=f"{gate_id}_{'PASS' if outcome is GateOutcomeV2.PASS else 'BLOCKED'}", critical=critical and required))

        if evidence.requested_stage is FeatureRolloutStageV2.FULL:
            gates.append(RolloutGateV2(gate_id="PRODUCTION_EVIDENCE", outcome=GateOutcomeV2.BLOCKED, reason_code="FULL_REQUIRES_FUTURE_PRODUCTION_EVIDENCE", critical=True))
        if evidence.requested_stage in {FeatureRolloutStageV2.INTERNAL, FeatureRolloutStageV2.CANARY, FeatureRolloutStageV2.EXPANDED, FeatureRolloutStageV2.FULL} and not evidence.full_regression_pass:
            gates.append(RolloutGateV2(gate_id="FULL_REGRESSION", outcome=GateOutcomeV2.BLOCKED, reason_code="FULL_REGRESSION_BLOCKED", critical=True))
        if evidence.requested_stage in {FeatureRolloutStageV2.CANARY, FeatureRolloutStageV2.EXPANDED, FeatureRolloutStageV2.FULL} and not evidence.runbook_ready:
            gates.append(RolloutGateV2(gate_id="RUNBOOK", outcome=GateOutcomeV2.BLOCKED, reason_code="RUNBOOK_BLOCKED", critical=True))

        blocked = tuple(g.gate_id for g in gates if g.outcome is not GateOutcomeV2.PASS)
        if blocked:
            state = RolloutReadinessStateV2.BLOCKED
            decision = RolloutDecisionV2.ROLLBACK if evidence.critical_security_failure else RolloutDecisionV2.DENY
        else:
            mapping = {
                FeatureRolloutStageV2.AUDIT_ONLY: (RolloutReadinessStateV2.READY_FOR_AUDIT, RolloutDecisionV2.ALLOW_AUDIT),
                FeatureRolloutStageV2.SHADOW: (RolloutReadinessStateV2.READY_FOR_SHADOW, RolloutDecisionV2.ALLOW_SHADOW),
                FeatureRolloutStageV2.INTERNAL: (RolloutReadinessStateV2.READY_FOR_INTERNAL, RolloutDecisionV2.ALLOW_INTERNAL),
                FeatureRolloutStageV2.CANARY: (RolloutReadinessStateV2.READY_FOR_CANARY, RolloutDecisionV2.ALLOW_CANARY),
                FeatureRolloutStageV2.EXPANDED: (RolloutReadinessStateV2.READY_FOR_EXPANSION, RolloutDecisionV2.ALLOW_EXPANSION),
            }
            state, decision = mapping.get(evidence.requested_stage, (RolloutReadinessStateV2.NOT_READY, RolloutDecisionV2.DENY))
        return RolloutReadinessV2(feature=feature, requested_stage=evidence.requested_stage, state=state, decision=decision, gates=tuple(gates), blocking_reasons=blocked)
