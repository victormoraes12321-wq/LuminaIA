from __future__ import annotations

import uuid
from dataclasses import dataclass

from contracts.enterprise_knowledge_v2 import (
    BusinessTermContentV2,
    KnowledgeAssetCreateV2,
    KnowledgeAssetType,
)
from services.enterprise_knowledge.normalization import normalize_lexical


@dataclass(frozen=True)
class LegacyKnowledgeConversion:
    draft: KnowledgeAssetCreateV2 | None
    warnings: tuple[str, ...]


class LegacyBusinessKnowledgeAdapter:
    """Converts explicit legacy records to V2 drafts without approval or publication."""

    @staticmethod
    def convert_concept(
        *,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID | None,
        name: str,
        description: str,
        domain: str,
        aliases: list[str],
    ) -> LegacyKnowledgeConversion:
        del tenant_id  # Tenant is required by the caller and applied by the service.
        if owner_user_id is None:
            return LegacyKnowledgeConversion(
                draft=None,
                warnings=("LEGACY_OWNER_REQUIRED",),
            )
        key = normalize_lexical(name).replace(" ", "_")
        if len(key) < 2:
            return LegacyKnowledgeConversion(
                draft=None,
                warnings=("LEGACY_CANONICAL_KEY_INVALID",),
            )
        content = BusinessTermContentV2(
            kind=KnowledgeAssetType.BUSINESS_TERM,
            canonical_name=key,
            display_name=name,
            definition=description,
            domain=domain,
            short_description=description[:500],
            full_description=description,
            aliases=aliases,
            allowed_examples=[],
            incorrect_examples=[],
            related_terms=[],
            source_references=[],
            tags=["legacy-import"],
        )
        return LegacyKnowledgeConversion(
            draft=KnowledgeAssetCreateV2(
                canonical_key=key,
                asset_type=KnowledgeAssetType.BUSINESS_TERM,
                domain=domain,
                owner_user_id=owner_user_id,
                accountable_area=domain,
                steward_label="Legacy import pending review",
                content=content,
            ),
            warnings=("LEGACY_DRAFT_REQUIRES_REVIEW",),
        )
