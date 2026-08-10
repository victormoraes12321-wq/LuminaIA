"""Static rollback matrix; feature disable precedes application/database action."""
from __future__ import annotations

from contracts.security_rollout_v2 import GovernedFeatureV2, RollbackPlanV2, RollbackReadinessV2, RollbackTypeV2


def _plan(feature: GovernedFeatureV2, in_flight: str, persistence: str) -> RollbackPlanV2:
    return RollbackPlanV2(
        feature=feature,
        rollback_types=(RollbackTypeV2.FEATURE, RollbackTypeV2.APPLICATION),
        disable_mechanism="global or feature server-side kill switch, then stage DISABLED",
        in_flight_policy=in_flight,
        persistent_data_policy=persistence,
        previous_app_compatible=True,
        database_down_automatic=False,
        validation_steps=("confirm no new execution", "validate historical data preserved", "run directed regression before re-enable"),
    )


_PLANS = (
    _plan(GovernedFeatureV2.DASHBOARD_V2_READ, "finish safe reads; cancel stale browser requests", "published dashboards and revision history remain immutable"),
    _plan(GovernedFeatureV2.DASHBOARD_V2_AUTHORING, "reject new writes and let committed transactions finish", "drafts, revisions and publications remain stored"),
    _plan(GovernedFeatureV2.DASHBOARD_AI, "cancel provider/tool work and reject new proposals", "published dashboards remain readable and existing drafts remain"),
    _plan(GovernedFeatureV2.POST_SYNC_INSIGHTS, "stop new publication/outbox consumption", "sync and reconciliation remain intact; historical insights are not deleted"),
    _plan(GovernedFeatureV2.OBSERVABILITY_V2, "business flow continues; security telemetry failure blocks readiness", "historical telemetry remains immutable"),
    _plan(GovernedFeatureV2.EVALUATIONS_V2, "cancel new evaluation execution", "runs and baselines remain immutable"),
    _plan(GovernedFeatureV2.WORK_QUEUE_V2, "stop enqueue, drain workers, preserve leases and apply cancellation policy", "queued jobs persist and no job is silently lost"),
    _plan(GovernedFeatureV2.PERFORMANCE_CERTIFICATION, "cancel synthetic run", "provisional baselines remain evidence only"),
)


class RollbackReadinessServiceV2:
    @staticmethod
    def evaluate() -> RollbackReadinessV2:
        missing = tuple(plan.feature.value for plan in _PLANS if not plan.disable_mechanism or not plan.validation_steps)
        return RollbackReadinessV2(plans=_PLANS, ready=not missing, blocking_reasons=missing)
