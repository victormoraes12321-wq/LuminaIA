from __future__ import annotations

from datetime import datetime, timezone

import pytest

from contracts.dashboard_backend_v2 import (
    DashboardCapabilityBackendV2,
)
from services.dashboard_backend_v2.application import DashboardBackupValidationServiceV2
from services.dashboard_backend_v2.errors import DashboardBackendError
from services.dashboard_backend_v2.legacy_dry_run import DashboardLegacyDryRunServiceV2
from services.dashboard_backend_v2.observability import (
    DASHBOARD_STRUCTURAL_METRICS,
    DashboardObservabilityV2,
)
from services.dashboard_backend_v2.policy import DashboardAccessPolicyServiceV2


pytestmark = pytest.mark.no_database


def test_ungranted_cross_user_cannot_read_a_draft() -> None:
    capabilities = DashboardAccessPolicyServiceV2.effective_capabilities(
        global_role="GESTOR", is_owner=False, collaborator_role=None
    )
    assert capabilities == frozenset()


def test_published_tenant_policy_is_intersected_with_global_role() -> None:
    capabilities = DashboardAccessPolicyServiceV2.effective_capabilities(
        global_role="CONSULTA",
        is_owner=False,
        collaborator_role=None,
        tenant_policy_capabilities=frozenset({
            DashboardCapabilityBackendV2.VIEW,
            DashboardCapabilityBackendV2.EXECUTE,
            DashboardCapabilityBackendV2.PUBLISH,
        }),
    )
    assert capabilities == frozenset({
        DashboardCapabilityBackendV2.VIEW,
        DashboardCapabilityBackendV2.EXECUTE,
    })


def test_legacy_dry_run_preserves_input_and_never_persists() -> None:
    legacy = {"name": "Executivo", "components": [{"type": "KPI"}], "legacy_id": "x"}
    before = repr(legacy)
    result = DashboardLegacyDryRunServiceV2(enabled=True, shadow=True).validate(legacy)
    assert result.proposal is not None
    assert result.original_unchanged is True
    assert repr(legacy) == before
    assert any("no V2 persistence" in warning for warning in result.warnings)


def test_disabled_legacy_dry_run_fails_closed() -> None:
    with pytest.raises(DashboardBackendError) as error:
        DashboardLegacyDryRunServiceV2(enabled=False).validate({})
    assert error.value.code == "DASHBOARD_RUNTIME_UNAVAILABLE"


def test_observability_accepts_every_structural_metric_and_rejects_payload_dimensions() -> None:
    sink = DashboardObservabilityV2()
    for metric in DASHBOARD_STRUCTURAL_METRICS:
        sink.record(metric, dimensions={"rollout_mode": "LEGACY_ONLY"})
    assert len(sink.snapshot()) == len(DASHBOARD_STRUCTURAL_METRICS)
    with pytest.raises(ValueError):
        sink.record("runtime_requests", dimensions={"business_value": "300.00"})
    with pytest.raises(ValueError):
        sink.record("raw_result", value=1)


def test_backup_manifest_and_restore_validation_are_deterministic_and_sanitized() -> None:
    tables = {
        "dashboards_v2": [
            {"id": "dashboard.synthetic.1", "description": "excluded", "lock_version": 1}
        ],
        "dashboard_revisions_v2": [
            {"id": "revision.synthetic.1", "blueprint_json": {"secret": "excluded"}}
        ],
    }
    first = DashboardBackupValidationServiceV2.create_manifest(
        backup_id="backup.synthetic.1", tables=tables
    )
    second = DashboardBackupValidationServiceV2.create_manifest(
        backup_id="backup.synthetic.1", tables=tables
    )
    assert [(item.table_name, item.row_count, item.content_checksum) for item in first.tables] == [
        (item.table_name, item.row_count, item.content_checksum) for item in second.tables
    ]
    restored = DashboardBackupValidationServiceV2.validate_restore(
        manifest=first,
        restored_manifest=second,
        active_publication_valid=True,
        tenant_isolation_valid=True,
        constraints_valid=True,
        indexes_valid=True,
    )
    assert restored.restored and restored.row_counts_match and restored.checksums_match

