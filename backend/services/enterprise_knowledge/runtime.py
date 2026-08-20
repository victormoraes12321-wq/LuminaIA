from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from contracts.enterprise_knowledge_v2 import (
    KnowledgeResolutionResultV2,
    KnowledgeRolloutMode,
)
from models.user import User
from services.enterprise_knowledge.service import EnterpriseKnowledgeService

logger = logging.getLogger("luminaai.enterprise_knowledge.runtime")


@dataclass(frozen=True)
class KnowledgeRuntimeProjection:
    canonical_id: str
    display_label: str
    domain: str
    asset_type: str
    unit: str | None
    allowed_dimensions: tuple[str, ...]
    exclusions: tuple[str, ...]
    provenance_asset_id: str
    provenance_version_id: str
    provenance_checksum: str

    def as_intent_context(self) -> dict[str, str | list[str]]:
        """Return the bounded, non-physical payload allowed at the intent boundary."""
        return {
            "canonical_id": self.canonical_id,
            "display_label": self.display_label,
            "domain": self.domain,
            "asset_type": self.asset_type,
            "unit": self.unit or "",
            "allowed_dimensions": list(self.allowed_dimensions),
            "exclusions": list(self.exclusions),
            "provenance_asset_id": self.provenance_asset_id,
            "provenance_version_id": self.provenance_version_id,
            "provenance_checksum": self.provenance_checksum,
        }


class EnterpriseKnowledgeRuntime:
    """Published-only semantic adapter. It never compiles SQL or calculates values."""

    def __init__(
        self,
        service: EnterpriseKnowledgeService,
        *,
        mode: KnowledgeRolloutMode,
    ) -> None:
        self.service = service
        self.mode = mode

    @property
    def v2_read_enabled(self) -> bool:
        return self.mode in {
            KnowledgeRolloutMode.SHADOW_READ,
            KnowledgeRolloutMode.V2_READ,
            KnowledgeRolloutMode.V2_READ_WRITE,
        }

    @property
    def v2_write_enabled(self) -> bool:
        return self.mode == KnowledgeRolloutMode.V2_READ_WRITE

    async def resolve(
        self,
        *,
        user: User,
        query: str,
        at: datetime | None = None,
    ) -> KnowledgeResolutionResultV2 | None:
        if not self.v2_read_enabled:
            return None
        result = await self.service.resolve(user=user, query=query, at=at)
        if self.mode == KnowledgeRolloutMode.SHADOW_READ:
            logger.info(
                "enterprise_knowledge_shadow candidates=%d ambiguous=%s contract=%s",
                len(result.candidates),
                result.ambiguous,
                result.schema_version,
            )
            return None
        return result

    async def projection_for_intent(
        self,
        *,
        user: User,
        query: str,
        at: datetime | None = None,
        limit: int = 5,
    ) -> tuple[KnowledgeRuntimeProjection, ...]:
        if not self.v2_read_enabled:
            return ()
        result = await self.service.resolve(user=user, query=query, at=at)
        projections: list[KnowledgeRuntimeProjection] = []
        for candidate in result.candidates[:limit]:
            projections.append(
                KnowledgeRuntimeProjection(
                    canonical_id=candidate.canonical_key,
                    display_label=candidate.display_name,
                    domain=candidate.domain,
                    asset_type=candidate.asset_type.value,
                    unit=None,
                    allowed_dimensions=(),
                    exclusions=(),
                    provenance_asset_id=str(candidate.asset_id),
                    provenance_version_id=str(candidate.version_id),
                    provenance_checksum=candidate.checksum,
                )
            )
        return tuple(projections)

    async def candidates_for_canonicalizer(
        self,
        *,
        user: User,
        query: str,
        at: datetime | None = None,
    ) -> tuple[KnowledgeRuntimeProjection, ...]:
        """Published-only candidates; ambiguity is preserved for the caller."""
        return await self.projection_for_intent(user=user, query=query, at=at)

    async def facts_for_context(
        self,
        *,
        user: User,
        query: str,
        at: datetime | None = None,
    ) -> tuple[dict[str, str | list[str]], ...]:
        """Context facts carry provenance and never contain conversation state."""
        projections = await self.projection_for_intent(user=user, query=query, at=at)
        return tuple(projection.as_intent_context() for projection in projections)
