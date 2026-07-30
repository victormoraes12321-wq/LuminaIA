from __future__ import annotations

from dataclasses import dataclass

from config import settings
from contracts.semantic_retrieval_v2 import SemanticRolloutMode


@dataclass(frozen=True)
class SemanticRetrievalFeaturePolicy:
    mode: SemanticRolloutMode
    frontend_enabled: bool
    entity_instance_indexing_enabled: bool
    vector_channel_enabled: bool
    profile_tie_breaker_enabled: bool
    approved_feedback_corpus_enabled: bool
    restricted_entities_enabled: bool
    admin_inspector_enabled: bool
    cache_enabled: bool
    incremental_build_enabled: bool

    @classmethod
    def from_settings(cls) -> "SemanticRetrievalFeaturePolicy":
        return cls(
            mode=SemanticRolloutMode(settings.SEMANTIC_RETRIEVAL_MODE),
            frontend_enabled=settings.SEMANTIC_RETRIEVAL_FRONTEND_ENABLED,
            entity_instance_indexing_enabled=(
                settings.SEMANTIC_ENTITY_INSTANCE_INDEXING_ENABLED
            ),
            vector_channel_enabled=settings.SEMANTIC_VECTOR_CHANNEL_ENABLED,
            profile_tie_breaker_enabled=settings.SEMANTIC_PROFILE_TIE_BREAKER_ENABLED,
            approved_feedback_corpus_enabled=(
                settings.SEMANTIC_APPROVED_FEEDBACK_CORPUS_ENABLED
            ),
            restricted_entities_enabled=settings.SEMANTIC_RESTRICTED_ENTITIES_ENABLED,
            admin_inspector_enabled=settings.SEMANTIC_ADMIN_INSPECTOR_ENABLED,
            cache_enabled=settings.SEMANTIC_RETRIEVAL_CACHE_ENABLED,
            incremental_build_enabled=settings.SEMANTIC_INCREMENTAL_BUILD_ENABLED,
        )

    @property
    def can_read_v2(self) -> bool:
        return self.mode in {
            SemanticRolloutMode.SHADOW,
            SemanticRolloutMode.HYBRID_READ,
            SemanticRolloutMode.V2_AUTHORITATIVE,
        }

    @property
    def can_author_intent(self) -> bool:
        return self.mode == SemanticRolloutMode.V2_AUTHORITATIVE

    @property
    def shadow_only(self) -> bool:
        return self.mode == SemanticRolloutMode.SHADOW
