from __future__ import annotations

import uuid

from contracts.semantic_retrieval_v2 import (
    EntityResolutionContextV2,
    EntityResolutionDecisionType,
    EntityResolutionDecisionV2,
    EntityResolutionPatchOperationV2,
    EntityResolutionPatchV2,
    EntityResolutionRequestV2,
    EntityResolutionResultV2,
    SemanticEntityType,
    SemanticPermission,
    SemanticSearchContextV2,
    SemanticSearchRequestV2,
)
from models.user import User
from services.semantic_retrieval.checksums import checksum_for
from services.semantic_retrieval.clarification import SemanticClarificationService
from services.semantic_retrieval.observability import semantic_observability
from services.semantic_retrieval.permissions import require_permission
from services.semantic_retrieval.retrieval import SemanticRetrievalService


def _operation_for(mention, candidate) -> str:
    if mention.source == "FILTER_FIELD":
        return "SET_CANONICAL_FILTER_FIELD"
    if mention.source == "FILTER_VALUE":
        return "SET_CANONICAL_FILTER_VALUE"
    if candidate.entity_type == SemanticEntityType.METRIC:
        return "SET_CANONICAL_METRIC"
    if candidate.entity_type == SemanticEntityType.DIMENSION:
        return "SET_CANONICAL_DIMENSION"
    return "SET_CANONICAL_ENTITY"


class GovernedEntityResolutionService:
    def __init__(
        self,
        retrieval: SemanticRetrievalService,
        *,
        clarification: SemanticClarificationService | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.clarification = clarification

    async def resolve(
        self,
        *,
        user: User,
        request: EntityResolutionRequestV2,
    ) -> EntityResolutionResultV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.RESOLVE,
        )
        if request.context.tenant_id != user.tenant_id or request.context.user_id != user.id:
            semantic_observability.increment("cross_tenant_denial")
            from services.semantic_retrieval.errors import semantic_error

            raise semantic_error(
                "ENTITY_RESOLUTION_FORBIDDEN",
                "O contexto de resolucao nao pertence ao usuario autenticado.",
            )

        decisions: list[EntityResolutionDecisionV2] = []
        references = []
        ambiguities = []
        unresolved: list[uuid.UUID] = []
        operations: list[EntityResolutionPatchOperationV2] = []
        first_ambiguous = None

        for mention in request.mentions:
            expected = (
                (mention.expected_entity_type,)
                if mention.expected_entity_type != SemanticEntityType.UNKNOWN
                else request.context.expected_entity_types
            )
            result = await self.retrieval.search(
                user=user,
                request=SemanticSearchRequestV2(
                    query=mention.text,
                    index_id=request.index_id,
                    context=SemanticSearchContextV2(
                        expected_entity_types=expected,
                        expected_domain=request.context.domain,
                        active_canonical_ids=request.context.active_canonical_ids,
                        profile_favorite_ids=request.context.profile_favorite_ids,
                        permission_fingerprint=request.context.permission_fingerprint,
                        profile_tie_breaker_enabled=(
                            request.context.profile_tie_breaker_enabled
                        ),
                    ),
                    top_k=10,
                ),
            )
            selected = result.selected
            decisions.append(
                EntityResolutionDecisionV2(
                    mention_id=mention.mention_id,
                    decision=result.decision,
                    reason_code=(
                        "UNIQUE_CANDIDATE_ABOVE_POLICY"
                        if result.decision == EntityResolutionDecisionType.RESOLVED
                        else (
                            result.ambiguity.reason_code
                            if result.ambiguity
                            else "NO_CANDIDATE_ABOVE_POLICY"
                        )
                    ),
                    candidate_count=len(result.candidates),
                    selected_candidate=selected,
                    confidence=selected.score if selected else 0.0,
                    score=selected.score if selected else (
                        result.candidates[0].score if result.candidates else 0.0
                    ),
                    margin=result.ambiguity.margin if result.ambiguity else None,
                    index_version_id=result.index_version_id,
                )
            )
            if selected:
                reference = selected.canonical_reference
                references.append(reference)
                operations.append(
                    EntityResolutionPatchOperationV2(
                        operation=_operation_for(mention, selected),
                        mention_id=mention.mention_id,
                        canonical_reference=reference,
                        reason_code="GOVERNED_SEMANTIC_RESOLUTION",
                    )
                )
                operations.append(
                    EntityResolutionPatchOperationV2(
                        operation="ATTACH_PROVENANCE",
                        mention_id=mention.mention_id,
                        canonical_reference=reference,
                        reason_code="PUBLISHED_INDEX_PROVENANCE",
                    )
                )
            elif result.ambiguity:
                ambiguities.append(result.ambiguity)
                first_ambiguous = first_ambiguous or (mention, result.candidates)
                operations.append(
                    EntityResolutionPatchOperationV2(
                        operation="CREATE_CLARIFICATION",
                        mention_id=mention.mention_id,
                        reason_code="AMBIGUITY_REQUIRES_USER_SELECTION",
                    )
                )
            else:
                unresolved.append(mention.mention_id)
                operations.append(
                    EntityResolutionPatchOperationV2(
                        operation="MARK_UNRESOLVED",
                        mention_id=mention.mention_id,
                        reason_code="NO_CANDIDATE_ABOVE_POLICY",
                    )
                )

        clarification = None
        if (
            first_ambiguous
            and self.clarification
            and request.context.session_id is not None
        ):
            mention, candidates = first_ambiguous
            clarification = await self.clarification.create(
                user=user,
                session_id=request.context.session_id,
                mention_id=mention.mention_id,
                candidates=candidates,
            )
        patch_checksum = checksum_for(
            [item.model_dump(mode="json") for item in operations]
        )
        patch = EntityResolutionPatchV2(
            operations=tuple(operations),
            checksum=patch_checksum,
        )
        readiness = (
            "CLARIFICATION_REQUIRED"
            if ambiguities
            else ("BLOCKED" if unresolved else "READY")
        )
        index_version_id = next(
            (
                item.index_version_id
                for item in decisions
                if item.index_version_id is not None
            ),
            None,
        )
        if ambiguities:
            semantic_observability.increment("resolution")
        elif unresolved:
            semantic_observability.increment("blocked")
        else:
            semantic_observability.increment("resolution")
        return EntityResolutionResultV2(
            readiness=readiness,
            decisions=tuple(decisions),
            resolved_references=tuple(references),
            ambiguities=tuple(ambiguities),
            unresolved_mentions=tuple(unresolved),
            patch=patch,
            clarification=clarification,
            index_version_id=index_version_id,
            provenance_checksum=checksum_for(
                {
                    "patch": patch_checksum,
                    "version": str(index_version_id) if index_version_id else None,
                    "resolved_ids": sorted(item.canonical_id for item in references),
                }
            ),
        )


def resolution_context(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    permission_fingerprint: str,
    session_id: uuid.UUID | None = None,
    expected_entity_types: tuple[SemanticEntityType, ...] = (),
    domain: str | None = None,
    active_canonical_ids: tuple[str, ...] = (),
    removed_canonical_ids: tuple[str, ...] = (),
    profile_favorite_ids: tuple[str, ...] = (),
    profile_tie_breaker_enabled: bool = False,
) -> EntityResolutionContextV2:
    return EntityResolutionContextV2(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        expected_entity_types=expected_entity_types,
        domain=domain,
        active_canonical_ids=active_canonical_ids,
        removed_canonical_ids=removed_canonical_ids,
        profile_favorite_ids=profile_favorite_ids,
        permission_fingerprint=permission_fingerprint,
        profile_tie_breaker_enabled=profile_tie_breaker_enabled,
    )
