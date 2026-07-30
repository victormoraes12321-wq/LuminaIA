from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.user_analytical_profile_v2 import (
    PreferenceApplicationContext,
    PreferenceApplicationResultV2,
    UserPreferenceType,
    UserProfileRolloutMode,
)
from models.enterprise_knowledge import EnterpriseKnowledgeAsset
from models.user import User
from services.context_resolution import ContextResolutionResult

from .application import UserPreferenceApplicationEngine
from .cache import UserProfileCache
from .repository import UserAnalyticalProfileRepository
from .service import UserAnalyticalProfileService


@dataclass(frozen=True)
class UserProfileShadowMetadata:
    eligible_count: int
    applied_count: int
    skipped_count: int
    conflict_count: int
    consent_required_count: int
    contract_version: str
    rollout_mode: str


class UserAnalyticalProfileRuntime:
    """Bounded integration after context resolution and before planning."""

    def __init__(
        self,
        *,
        mode: UserProfileRolloutMode | None = None,
        engine: UserPreferenceApplicationEngine | None = None,
        cache: UserProfileCache | None = None,
    ) -> None:
        self.mode = mode or UserProfileRolloutMode(
            settings.USER_ANALYTICAL_PROFILE_MODE
        )
        self.engine = engine or UserPreferenceApplicationEngine()
        self.cache = cache or UserProfileCache(
            enabled=settings.USER_ANALYTICAL_PROFILE_CACHE_ENABLED,
            ttl_seconds=settings.USER_ANALYTICAL_PROFILE_CACHE_TTL_SECONDS,
        )

    async def resolve_after_context(
        self,
        *,
        db: AsyncSession,
        user: User,
        current_question: str,
        conversation_state,
        context_resolution: ContextResolutionResult,
        request_id: str,
    ) -> PreferenceApplicationResultV2 | None:
        if self.mode == UserProfileRolloutMode.LEGACY_ONLY:
            return None
        repo = UserAnalyticalProfileRepository(db)
        row = await repo.get_profile(
            tenant_id=user.tenant_id,
            user_id=user.id,
        )
        if row is None:
            return None
        profile = await UserAnalyticalProfileService(
            db,
            cache=self.cache,
        ).profile_contract(user=user)
        preferences = profile.preferences
        if not settings.USER_ANALYTICAL_PROFILE_DEFAULTS_ENABLED:
            preferences = [
                item
                for item in preferences
                if item.preference_type != UserPreferenceType.ANALYTICAL_DEFAULT
            ]
        if not settings.USER_ANALYTICAL_PROFILE_SAVED_FILTERS_ENABLED:
            preferences = [
                item
                for item in preferences
                if item.preference_type != UserPreferenceType.SAVED_FILTER_REFERENCE
            ]
        profile = profile.model_copy(update={"preferences": preferences})

        published_ids = list(
            await db.scalars(
                select(EnterpriseKnowledgeAsset.canonical_key).where(
                    EnterpriseKnowledgeAsset.tenant_id == user.tenant_id,
                    EnterpriseKnowledgeAsset.status == "ACTIVE",
                    EnterpriseKnowledgeAsset.current_published_version_id.is_not(None),
                )
            )
        )
        relationship = context_resolution.relationship.value
        application_context = PreferenceApplicationContext(
            tenant_id=user.tenant_id,
            user_id=user.id,
            request_id=request_id,
            reference_datetime=context_resolution.patch.resolved_at,
            current_question=current_question,
            reset_explicit=relationship == "RESET",
            removal_fields=list(
                context_resolution.public_context_summary.removed_fields
            ),
            pending_clarification=context_resolution.clarification is not None,
            allowed_canonical_ids=published_ids,
            allowed_filter_fields=[
                "filial",
                "filial_id",
                "unidade_negocio_id",
                "vendedor_id",
                "cliente_id",
                "produto_id",
            ],
            rollout_mode=self.mode,
        )
        return self.engine.apply(
            current_intent=context_resolution.resolved_intent,
            current_question=current_question,
            conversation_state=conversation_state,
            context_resolution=context_resolution,
            profile=profile,
            context=application_context,
        )

    @staticmethod
    def safe_metadata(
        result: PreferenceApplicationResultV2,
    ) -> UserProfileShadowMetadata:
        return UserProfileShadowMetadata(
            eligible_count=len(result.decisions),
            applied_count=sum(item.decision.value == "APPLIED" for item in result.decisions),
            skipped_count=sum(item.decision.value == "SKIPPED" for item in result.decisions),
            conflict_count=len(result.conflicts),
            consent_required_count=sum(
                item.decision.value == "CONSENT_REQUIRED" for item in result.decisions
            ),
            contract_version=result.schema_version,
            rollout_mode="SHADOW" if result.shadow_only else "ACTIVE",
        )
