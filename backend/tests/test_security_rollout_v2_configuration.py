from __future__ import annotations

from types import SimpleNamespace

import pytest

from config import Settings
from contracts.security_rollout_v2 import ConfigurationReadinessStateV2
from services.security_rollout_v2 import ConfigurationReadinessServiceV2

pytestmark = pytest.mark.no_database


def _settings_stub(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "ENVIRONMENT": "production", "LUMINA_TESTING": False, "LUMINA_DISABLE_EXTERNAL_NETWORK": False,
        "MOCK_ORACLE": False, "MOCK_OPENAI": False, "V2_GLOBAL_EMERGENCY_DISABLE": True,
        "ROLLOUT_EXECUTION_ENABLED": False, "ROLLOUT_CANARY_PERCENTAGE": 0, "ROLLOUT_CANARY_TENANT_ALLOWLIST": (),
        "DASHBOARD_BACKEND_MODE": "LEGACY_ONLY", "DASHBOARD_RUNTIME_APIS_ENABLED": False, "DASHBOARD_ADMIN_APIS_ENABLED": False,
        "DASHBOARD_AI_ASSISTANCE_MODE": "LEGACY_ONLY", "DASHBOARD_AI_APIS_ENABLED": False,
        "POST_SYNC_INSIGHTS_MODE": "LEGACY_ONLY", "POST_SYNC_INSIGHTS_APIS_ENABLED": False, "POST_SYNC_INSIGHTS_AUTO_RUN_ENABLED": False,
        "OBSERVABILITY_MODE": "LEGACY_ONLY", "OBSERVABILITY_APIS_ENABLED": False,
        "WORK_QUEUE_MODE": "LEGACY_ONLY", "WORK_QUEUE_APIS_ENABLED": False, "WORK_QUEUE_WORKER_ENABLED": False,
        "PERFORMANCE_CERTIFICATION_MODE": False,
        "KILL_SWITCH_DASHBOARD_V2_READ": True, "KILL_SWITCH_DASHBOARD_V2_AUTHORING": True,
        "KILL_SWITCH_DASHBOARD_AI": True, "KILL_SWITCH_POST_SYNC_INSIGHTS": True,
        "KILL_SWITCH_OBSERVABILITY_V2": True, "KILL_SWITCH_EVALUATIONS_V2": True,
        "KILL_SWITCH_WORK_QUEUE_V2": True, "KILL_SWITCH_PERFORMANCE_CERTIFICATION": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_default_production_snapshot_is_fail_closed_and_ready() -> None:
    result = ConfigurationReadinessServiceV2.evaluate(ConfigurationReadinessServiceV2.from_settings(_settings_stub()))
    assert result.state is ConfigurationReadinessStateV2.READY


def test_invalid_feature_and_canary_configuration_is_blocked() -> None:
    snapshot = ConfigurationReadinessServiceV2.from_settings(_settings_stub(WORK_QUEUE_APIS_ENABLED=True, ROLLOUT_EXECUTION_ENABLED=True, ROLLOUT_CANARY_PERCENTAGE=5))
    result = ConfigurationReadinessServiceV2.evaluate(snapshot)
    assert result.state is ConfigurationReadinessStateV2.BLOCKED
    assert {"CFG-FEATURE-COHERENCE", "CFG-NO-REAL-ROLLOUT"}.issubset(result.blocking_reasons)


def _production_settings(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "_env_file": None,
        "ENVIRONMENT": "production",
        "LUMINA_TESTING": False,
        "MOCK_ORACLE": False,
        "MOCK_OPENAI": False,
        "LUMINA_DISABLE_EXTERNAL_NETWORK": False,
        "DATABASE_URL": "postgresql+asyncpg://synthetic:synthetic@db.invalid/lumina",
        "SECRET_KEY": "synthetic-secret-key-with-at-least-32-characters",
        "ENCRYPTION_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "OPENAI_API_KEY": "sk-synthetic-not-real-credential-000000000",
        "CORS_ORIGINS": ["https://app.synthetic.invalid"],
    }
    values.update(overrides)
    return values


def test_production_baseline_settings_are_valid_and_disabled() -> None:
    configured = Settings(**_production_settings())
    assert configured.ENVIRONMENT == "production"
    assert configured.WORK_QUEUE_WORKER_ENABLED is False
    assert configured.PERFORMANCE_CERTIFICATION_MODE is False
    assert configured.ROLLOUT_EXECUTION_ENABLED is False
    assert configured.ROLLOUT_CANARY_PERCENTAGE == 0


@pytest.mark.parametrize("override", [
    {"CORS_ORIGINS": ["*"], "CORS_ALLOW_CREDENTIALS": True},
    {"CORS_ORIGINS": ["http://localhost:3002"]},
    {"WORK_QUEUE_WORKER_ENABLED": True},
    {"PERFORMANCE_CERTIFICATION_MODE": True},
    {"ROLLOUT_EXECUTION_ENABLED": True},
    {"ROLLOUT_CANARY_PERCENTAGE": 1},
    {"ROLLOUT_STAGE": "CANARY"},
    {"MOCK_OPENAI": True},
])
def test_unsafe_production_settings_fail_closed(override: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Settings(**_production_settings(**override))
