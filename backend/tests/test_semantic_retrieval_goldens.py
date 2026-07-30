from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.semantic_retrieval_v2 import SemanticRetrievalChannel
from services.semantic_retrieval.normalization import normalize_semantic_text
from services.semantic_retrieval.policies import (
    default_ranking_policy,
    default_threshold_policy,
)
from services.semantic_retrieval.ranking import (
    SemanticRankingEngine,
    SemanticRankingEvidence,
)
from services.semantic_retrieval.representation import (
    DeterministicFeatureEmbeddingProvider,
)


pytestmark = pytest.mark.no_database
GOLDEN = (
    Path(__file__).resolve().parent
    / "golden"
    / "semantic_retrieval_v2.json"
)


def test_semantic_normalizer_and_provider_match_reviewed_golden() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for expected in golden["normalization"].values():
        actual = normalize_semantic_text(expected["input"])
        assert {
            "input": actual.original,
            "normalized": actual.normalized,
            "tokens": list(actual.tokens),
            "significant_tokens": list(actual.significant_tokens),
            "possible_code": actual.possible_code,
            "version": actual.version,
            "checksum": actual.checksum,
        } == expected

    expected_provider = golden["provider"]
    provider = DeterministicFeatureEmbeddingProvider(
        dimension=expected_provider["dimension"]
    )
    representation = provider.encode_query(
        normalize_semantic_text(expected_provider["query"])
    )
    info = provider.provider_info()
    assert info.provider_type == expected_provider["provider_type"]
    assert info.version == expected_provider["version"]
    assert info.checksum == expected_provider["fingerprint"]
    assert info.network_required is expected_provider["network_required"]
    assert representation.checksum == expected_provider["checksum"]
    assert list(representation.vector[:8]) == expected_provider["vector_prefix"]
    assert round(sum(value * value for value in representation.vector), 12) == (
        expected_provider["l2_norm"]
    )


def test_semantic_ranking_and_thresholds_match_reviewed_golden() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    actual = SemanticRankingEngine().score(
        (
            SemanticRankingEvidence(
                SemanticRetrievalChannel.EXACT_ALIAS,
                1.0,
                "PUBLISHED_ALIAS",
            ),
            SemanticRankingEvidence(
                SemanticRetrievalChannel.TOKEN_OVERLAP,
                0.5,
                "TOKEN_JACCARD",
            ),
        ),
        policy=default_ranking_policy(),
    )
    expected_ranking = golden["ranking"]
    assert actual.policy_version == expected_ranking["policy_version"]
    assert actual.positive_score == expected_ranking["positive_score"]
    assert actual.penalties == expected_ranking["penalties"]
    assert actual.final_score == expected_ranking["final_score"]
    assert [
        {
            "channel": item.channel.value,
            "raw_score": item.raw_score,
            "weight": item.weight,
            "contribution": item.contribution,
            "reason_code": item.reason_code,
            "penalty": item.penalty,
        }
        for item in actual.channels
    ] == expected_ranking["channels"]

    thresholds = default_threshold_policy()
    assert {
        "policy_version": thresholds.policy_version,
        "minimum_retrieval_score": thresholds.minimum_retrieval_score,
        "minimum_automatic_resolution_score": (
            thresholds.minimum_automatic_resolution_score
        ),
        "ambiguity_margin": thresholds.ambiguity_margin,
        "maximum_candidates": thresholds.maximum_candidates,
        "maximum_total_candidates": thresholds.maximum_total_candidates,
        "checksum": thresholds.checksum,
    } == golden["thresholds"]
