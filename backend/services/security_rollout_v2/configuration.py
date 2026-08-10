"""Deterministic, secret-free configuration readiness checks."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    ConfigurationReadinessStateV2,
    ConfigurationReadinessV2,
    ConfigurationSnapshotV2,
    FeatureConfigurationV2,
    GovernedFeatureV2,
    SecurityControlStatusV2,
    SecurityControlV2,
    SecuritySeverityV2,
    ThreatSurfaceKindV2,
)


def _control(control_id: str, status: SecurityControlStatusV2, title: str, evidence: str) -> SecurityControlV2:
    return SecurityControlV2(
        control_id=control_id,
        surface=ThreatSurfaceKindV2.ROLLOUT,
        status=status,
        severity=SecuritySeverityV2.CRITICAL if status is SecurityControlStatusV2.FAIL else SecuritySeverityV2.INFO,
        title=title,
        evidence=evidence,
    )


class ConfigurationReadinessServiceV2:
    @staticmethod
    def from_settings(settings: object) -> ConfigurationSnapshotV2:
        features = (
            FeatureConfigurationV2(feature=GovernedFeatureV2.DASHBOARD_V2_READ, mode=str(getattr(settings, "DASHBOARD_BACKEND_MODE")), api_enabled=bool(getattr(settings, "DASHBOARD_RUNTIME_APIS_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_DASHBOARD_V2_READ"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.DASHBOARD_V2_AUTHORING, mode=str(getattr(settings, "DASHBOARD_BACKEND_MODE")), api_enabled=bool(getattr(settings, "DASHBOARD_ADMIN_APIS_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_DASHBOARD_V2_AUTHORING"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.DASHBOARD_AI, mode=str(getattr(settings, "DASHBOARD_AI_ASSISTANCE_MODE")), api_enabled=bool(getattr(settings, "DASHBOARD_AI_APIS_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_DASHBOARD_AI"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.POST_SYNC_INSIGHTS, mode=str(getattr(settings, "POST_SYNC_INSIGHTS_MODE")), api_enabled=bool(getattr(settings, "POST_SYNC_INSIGHTS_APIS_ENABLED")), execution_enabled=bool(getattr(settings, "POST_SYNC_INSIGHTS_AUTO_RUN_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_POST_SYNC_INSIGHTS"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.OBSERVABILITY_V2, mode=str(getattr(settings, "OBSERVABILITY_MODE")), api_enabled=bool(getattr(settings, "OBSERVABILITY_APIS_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_OBSERVABILITY_V2"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.EVALUATIONS_V2, mode=str(getattr(settings, "OBSERVABILITY_MODE")), api_enabled=bool(getattr(settings, "OBSERVABILITY_APIS_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_EVALUATIONS_V2"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.WORK_QUEUE_V2, mode=str(getattr(settings, "WORK_QUEUE_MODE")), api_enabled=bool(getattr(settings, "WORK_QUEUE_APIS_ENABLED")), worker_enabled=bool(getattr(settings, "WORK_QUEUE_WORKER_ENABLED")), execution_enabled=bool(getattr(settings, "WORK_QUEUE_WORKER_ENABLED")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_WORK_QUEUE_V2"))),
            FeatureConfigurationV2(feature=GovernedFeatureV2.PERFORMANCE_CERTIFICATION, mode="ENABLED" if bool(getattr(settings, "PERFORMANCE_CERTIFICATION_MODE")) else "DISABLED", execution_enabled=bool(getattr(settings, "PERFORMANCE_CERTIFICATION_MODE")), kill_switch_active=bool(getattr(settings, "KILL_SWITCH_PERFORMANCE_CERTIFICATION"))),
        )
        return ConfigurationSnapshotV2(
            environment=str(getattr(settings, "ENVIRONMENT")),
            testing_enabled=bool(getattr(settings, "LUMINA_TESTING")),
            external_network_disabled=bool(getattr(settings, "LUMINA_DISABLE_EXTERNAL_NETWORK")),
            mock_oracle=bool(getattr(settings, "MOCK_ORACLE")),
            mock_openai=bool(getattr(settings, "MOCK_OPENAI")),
            global_emergency_disable=bool(getattr(settings, "V2_GLOBAL_EMERGENCY_DISABLE")),
            rollout_execution_enabled=bool(getattr(settings, "ROLLOUT_EXECUTION_ENABLED")),
            canary_percentage=int(getattr(settings, "ROLLOUT_CANARY_PERCENTAGE")),
            canary_tenant_count=len(tuple(getattr(settings, "ROLLOUT_CANARY_TENANT_ALLOWLIST"))),
            features=features,
        )

    @staticmethod
    def evaluate(snapshot: ConfigurationSnapshotV2) -> ConfigurationReadinessV2:
        controls: list[SecurityControlV2] = []
        production = snapshot.environment == "production"
        test_safe = not production or (
            not snapshot.testing_enabled and not snapshot.mock_oracle and not snapshot.mock_openai
        )
        controls.append(_control("CFG-TEST-BOUNDARY", SecurityControlStatusV2.PASS if test_safe else SecurityControlStatusV2.FAIL, "Test-only flags are isolated", "production rejects testing and fake provider flags" if test_safe else "test-only or fake provider flag enabled in production"))

        performance_safe = not production or all(
            feature.feature is not GovernedFeatureV2.PERFORMANCE_CERTIFICATION or not feature.execution_enabled
            for feature in snapshot.features
        )
        controls.append(_control("CFG-PERFORMANCE-PROD", SecurityControlStatusV2.PASS if performance_safe else SecurityControlStatusV2.FAIL, "Synthetic performance is not a production mode", "performance certification disabled in production" if performance_safe else "performance certification enabled in production"))

        invalid_features: list[str] = []
        for feature in snapshot.features:
            legacy = feature.mode == "LEGACY_ONLY" or feature.mode == "DISABLED"
            if legacy and (feature.api_enabled or feature.worker_enabled or feature.execution_enabled):
                invalid_features.append(feature.feature.value)
            if feature.worker_enabled and not feature.execution_enabled:
                invalid_features.append(f"{feature.feature.value}:worker_without_execution")
        controls.append(_control("CFG-FEATURE-COHERENCE", SecurityControlStatusV2.PASS if not invalid_features else SecurityControlStatusV2.FAIL, "Feature modes and execution flags are coherent", "no legacy feature has API/worker/execution enabled" if not invalid_features else "invalid combinations: " + ",".join(sorted(set(invalid_features)))))

        no_real_rollout = not production or (
            not snapshot.rollout_execution_enabled
            and snapshot.canary_percentage == 0
            and snapshot.canary_tenant_count == 0
        )
        controls.append(_control("CFG-NO-REAL-ROLLOUT", SecurityControlStatusV2.PASS if no_real_rollout else SecurityControlStatusV2.FAIL, "Production rollout remains disabled", "rollout disabled and canary cohort empty" if no_real_rollout else "production rollout or canary selection is active"))

        failures = tuple(c for c in controls if c.status is SecurityControlStatusV2.FAIL)
        state = ConfigurationReadinessStateV2.BLOCKED if failures else ConfigurationReadinessStateV2.READY
        return ConfigurationReadinessV2(
            state=state,
            controls=tuple(controls),
            blocking_reasons=tuple(c.control_id for c in failures),
        )
