from __future__ import annotations

from typing import Any, get_args, get_origin

import pytest
from pydantic import ValidationError

from contracts.smart_cache_materialization_v2 import (
    CacheEligibilityRequestV2,
    CacheEntryV2,
    CacheInvalidationRequestV2,
    CacheKeyV2,
    CacheLookupRequestV2,
    CacheScopeV2,
    CacheType,
    CacheWriteRequestV2,
    CertificationStatus,
    DataClassification,
    FreshnessStatus,
    MaterializationDefinitionV2,
    MaterializationLifecycle,
    MaterializationQueryV2,
    MaterializationSourceV2,
    MaterializationType,
    SmartCachePolicyV2,
)
from services.smart_cache_materialization import (
    SmartCacheEligibilityEngine,
    SmartCacheKeyBuilder,
)


pytestmark = pytest.mark.no_database


def _scope(tenant: str = "tenant-a", permission: str = "a" * 64) -> CacheScopeV2:
    return CacheScopeV2(tenant_id=tenant, permission_fingerprint=permission)


def _key(**overrides) -> CacheKeyV2:
    values = {
        "cache_type": CacheType.CERTIFIED_ANALYTICAL_RESULT,
        "scope": _scope(),
        "canonical_query_fingerprint": "q" * 64,
        "analytical_catalog_version": "catalog-v1",
        "metric_fingerprints": ["m" * 64],
        "filter_structure_fingerprint": "f" * 64,
        "canonical_period_fingerprint": "p" * 64,
        "source_sync_version": "sync-v1",
        "source_watermark": "watermark-v1",
        "compiler_version": "compiler-v1",
        "tool_registry_snapshot": "tools-v1",
        "generation_counters": {"catalog": 1, "permissions": 1},
    }
    values.update(overrides)
    return SmartCacheKeyBuilder.build_key(**values)


def _eligibility(**updates) -> CacheEligibilityRequestV2:
    values = {
        "cache_type": CacheType.CERTIFIED_ANALYTICAL_RESULT,
        "certification_status": CertificationStatus.VALID,
        "tenant_proof_valid": True,
        "query_fingerprint_valid": True,
        "result_checksum_valid": True,
        "metric_fingerprints_valid": True,
        "source_freshness": FreshnessStatus.FRESH,
        "is_complete": True,
        "payload_size_bytes": 100,
        "data_classification": DataClassification.INTERNAL,
    }
    values.update(updates)
    return CacheEligibilityRequestV2(**values)


def test_canonical_contracts_are_strict_and_have_no_untyped_any_core_fields() -> None:
    core_models = (
        CacheScopeV2,
        CacheKeyV2,
        CacheEntryV2,
        CacheLookupRequestV2,
        CacheWriteRequestV2,
        CacheInvalidationRequestV2,
        MaterializationDefinitionV2,
    )
    for model in core_models:
        assert model.model_config.get("extra") == "forbid"
        for field in model.model_fields.values():
            annotation = field.annotation
            assert annotation is not Any
            assert Any not in get_args(annotation)


def test_key_is_deterministic_and_alias_text_is_not_part_of_contract() -> None:
    first = _key()
    second = _key(metric_fingerprints=["m" * 64])
    assert first.compute_key_checksum() == second.compute_key_checksum()
    fields = set(CacheKeyV2.model_fields)
    assert not {"question", "prompt", "sql", "binds", "credentials", "user_name", "chain_of_thought"} & fields


@pytest.mark.parametrize(
    "change",
    [
        {"scope": _scope("tenant-b")},
        {"scope": _scope(permission="b" * 64)},
        {"analytical_catalog_version": "catalog-v2"},
        {"metric_fingerprints": ["x" * 64]},
        {"source_sync_version": "sync-v2"},
        {"source_watermark": "watermark-v2"},
        {"compiler_version": "compiler-v2"},
        {"tool_registry_snapshot": "tools-v2"},
        {"generation_counters": {"catalog": 2, "permissions": 1}},
    ],
)
def test_key_separates_all_governed_authorities(change: dict[str, object]) -> None:
    assert _key().compute_key_checksum() != _key(**change).compute_key_checksum()


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"certification_status": CertificationStatus.INVALID}, "CERTIFICATION_NOT_VALID"),
        ({"certification_status": CertificationStatus.BLOCKED}, "CERTIFICATION_NOT_VALID"),
        ({"certification_status": CertificationStatus.UNVERIFIABLE}, "CERTIFICATION_NOT_VALID"),
        ({"tenant_proof_valid": False}, "TENANT_PROOF_MISSING"),
        ({"query_fingerprint_valid": False}, "QUERY_FINGERPRINT_MISSING"),
        ({"result_checksum_valid": False}, "RESULT_CHECKSUM_INVALID"),
        ({"metric_fingerprints_valid": False}, "METRIC_FINGERPRINT_INVALID"),
        ({"source_freshness": FreshnessStatus.STALE_HARD}, "SOURCE_NOT_FRESH"),
        ({"is_complete": False}, "RESULT_PARTIAL"),
        ({"is_partial": True}, "RESULT_PARTIAL"),
        ({"is_truncated": True}, "RESULT_TRUNCATED"),
        ({"has_pii": True}, "CLASSIFICATION_FORBIDDEN"),
        ({"is_row_level": True}, "CLASSIFICATION_FORBIDDEN"),
        ({"has_ambiguity": True}, "AMBIGUOUS_RESULT"),
        ({"timed_out": True}, "EXECUTION_TIMEOUT"),
        ({"cancelled": True}, "EXECUTION_CANCELLED"),
        ({"has_error": True}, "EXECUTION_ERROR"),
    ],
)
def test_eligibility_fails_closed(updates: dict[str, object], reason: str) -> None:
    decision = SmartCacheEligibilityEngine().evaluate(
        _eligibility(**updates), SmartCachePolicyV2()
    )
    assert not decision.eligible
    assert decision.reason_code == reason


def test_complete_zero_rows_is_cacheable_but_warning_requires_policy_opt_in() -> None:
    engine = SmartCacheEligibilityEngine()
    assert engine.evaluate(_eligibility(payload_size_bytes=0), SmartCachePolicyV2()).eligible
    warning = _eligibility(certification_status=CertificationStatus.VALID_WITH_WARNINGS)
    assert not engine.evaluate(warning, SmartCachePolicyV2()).eligible
    assert engine.evaluate(
        warning, SmartCachePolicyV2(allow_valid_with_warnings=True)
    ).eligible


def test_ttl_is_governed_and_not_accepted_from_write_payload() -> None:
    with pytest.raises(ValidationError):
        SmartCachePolicyV2(default_ttl_seconds={CacheType.METADATA.value: 0})
    with pytest.raises(ValidationError):
        CacheWriteRequestV2(
            scope=_scope(),
            cache_key=_key(),
            payload={"value": 1},
            certification_id="cert-1",
            tenant_proof_id="proof-1",
            eligibility=_eligibility(),
            ttl_seconds=999999,
        )


def test_materialization_contract_rejects_row_level_and_pii() -> None:
    base = {
        "definition_id": "monthly-sales",
        "tenant_id": "tenant-a",
        "canonical_name": "Monthly sales",
        "materialization_type": MaterializationType.SCALAR_AGGREGATE,
        "query": MaterializationQueryV2(
            canonical_query_spec_id="spec-1",
            metrics=["sales"],
            dimensions=[],
            filters_fingerprint="f" * 64,
            time_window_fingerprint="t" * 64,
        ),
        "source": MaterializationSourceV2(
            dataset="sales",
            relation_references=["sales"],
            metric_fingerprints=["m" * 64],
            catalog_version="v1",
            source_sync_version="v1",
            watermark="verified-1",
        ),
        "created_at": "2026-08-04T00:00:00Z",
        "updated_at": "2026-08-04T00:00:00Z",
        "checksum": "c" * 64,
    }
    with pytest.raises(ValidationError):
        MaterializationDefinitionV2(**{**base, "materialization_type": MaterializationType.ROW_LEVEL_DETAIL})
    with pytest.raises(ValidationError):
        MaterializationDefinitionV2(**{**base, "classification": "PII"})
