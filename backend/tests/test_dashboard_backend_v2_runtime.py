from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from contracts.dashboard_backend_v2 import (
    DashboardRuntimeFilterValueV2,
    DashboardRuntimeInteractionV2,
    DashboardRuntimeRequestV2,
)
from contracts.dashboard_blueprint_v2 import DashboardClassificationV2
from services.dashboard_backend_v2.application import DashboardActorContextV2
from services.dashboard_backend_v2.errors import DashboardBackendError
from services.dashboard_backend_v2.runtime import DashboardRuntimePlanningServiceV2
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer
from services.dashboard_blueprint_v2.fixtures import build_executive_dashboard
from models.dashboard_backend_v2 import DashboardPublicationModelV2, DashboardRevisionModelV2

pytestmark = pytest.mark.no_database


def _authority_rows(blueprint=None):
    blueprint = blueprint or build_executive_dashboard()
    canonical = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
    tenant_id, dashboard_id, revision_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    revision = DashboardRevisionModelV2(
        id=revision_id, dashboard_id=dashboard_id, tenant_id=tenant_id, parent_revision_id=None,
        revision_number=1, blueprint_contract_version=blueprint.version.contract_version,
        blueprint_version=blueprint.version.blueprint_version,
        semantic_revision=blueprint.version.revision.semantic_revision, visual_revision=blueprint.version.revision.visual_revision,
        blueprint_json=blueprint.model_dump(mode="json", exclude_none=True),
        blueprint_checksum=canonical.checksums.blueprint_checksum, semantic_checksum=canonical.checksums.semantic_checksum,
        visual_checksum=canonical.checksums.visual_checksum, validation_status="VALID", validation_json={},
        author_user_id=uuid.uuid4(), reason="Synthetic runtime", origin=blueprint.created_origin.value,
        lock_version=1, idempotency_scope="a" * 64, request_checksum="b" * 64,
        created_at=datetime.now(timezone.utc),
    )
    publication = DashboardPublicationModelV2(
        id=uuid.uuid4(), dashboard_id=dashboard_id, tenant_id=tenant_id, revision_id=revision_id,
        approval_id=uuid.uuid4(), publication_version="1.0.0", generation=1,
        blueprint_checksum=revision.blueprint_checksum, semantic_checksum=revision.semantic_checksum,
        visual_checksum=revision.visual_checksum, published_by_user_id=uuid.uuid4(),
        idempotency_scope="c" * 64, request_checksum="d" * 64,
        published_at=datetime.now(timezone.utc),
    )
    actor = DashboardActorContextV2(tenant_id=str(tenant_id), user_id=str(uuid.uuid4()), global_role="ADMIN")
    return actor, publication, revision, blueprint


def test_runtime_plan_has_no_sql_or_physical_identifiers() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    plan = DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=DashboardRuntimeRequestV2())
    payload = plan.model_dump_json()
    assert len(plan.widget_plans) == 6
    assert len(plan.execution_groups) == 6
    assert "sql" not in payload.lower()
    assert "physical" not in payload.lower()
    assert all(widget.metric_ids for widget in plan.widget_plans)


def test_unknown_filter_is_rejected_before_execution() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    request = DashboardRuntimeRequestV2(filters=(DashboardRuntimeFilterValueV2(filter_id="filter.unknown", values=("x",)),))
    with pytest.raises(DashboardBackendError) as raised:
        DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=request)
    assert raised.value.code == "DASHBOARD_FILTER_INVALID"


def test_filter_sql_injection_is_rejected_before_execution() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    request = DashboardRuntimeRequestV2(filters=(DashboardRuntimeFilterValueV2(filter_id="filter.branch", values=("x'; DROP TABLE sales;--",)),))
    with pytest.raises(DashboardBackendError) as raised:
        DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=request)
    assert raised.value.code == "DASHBOARD_FILTER_INVALID"


def test_undeclared_interaction_is_rejected() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    request = DashboardRuntimeRequestV2(interactions=(DashboardRuntimeInteractionV2(interaction_id="interaction.evil", action="EXPAND", source_widget_id="widget.revenue"),))
    with pytest.raises(DashboardBackendError) as raised:
        DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=request)
    assert raised.value.code == "DASHBOARD_INTERACTION_INVALID"


def test_requested_widget_subset_is_preserved() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    request = DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",))
    plan = DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=request)
    assert [item.widget_id for item in plan.widget_plans] == ["widget.revenue"]


def test_visual_only_revision_reuses_analytical_cache_fingerprint() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    first = DashboardRuntimePlanningServiceV2().plan(actor=actor, publication=publication, revision=revision, blueprint=blueprint, request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",)))
    visual_blueprint = blueprint.model_copy(update={
        "identity": blueprint.identity.model_copy(update={"title": "Resumo visual revisado"}),
        "version": blueprint.version.model_copy(update={"revision": blueprint.version.revision.model_copy(update={"visual_revision": blueprint.version.revision.visual_revision + 1})}),
    })
    second_actor, second_publication, second_revision, _ = _authority_rows(visual_blueprint)
    second_actor = DashboardActorContextV2(tenant_id=actor.tenant_id, user_id=actor.user_id, global_role=actor.global_role)
    second_publication.tenant_id = publication.tenant_id
    second_publication.dashboard_id = publication.dashboard_id
    second_revision.tenant_id = revision.tenant_id
    second_revision.dashboard_id = revision.dashboard_id
    second_publication.dashboard_id = revision.dashboard_id
    second = DashboardRuntimePlanningServiceV2().plan(actor=second_actor, publication=second_publication, revision=second_revision, blueprint=visual_blueprint, request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",)))
    assert revision.semantic_checksum == second_revision.semantic_checksum
    assert first.widget_plans[0].analytical_cache_fingerprint == second.widget_plans[0].analytical_cache_fingerprint
    assert first.widget_plans[0].plan_checksum != second.widget_plans[0].plan_checksum


def test_runtime_plan_never_reduces_blueprint_classification() -> None:
    actor, publication, revision, blueprint = _authority_rows()
    public_binding = blueprint.data_bindings[0].model_copy(
        update={"classification": DashboardClassificationV2.PUBLIC_METADATA}
    )
    governed = blueprint.model_copy(update={
        "data_bindings": (public_binding, *blueprint.data_bindings[1:])
    })
    plan = DashboardRuntimePlanningServiceV2().plan(
        actor=actor, publication=publication, revision=revision, blueprint=governed,
        request=DashboardRuntimeRequestV2(requested_widget_ids=("widget.revenue",)),
    )
    assert plan.widget_plans[0].classification_ceiling == governed.governance.classification.value
