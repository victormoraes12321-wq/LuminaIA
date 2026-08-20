from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.supervised_feedback_v2 import (
    CandidateStatus,
    FeedbackCategoryV2,
    FeedbackCorrectionV2,
    FeedbackLifecycle,
    FeedbackPermission,
    FeedbackSubmissionV2,
    FeedbackTargetV2,
)
from contracts.supervised_feedback_v2.models import (
    FreeTextExplanationCorrectionV2,
)
from models.user import UserRole
from services.supervised_feedback.checksums import canonical_json, checksum
from services.supervised_feedback.errors import (
    FeedbackAccessDeniedError,
    FeedbackInvalidTransitionError,
)
from services.supervised_feedback.lifecycle import (
    CANDIDATE_TRANSITIONS,
    FEEDBACK_TRANSITIONS,
    require_candidate_transition,
    require_transition,
)
from services.supervised_feedback.permissions import access_decision, require_permission
from services.supervised_feedback.redaction import FeedbackRedactionEngine
from services.supervised_feedback.triage import FeedbackTriageEngine


pytestmark = pytest.mark.unit


TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
USER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
RESPONSE_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
QUERY_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
RESPONSE_CHECKSUM = "a" * 64


def target() -> FeedbackTargetV2:
    return FeedbackTargetV2(
        response_node_id=RESPONSE_ID,
        session_id="lumina-55555555-5555-4555-8555-555555555555",
        response_checksum=RESPONSE_CHECKSUM,
        query_node_id=QUERY_ID,
    )


def correction(text: str = "O valor correto deve ser revisado.") -> FeedbackCorrectionV2:
    return FeedbackCorrectionV2(
        items=[FreeTextExplanationCorrectionV2(explanation=text)]
    )


def test_contract_rejects_unknown_fields_and_client_identity() -> None:
    with pytest.raises(ValidationError):
        FeedbackSubmissionV2.model_validate(
            {
                "target": target().model_dump(mode="json"),
                "category": "POSITIVE",
                "idempotency_key": "idem-12345678",
                "tenant_id": str(TENANT_ID),
            }
        )


def test_non_positive_feedback_requires_detail() -> None:
    with pytest.raises(ValidationError):
        FeedbackSubmissionV2(
            target=target(),
            category=FeedbackCategoryV2.INCORRECT_VALUE,
            idempotency_key="idem-12345678",
        )


def test_correction_union_is_discriminated() -> None:
    value = FeedbackCorrectionV2.model_validate(
        {
            "items": [
                {
                    "kind": "EXPECTED_PERIOD",
                    "start_date": "2026-07-01",
                    "end_date": "2026-07-31",
                    "timezone": "America/Sao_Paulo",
                }
            ]
        }
    )
    assert value.items[0].kind == "EXPECTED_PERIOD"
    with pytest.raises(ValidationError):
        FeedbackCorrectionV2.model_validate(
            {"items": [{"kind": "UNKNOWN", "value": "x"}]}
        )


def test_checksum_is_canonical_and_excludes_volatile_timestamps() -> None:
    first = {"b": 2, "a": 1, "created_at": "one"}
    second = {"a": 1, "created_at": "two", "b": 2}
    assert canonical_json(first) == canonical_json(second)
    assert checksum(first) == checksum(second)
    assert checksum(first) != checksum({"a": 1, "b": 3})


@pytest.mark.parametrize(
    ("current", "expected"),
    [(state, targets) for state, targets in FEEDBACK_TRANSITIONS.items()],
)
def test_feedback_lifecycle_allows_only_declared_transitions(
    current: FeedbackLifecycle,
    expected: frozenset[FeedbackLifecycle],
) -> None:
    for target_state in FeedbackLifecycle:
        if target_state in expected:
            require_transition(current, target_state)
        else:
            with pytest.raises(FeedbackInvalidTransitionError):
                require_transition(current, target_state)


def test_received_cannot_be_approved_directly() -> None:
    with pytest.raises(FeedbackInvalidTransitionError):
        require_transition(FeedbackLifecycle.RECEIVED, FeedbackLifecycle.APPROVED)


def test_expired_feedback_can_only_be_archived() -> None:
    assert FEEDBACK_TRANSITIONS[FeedbackLifecycle.EXPIRED] == frozenset(
        {FeedbackLifecycle.ARCHIVED}
    )


@pytest.mark.parametrize(
    ("current", "expected"),
    [(state, targets) for state, targets in CANDIDATE_TRANSITIONS.items()],
)
def test_candidate_lifecycle_requires_validation_before_approval(
    current: CandidateStatus,
    expected: frozenset[CandidateStatus],
) -> None:
    for target_state in CandidateStatus:
        if target_state in expected:
            require_candidate_transition(current, target_state)
        else:
            with pytest.raises(FeedbackInvalidTransitionError):
                require_candidate_transition(current, target_state)
    with pytest.raises(FeedbackInvalidTransitionError):
        require_candidate_transition(
            CandidateStatus.CANDIDATE, CandidateStatus.APPROVED
        )


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("permission", list(FeedbackPermission))
def test_permission_matrix_is_total(role: UserRole, permission: FeedbackPermission) -> None:
    decision = access_decision(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        role=role,
        permission=permission,
    )
    assert decision.permission is permission
    assert decision.reason_code in {"ROLE_PERMISSION_GRANTED", "ROLE_PERMISSION_DENIED"}


def test_consulta_cannot_review_or_publish() -> None:
    for permission in (FeedbackPermission.REVIEW, FeedbackPermission.PUBLISH_DATASET):
        with pytest.raises(FeedbackAccessDeniedError):
            require_permission(
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                role=UserRole.CONSULTA,
                permission=permission,
            )


def test_redaction_removes_secrets_pii_controls_and_normalizes_space() -> None:
    engine = FeedbackRedactionEngine()
    result = engine.redact(
        explanation=(
            "  authorization: Bearer abcdefghijklmnop \x00 "
            "cpf 123.456.789-00 email pessoa@empresa.com  "
        ),
        correction=correction("password=segredo123"),
    )
    serialized = json.dumps(
        {
            "explanation": result.explanation,
            "correction": result.correction.model_dump(mode="json"),
        }
    )
    assert "abcdefghijklmnop" not in serialized
    assert "123.456.789-00" not in serialized
    assert "pessoa@empresa.com" not in serialized
    assert "segredo123" not in serialized
    assert result.manifest.sensitive_content_detected is True
    assert all("original" not in item.field_name for item in result.manifest.transformed_fields)


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_csv_formula_injection_is_neutralized(prefix: str) -> None:
    assert FeedbackRedactionEngine.neutralize_csv(prefix + "SUM(A1:A2)").startswith("'")


def test_duplicate_fingerprint_ignores_user_but_preserves_tenant() -> None:
    engine = FeedbackTriageEngine()
    first = engine.triage(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        target=target(),
        category=FeedbackCategoryV2.INCORRECT_VALUE,
        correction=correction(),
        sensitive_content_detected=False,
    )
    second = engine.triage(
        tenant_id=TENANT_ID,
        user_id=uuid.uuid4(),
        target=target(),
        category=FeedbackCategoryV2.INCORRECT_VALUE,
        correction=correction(),
        sensitive_content_detected=False,
    )
    other_tenant = engine.triage(
        tenant_id=uuid.uuid4(),
        user_id=USER_ID,
        target=target(),
        category=FeedbackCategoryV2.INCORRECT_VALUE,
        correction=correction(),
        sensitive_content_detected=False,
    )
    assert first.duplicate_fingerprint == second.duplicate_fingerprint
    assert first.duplicate_fingerprint != other_tenant.duplicate_fingerprint


def test_all_golden_triage_scenarios() -> None:
    golden_path = Path(__file__).parent / "goldens" / "supervised_feedback_v2.json"
    scenarios = json.loads(golden_path.read_text(encoding="utf-8"))
    assert len(scenarios) == 21
    engine = FeedbackTriageEngine()
    for scenario in scenarios:
        result = engine.triage(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            target=target(),
            category=FeedbackCategoryV2(scenario["category"]),
            correction=correction(),
            sensitive_content_detected=scenario["id"] == "secret_redaction",
        )
        assert result.severity.value == scenario["severity"], scenario["id"]
        assert result.priority.value == scenario["priority"], scenario["id"]
        assert result.review_queue == scenario["queue"], scenario["id"]


def test_no_automatic_training_authority_exists_in_contract() -> None:
    fields = set(FeedbackSubmissionV2.model_fields)
    assert "train" not in fields
    assert "publish" not in fields
    assert "prompt" not in fields
