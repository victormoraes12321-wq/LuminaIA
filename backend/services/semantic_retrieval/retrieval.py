from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.semantic_retrieval_v2 import (
    EntityCanonicalReferenceV2,
    EntityResolutionDecisionType,
    SemanticAmbiguityV2,
    SemanticCacheKeyV2,
    SemanticChannelScoreV2,
    SemanticDataClassification,
    SemanticEntityType,
    SemanticPermission,
    SemanticRankingPolicyV2,
    SemanticRetrievalChannel,
    SemanticScoreBreakdownV2,
    SemanticSearchCandidateV2,
    SemanticSearchRequestV2,
    SemanticSearchResultV2,
    SemanticThresholdPolicyV2,
)
from models.user import User
from services.semantic_retrieval.cache import SemanticRetrievalCache
from services.semantic_retrieval.checksums import checksum_for, fingerprint_text
from services.semantic_retrieval.errors import semantic_error
from services.semantic_retrieval.normalization import (
    character_similarity,
    normalize_semantic_text,
    token_overlap,
)
from services.semantic_retrieval.observability import semantic_observability
from services.semantic_retrieval.permissions import (
    ROLE_PERMISSIONS,
    permission_fingerprint,
    require_permission,
)
from services.semantic_retrieval.ranking import (
    SemanticRankingEngine,
    SemanticRankingEvidence,
)
from services.semantic_retrieval.repository import (
    SemanticRetrievalRepository,
    SemanticStoredCandidate,
)
from services.semantic_retrieval.representation import (
    DeterministicFeatureEmbeddingProvider,
)


def _confidence_band(score: float, policy: SemanticThresholdPolicyV2) -> str:
    selected = "LOW"
    for band in sorted(policy.confidence_bands, key=lambda item: item.minimum):
        if score >= band.minimum:
            selected = band.label
    return selected


def _safe_breakdown(
    breakdown: SemanticScoreBreakdownV2,
    *,
    inspect_scores: bool,
) -> SemanticScoreBreakdownV2:
    if inspect_scores:
        return breakdown
    return SemanticScoreBreakdownV2(
        channels=(),
        positive_score=breakdown.final_score,
        penalties=0.0,
        final_score=breakdown.final_score,
        policy_version=breakdown.policy_version,
    )


class SemanticRetrievalService:
    def __init__(
        self,
        repository: SemanticRetrievalRepository,
        *,
        cache: SemanticRetrievalCache | None = None,
        representation_provider: DeterministicFeatureEmbeddingProvider | None = None,
        vector_channel_enabled: bool = False,
        profile_tie_breaker_enabled: bool = False,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.representation_provider = (
            representation_provider or DeterministicFeatureEmbeddingProvider()
        )
        self.vector_channel_enabled = vector_channel_enabled
        self.profile_tie_breaker_enabled = profile_tie_breaker_enabled
        self.ranking = SemanticRankingEngine()

    @staticmethod
    def _cache_key(
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        version_id: uuid.UUID,
        request: SemanticSearchRequestV2,
        permission_hash: str,
        normalized_query: str,
        ranking_policy: SemanticRankingPolicyV2,
        threshold_policy: SemanticThresholdPolicyV2,
    ) -> SemanticCacheKeyV2:
        payload = {
            "tenant_id": str(tenant_id),
            "permission": permission_hash,
            "index_id": str(index_id),
            "version_id": str(version_id),
            "ranking": ranking_policy.policy_version,
            "thresholds": threshold_policy.policy_version,
            "locale": request.locale,
            "query": fingerprint_text(normalized_query),
            "types": sorted(item.value for item in request.context.expected_entity_types),
            "domain": request.context.expected_domain,
            "active": sorted(request.context.active_canonical_ids),
            "profile": sorted(request.context.profile_favorite_ids),
            "profile_enabled": request.context.profile_tie_breaker_enabled,
            "top_k": request.top_k,
        }
        checksum = checksum_for(payload)
        return SemanticCacheKeyV2(
            tenant_id=tenant_id,
            user_permission_fingerprint=permission_hash,
            index_id=index_id,
            index_version_id=version_id,
            ranking_policy_version=ranking_policy.policy_version,
            threshold_policy_version=threshold_policy.policy_version,
            locale=request.locale,
            normalized_query_fingerprint=fingerprint_text(normalized_query),
            expected_entity_types=tuple(sorted(request.context.expected_entity_types, key=lambda x: x.value)),
            domain_fingerprint=checksum_for(request.context.expected_domain or ""),
            context_fingerprint=checksum_for(sorted(request.context.active_canonical_ids)),
            profile_fingerprint=checksum_for(sorted(request.context.profile_favorite_ids)),
            top_k=request.top_k,
            checksum=checksum,
        )

    @staticmethod
    def _permission_allowed(candidate: SemanticStoredCandidate, user: User) -> bool:
        required = candidate.document.permission_requirement
        if required is None:
            return candidate.document.classification in {
                SemanticDataClassification.PUBLIC_BUSINESS_METADATA.value,
                SemanticDataClassification.TENANT_BUSINESS_METADATA.value,
            }
        try:
            permission = SemanticPermission(required)
        except ValueError:
            return False
        return permission in ROLE_PERMISSIONS.get(user.role, frozenset())

    def _evidence(
        self,
        *,
        stored: SemanticStoredCandidate,
        normalized_query,
        request: SemanticSearchRequestV2,
    ) -> tuple[SemanticRankingEvidence, ...]:
        document = stored.document
        label_normalized = normalize_semantic_text(
            document.display_label, locale=request.locale
        )
        canonical_normalized = normalize_semantic_text(
            document.canonical_key, locale=request.locale
        )
        evidence: list[SemanticRankingEvidence] = []
        if normalized_query.original.casefold() == document.canonical_key.casefold():
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.EXACT_CANONICAL,
                    1.0,
                    "EXACT_CANONICAL_ID",
                )
            )
        if normalized_query.normalized in stored.aliases:
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.EXACT_ALIAS,
                    1.0,
                    "PUBLISHED_ALIAS",
                )
            )
        if normalized_query.original.casefold() == document.display_label.casefold():
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.EXACT_LABEL,
                    1.0,
                    "EXACT_DISPLAY_LABEL",
                )
            )
        if normalized_query.normalized in {
            document.normalized_label,
            canonical_normalized.normalized,
        }:
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.NORMALIZED_EXACT,
                    1.0,
                    "NORMALIZED_EXACT",
                )
            )
        if (
            document.normalized_label.startswith(normalized_query.normalized)
            or normalized_query.normalized.startswith(document.normalized_label)
        ):
            shorter = min(len(document.normalized_label), len(normalized_query.normalized))
            longer = max(len(document.normalized_label), len(normalized_query.normalized), 1)
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.PREFIX,
                    shorter / longer,
                    "CONTROLLED_PREFIX",
                )
            )
        overlap = token_overlap(
            normalized_query.significant_tokens,
            label_normalized.significant_tokens,
        )
        if overlap:
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.TOKEN_OVERLAP,
                    overlap,
                    "TOKEN_JACCARD",
                )
            )
        character = max(
            [character_similarity(normalized_query.character_ngrams, label_normalized.character_ngrams)]
            + [
                character_similarity(
                    normalized_query.character_ngrams,
                    normalize_semantic_text(alias, locale=request.locale).character_ngrams,
                )
                for alias in stored.aliases
            ]
        )
        if character:
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.CHARACTER_SIMILARITY,
                    character,
                    "TRIGRAM_JACCARD",
                )
            )
        if self.vector_channel_enabled and stored.representation:
            stored_vector = tuple(stored.representation.get("vector", ()))
            query_vector = self.representation_provider.encode_query(normalized_query)
            if len(stored_vector) == query_vector.dimension:
                evidence.append(
                    SemanticRankingEvidence(
                        SemanticRetrievalChannel.VECTOR_SIMILARITY,
                        self.representation_provider.similarity(
                            query_vector.vector, stored_vector
                        ),
                        "LOCAL_FEATURE_HASH",
                    )
                )
        expected_types = request.context.expected_entity_types
        if expected_types:
            compatible = SemanticEntityType(document.entity_type) in expected_types
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.TYPE_COMPATIBILITY,
                    1.0 if compatible else 0.0,
                    "EXPECTED_TYPE_MATCH" if compatible else "EXPECTED_TYPE_MISMATCH",
                )
            )
        if request.context.expected_domain:
            compatible = document.domain.casefold() == request.context.expected_domain.casefold()
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.DOMAIN_COMPATIBILITY,
                    1.0 if compatible else 0.0,
                    "EXPECTED_DOMAIN_MATCH" if compatible else "EXPECTED_DOMAIN_MISMATCH",
                )
            )
        if document.canonical_key in request.context.active_canonical_ids:
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.CONTEXT_COMPATIBILITY,
                    1.0,
                    "ACTIVE_CONTEXT_REFERENCE",
                )
            )
        if (
            self.profile_tie_breaker_enabled
            and request.context.profile_tie_breaker_enabled
            and document.canonical_key in request.context.profile_favorite_ids
        ):
            evidence.append(
                SemanticRankingEvidence(
                    SemanticRetrievalChannel.PROFILE_TIE_BREAKER,
                    1.0,
                    "CONSENTED_PROFILE_FAVORITE",
                )
            )
        return tuple(evidence)

    async def search(
        self,
        *,
        user: User,
        request: SemanticSearchRequestV2,
        inspect_scores: bool = False,
        at: datetime | None = None,
    ) -> SemanticSearchResultV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.SEARCH,
        )
        if inspect_scores:
            require_permission(
                tenant_id=user.tenant_id,
                user_id=user.id,
                role=user.role,
                permission=SemanticPermission.INSPECT_SCORES,
            )
        if request.context.permission_fingerprint != permission_fingerprint(user.role):
            raise semantic_error(
                "SEMANTIC_INDEX_ACCESS_DENIED",
                "O contexto de permissao da busca nao corresponde ao usuario autenticado.",
            )
        normalized = normalize_semantic_text(request.query, locale=request.locale)
        active = await self.repository.get_active_version(
            tenant_id=user.tenant_id,
            index_id=request.index_id,
        )
        if active is None:
            return SemanticSearchResultV2(
                decision=EntityResolutionDecisionType.NOT_FOUND,
                normalized_query=normalized.normalized,
                candidates=(),
                public_explanation="Nenhum indice semantico publicado esta disponivel.",
                query_fingerprint=fingerprint_text(normalized.normalized),
            )
        definition, version = active
        ranking_policy = SemanticRankingPolicyV2.model_validate(definition.ranking_policy)
        threshold_policy = SemanticThresholdPolicyV2.model_validate(
            definition.threshold_policy
        )
        cache_key = self._cache_key(
            tenant_id=user.tenant_id,
            index_id=definition.id,
            version_id=version.id,
            request=request,
            permission_hash=permission_fingerprint(user.role),
            normalized_query=normalized.normalized,
            ranking_policy=ranking_policy,
            threshold_policy=threshold_policy,
        )
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                semantic_observability.increment("cache_hit")
                return cached.model_copy(update={"cache_hit": True})
            semantic_observability.increment("cache_miss")

        stored_candidates = await self.repository.find_candidate_documents(
            tenant_id=user.tenant_id,
            version_id=version.id,
            normalized_query=normalized.normalized,
            terms=normalized.significant_tokens,
            now=at or datetime.now(timezone.utc),
            limit=threshold_policy.maximum_total_candidates,
        )
        allowed_candidates = [
            item for item in stored_candidates if self._permission_allowed(item, user)
        ]
        if request.context.expected_entity_types:
            expected_types = set(request.context.expected_entity_types)
            allowed_candidates = [
                item
                for item in allowed_candidates
                if SemanticEntityType(item.document.entity_type) in expected_types
            ]
        if request.context.expected_domain:
            expected_domain = request.context.expected_domain.casefold()
            allowed_candidates = [
                item
                for item in allowed_candidates
                if item.document.domain.casefold() == expected_domain
            ]
        candidates: list[SemanticSearchCandidateV2] = []
        for stored in allowed_candidates:
            breakdown = self.ranking.score(
                self._evidence(
                    stored=stored,
                    normalized_query=normalized,
                    request=request,
                ),
                policy=ranking_policy,
                deprecated=False,
                stale=False,
            )
            if breakdown.final_score < threshold_policy.minimum_retrieval_score:
                continue
            reference = EntityCanonicalReferenceV2(
                canonical_id=stored.document.canonical_key,
                entity_type=SemanticEntityType(stored.document.entity_type),
                display_label=stored.document.display_label,
                tenant_id=user.tenant_id,
                domain=stored.document.domain,
                source_type=stored.document.source_type,
                source_id=stored.document.source_id,
                source_version=stored.document.source_version,
                permission_requirement=stored.document.permission_requirement,
            )
            candidates.append(
                SemanticSearchCandidateV2(
                    document_id=stored.document.id,
                    canonical_reference=reference,
                    public_label=stored.document.display_label,
                    entity_type=reference.entity_type,
                    domain=stored.document.domain,
                    score=breakdown.final_score,
                    confidence_band=_confidence_band(
                        breakdown.final_score, threshold_policy
                    ),
                    matched_channels=tuple(
                        item.channel
                        for item in breakdown.channels
                        if item.contribution > 0
                    ),
                    breakdown=_safe_breakdown(
                        breakdown, inspect_scores=inspect_scores
                    ),
                    index_version_id=version.id,
                    warnings=(),
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.score,
                item.canonical_reference.canonical_id,
                str(item.document_id),
            )
        )
        candidates = candidates[: min(request.top_k, threshold_policy.maximum_candidates)]
        selected = None
        ambiguity = None
        if not candidates:
            decision = EntityResolutionDecisionType.UNRESOLVED
            explanation = "Nao encontrei uma correspondencia semantica confiavel."
        else:
            top = candidates[0]
            runner_up = candidates[1] if len(candidates) > 1 else None
            margin = top.score - runner_up.score if runner_up else 1.0
            if (
                top.score >= threshold_policy.minimum_automatic_resolution_score
                and margin >= threshold_policy.ambiguity_margin
            ):
                decision = EntityResolutionDecisionType.RESOLVED
                selected = top
                explanation = f"Correspondencia identificada: {top.public_label}."
                semantic_observability.increment("resolved")
            elif runner_up and top.score >= threshold_policy.minimum_retrieval_score:
                decision = EntityResolutionDecisionType.AMBIGUOUS
                ambiguity = SemanticAmbiguityV2(
                    reason_code="CANDIDATE_MARGIN_BELOW_POLICY",
                    top_score=top.score,
                    runner_up_score=runner_up.score,
                    margin=max(0.0, margin),
                    required_margin=threshold_policy.ambiguity_margin,
                    candidate_ids=tuple(item.document_id for item in candidates),
                )
                explanation = "Encontrei mais de uma opcao possivel. Selecione a correta."
                semantic_observability.increment("ambiguous")
            else:
                decision = EntityResolutionDecisionType.UNRESOLVED
                explanation = "Nao encontrei uma correspondencia semantica confiavel."
                semantic_observability.increment("unresolved")
        result = SemanticSearchResultV2(
            decision=decision,
            normalized_query=normalized.normalized,
            candidates=tuple(candidates),
            selected=selected,
            ambiguity=ambiguity,
            public_explanation=explanation,
            index_version_id=version.id,
            ranking_policy_version=ranking_policy.policy_version,
            threshold_policy_version=threshold_policy.policy_version,
            query_fingerprint=fingerprint_text(normalized.normalized),
        )
        semantic_observability.increment("search")
        if self.cache:
            self.cache.put(cache_key, result)
        return result
