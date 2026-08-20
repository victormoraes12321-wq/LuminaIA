from __future__ import annotations

import pytest

from contracts.dashboard_backend_v2 import DashboardCapabilityBackendV2, DashboardCollaboratorRoleV2
from contracts.dashboard_blueprint_v2 import DashboardLifecycleV2
from services.dashboard_backend_v2.errors import DashboardBackendError, ERROR_CODES
from services.dashboard_backend_v2.policy import (
    DashboardAccessPolicyServiceV2,
    DashboardBackendMode,
    DashboardLifecycleServiceV2,
    TRANSITIONS,
)

pytestmark = pytest.mark.no_database


ALLOWED = {
    ("DRAFT", "IN_REVIEW"), ("IN_REVIEW", "DRAFT"), ("IN_REVIEW", "APPROVED"),
    ("IN_REVIEW", "REJECTED"), ("APPROVED", "PUBLISHED"), ("APPROVED", "DRAFT"),
    ("PUBLISHED", "SUPERSEDED"), ("PUBLISHED", "DEPRECATED"),
    ("SUPERSEDED", "ARCHIVED"), ("DEPRECATED", "ARCHIVED"), ("REJECTED", "DRAFT"),
}


def test_lifecycle_matrix_exact() -> None:
    actual = {(source.value, target.value) for source, targets in TRANSITIONS.items() for target in targets}
    assert actual == ALLOWED


@pytest.mark.parametrize("source,target", sorted(ALLOWED))
def test_each_allowed_transition(source: str, target: str) -> None:
    DashboardLifecycleServiceV2.assert_transition(DashboardLifecycleV2(source), DashboardLifecycleV2(target))


@pytest.mark.parametrize("source,target", [("PUBLISHED", "DRAFT"), ("ARCHIVED", "DRAFT"), ("REJECTED", "PUBLISHED"), ("DRAFT", "PUBLISHED")])
def test_forbidden_transitions_fail_closed(source: str, target: str) -> None:
    with pytest.raises(DashboardBackendError, match="não permitida"):
        DashboardLifecycleServiceV2.assert_transition(DashboardLifecycleV2(source), DashboardLifecycleV2(target))


def test_only_published_is_runtime_eligible() -> None:
    assert [state for state in DashboardLifecycleV2 if DashboardLifecycleServiceV2.runtime_eligible(state)] == [DashboardLifecycleV2.PUBLISHED]


def test_rollout_defaults_have_closed_legacy_mode() -> None:
    assert DashboardBackendMode.LEGACY_ONLY.value == "LEGACY_ONLY"
    assert len(DashboardBackendMode) == 5


def test_global_role_and_collaborator_grant_are_intersected() -> None:
    visual = DashboardAccessPolicyServiceV2.effective_capabilities(global_role="GESTOR", is_owner=False, collaborator_role=DashboardCollaboratorRoleV2.EDITOR_VISUAL)
    assert DashboardCapabilityBackendV2.EDIT_VISUAL in visual
    assert DashboardCapabilityBackendV2.EDIT_SEMANTIC not in visual
    publisher_without_global_publish = DashboardAccessPolicyServiceV2.effective_capabilities(global_role="GESTOR", is_owner=False, collaborator_role=DashboardCollaboratorRoleV2.PUBLISHER)
    assert DashboardCapabilityBackendV2.PUBLISH not in publisher_without_global_publish


def test_owner_does_not_recover_capability_missing_from_global_rbac() -> None:
    consulta_owner = DashboardAccessPolicyServiceV2.effective_capabilities(global_role="CONSULTA", is_owner=True, collaborator_role=None)
    assert DashboardCapabilityBackendV2.EDIT_VISUAL not in consulta_owner
    assert DashboardCapabilityBackendV2.PUBLISH not in consulta_owner


def test_typed_error_catalog_is_complete() -> None:
    assert len(ERROR_CODES) == 28
    assert "DASHBOARD_NOT_FOUND" in ERROR_CODES
    assert "DASHBOARD_BACKUP_VALIDATION_FAILED" in ERROR_CODES
