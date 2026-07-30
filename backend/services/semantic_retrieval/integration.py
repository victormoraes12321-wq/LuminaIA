from __future__ import annotations

from dataclasses import dataclass

from contracts.analytical_v2 import FieldOrigin, QueryIntentV2
from contracts.semantic_retrieval_v2 import (
    EntityMentionV2,
    EntityResolutionRequestV2,
    EntityResolutionResultV2,
)
from database import get_db_context
from models.user import User
from services.semantic_retrieval.cache import SemanticRetrievalCache
from services.semantic_retrieval.clarification import SemanticClarificationService
from services.semantic_retrieval.feature_flags import SemanticRetrievalFeaturePolicy
from services.semantic_retrieval.mentions import SemanticMentionExtractor
from services.semantic_retrieval.normalization import normalize_semantic_text
from services.semantic_retrieval.permissions import permission_fingerprint
from services.semantic_retrieval.repository import SemanticRetrievalRepository
from services.semantic_retrieval.resolution import (
    GovernedEntityResolutionService,
    resolution_context,
)
from services.semantic_retrieval.retrieval import SemanticRetrievalService


@dataclass(frozen=True)
class SemanticPipelineResolution:
    original_intent: QueryIntentV2
    resolved_intent: QueryIntentV2
    result: EntityResolutionResultV2
    authored: bool


def apply_resolution_patch(
    intent: QueryIntentV2,
    result: EntityResolutionResultV2,
    mentions: tuple[EntityMentionV2, ...],
) -> QueryIntentV2:
    mention_by_id = {mention.mention_id: mention for mention in mentions}
    operation_by_mention = {
        operation.mention_id: operation
        for operation in result.patch.operations
        if operation.canonical_reference is not None
        and operation.operation != "ATTACH_PROVENANCE"
    }
    metric_refs = []
    dimension_refs = []
    filters = list(intent.filters)

    for metric in intent.metric_refs:
        replacement = next(
            (
                operation.canonical_reference
                for mention_id, operation in operation_by_mention.items()
                if operation.operation == "SET_CANONICAL_METRIC"
                and operation.canonical_reference is not None
                and mention_id in mention_by_id
                and mention_by_id[mention_id].normalized_text
                == normalize_semantic_text(metric.display_name).normalized
            ),
            None,
        )
        metric_refs.append(
            metric.model_copy(
                update={
                    "metric_id": replacement.canonical_id,
                    "display_name": replacement.display_label,
                    "origin": FieldOrigin.TENANT_KNOWLEDGE,
                }
            )
            if replacement
            else metric
        )

    for dimension in intent.dimension_refs:
        replacement = next(
            (
                operation.canonical_reference
                for mention_id, operation in operation_by_mention.items()
                if operation.operation == "SET_CANONICAL_DIMENSION"
                and operation.canonical_reference is not None
                and mention_id in mention_by_id
                and mention_by_id[mention_id].normalized_text
                == normalize_semantic_text(dimension.display_name).normalized
            ),
            None,
        )
        dimension_refs.append(
            dimension.model_copy(
                update={
                    "dimension_id": replacement.canonical_id,
                    "display_name": replacement.display_label,
                    "origin": FieldOrigin.TENANT_KNOWLEDGE,
                }
            )
            if replacement
            else dimension
        )

    filters = []
    for query_filter in intent.filters:
        updated = query_filter
        field_replacement = next(
            (
                operation.canonical_reference
                for mention_id, operation in operation_by_mention.items()
                if operation.operation == "SET_CANONICAL_FILTER_FIELD"
                and operation.canonical_reference is not None
                and mention_id in mention_by_id
                and mention_by_id[mention_id].candidate_field
                == query_filter.filter_id
            ),
            None,
        )
        if field_replacement is not None:
            updated = updated.model_copy(
                update={
                    "field_id": field_replacement.canonical_id,
                    "origin": FieldOrigin.TENANT_KNOWLEDGE,
                }
            )

        scalar_value = query_filter.value
        list_values = list(query_filter.values)
        values_changed = False
        for mention_id, operation in operation_by_mention.items():
            mention = mention_by_id.get(mention_id)
            reference = operation.canonical_reference
            if (
                operation.operation != "SET_CANONICAL_FILTER_VALUE"
                or reference is None
                or mention is None
                or mention.candidate_field != query_filter.field_id
            ):
                continue
            if (
                isinstance(scalar_value, (str, int))
                and str(scalar_value).casefold() == mention.text.casefold()
            ):
                scalar_value = reference.canonical_id
                values_changed = True
            for index, value in enumerate(list_values):
                if (
                    isinstance(value, (str, int))
                    and str(value).casefold() == mention.text.casefold()
                ):
                    list_values[index] = reference.canonical_id
                    values_changed = True
        if values_changed:
            updated = updated.model_copy(
                update={
                    "value": scalar_value,
                    "values": list_values,
                    "origin": FieldOrigin.TENANT_KNOWLEDGE,
                }
            )
        filters.append(updated)

    field_origins = dict(intent.field_origins)
    if metric_refs != intent.metric_refs:
        field_origins["metric_refs"] = FieldOrigin.TENANT_KNOWLEDGE
    if dimension_refs != intent.dimension_refs:
        field_origins["dimension_refs"] = FieldOrigin.TENANT_KNOWLEDGE
    if filters != intent.filters:
        field_origins["filters"] = FieldOrigin.TENANT_KNOWLEDGE
    return intent.model_copy(
        update={
            "metric_refs": metric_refs,
            "dimension_refs": dimension_refs,
            "filters": filters,
            "field_origins": field_origins,
        }
    )


class SemanticResolutionRuntime:
    def __init__(self, policy: SemanticRetrievalFeaturePolicy | None = None) -> None:
        self.policy = policy or SemanticRetrievalFeaturePolicy.from_settings()
        self.extractor = SemanticMentionExtractor()

    async def resolve_after_context(
        self,
        *,
        intent: QueryIntentV2,
        context,
    ) -> SemanticPipelineResolution | None:
        if not self.policy.can_read_v2:
            return None
        mentions = self.extractor.extract(intent)
        if not mentions:
            return None
        from config import settings
        from sqlalchemy import select

        async with get_db_context() as db:
            user = await db.scalar(
                select(User).where(
                    User.id == context.user_id,
                    User.tenant_id == context.tenant_id,
                    User.ativo.is_(True),
                )
            )
            if user is None:
                return None
            repository = SemanticRetrievalRepository(db)
            cache = SemanticRetrievalCache(
                enabled=self.policy.cache_enabled,
                ttl_seconds=settings.SEMANTIC_RETRIEVAL_CACHE_TTL_SECONDS,
            )
            retrieval = SemanticRetrievalService(
                repository,
                cache=cache,
                vector_channel_enabled=self.policy.vector_channel_enabled,
                profile_tie_breaker_enabled=self.policy.profile_tie_breaker_enabled,
            )
            clarification = SemanticClarificationService(
                repository,
                signing_secret=settings.SECRET_KEY,
            )
            resolver = GovernedEntityResolutionService(
                retrieval, clarification=clarification
            )
            result = await resolver.resolve(
                user=user,
                request=EntityResolutionRequestV2(
                    mentions=mentions,
                    context=resolution_context(
                        tenant_id=user.tenant_id,
                        user_id=user.id,
                        session_id=context.session_id,
                        permission_fingerprint=permission_fingerprint(user.role),
                    ),
                ),
            )
            resolved_intent = (
                apply_resolution_patch(intent, result, mentions)
                if self.policy.can_author_intent and result.readiness == "READY"
                else intent
            )
            return SemanticPipelineResolution(
                original_intent=intent,
                resolved_intent=resolved_intent,
                result=result,
                authored=resolved_intent is not intent,
            )
