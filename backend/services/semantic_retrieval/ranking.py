from __future__ import annotations

from dataclasses import dataclass

from contracts.semantic_retrieval_v2 import (
    SemanticChannelScoreV2,
    SemanticRankingPolicyV2,
    SemanticRetrievalChannel,
    SemanticScoreBreakdownV2,
)


@dataclass(frozen=True)
class SemanticRankingEvidence:
    channel: SemanticRetrievalChannel
    raw_score: float
    reason_code: str
    evidence_reference: str | None = None
    penalty: bool = False


class SemanticRankingEngine:
    _IDENTITY_CHANNELS = frozenset(
        {
            SemanticRetrievalChannel.EXACT_CANONICAL,
            SemanticRetrievalChannel.EXACT_ALIAS,
            SemanticRetrievalChannel.EXACT_LABEL,
            SemanticRetrievalChannel.NORMALIZED_EXACT,
            SemanticRetrievalChannel.PREFIX,
            SemanticRetrievalChannel.TOKEN_OVERLAP,
            SemanticRetrievalChannel.CHARACTER_SIMILARITY,
            SemanticRetrievalChannel.VECTOR_SIMILARITY,
            SemanticRetrievalChannel.LEGACY_FALLBACK,
        }
    )

    def score(
        self,
        evidence: tuple[SemanticRankingEvidence, ...],
        *,
        policy: SemanticRankingPolicyV2,
        deprecated: bool = False,
        stale: bool = False,
    ) -> SemanticScoreBreakdownV2:
        weight_by_channel = {item.channel: item.weight for item in policy.weights}
        breakdown: list[SemanticChannelScoreV2] = []
        identity_contributions: list[float] = []
        boost_total = 0.0
        penalties = 0.0

        for item in sorted(evidence, key=lambda row: row.channel.value):
            weight = weight_by_channel.get(item.channel, 0.0)
            raw = round(max(0.0, min(1.0, item.raw_score)), policy.score_precision)
            contribution = round(raw * weight, policy.score_precision)
            if item.penalty:
                contribution = -abs(contribution)
                penalties += abs(contribution)
            elif item.channel in self._IDENTITY_CHANNELS:
                identity_contributions.append(max(0.0, contribution))
            else:
                boost_total += max(0.0, contribution)
            breakdown.append(
                SemanticChannelScoreV2(
                    channel=item.channel,
                    raw_score=raw,
                    weight=weight,
                    contribution=contribution,
                    reason_code=item.reason_code,
                    evidence_reference=item.evidence_reference,
                    penalty=item.penalty,
                    policy_version=policy.policy_version,
                )
            )

        positive = (max(identity_contributions) if identity_contributions else 0.0) + boost_total
        if deprecated:
            penalties += policy.deprecated_penalty
        if stale:
            penalties += policy.stale_penalty
        final = round(max(0.0, min(1.0, positive - penalties)), policy.score_precision)
        return SemanticScoreBreakdownV2(
            channels=tuple(breakdown),
            positive_score=round(positive, policy.score_precision),
            penalties=round(penalties, policy.score_precision),
            final_score=final,
            policy_version=policy.policy_version,
        )
