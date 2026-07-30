from __future__ import annotations

import csv
import io
import time
import uuid
from datetime import datetime, timezone

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.enterprise_knowledge_v2 import (
    CONTRACT_VERSION,
    EnterpriseKnowledgeAssetV2,
    EnterpriseKnowledgeContentV2,
    EnterpriseKnowledgeVersionV2,
    KnowledgeApprovalDecision,
    KnowledgeApprovalV2,
    KnowledgeAssetCreateV2,
    KnowledgeAssetStatus,
    KnowledgeAssetType,
    KnowledgeAuditEventType,
    KnowledgeAuditEventV2,
    KnowledgeDiffV2,
    KnowledgeExportFormat,
    KnowledgeExportV2,
    KnowledgeImportRequestV2,
    KnowledgeImportResultV2,
    KnowledgeLifecycle,
    KnowledgeMatchType,
    KnowledgeOwnershipV2,
    KnowledgePermission,
    KnowledgePublicationV2,
    KnowledgeResolutionCandidateV2,
    KnowledgeResolutionResultV2,
    KnowledgeSearchRequestV2,
    KnowledgeSearchResultV2,
    KnowledgeSourceReferenceV2,
    KnowledgeVersionUpdateV2,
    MetricKnowledgeContentV2,
    SemanticRelationContentV2,
)
from models.enterprise_knowledge import (
    EnterpriseKnowledgeApproval,
    EnterpriseKnowledgeAsset,
    EnterpriseKnowledgeEvent,
    EnterpriseKnowledgeImport,
    EnterpriseKnowledgePublication,
    EnterpriseKnowledgeRelation,
    EnterpriseKnowledgeVersion,
)
from models.user import User, UserRole
from services.enterprise_knowledge.cache import EnterpriseKnowledgeCache
from services.enterprise_knowledge.errors import (
    KnowledgeAccessDeniedError,
    KnowledgeBindingError,
    KnowledgeConflictError,
    KnowledgeFeatureDisabledError,
    KnowledgeLifecycleError,
    KnowledgeNotFoundError,
    KnowledgeValidationError,
)
from services.enterprise_knowledge.metric_binding import validate_metric_binding
from services.enterprise_knowledge.normalization import (
    compute_checksum,
    csv_safe,
    decode_cursor,
    encode_cursor,
    normalize_lexical,
)
from services.enterprise_knowledge.observability import KnowledgeCounters
from services.enterprise_knowledge.permissions import require_permission
from services.enterprise_knowledge.repository import EnterpriseKnowledgeRepository


CONTENT_ADAPTER = TypeAdapter(EnterpriseKnowledgeContentV2)
IMMUTABLE_LIFECYCLES = {"APPROVED", "PUBLISHED", "DEPRECATED", "ARCHIVED"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _content_from_row(row: EnterpriseKnowledgeVersion) -> EnterpriseKnowledgeContentV2:
    return CONTENT_ADAPTER.validate_python(row.content, strict=False)


def _display_name(content: EnterpriseKnowledgeContentV2) -> str:
    return content.display_name


def _source_references(
    content: EnterpriseKnowledgeContentV2,
) -> list[KnowledgeSourceReferenceV2]:
    references = getattr(content, "source_references", [])
    return list(references)


def _content_aliases(content: EnterpriseKnowledgeContentV2) -> tuple[list[str], str]:
    aliases = list(getattr(content, "aliases", []))
    locale = str(getattr(content, "locale", "pt-BR"))
    return aliases, locale


class EnterpriseKnowledgeService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        cache: EnterpriseKnowledgeCache | None = None,
        counters: KnowledgeCounters | None = None,
        import_enabled: bool = False,
        export_enabled: bool = False,
    ) -> None:
        self.db = db
        self.repository = EnterpriseKnowledgeRepository(db)
        self.cache = cache or EnterpriseKnowledgeCache(enabled=False)
        self.counters = counters
        self.import_enabled = import_enabled
        self.export_enabled = export_enabled

    @staticmethod
    def _require(user: User, permission: KnowledgePermission) -> None:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=permission,
        )

    def _invalidate_cache(self, tenant_id: uuid.UUID) -> None:
        self.cache.invalidate_tenant(tenant_id)
        if self.counters is not None:
            self.counters.increment("cache_invalidations")

    async def _require_user_in_tenant(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User:
        row = await self.db.scalar(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.ativo.is_(True),
            )
        )
        if row is None:
            raise KnowledgeValidationError(
                "O responsável informado não existe ou não está ativo neste tenant.",
                details={"reason": "INVALID_TENANT_USER"},
            )
        return row

    async def _asset(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        for_update: bool = False,
    ) -> EnterpriseKnowledgeAsset:
        row = await self.repository.get_asset(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            for_update=for_update,
        )
        if row is None:
            raise KnowledgeNotFoundError("Asset de conhecimento não encontrado.")
        return row

    async def _version(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        for_update: bool = False,
    ) -> EnterpriseKnowledgeVersion:
        row = await self.repository.get_version(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            version_id=version_id,
            for_update=for_update,
        )
        if row is None:
            raise KnowledgeNotFoundError("Versão de conhecimento não encontrada.")
        return row

    async def _event(
        self,
        *,
        user: User,
        event_type: KnowledgeAuditEventType,
        reason_code: str,
        asset_id: uuid.UUID | None = None,
        version_id: uuid.UUID | None = None,
        metadata: dict[str, str | int | bool] | None = None,
    ) -> EnterpriseKnowledgeEvent:
        event = await self.repository.add_event(
            EnterpriseKnowledgeEvent(
                tenant_id=user.tenant_id,
                asset_id=asset_id,
                version_id=version_id,
                actor_user_id=user.id,
                event_type=event_type.value,
                reason_code=reason_code,
                event_metadata=metadata or {},
                schema_version=CONTRACT_VERSION,
            )
        )
        if self.counters is not None:
            self.counters.increment(event_type.value.lower())
        return event

    @staticmethod
    def asset_contract(row: EnterpriseKnowledgeAsset) -> EnterpriseKnowledgeAssetV2:
        return EnterpriseKnowledgeAssetV2(
            asset_id=row.id,
            tenant_id=row.tenant_id,
            canonical_key=row.canonical_key,
            asset_type=KnowledgeAssetType(row.asset_type),
            domain=row.domain,
            ownership=KnowledgeOwnershipV2(
                owner_user_id=row.owner_user_id,
                steward_label=row.steward_label,
                accountable_area=row.accountable_area,
            ),
            status=KnowledgeAssetStatus(row.status),
            current_published_version_id=row.current_published_version_id,
            lock_version=row.lock_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def version_contract(row: EnterpriseKnowledgeVersion) -> EnterpriseKnowledgeVersionV2:
        return EnterpriseKnowledgeVersionV2(
            version_id=row.id,
            tenant_id=row.tenant_id,
            asset_id=row.asset_id,
            version_number=row.version_number,
            lifecycle=KnowledgeLifecycle(row.lifecycle),
            content=_content_from_row(row),
            checksum=row.checksum,
            author_user_id=row.author_user_id,
            previous_version_id=row.previous_version_id,
            effective_from=row.effective_from,
            effective_to=row.effective_to,
            lock_version=row.lock_version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_asset(
        self,
        *,
        user: User,
        request: KnowledgeAssetCreateV2,
    ) -> tuple[EnterpriseKnowledgeAssetV2, EnterpriseKnowledgeVersionV2]:
        self._require(user, KnowledgePermission.CREATE)
        await self._require_user_in_tenant(
            tenant_id=user.tenant_id,
            user_id=request.owner_user_id,
        )
        existing = await self.repository.get_asset_by_key(
            tenant_id=user.tenant_id,
            asset_type=request.asset_type.value,
            canonical_key=request.canonical_key,
        )
        if existing is not None:
            raise KnowledgeConflictError(
                "Já existe um asset com esta chave canônica e tipo neste tenant."
            )
        now = utc_now()
        asset = await self.repository.create_asset(
            EnterpriseKnowledgeAsset(
                tenant_id=user.tenant_id,
                canonical_key=request.canonical_key,
                asset_type=request.asset_type.value,
                domain=request.domain,
                owner_user_id=request.owner_user_id,
                steward_label=request.steward_label,
                accountable_area=request.accountable_area,
                status="ACTIVE",
                lock_version=0,
                schema_version=CONTRACT_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        content_json = request.content.model_dump(mode="json", exclude_none=True)
        version = await self.repository.create_version(
            EnterpriseKnowledgeVersion(
                tenant_id=user.tenant_id,
                asset_id=asset.id,
                version_number=1,
                lifecycle="DRAFT",
                content=content_json,
                checksum=compute_checksum(content_json),
                author_user_id=user.id,
                source_kind="MANUAL",
                source_metadata={},
                effective_from=request.effective_from,
                effective_to=request.effective_to,
                lock_version=0,
                schema_version=CONTRACT_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.ASSET_CREATED,
            reason_code="MANUAL_CREATE",
            asset_id=asset.id,
            version_id=version.id,
            metadata={"version": 1, "asset_type": request.asset_type.value},
        )
        return self.asset_contract(asset), self.version_contract(version)

    async def create_draft(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        from_version_id: uuid.UUID | None = None,
        source_kind: str = "REVISION",
    ) -> EnterpriseKnowledgeVersionV2:
        self._require(user, KnowledgePermission.EDIT)
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        source_id = from_version_id or asset.current_published_version_id
        if source_id is None:
            raise KnowledgeLifecycleError("O asset não possui versão base para uma nova revisão.")
        source = await self._version(
            user=user,
            asset_id=asset.id,
            version_id=source_id,
        )
        number = await self.repository.next_version_number(
            tenant_id=user.tenant_id,
            asset_id=asset.id,
        )
        now = utc_now()
        row = await self.repository.create_version(
            EnterpriseKnowledgeVersion(
                tenant_id=user.tenant_id,
                asset_id=asset.id,
                version_number=number,
                lifecycle="DRAFT",
                content=dict(source.content),
                checksum=source.checksum,
                author_user_id=user.id,
                previous_version_id=source.id,
                source_kind=source_kind,
                source_metadata={"source_version": source.version_number},
                effective_from=source.effective_from,
                effective_to=source.effective_to,
                lock_version=0,
                schema_version=CONTRACT_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        await self._event(
            user=user,
            event_type=(
                KnowledgeAuditEventType.ROLLBACK_CREATED
                if source_kind == "ROLLBACK"
                else KnowledgeAuditEventType.DRAFT_CREATED
            ),
            reason_code=source_kind,
            asset_id=asset.id,
            version_id=row.id,
            metadata={"version": number, "source_version": source.version_number},
        )
        return self.version_contract(row)

    async def update_draft(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        request: KnowledgeVersionUpdateV2,
    ) -> EnterpriseKnowledgeVersionV2:
        self._require(user, KnowledgePermission.EDIT)
        asset = await self._asset(user=user, asset_id=asset_id)
        current = await self._version(user=user, asset_id=asset_id, version_id=version_id)
        if current.lifecycle != "DRAFT":
            raise KnowledgeLifecycleError("Somente versões DRAFT podem ser editadas.")
        if current.author_user_id != user.id and asset.owner_user_id != user.id and user.role != UserRole.ADMIN:
            raise KnowledgeAccessDeniedError("Somente autor, owner ou ADMIN pode editar este draft.")
        if request.content.kind.value != asset.asset_type:
            raise KnowledgeValidationError("O tipo do conteúdo não corresponde ao asset.")
        content_json = request.content.model_dump(mode="json", exclude_none=True)
        changed = await self.repository.update_draft_cas(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            version_id=version_id,
            expected_lock_version=request.expected_lock_version,
            content=content_json,
            checksum=compute_checksum(content_json),
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            updated_at=utc_now(),
        )
        if not changed:
            await self._event(
                user=user,
                event_type=KnowledgeAuditEventType.VERSION_CONFLICT,
                reason_code="STALE_LOCK_VERSION",
                asset_id=asset_id,
                version_id=version_id,
                metadata={"expected_lock_version": request.expected_lock_version},
            )
            raise KnowledgeConflictError(
                "O draft foi alterado por outra sessão. Recarregue antes de salvar."
            )
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.DRAFT_UPDATED,
            reason_code="CAS_UPDATE",
            asset_id=asset_id,
            version_id=version_id,
            metadata={"previous_lock_version": request.expected_lock_version},
        )
        refreshed = await self._version(user=user, asset_id=asset_id, version_id=version_id)
        return self.version_contract(refreshed)

    async def submit_review(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        expected_lock_version: int,
    ) -> EnterpriseKnowledgeVersionV2:
        self._require(user, KnowledgePermission.SUBMIT)
        row = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            for_update=True,
        )
        if row.lifecycle != "DRAFT":
            raise KnowledgeLifecycleError("Somente DRAFT pode ser submetido para revisão.")
        if row.lock_version != expected_lock_version:
            raise KnowledgeConflictError("A versão informada está desatualizada.")
        row.lifecycle = "IN_REVIEW"
        row.lock_version += 1
        row.submitted_at = utc_now()
        row.updated_at = row.submitted_at
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.REVIEW_SUBMITTED,
            reason_code="AUTHOR_SUBMISSION",
            asset_id=asset_id,
            version_id=version_id,
            metadata={"checksum": row.checksum},
        )
        return self.version_contract(row)

    async def review(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        decision: KnowledgeApprovalDecision,
        comment: str,
        expected_lock_version: int,
    ) -> tuple[EnterpriseKnowledgeVersionV2, KnowledgeApprovalV2]:
        permission = (
            KnowledgePermission.APPROVE
            if decision == KnowledgeApprovalDecision.APPROVED
            else KnowledgePermission.REJECT
        )
        self._require(user, permission)
        if not comment.strip():
            raise KnowledgeValidationError("O comentário da revisão é obrigatório.")
        row = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            for_update=True,
        )
        if row.lifecycle != "IN_REVIEW":
            raise KnowledgeLifecycleError("A versão não está aguardando revisão.")
        if row.lock_version != expected_lock_version:
            raise KnowledgeConflictError("A aprovação foi baseada em uma versão desatualizada.")
        if row.author_user_id == user.id:
            await self._event(
                user=user,
                event_type=KnowledgeAuditEventType.ACCESS_DENIED,
                reason_code="SELF_APPROVAL_BLOCKED",
                asset_id=asset_id,
                version_id=version_id,
            )
            raise KnowledgeAccessDeniedError("O autor não pode aprovar ou rejeitar a própria versão.")
        now = utc_now()
        approval = await self.repository.add_approval(
            EnterpriseKnowledgeApproval(
                tenant_id=user.tenant_id,
                asset_id=asset_id,
                version_id=version_id,
                reviewer_user_id=user.id,
                decision=decision.value,
                comment=comment.strip(),
                policy_version="knowledge-sod/1.0",
                version_checksum=row.checksum,
                created_at=now,
            )
        )
        row.lifecycle = decision.value
        row.lock_version += 1
        row.reviewed_at = now
        row.updated_at = now
        row.rejection_comment = comment.strip() if decision == KnowledgeApprovalDecision.REJECTED else None
        await self._event(
            user=user,
            event_type=(
                KnowledgeAuditEventType.REVIEW_APPROVED
                if decision == KnowledgeApprovalDecision.APPROVED
                else KnowledgeAuditEventType.REVIEW_REJECTED
            ),
            reason_code=f"HUMAN_{decision.value}",
            asset_id=asset_id,
            version_id=version_id,
            metadata={"checksum": row.checksum},
        )
        return (
            self.version_contract(row),
            KnowledgeApprovalV2(
                approval_id=approval.id,
                tenant_id=approval.tenant_id,
                asset_id=approval.asset_id,
                version_id=approval.version_id,
                reviewer_user_id=approval.reviewer_user_id,
                decision=KnowledgeApprovalDecision(approval.decision),
                comment=approval.comment,
                policy_version=approval.policy_version,
                version_checksum=approval.version_checksum,
                created_at=approval.created_at,
            ),
        )

    async def publish(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
        expected_lock_version: int,
        effective_at: datetime | None = None,
    ) -> tuple[EnterpriseKnowledgeVersionV2, KnowledgePublicationV2]:
        self._require(user, KnowledgePermission.PUBLISH)
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        row = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            for_update=True,
        )
        if row.lifecycle != "APPROVED":
            raise KnowledgeLifecycleError("Somente uma versão APPROVED pode ser publicada.")
        if row.lock_version != expected_lock_version:
            raise KnowledgeConflictError("A publicação foi baseada em uma versão desatualizada.")
        content = _content_from_row(row)
        if compute_checksum(row.content) != row.checksum:
            raise KnowledgeConflictError("O checksum da versão não corresponde ao conteúdo aprovado.")
        approval = await self.repository.get_approval(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            version_id=version_id,
        )
        if approval is None or approval.version_checksum != row.checksum:
            raise KnowledgeConflictError("Não existe aprovação válida para o checksum atual.")
        if approval.reviewer_user_id == row.author_user_id:
            raise KnowledgeAccessDeniedError("A publicação viola a separação autor/revisor.")
        binding = validate_metric_binding(
            asset_type=KnowledgeAssetType(asset.asset_type),
            content=content,
        )
        if binding.status.value in {"CONFLICT", "MISSING_REGISTRY_ENTRY", "BLOCKED"}:
            await self._event(
                user=user,
                event_type=KnowledgeAuditEventType.BINDING_CONFLICT,
                reason_code=binding.reason_code,
                asset_id=asset_id,
                version_id=version_id,
                metadata={"canonical_metric_id": binding.canonical_metric_id},
            )
            raise KnowledgeBindingError(
                "A publicação foi bloqueada por divergência com o MetricRegistry.",
                details={
                    "status": binding.status.value,
                    "reason": binding.reason_code,
                    "canonical_metric_id": binding.canonical_metric_id,
                },
            )
        relation_target: EnterpriseKnowledgeAsset | None = None
        if isinstance(content, SemanticRelationContentV2):
            if content.source_canonical_key != asset.canonical_key:
                raise KnowledgeValidationError(
                    "A origem da relação deve coincidir com a chave canônica do asset.",
                    details={"reason": "RELATION_SOURCE_MISMATCH"},
                )
            targets = await self.repository.find_assets_by_canonical_key(
                tenant_id=user.tenant_id,
                canonical_key=content.target_canonical_key,
            )
            if len(targets) != 1:
                raise KnowledgeValidationError(
                    "O alvo da relação não existe ou é ambíguo neste tenant.",
                    details={"reason": "RELATION_TARGET_INVALID", "candidates": len(targets)},
                )
            relation_target = targets[0]
            if relation_target.id == asset.id:
                raise KnowledgeValidationError(
                    "Uma relação não pode apontar para o próprio asset.",
                    details={"reason": "RELATION_SELF_REFERENCE"},
                )
            if relation_target.current_published_version_id is None:
                raise KnowledgeValidationError(
                    "O alvo da relação precisa possuir uma versão publicada.",
                    details={"reason": "RELATION_TARGET_NOT_PUBLISHED"},
                )
        now = utc_now()
        active_at = effective_at or row.effective_from or now
        previous_id = asset.current_published_version_id
        if previous_id is not None and previous_id != row.id:
            previous = await self._version(
                user=user,
                asset_id=asset_id,
                version_id=previous_id,
                for_update=True,
            )
            previous.lifecycle = "DEPRECATED"
            previous.deprecated_at = now
            previous.updated_at = now
            if previous.effective_to is None or previous.effective_to > active_at:
                previous.effective_to = active_at
        row.lifecycle = "PUBLISHED"
        row.lock_version += 1
        row.published_at = now
        row.updated_at = now
        asset.current_published_version_id = row.id
        asset.lock_version += 1
        asset.updated_at = now
        publication = await self.repository.add_publication(
            EnterpriseKnowledgePublication(
                tenant_id=user.tenant_id,
                asset_id=asset_id,
                version_id=row.id,
                publisher_user_id=user.id,
                effective_at=active_at,
                published_at=now,
                superseded_version_id=previous_id,
                schema_version=CONTRACT_VERSION,
            )
        )
        aliases, locale = _content_aliases(content)
        alias_values = [(_display_name(content), normalize_lexical(_display_name(content)), locale)]
        alias_values.extend((alias, normalize_lexical(alias), locale) for alias in aliases)
        deduplicated = list(
            {
                (normalized_alias, alias_locale): (alias, normalized_alias, alias_locale)
                for alias, normalized_alias, alias_locale in alias_values
            }.values()
        )
        await self.repository.replace_published_aliases(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            version_id=row.id,
            aliases=deduplicated,
        )
        if isinstance(content, SemanticRelationContentV2) and relation_target is not None:
            await self.repository.add_relation(
                EnterpriseKnowledgeRelation(
                    tenant_id=user.tenant_id,
                    source_asset_id=asset.id,
                    target_asset_id=relation_target.id,
                    source_version_id=row.id,
                    relation_type=content.relation_type.value,
                    description=content.description,
                    created_at=now,
                )
            )
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.VERSION_PUBLISHED,
            reason_code="HUMAN_PUBLICATION",
            asset_id=asset_id,
            version_id=row.id,
            metadata={
                "version": row.version_number,
                "binding_status": binding.status.value,
                "superseded": str(previous_id) if previous_id else "",
            },
        )
        self._invalidate_cache(user.tenant_id)
        return (
            self.version_contract(row),
            KnowledgePublicationV2(
                publication_id=publication.id,
                tenant_id=publication.tenant_id,
                asset_id=publication.asset_id,
                version_id=publication.version_id,
                publisher_user_id=publication.publisher_user_id,
                effective_at=publication.effective_at,
                published_at=publication.published_at,
                superseded_version_id=publication.superseded_version_id,
            ),
        )

    async def deprecate(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> EnterpriseKnowledgeVersionV2:
        self._require(user, KnowledgePermission.DEPRECATE)
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        row = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=version_id,
            for_update=True,
        )
        if row.lifecycle != "PUBLISHED" or asset.current_published_version_id != row.id:
            raise KnowledgeLifecycleError("Somente a versão publicada atual pode ser depreciada.")
        now = utc_now()
        row.lifecycle = "DEPRECATED"
        row.deprecated_at = now
        row.updated_at = now
        row.lock_version += 1
        asset.current_published_version_id = None
        asset.lock_version += 1
        asset.updated_at = now
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.VERSION_DEPRECATED,
            reason_code="GOVERNANCE_DEPRECATION",
            asset_id=asset_id,
            version_id=version_id,
        )
        self._invalidate_cache(user.tenant_id)
        return self.version_contract(row)

    async def archive(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
    ) -> EnterpriseKnowledgeAssetV2:
        self._require(user, KnowledgePermission.ARCHIVE)
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        if asset.current_published_version_id is not None:
            raise KnowledgeLifecycleError("Deprecie a versão publicada antes de arquivar o asset.")
        asset.status = "ARCHIVED"
        asset.lock_version += 1
        asset.updated_at = utc_now()
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.ASSET_ARCHIVED,
            reason_code="GOVERNANCE_ARCHIVE",
            asset_id=asset_id,
        )
        self._invalidate_cache(user.tenant_id)
        return self.asset_contract(asset)

    async def soft_delete(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
    ) -> None:
        self._require(user, KnowledgePermission.ARCHIVE)
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        history = await self.repository.list_versions(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            include_private=True,
        )
        if asset.current_published_version_id is not None or any(
            version.lifecycle in {"PUBLISHED", "DEPRECATED", "ARCHIVED"}
            for version in history
        ):
            raise KnowledgeLifecycleError(
                "Asset com histórico publicado não pode ser removido; use depreciação e arquivo."
            )
        now = utc_now()
        asset.status = "DELETED"
        asset.deleted_at = now
        asset.lock_version += 1
        asset.updated_at = now
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.ASSET_ARCHIVED,
            reason_code="SOFT_DELETE_UNPUBLISHED",
            asset_id=asset_id,
        )

    async def rollback(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        source_version_id: uuid.UUID,
    ) -> EnterpriseKnowledgeVersionV2:
        self._require(user, KnowledgePermission.ROLLBACK)
        source = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=source_version_id,
        )
        if source.lifecycle not in {"PUBLISHED", "DEPRECATED"}:
            raise KnowledgeLifecycleError("Rollback exige uma versão publicada histórica.")
        draft = await self.create_draft(
            user=user,
            asset_id=asset_id,
            from_version_id=source_version_id,
            source_kind="ROLLBACK",
        )
        self._invalidate_cache(user.tenant_id)
        return draft

    async def transfer_ownership(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        new_owner_user_id: uuid.UUID,
        expected_lock_version: int,
    ) -> EnterpriseKnowledgeAssetV2:
        self._require(user, KnowledgePermission.TRANSFER_OWNERSHIP)
        await self._require_user_in_tenant(
            tenant_id=user.tenant_id,
            user_id=new_owner_user_id,
        )
        asset = await self._asset(user=user, asset_id=asset_id, for_update=True)
        if asset.lock_version != expected_lock_version:
            raise KnowledgeConflictError("O ownership foi alterado por outra sessão.")
        previous_owner = asset.owner_user_id
        asset.owner_user_id = new_owner_user_id
        asset.lock_version += 1
        asset.updated_at = utc_now()
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.OWNERSHIP_TRANSFERRED,
            reason_code="EXPLICIT_TRANSFER",
            asset_id=asset_id,
            metadata={
                "previous_owner": str(previous_owner),
                "new_owner": str(new_owner_user_id),
            },
        )
        return self.asset_contract(asset)

    async def list_assets(
        self,
        *,
        user: User,
        limit: int,
        lifecycle: str | None = None,
        asset_type: str | None = None,
        domain: str | None = None,
    ) -> list[EnterpriseKnowledgeAssetV2]:
        self._require(user, KnowledgePermission.READ)
        published_only = user.role == UserRole.CONSULTA
        rows = await self.repository.list_assets(
            tenant_id=user.tenant_id,
            limit=limit,
            lifecycle=None if published_only else lifecycle,
            asset_type=asset_type,
            domain=domain,
            published_only=published_only,
        )
        return [self.asset_contract(asset) for asset, _ in rows]

    async def list_review_queue(
        self,
        *,
        user: User,
        limit: int,
        asset_type: str | None = None,
        domain: str | None = None,
    ) -> list[EnterpriseKnowledgeAssetV2]:
        self._require(user, KnowledgePermission.REVIEW)
        rows = await self.repository.list_assets(
            tenant_id=user.tenant_id,
            limit=limit,
            lifecycle="IN_REVIEW",
            asset_type=asset_type,
            domain=domain,
        )
        return [self.asset_contract(asset) for asset, _ in rows]

    async def list_versions(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
    ) -> list[EnterpriseKnowledgeVersionV2]:
        self._require(user, KnowledgePermission.READ)
        await self._asset(user=user, asset_id=asset_id)
        rows = await self.repository.list_versions(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
            include_private=user.role != UserRole.CONSULTA,
        )
        return [self.version_contract(row) for row in rows]

    async def get_published_asset(
        self,
        *,
        user: User,
        canonical_key: str,
        asset_types: tuple[KnowledgeAssetType, ...] = (),
        at: datetime | None = None,
    ) -> tuple[EnterpriseKnowledgeAssetV2, EnterpriseKnowledgeVersionV2]:
        self._require(user, KnowledgePermission.READ)
        rows = await self.repository.list_effective_published(
            tenant_id=user.tenant_id,
            at=at or utc_now(),
            asset_types=tuple(item.value for item in asset_types),
        )
        normalized_key = normalize_lexical(canonical_key)
        for asset, version in rows:
            if normalize_lexical(asset.canonical_key) == normalized_key:
                return self.asset_contract(asset), self.version_contract(version)
        raise KnowledgeNotFoundError("Conhecimento publicado não encontrado.")

    async def search(
        self,
        *,
        user: User,
        request: KnowledgeSearchRequestV2,
    ) -> KnowledgeSearchResultV2:
        self._require(user, KnowledgePermission.READ)
        started = time.perf_counter()
        normalized_query = normalize_lexical(request.query)
        at = request.at or utc_now()
        rows = await self.repository.list_effective_published(
            tenant_id=user.tenant_id,
            at=at,
            asset_types=tuple(item.value for item in request.asset_types),
            domains=tuple(request.domains),
        )
        aliases = await self.repository.aliases_for_versions(
            tenant_id=user.tenant_id,
            version_ids=tuple(version.id for _, version in rows),
            locale=request.locale,
        )
        candidates: list[KnowledgeResolutionCandidateV2] = []
        query_tokens = set(normalized_query.split())
        for asset, version in rows:
            content = _content_from_row(version)
            display_name = _display_name(content)
            display_normalized = normalize_lexical(display_name)
            canonical_normalized = normalize_lexical(asset.canonical_key)
            score = 0
            match_type = KnowledgeMatchType.DESCRIPTION
            matched_field = "definition"
            matched_text = str(getattr(content, "definition", display_name))
            if normalized_query == canonical_normalized:
                score, match_type, matched_field, matched_text = (
                    1000,
                    KnowledgeMatchType.CANONICAL_EXACT,
                    "canonical_key",
                    asset.canonical_key,
                )
            elif normalized_query == display_normalized:
                score, match_type, matched_field, matched_text = (
                    900,
                    KnowledgeMatchType.DISPLAY_EXACT,
                    "display_name",
                    display_name,
                )
            else:
                alias_rows = aliases.get(version.id, [])
                exact_alias = next(
                    (item for item in alias_rows if item.normalized_alias == normalized_query),
                    None,
                )
                prefix_alias = next(
                    (
                        item
                        for item in alias_rows
                        if item.normalized_alias.startswith(normalized_query)
                        or normalized_query.startswith(item.normalized_alias)
                    ),
                    None,
                )
                if exact_alias is not None:
                    score, match_type, matched_field, matched_text = (
                        950,
                        KnowledgeMatchType.ALIAS_EXACT,
                        "alias",
                        exact_alias.alias,
                    )
                elif display_normalized.startswith(normalized_query):
                    score, match_type, matched_field, matched_text = (
                        800,
                        KnowledgeMatchType.DISPLAY_PREFIX,
                        "display_name",
                        display_name,
                    )
                elif prefix_alias is not None:
                    score, match_type, matched_field, matched_text = (
                        850,
                        KnowledgeMatchType.ALIAS_PREFIX,
                        "alias",
                        prefix_alias.alias,
                    )
                else:
                    searchable = {
                        canonical_normalized,
                        display_normalized,
                        normalize_lexical(str(getattr(content, "definition", ""))),
                        *(item.normalized_alias for item in alias_rows),
                    }
                    best_overlap = max(
                        (
                            len(query_tokens & set(value.split()))
                            / max(len(query_tokens | set(value.split())), 1)
                            for value in searchable
                            if value
                        ),
                        default=0.0,
                    )
                    if best_overlap > 0:
                        score = 400 + round(best_overlap * 300)
                        match_type = KnowledgeMatchType.TOKEN_OVERLAP
                        matched_field = "tokens"
                        matched_text = display_name
            if score == 0:
                continue
            candidates.append(
                KnowledgeResolutionCandidateV2(
                    asset_id=asset.id,
                    version_id=version.id,
                    canonical_key=asset.canonical_key,
                    asset_type=KnowledgeAssetType(asset.asset_type),
                    display_name=display_name,
                    domain=asset.domain,
                    score=score,
                    match_type=match_type,
                    matched_field=matched_field,
                    matched_text=matched_text[:256],
                    checksum=version.checksum,
                    provenance=_source_references(content),
                )
            )
        candidates.sort(key=lambda item: (-item.score, item.asset_id.int))
        if request.cursor:
            cursor_score, cursor_id = decode_cursor(
                request.cursor,
                normalized_query=normalized_query,
            )
            candidates = [
                item
                for item in candidates
                if item.score < cursor_score
                or (item.score == cursor_score and item.asset_id.int > cursor_id.int)
            ]
        ambiguous = len(candidates) > 1 and candidates[0].score == candidates[1].score
        page = candidates[: request.limit]
        next_cursor = None
        if len(candidates) > request.limit and page:
            last = page[-1]
            next_cursor = encode_cursor(
                normalized_query=normalized_query,
                score=last.score,
                asset_id=last.asset_id,
            )
        duration_ms = (time.perf_counter() - started) * 1000
        result = KnowledgeSearchResultV2(
            query_normalized=normalized_query,
            candidates=page,
            next_cursor=next_cursor,
            ambiguous=ambiguous,
            duration_ms=duration_ms,
        )
        if self.counters is not None:
            self.counters.increment("searches")
            self.counters.increment("search_candidates", len(page))
            self.counters.increment("search_latency_ms_total", round(duration_ms))
            if ambiguous:
                self.counters.increment("alias_ambiguities")
        return result

    async def resolve(
        self,
        *,
        user: User,
        query: str,
        locale: str = "pt-BR",
        at: datetime | None = None,
    ) -> KnowledgeResolutionResultV2:
        normalized_query = normalize_lexical(query)
        effective_at = at.isoformat() if at is not None else "CURRENT"
        cached = self.cache.get_resolution(
            tenant_id=user.tenant_id,
            locale=locale,
            normalized_query=normalized_query,
            effective_at=effective_at,
        )
        if cached is not None:
            return cached
        search = await self.search(
            user=user,
            request=KnowledgeSearchRequestV2(
                query=query,
                locale=locale,
                at=at,
                limit=20,
            ),
        )
        selected = search.candidates[0] if search.candidates and not search.ambiguous else None
        result = KnowledgeResolutionResultV2(
            query=query,
            candidates=search.candidates,
            selected=selected,
            ambiguous=search.ambiguous,
            clarification_required=search.ambiguous,
        )
        self.cache.set_resolution(
            tenant_id=user.tenant_id,
            locale=locale,
            normalized_query=normalized_query,
            effective_at=effective_at,
            value=result,
        )
        return result

    async def diff(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
        from_version_id: uuid.UUID,
        to_version_id: uuid.UUID,
    ) -> KnowledgeDiffV2:
        self._require(user, KnowledgePermission.READ)
        before = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=from_version_id,
        )
        after = await self._version(
            user=user,
            asset_id=asset_id,
            version_id=to_version_id,
        )
        if user.role == UserRole.CONSULTA and (
            before.lifecycle not in {"PUBLISHED", "DEPRECATED"}
            or after.lifecycle not in {"PUBLISHED", "DEPRECATED"}
        ):
            raise KnowledgeNotFoundError("Versão não encontrada.")
        before_keys = set(before.content)
        after_keys = set(after.content)
        changed = sorted(
            key for key in before_keys & after_keys if before.content[key] != after.content[key]
        )
        return KnowledgeDiffV2(
            asset_id=asset_id,
            from_version=before.version_number,
            to_version=after.version_number,
            added_fields=sorted(after_keys - before_keys),
            removed_fields=sorted(before_keys - after_keys),
            changed_fields=changed,
            from_checksum=before.checksum,
            to_checksum=after.checksum,
        )

    async def import_assets(
        self,
        *,
        user: User,
        request: KnowledgeImportRequestV2,
    ) -> KnowledgeImportResultV2:
        self._require(user, KnowledgePermission.IMPORT)
        if not self.import_enabled:
            raise KnowledgeFeatureDisabledError("A importação governada está desabilitada.")
        source_checksum = compute_checksum(request.items)
        idempotency_hash = compute_checksum(request.idempotency_key)
        existing = await self.repository.get_import(
            tenant_id=user.tenant_id,
            idempotency_key_hash=idempotency_hash,
        )
        if existing is None:
            existing = await self.repository.get_import_by_checksum(
                tenant_id=user.tenant_id,
                source_checksum=source_checksum,
                dry_run=request.dry_run,
            )
        if existing is not None:
            return KnowledgeImportResultV2(
                import_id=existing.id,
                dry_run=existing.dry_run,
                source_checksum=existing.source_checksum,
                accepted=existing.accepted_count,
                rejected=existing.rejected_count,
                warnings=list(existing.warnings),
                idempotent_replay=True,
            )
        warnings: list[str] = []
        for item in request.items:
            if item.content.kind != item.asset_type:
                warnings.append(f"{item.canonical_key}: content kind mismatch")
        accepted = len(request.items) - len(warnings)
        created_ids: list[uuid.UUID] = []
        if not request.dry_run and not warnings:
            for item in request.items:
                asset, _ = await self.create_asset(
                    user=user,
                    request=KnowledgeAssetCreateV2(
                        canonical_key=item.canonical_key,
                        asset_type=item.asset_type,
                        domain=item.domain,
                        owner_user_id=item.owner_user_id,
                        accountable_area=item.domain,
                        steward_label="Imported draft",
                        content=item.content,
                        effective_from=item.effective_from,
                        effective_to=item.effective_to,
                    ),
                )
                created_ids.append(asset.asset_id)
        if request.dry_run:
            return KnowledgeImportResultV2(
                import_id=None,
                dry_run=True,
                source_checksum=source_checksum,
                accepted=accepted,
                rejected=len(warnings),
                warnings=warnings,
            )
        row = await self.repository.add_import(
            EnterpriseKnowledgeImport(
                tenant_id=user.tenant_id,
                author_user_id=user.id,
                source_format=request.source_format,
                source_checksum=source_checksum,
                idempotency_key_hash=idempotency_hash,
                dry_run=request.dry_run,
                accepted_count=accepted,
                rejected_count=len(warnings),
                warnings=warnings,
                schema_version=CONTRACT_VERSION,
            )
        )
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.IMPORT_COMPLETED,
            reason_code="GOVERNED_IMPORT",
            metadata={"accepted": accepted, "rejected": len(warnings)},
        )
        return KnowledgeImportResultV2(
            import_id=row.id,
            dry_run=request.dry_run,
            source_checksum=source_checksum,
            accepted=accepted,
            rejected=len(warnings),
            created_asset_ids=created_ids,
            warnings=warnings,
        )

    async def export_published(
        self,
        *,
        user: User,
        export_format: KnowledgeExportFormat,
    ) -> KnowledgeExportV2:
        self._require(user, KnowledgePermission.EXPORT)
        if not self.export_enabled:
            raise KnowledgeFeatureDisabledError("A exportação governada está desabilitada.")
        rows = await self.repository.list_effective_published(
            tenant_id=user.tenant_id,
            at=utc_now(),
        )
        records = [self.version_contract(version) for _, version in rows]
        csv_content = None
        if export_format == KnowledgeExportFormat.CSV:
            target = io.StringIO(newline="")
            writer = csv.writer(target)
            writer.writerow(
                ["canonical_key", "asset_type", "domain", "version", "display_name", "checksum"]
            )
            for asset, version in rows:
                writer.writerow(
                    [
                        csv_safe(asset.canonical_key),
                        asset.asset_type,
                        csv_safe(asset.domain),
                        version.version_number,
                        csv_safe(_display_name(_content_from_row(version))),
                        version.checksum,
                    ]
                )
            csv_content = target.getvalue()
        payload = [record.model_dump(mode="json") for record in records]
        checksum = compute_checksum(
            {"format": export_format.value, "records": payload, "csv": csv_content}
        )
        await self._event(
            user=user,
            event_type=KnowledgeAuditEventType.EXPORT_COMPLETED,
            reason_code="GOVERNED_EXPORT",
            metadata={"format": export_format.value, "count": len(records)},
        )
        return KnowledgeExportV2(
            tenant_id=user.tenant_id,
            export_format=export_format,
            generated_at=utc_now(),
            checksum=checksum,
            records=records,
            csv_content=csv_content,
        )

    async def audit_events(
        self,
        *,
        user: User,
        asset_id: uuid.UUID,
    ) -> list[KnowledgeAuditEventV2]:
        self._require(user, KnowledgePermission.AUDIT_READ)
        await self._asset(user=user, asset_id=asset_id)
        rows = await self.repository.list_events(
            tenant_id=user.tenant_id,
            asset_id=asset_id,
        )
        return [
            KnowledgeAuditEventV2(
                event_id=row.id,
                tenant_id=row.tenant_id,
                asset_id=row.asset_id,
                version_id=row.version_id,
                actor_user_id=row.actor_user_id,
                event_type=KnowledgeAuditEventType(row.event_type),
                reason_code=row.reason_code,
                metadata=row.event_metadata,
                created_at=row.created_at,
            )
            for row in rows
        ]
