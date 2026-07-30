from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import pytest

from contracts.supervised_feedback_v2 import (
    EvaluationCaseV2,
    EvaluationKind,
    FeedbackCategoryV2,
    FeedbackReviewDecisionV2,
    FeedbackTargetV2,
    GovernedImportDryRunRequestV2,
    TrainingDatasetManifestV2,
    TrainingExampleExpectedOutputV2,
    TrainingExampleInputV2,
)
from services.supervised_feedback.cache import FeedbackMetadataCache
from services.supervised_feedback.checksums import checksum, content_sha256
from services.supervised_feedback.imports import GovernedImportDryRunValidator
from services.supervised_feedback.observability import FeedbackCounters
from services.supervised_feedback.redaction import FeedbackRedactionEngine
from services.supervised_feedback.triage import FeedbackTriageEngine


@pytest.mark.unit
def test_deterministic_triage_handles_ten_thousand_items_with_tenant_isolation() -> None:
    engine = FeedbackTriageEngine()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000101")
    tenant_a = uuid.UUID("00000000-0000-0000-0000-000000000201")
    tenant_b = uuid.UUID("00000000-0000-0000-0000-000000000202")
    target = FeedbackTargetV2(
        response_node_id=uuid.UUID("00000000-0000-0000-0000-000000000301"),
        session_id="performance-structural-session",
        response_checksum="a" * 64,
    )

    started_at = time.perf_counter()
    fingerprints = {
        engine.triage(
            tenant_id=tenant_a,
            user_id=user_id,
            target=target,
            category=FeedbackCategoryV2.INCORRECT_VALUE,
            correction=None,
            sensitive_content_detected=False,
        ).duplicate_fingerprint
        for _ in range(10_000)
    }
    elapsed_seconds = time.perf_counter() - started_at

    tenant_b_result = engine.triage(
        tenant_id=tenant_b,
        user_id=user_id,
        target=target,
        category=FeedbackCategoryV2.INCORRECT_VALUE,
        correction=None,
        sensitive_content_detected=False,
    )

    assert len(fingerprints) == 1
    assert tenant_b_result.duplicate_fingerprint not in fingerprints
    assert elapsed_seconds < 30


def evaluation_case() -> EvaluationCaseV2:
    input_contract = TrainingExampleInputV2(
        minimized_question="Compare o faturamento de junho e julho.",
        intent_kind="COMPARISON",
    )
    expected = TrainingExampleExpectedOutputV2(
        expected_classification=FeedbackReviewDecisionV2.CORRECT,
        expected_readiness="READY",
    )
    payload = {
        "evaluation_id": uuid.UUID("00000000-0000-0000-0000-000000000401"),
        "kind": EvaluationKind.REGRESSION,
        "name": "comparacao mensal sintetica",
        "input": input_contract,
        "expected_output": expected,
        "runner_id": "offline-structural-v1",
        "tolerance": None,
    }
    return EvaluationCaseV2(**payload, checksum=checksum(payload))


@pytest.mark.unit
def test_governed_import_is_dry_run_deterministic_and_rejects_forbidden_fields() -> None:
    valid_line = evaluation_case().model_dump_json()
    content = valid_line + "\n"
    request = GovernedImportDryRunRequestV2(
        source_kind="SYNTHETIC_FIXTURE",
        schema_version="lumina.supervised-feedback/1.0",
        lines=[valid_line],
        content_checksum=content_sha256(content.encode("utf-8")),
        idempotency_key="dry-run-0001",
    )
    validator = GovernedImportDryRunValidator()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000201")
    first = validator.validate(
        request=request, authenticated_tenant_id=tenant_id
    )
    second = validator.validate(
        request=request, authenticated_tenant_id=tenant_id
    )
    assert first == second
    assert first.valid_count == 1
    assert first.persisted is False
    assert first.published is False

    poisoned_line = '{"sql":"select secret","contract_version":"unknown"}'
    poisoned = request.model_copy(
        update={
            "lines": [poisoned_line],
            "content_checksum": content_sha256((poisoned_line + "\n").encode("utf-8")),
            "idempotency_key": "dry-run-0002",
        }
    )
    rejected = validator.validate(
        request=poisoned, authenticated_tenant_id=tenant_id
    )
    assert rejected.valid_count == 0
    assert rejected.rejected_count == 1
    assert any("FORBIDDEN_FIELD" in issue for issue in rejected.issues)


@pytest.mark.unit
def test_manifest_cache_is_tenant_scoped_and_observability_is_allowlisted() -> None:
    tenant_a = uuid.UUID("00000000-0000-0000-0000-000000000201")
    tenant_b = uuid.UUID("00000000-0000-0000-0000-000000000202")
    snapshot_id = uuid.UUID("00000000-0000-0000-0000-000000000501")
    manifest_payload = {
        "dataset_id": uuid.UUID("00000000-0000-0000-0000-000000000502"),
        "version": 1,
        "schema_version": "lumina.training-dataset/1.0",
        "contract_version": "lumina.supervised-feedback/1.0",
        "example_checksums": ["b" * 64],
        "redaction_policy_version": "lumina.feedback-redaction/1.0",
        "inclusion_criteria": ["HUMAN_REVIEWED"],
        "exclusion_criteria": ["SENSITIVE"],
    }
    manifest = TrainingDatasetManifestV2(
        **manifest_payload, checksum=checksum(manifest_payload)
    )
    cache = FeedbackMetadataCache(enabled=True, ttl_seconds=60)
    cache.put_manifest(
        tenant_id=tenant_a,
        snapshot_id=snapshot_id,
        version=1,
        checksum="c" * 64,
        manifest=manifest,
    )
    assert cache.get_manifest(
        tenant_id=tenant_a,
        snapshot_id=snapshot_id,
        version=1,
        checksum="c" * 64,
    ) == manifest
    assert cache.get_manifest(
        tenant_id=tenant_b,
        snapshot_id=snapshot_id,
        version=1,
        checksum="c" * 64,
    ) is None

    counters = FeedbackCounters(rollout_mode="V2_CURATE")
    counters.increment("cache_hit")
    assert counters.snapshot()["cache_hit"] == 1
    with pytest.raises(ValueError):
        counters.increment("question=conteudo-sensivel")


@pytest.mark.unit
def test_ten_thousand_redactions_and_manifest_entries_remain_bounded() -> None:
    redaction = FeedbackRedactionEngine()
    started_at = time.perf_counter()
    for index in range(10_000):
        clean, reasons = redaction.sanitize_text(
            f"feedback estrutural {index} token=segredo-{index:05d}"
        )
        assert "[REDACTED]" in clean
        assert reasons == ["SECRET_REDACTED"]

    example_checksums = [
        checksum({"example": index, "created_at": datetime.now(timezone.utc)})
        for index in range(10_000)
    ]
    payload = {
        "dataset_id": uuid.UUID("00000000-0000-0000-0000-000000000601"),
        "version": 1,
        "schema_version": "lumina.training-dataset/1.0",
        "contract_version": "lumina.supervised-feedback/1.0",
        "example_checksums": example_checksums,
        "redaction_policy_version": "lumina.feedback-redaction/1.0",
        "inclusion_criteria": ["HUMAN_REVIEWED"],
        "exclusion_criteria": ["SENSITIVE"],
    }
    manifest = TrainingDatasetManifestV2(
        **payload, checksum=checksum(payload)
    )
    assert len(manifest.example_checksums) == 10_000
    assert time.perf_counter() - started_at < 30
