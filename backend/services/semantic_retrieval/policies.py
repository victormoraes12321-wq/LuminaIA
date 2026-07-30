from __future__ import annotations

from contracts.semantic_retrieval_v2 import (
    RANKING_POLICY_VERSION,
    THRESHOLD_POLICY_VERSION,
    SemanticConfidenceBandV2,
    SemanticRankingPolicyV2,
    SemanticRankingWeightV2,
    SemanticRetrievalChannel,
    SemanticThresholdPolicyV2,
)
from services.semantic_retrieval.checksums import checksum_for


def default_ranking_policy() -> SemanticRankingPolicyV2:
    weights = (
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.EXACT_CANONICAL, weight=1.0),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.EXACT_ALIAS, weight=0.96),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.EXACT_LABEL, weight=0.92),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.NORMALIZED_EXACT, weight=0.88),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.PREFIX, weight=0.80),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.TOKEN_OVERLAP, weight=0.65),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.CHARACTER_SIMILARITY, weight=0.78),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.RELATION_EXPANSION, weight=0.03),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.VECTOR_SIMILARITY, weight=0.25),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.CONTEXT_COMPATIBILITY, weight=0.04),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.DOMAIN_COMPATIBILITY, weight=0.05),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.TYPE_COMPATIBILITY, weight=0.08),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.PROFILE_TIE_BREAKER, weight=0.01),
        SemanticRankingWeightV2(channel=SemanticRetrievalChannel.LEGACY_FALLBACK, weight=0.10),
    )
    payload = {
        "policy_version": RANKING_POLICY_VERSION,
        "weights": [item.model_dump(mode="json") for item in weights],
        "deprecated_penalty": 0.25,
        "stale_penalty": 0.15,
        "profile_tie_breaker_cap": 0.02,
        "score_precision": 6,
    }
    return SemanticRankingPolicyV2(
        weights=weights,
        checksum=checksum_for(payload),
    )


def default_threshold_policy() -> SemanticThresholdPolicyV2:
    bands = (
        SemanticConfidenceBandV2(label="LOW", minimum=0.0),
        SemanticConfidenceBandV2(label="MEDIUM", minimum=0.50),
        SemanticConfidenceBandV2(label="HIGH", minimum=0.72),
        SemanticConfidenceBandV2(label="EXACT", minimum=0.95),
    )
    payload = {
        "policy_version": THRESHOLD_POLICY_VERSION,
        "minimum_retrieval_score": 0.30,
        "minimum_automatic_resolution_score": 0.72,
        "ambiguity_margin": 0.08,
        "maximum_candidates": 10,
        "maximum_relation_expansion": 10,
        "maximum_lexical_candidates": 50,
        "maximum_vector_candidates": 20,
        "maximum_total_candidates": 100,
        "stale_index_tolerance_seconds": 3600,
        "confidence_bands": [item.model_dump(mode="json") for item in bands],
    }
    return SemanticThresholdPolicyV2(
        confidence_bands=bands,
        checksum=checksum_for(payload),
    )
