from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

import contracts.dashboard_backend_v2 as contracts
from contracts.dashboard_backend_v2 import (
    DashboardBackupManifestV2,
    DashboardBackupTableV2,
    DashboardCreateRequestV2,
    DashboardIdentityRecordV2,
    DashboardOwnershipTypeV2,
    DashboardOwnershipV2,
    DashboardRecordV2,
    DashboardRestoreValidationV2,
)
from contracts.dashboard_blueprint_v2 import DashboardLifecycleV2, DashboardOriginV2
from services.dashboard_blueprint_v2.fixtures import build_executive_dashboard

pytestmark = pytest.mark.no_database


EXPECTED_CONTRACTS = {
    "DashboardRecordV2", "DashboardIdentityRecordV2", "DashboardOwnershipV2",
    "DashboardCollaboratorV2", "DashboardAccessPolicyV2", "DashboardLifecyclePolicyV2",
    "DashboardCreateRequestV2", "DashboardCreateResultV2", "DashboardUpdateDraftRequestV2",
    "DashboardRevisionV2", "DashboardRevisionReferenceV2", "DashboardVisualRevisionV2",
    "DashboardSemanticRevisionV2", "DashboardRevisionCreateRequestV2", "DashboardReviewRequestV2",
    "DashboardReviewDecisionV2", "DashboardApprovalV2", "DashboardPublicationV2",
    "DashboardPublicationRequestV2", "DashboardPublicationResultV2", "DashboardSupersessionV2",
    "DashboardRollbackRequestV2", "DashboardRollbackResultV2", "DashboardArchiveRequestV2",
    "DashboardCloneRequestV2", "DashboardListRequestV2", "DashboardListItemV2",
    "DashboardDetailV2", "DashboardRuntimeRequestV2", "DashboardRuntimePlanV2",
    "DashboardWidgetRuntimePlanV2", "DashboardWidgetRuntimeResultV2", "DashboardRuntimeResultV2",
    "DashboardRuntimeWarningV2", "DashboardRuntimeProvenanceV2", "DashboardAuditEventV2",
    "DashboardEvaluationCaseV2", "DashboardEvaluationResultV2", "DashboardBackupManifestV2",
    "DashboardRestoreValidationV2",
}


def test_public_contract_surface_is_complete() -> None:
    assert contracts.DASHBOARD_BACKEND_CONTRACT_VERSION == "lumina.dashboard-backend/1.0"
    assert EXPECTED_CONTRACTS.issubset(set(contracts.__all__))


def test_central_contracts_are_strict_and_frozen() -> None:
    now = datetime.now(timezone.utc)
    record = DashboardRecordV2(
        identity=DashboardIdentityRecordV2(dashboard_id="dashboard.001", canonical_name="dashboard.sales", title="Vendas", description="Resumo executivo de vendas"),
        ownership=DashboardOwnershipV2(ownership_type=DashboardOwnershipTypeV2.USER, owner_reference="user.001"),
        lifecycle=DashboardLifecycleV2.DRAFT, head_lifecycle=DashboardLifecycleV2.DRAFT, origin=DashboardOriginV2.HUMAN_AUTHORED,
        classification="TENANT_BUSINESS_DATA", lock_version=1, created_at=now, updated_at=now,
    )
    with pytest.raises(ValidationError):
        DashboardRecordV2.model_validate({**record.model_dump(), "tenant_id": "client-controlled"})
    with pytest.raises(ValidationError):
        record.lock_version = 2  # type: ignore[misc]


def test_create_request_has_no_owner_or_tenant_mass_assignment() -> None:
    blueprint = build_executive_dashboard()
    request = DashboardCreateRequestV2(
        canonical_name=blueprint.identity.canonical_name, title=blueprint.identity.title,
        description=blueprint.identity.description, blueprint=blueprint,
        origin=DashboardOriginV2.HUMAN_AUTHORED, reason="Criação governada",
    )
    payload = request.model_dump(mode="json")
    assert "tenant_id" not in payload
    assert "owner" not in payload
    with pytest.raises(ValidationError):
        DashboardCreateRequestV2.model_validate({**payload, "tenant_id": "tenant.evil"})


def test_backup_and_restore_contracts_are_sanitized_and_explicit() -> None:
    now = datetime.now(timezone.utc)
    table = DashboardBackupTableV2(table_name="dashboards_v2", row_count=2, content_checksum="a" * 64)
    manifest = DashboardBackupManifestV2(backup_id="backup.synthetic.001", tables=(table,), created_at=now, checksum="b" * 64)
    restored = DashboardRestoreValidationV2(backup_id=manifest.backup_id, restored=True, row_counts_match=True, checksums_match=True, active_publication_valid=True, tenant_isolation_valid=True, constraints_valid=True, indexes_valid=True, validated_at=now)
    assert manifest.sanitized is True
    assert all(restored.model_dump().values())


@pytest.mark.parametrize("field,value", [("canonical_name", "x"), ("title", "x"), ("description", "short")])
def test_create_request_limits(field: str, value: str) -> None:
    blueprint = build_executive_dashboard()
    payload = {
        "canonical_name": blueprint.identity.canonical_name,
        "title": blueprint.identity.title,
        "description": blueprint.identity.description,
        "blueprint": blueprint,
        "origin": DashboardOriginV2.HUMAN_AUTHORED,
        "reason": "Criação governada",
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        DashboardCreateRequestV2.model_validate(payload)
