from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from config import settings
from contracts.analytical_v2 import (
    ConfidenceAssessment,
    ConfidenceLevel,
    DimensionReference,
    DimensionRole,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    MetricReference,
    TemporalGranularity,
    TimeWindow,
)
from contracts.conversation_state_v2 import (
    CONVERSATION_STATE_VERSION,
    ConversationRetentionPolicy,
    ConversationRolloutMode,
    ConversationStateV2,
    compute_state_checksum,
)
from services.conversation_state.content_protector import (
    ConversationContentError,
    ConversationContentProtector,
)
from services.conversation_state.legacy_adapter import LegacyConversationGraphAdapter
from services.conversation_state.service import ConversationStateService
from services.metadata_catalog.conversation_graph import StatelessConversationGraphAdapter


pytestmark = [pytest.mark.unit, pytest.mark.baseline, pytest.mark.no_database]


def _confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["explicit synthetic fixture"],
        requires_confirmation=False,
    )


def test_state_contract_round_trip_and_checksum_are_deterministic() -> None:
    state = ConversationStateV2(
        context_epoch=2,
        context_version=4,
        active_metric_refs=[
            MetricReference(
                metric_id="sales.revenue",
                metric_version="1",
                display_name="Faturamento",
                unit="BRL",
                aggregation="SUM",
                origin=FieldOrigin.EXPLICIT_USER,
                confidence=_confidence(),
            )
        ],
        active_dimension_refs=[
            DimensionReference(
                dimension_id="product",
                display_name="Produto",
                role=DimensionRole.GROUPING,
                origin=FieldOrigin.EXPLICIT_USER,
                confidence=_confidence(),
            )
        ],
        active_filters=[
            FilterSpecification(
                filter_id="branch.centro",
                field_id="branch",
                operator=FilterOperator.EQ,
                value="Centro",
                origin=FieldOrigin.INHERITED_CONVERSATION,
                confidence=_confidence(),
                is_explicit=False,
            )
        ],
        active_time_windows=[
            TimeWindow(
                window_id="june.2026",
                label="Junho de 2026",
                start=date(2026, 6, 1),
                end=date(2026, 6, 30),
                granularity=TemporalGranularity.MONTH,
                timezone="America/Sao_Paulo",
                origin=FieldOrigin.EXPLICIT_USER,
                confidence=_confidence(),
            ),
            TimeWindow(
                window_id="july.2026",
                label="Julho de 2026",
                start=date(2026, 7, 1),
                end=date(2026, 7, 31),
                granularity=TemporalGranularity.MONTH,
                timezone="America/Sao_Paulo",
                origin=FieldOrigin.INHERITED_CONVERSATION,
                confidence=_confidence(),
            ),
        ],
        field_origins={
            "metric": FieldOrigin.EXPLICIT_USER,
            "branch": FieldOrigin.INHERITED_CONVERSATION,
        },
        context_markers=["four-turn-roundtrip"],
        updated_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
    )
    serialized = state.model_dump_json()
    restored = ConversationStateV2.model_validate_json(serialized)
    assert restored == state
    assert compute_state_checksum(restored) == compute_state_checksum(state)
    changed_time = state.model_copy(update={"updated_at": datetime(2026, 7, 29, tzinfo=timezone.utc)})
    assert compute_state_checksum(changed_time) == compute_state_checksum(state)


def test_state_contract_rejects_unknown_fields_and_unknown_version() -> None:
    with pytest.raises(ValidationError):
        ConversationStateV2.model_validate({
            "schema_version": CONVERSATION_STATE_VERSION,
            "unexpected": True,
        })
    with pytest.raises(ValidationError):
        ConversationStateV2(schema_version="future/99")


def test_content_protector_encrypts_authenticates_and_detects_corruption() -> None:
    protector = ConversationContentProtector(key=Fernet.generate_key(), key_version="test-v1")
    protected = protector.protect("Faturamento de julho por filial")
    assert protected.ciphertext is not None
    assert b"Faturamento" not in protected.ciphertext
    assert protector.decrypt(protected.ciphertext, key_version="test-v1") == (
        "Faturamento de julho por filial"
    )
    corrupted = protected.ciphertext[:-1] + bytes([protected.ciphertext[-1] ^ 1])
    with pytest.raises(ConversationContentError):
        protector.decrypt(corrupted, key_version="test-v1")


@pytest.mark.parametrize(
    "content",
    [
        "Authorization: Bearer synthetic-token",
        "password=synthetic-secret",
        "SELECT * FROM private_table",
    ],
)
def test_content_protector_redacts_sensitive_or_executable_content(content: str) -> None:
    protector = ConversationContentProtector(key=Fernet.generate_key())
    protected = protector.protect(content)
    assert protected.redacted is True
    assert protected.ciphertext is None
    assert len(protected.fingerprint) == 64


def test_content_protector_fails_closed_and_enforces_size() -> None:
    with pytest.raises(ConversationContentError):
        ConversationContentProtector(key=None, persist_content=True)
    protector = ConversationContentProtector(
        key=Fernet.generate_key(),
        max_content_bytes=16,
    )
    with pytest.raises(ConversationContentError):
        protector.protect("x" * 17)


def test_rollout_modes_and_retention_policy_are_governed() -> None:
    assert ConversationRolloutMode("LEGACY_ONLY") is ConversationRolloutMode.LEGACY_ONLY
    assert settings.CONVERSATION_STATE_MODE == "LEGACY_ONLY"
    assert settings.CONVERSATION_RETENTION_JOB_ENABLED is False
    assert settings.CONVERSATION_LEGACY_IMPORT_ENABLED is False
    protector = ConversationContentProtector(key=Fernet.generate_key())
    legacy = ConversationStateService(
        protector=protector,
        mode=ConversationRolloutMode.LEGACY_ONLY,
    )
    shadow = ConversationStateService(
        protector=protector,
        mode=ConversationRolloutMode.SHADOW_WRITE,
    )
    authority = ConversationStateService(
        protector=protector,
        mode=ConversationRolloutMode.POSTGRES_READ_WRITE,
    )
    assert legacy.postgres_writes_enabled is False
    assert legacy.postgres_is_authority is False
    assert shadow.postgres_writes_enabled is True
    assert shadow.postgres_is_authority is False
    assert authority.postgres_is_authority is True
    with pytest.raises(ValidationError):
        ConversationRetentionPolicy(
            archive_after_days=100,
            soft_delete_after_days=20,
            purge_after_days=10,
        )


def test_stateless_adapter_never_writes_legacy_json() -> None:
    adapter = StatelessConversationGraphAdapter()
    graph = adapter.get_graph("ignored")
    assert graph.nodes == {}
    assert adapter.try_dataset_reuse(object(), graph) is None


def test_legacy_adapter_is_explicit_deterministic_and_rejects_cycles(tmp_path: Path) -> None:
    plan = {
        "status": "READY",
        "intent": "KPI",
        "goal": "Consulta sintetica",
        "entities": ["Venda"],
        "metrics": ["receita_total"],
        "dimensions": [],
    }
    dashboard = {"chart_type": "KPI_CARD"}
    payload = {
        "nodes": {
            "child": {
                "node_id": "child",
                "parent_id": "root",
                "user_query": "E em julho?",
                "canonical_plan": plan,
                "dashboard_state": dashboard,
            },
            "root": {
                "node_id": "root",
                "user_query": "Faturamento de junho",
                "canonical_plan": plan,
                "dashboard_state": dashboard,
            },
        },
        "current_node_id": "child",
    }
    source = tmp_path / "conversation.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    adapted, checksum = LegacyConversationGraphAdapter().read(source)
    assert [node.legacy_id for node in adapted.nodes] == ["root", "child"]
    assert adapted.current_legacy_id == "child"
    assert len(checksum) == 64
    assert all("dataset" not in warning.lower() or "not imported" in warning.lower()
               for warning in adapted.warnings)

    payload["nodes"]["root"]["parent_id"] = "child"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        LegacyConversationGraphAdapter().read(source)


def test_all_golden_conversation_states_are_strict_and_deterministic() -> None:
    fixture_path = Path(__file__).parent / "golden" / "conversation_state_v2.json"
    golden = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert golden["schema_version"] == CONVERSATION_STATE_VERSION
    assert len(golden["cases"]) == 16
    names: set[str] = set()
    for case in golden["cases"]:
        state = ConversationStateV2(
            context_epoch=case["epoch"],
            context_version=case["version"],
            active_subject=case["subject"],
            pending_clarification=case.get("pending_clarification", False),
            context_markers=case["markers"],
            updated_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
        )
        names.add(case["name"])
        restored = ConversationStateV2.model_validate_json(state.model_dump_json())
        assert restored == state
        assert compute_state_checksum(restored) == compute_state_checksum(state)
    assert len(names) == 16
