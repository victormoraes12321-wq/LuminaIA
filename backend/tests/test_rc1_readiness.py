from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from config import settings
from services.readiness import (
    dependency_component,
    migration_readiness_component,
    overall_readiness,
)
from services.security_rollout_v2 import (
    ConfigurationReadinessServiceV2,
    MigrationCompatibilityServiceV2,
)


def _settings_snapshot(**overrides: object):
    values = settings.model_dump()
    values.update(overrides)
    return ConfigurationReadinessServiceV2.from_settings(SimpleNamespace(**values))


class _FailingConnection:
    async def __aenter__(self):
        raise RuntimeError("controlled database outage")

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _FailingEngine:
    def connect(self) -> _FailingConnection:
        return _FailingConnection()


def test_legacy_only_with_healthy_postgres_is_ready() -> None:
    with TestClient(main.app) as client:
        response = client.get("/health/deep")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["ready_for_traffic"] is True
    assert payload["components"]["postgres"]["status"] == "healthy"
    assert payload["components"]["scheduler"]["status"] == "disabled_by_policy"
    assert payload["components"]["migration_compatibility"]["status"] == "disabled_by_policy"


def test_required_postgres_failure_blocks_readiness_but_not_liveness() -> None:
    with TestClient(main.app) as client:
        with patch.object(main, "engine", _FailingEngine()):
            readiness = client.get("/health/deep")
            liveness = client.get("/health")
    assert liveness.json()["status"] == "healthy"
    assert readiness.json()["status"] == "degraded"
    assert readiness.json()["ready_for_traffic"] is False
    assert readiness.json()["components"]["postgres"]["status"] == "degraded"


def test_disabled_v2_dependency_does_not_degrade_required_components() -> None:
    snapshot = _settings_snapshot(
        WORK_QUEUE_MODE="LEGACY_ONLY",
        WORK_QUEUE_APIS_ENABLED=False,
        WORK_QUEUE_WORKER_ENABLED=False,
        PERFORMANCE_CERTIFICATION_MODE=False,
    )
    migration = migration_readiness_component(snapshot, ())
    postgres = dependency_component(
        raw_status="healthy",
        required=True,
        reason="synthetic healthy dependency",
    )
    assert migration["status"] == "disabled_by_policy"
    assert migration["required_in_current_mode"] is False
    assert overall_readiness({"postgres": postgres, "migration": migration}) == "healthy"


def test_enabled_v2_feature_without_schema_prerequisite_is_blocked() -> None:
    snapshot = _settings_snapshot(
        WORK_QUEUE_MODE="V2_PERFORMANCE_CERTIFICATION",
        WORK_QUEUE_APIS_ENABLED=True,
        WORK_QUEUE_WORKER_ENABLED=False,
        PERFORMANCE_CERTIFICATION_MODE=False,
    )
    migration = migration_readiness_component(snapshot, ())
    assert migration["status"] == "degraded"
    assert migration["required_in_current_mode"] is True
    assert migration["details"]["compatibility_state"] == "BLOCKED"
    assert migration["details"]["missing_objects"]


def test_enabled_v2_feature_with_compatible_schema_is_ready() -> None:
    snapshot = _settings_snapshot(
        WORK_QUEUE_MODE="V2_PERFORMANCE_CERTIFICATION",
        WORK_QUEUE_APIS_ENABLED=True,
        WORK_QUEUE_WORKER_ENABLED=False,
        PERFORMANCE_CERTIFICATION_MODE=False,
    )
    tables = MigrationCompatibilityServiceV2.required_objects(26)
    migration = migration_readiness_component(snapshot, tables)
    assert migration["status"] == "healthy"
    assert migration["details"]["compatibility_state"] == "COMPATIBLE"
