"""Static governed feature inventory and dependency registry."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    FeatureRolloutPolicyV2,
    GovernedFeatureV2,
    RollbackTypeV2,
)


_POLICIES: dict[GovernedFeatureV2, FeatureRolloutPolicyV2] = {
    GovernedFeatureV2.DASHBOARD_V2_READ: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.DASHBOARD_V2_READ,
        required_migration=22,
        dependency_ids=("dashboard_backend", "safe_pg", "validation_provenance"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.DASHBOARD_V2_AUTHORING: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.DASHBOARD_V2_AUTHORING,
        required_migration=22,
        dependency_ids=("dashboard_backend", "blueprint_v2", "audit"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.DASHBOARD_AI: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.DASHBOARD_AI,
        required_migration=23,
        dependency_ids=("dashboard_v2", "ai_orchestration", "governed_tools", "safe_pg", "validation_provenance"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.POST_SYNC_INSIGHTS: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.POST_SYNC_INSIGHTS,
        required_migration=24,
        dependency_ids=("sync_reconciliation_certified", "post_sync_feature"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.OBSERVABILITY_V2: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.OBSERVABILITY_V2,
        required_migration=25,
        dependency_ids=("observability_storage", "redaction", "cardinality_guard"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.EVALUATIONS_V2: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.EVALUATIONS_V2,
        required_migration=25,
        dependency_ids=("observability_v2", "evaluation_registry", "synthetic_corpus"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.WORK_QUEUE_V2: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.WORK_QUEUE_V2,
        required_migration=26,
        dependency_ids=("work_queue_storage", "observability_v2", "worker_enable"),
        allowed_environments=("test", "staging", "production"),
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
    ),
    GovernedFeatureV2.PERFORMANCE_CERTIFICATION: FeatureRolloutPolicyV2(
        feature=GovernedFeatureV2.PERFORMANCE_CERTIFICATION,
        required_migration=26,
        dependency_ids=("work_queue_v2", "synthetic_test_environment"),
        allowed_environments=("test",),
        rollback_types=(RollbackTypeV2.FEATURE,),
    ),
}


class GovernedFeatureRegistryV2:
    @staticmethod
    def list_policies() -> tuple[FeatureRolloutPolicyV2, ...]:
        return tuple(_POLICIES[feature] for feature in GovernedFeatureV2)

    @staticmethod
    def get_policy(feature: GovernedFeatureV2) -> FeatureRolloutPolicyV2:
        return _POLICIES[feature]
