from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from contracts.enterprise_knowledge_v2 import (
    BusinessTermContentV2,
    KnowledgeApprovalDecision,
    KnowledgeAssetCreateV2,
    KnowledgeAssetType,
    KnowledgeExportFormat,
    KnowledgeImportItemV2,
    KnowledgeImportRequestV2,
    KnowledgeLifecycle,
    KnowledgeRelationType,
    KnowledgeSearchRequestV2,
    KnowledgeVersionUpdateV2,
    MetricKnowledgeContentV2,
    SemanticRelationContentV2,
)
from database import AsyncSessionLocal
from models.enterprise_knowledge import (
    EnterpriseKnowledgeAsset,
    EnterpriseKnowledgeEvent,
    EnterpriseKnowledgeImport,
    EnterpriseKnowledgeRelation,
    EnterpriseKnowledgeVersion,
)
from models.user import User
from services.enterprise_knowledge.errors import (
    KnowledgeAccessDeniedError,
    KnowledgeBindingError,
    KnowledgeConflictError,
    KnowledgeLifecycleError,
    KnowledgeNotFoundError,
)
from services.enterprise_knowledge.metric_binding import official_formula_fingerprint
from services.enterprise_knowledge.cache import EnterpriseKnowledgeCache
from services.enterprise_knowledge.service import EnterpriseKnowledgeService
from services.metric_registry import METRIC_DEFINITIONS
from testing.test_database import (
    ADMIN_A,
    ADMIN_B,
    CONSULTA_A,
    GESTOR_A,
    TECH_ADMIN_A,
)


def term_content(
    *,
    key: str = "faturamento",
    display: str = "Faturamento",
    aliases: list[str] | None = None,
    definition: str = "Receita comercial reconhecida.",
) -> BusinessTermContentV2:
    return BusinessTermContentV2(
        kind=KnowledgeAssetType.BUSINESS_TERM,
        canonical_name=key,
        display_name=display,
        definition=definition,
        domain="Vendas",
        short_description=definition[:500],
        full_description=definition,
        aliases=aliases or [],
    )


async def user(db, user_id: uuid.UUID) -> User:
    row = await db.scalar(select(User).where(User.id == user_id))
    assert row is not None
    return row


async def create_term(
    service: EnterpriseKnowledgeService,
    *,
    author: User,
    key: str = "faturamento",
    display: str = "Faturamento",
    aliases: list[str] | None = None,
    effective_from: datetime | None = None,
) -> tuple:
    return await service.create_asset(
        user=author,
        request=KnowledgeAssetCreateV2(
            canonical_key=key,
            asset_type=KnowledgeAssetType.BUSINESS_TERM,
            domain="Vendas",
            owner_user_id=author.id,
            accountable_area="Comercial",
            steward_label="Gestão comercial",
            content=term_content(key=key, display=display, aliases=aliases),
            effective_from=effective_from,
        ),
    )


async def publish_term(
    service: EnterpriseKnowledgeService,
    *,
    author: User,
    reviewer: User,
    publisher: User,
    key: str,
    display: str,
    aliases: list[str],
    effective_from: datetime | None = None,
) -> tuple:
    asset, draft = await create_term(
        service,
        author=author,
        key=key,
        display=display,
        aliases=aliases,
        effective_from=effective_from,
    )
    submitted = await service.submit_review(
        user=author,
        asset_id=asset.asset_id,
        version_id=draft.version_id,
        expected_lock_version=draft.lock_version,
    )
    approved, _ = await service.review(
        user=reviewer,
        asset_id=asset.asset_id,
        version_id=draft.version_id,
        decision=KnowledgeApprovalDecision.APPROVED,
        comment="Definição conferida com a política comercial.",
        expected_lock_version=submitted.lock_version,
    )
    published, publication = await service.publish(
        user=publisher,
        asset_id=asset.asset_id,
        version_id=draft.version_id,
        expected_lock_version=approved.lock_version,
    )
    return asset, published, publication


@pytest.mark.asyncio
async def test_full_workflow_self_approval_and_published_search() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        consulta = await user(db, CONSULTA_A)
        service = EnterpriseKnowledgeService(db)

        asset, draft = await create_term(
            service,
            author=author,
            aliases=["receita de vendas", "vendas líquidas"],
        )
        assert draft.lifecycle is KnowledgeLifecycle.DRAFT
        before_publish = await service.search(
            user=consulta,
            request=KnowledgeSearchRequestV2(query="receita de vendas"),
        )
        assert before_publish.candidates == []

        submitted = await service.submit_review(
            user=author,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=0,
        )
        with pytest.raises(KnowledgeAccessDeniedError):
            await service.review(
                user=author,
                asset_id=asset.asset_id,
                version_id=draft.version_id,
                decision=KnowledgeApprovalDecision.APPROVED,
                comment="Tentativa indevida.",
                expected_lock_version=submitted.lock_version,
            )
        reviewed, approval = await service.review(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            decision=KnowledgeApprovalDecision.APPROVED,
            comment="Aprovado por revisor distinto.",
            expected_lock_version=submitted.lock_version,
        )
        assert approval.reviewer_user_id != reviewed.author_user_id
        published, _ = await service.publish(
            user=publisher,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=reviewed.lock_version,
        )
        await db.flush()
        assert published.lifecycle is KnowledgeLifecycle.PUBLISHED

        result = await service.search(
            user=consulta,
            request=KnowledgeSearchRequestV2(query="receita de vendas"),
        )
        assert len(result.candidates) == 1
        assert result.candidates[0].canonical_key == "faturamento"
        assert result.candidates[0].match_type.value == "ALIAS_EXACT"


@pytest.mark.asyncio
async def test_consulta_cannot_write_or_read_draft_and_cross_tenant_is_hidden() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        consulta = await user(db, CONSULTA_A)
        tenant_b_admin = await user(db, ADMIN_B)
        service = EnterpriseKnowledgeService(db)
        asset, _ = await create_term(service, author=author)

        with pytest.raises(KnowledgeAccessDeniedError):
            await create_term(service, author=consulta, key="desconto")
        with pytest.raises(KnowledgeNotFoundError):
            await service._asset(user=tenant_b_admin, asset_id=asset.asset_id)
        assert await service.list_versions(user=consulta, asset_id=asset.asset_id) == []


@pytest.mark.asyncio
async def test_optimistic_concurrency_prevents_lost_update() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        service = EnterpriseKnowledgeService(db)
        asset, draft = await create_term(service, author=author)
        update = KnowledgeVersionUpdateV2(
            content=term_content(definition="Definição revisada."),
            expected_lock_version=draft.lock_version,
        )
        saved = await service.update_draft(
            user=author,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            request=update,
        )
        assert saved.lock_version == 1
        with pytest.raises(KnowledgeConflictError):
            await service.update_draft(
                user=author,
                asset_id=asset.asset_id,
                version_id=draft.version_id,
                request=update,
            )


@pytest.mark.asyncio
async def test_alias_ambiguity_is_preserved() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        consulta = await user(db, CONSULTA_A)
        service = EnterpriseKnowledgeService(db)
        await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="receita_comercial",
            display="Receita comercial",
            aliases=["receita"],
        )
        await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="receita_contabil",
            display="Receita contábil",
            aliases=["receita"],
        )
        result = await service.resolve(user=consulta, query="receita")
        assert result.ambiguous is True
        assert result.clarification_required is True
        assert result.selected is None
        assert len(result.candidates) == 2


@pytest.mark.asyncio
async def test_versioning_and_rollback_create_v3_without_mutating_v1() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        service = EnterpriseKnowledgeService(db)
        asset, v1, _ = await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="ticket_medio",
            display="Ticket médio",
            aliases=["valor médio por pedido"],
        )
        v2_draft = await service.create_draft(user=author, asset_id=asset.asset_id)
        v2_saved = await service.update_draft(
            user=author,
            asset_id=asset.asset_id,
            version_id=v2_draft.version_id,
            request=KnowledgeVersionUpdateV2(
                content=term_content(
                    key="ticket_medio",
                    display="Ticket médio",
                    definition="Valor médio dos pedidos comerciais.",
                ),
                expected_lock_version=v2_draft.lock_version,
            ),
        )
        v2_submitted = await service.submit_review(
            user=author,
            asset_id=asset.asset_id,
            version_id=v2_saved.version_id,
            expected_lock_version=v2_saved.lock_version,
        )
        v2_approved, _ = await service.review(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=v2_saved.version_id,
            decision=KnowledgeApprovalDecision.APPROVED,
            comment="Segunda versão aprovada.",
            expected_lock_version=v2_submitted.lock_version,
        )
        v2, _ = await service.publish(
            user=publisher,
            asset_id=asset.asset_id,
            version_id=v2_saved.version_id,
            expected_lock_version=v2_approved.lock_version,
        )
        rollback = await service.rollback(
            user=publisher,
            asset_id=asset.asset_id,
            source_version_id=v1.version_id,
        )
        assert rollback.version_number == 3
        assert rollback.checksum == v1.checksum
        assert rollback.version_id not in {v1.version_id, v2.version_id}
        history = await service.list_versions(user=publisher, asset_id=asset.asset_id)
        assert [item.version_number for item in history] == [3, 2, 1]


@pytest.mark.asyncio
async def test_future_effective_version_and_deprecation_are_not_resolved() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        consulta = await user(db, CONSULTA_A)
        cache = EnterpriseKnowledgeCache(enabled=True)
        service = EnterpriseKnowledgeService(db, cache=cache)
        future = datetime.now(timezone.utc) + timedelta(days=10)
        asset, published, _ = await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="estoque_disponivel",
            display="Estoque disponível",
            aliases=["estoque"],
            effective_from=future,
        )
        before = await service.search(
            user=consulta,
            request=KnowledgeSearchRequestV2(query="estoque", at=future - timedelta(seconds=1)),
        )
        after = await service.resolve(user=consulta, query="estoque", at=future)
        assert before.candidates == []
        assert len(after.candidates) == 1
        cached = await service.resolve(user=consulta, query="estoque", at=future)
        assert cached == after
        assert cache.snapshot()["hits"] == 1
        await service.deprecate(
            user=publisher,
            asset_id=asset.asset_id,
            version_id=published.version_id,
        )
        assert cache.snapshot()["entries"] == 0
        deprecated = await service.search(
            user=consulta,
            request=KnowledgeSearchRequestV2(query="estoque", at=future),
        )
        assert deprecated.candidates == []


@pytest.mark.asyncio
async def test_metric_formula_conflict_blocks_publication_and_is_audited() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        service = EnterpriseKnowledgeService(db)
        official = METRIC_DEFINITIONS["faturamento_comercial"]
        content = MetricKnowledgeContentV2(
            kind=KnowledgeAssetType.METRIC,
            canonical_metric_id="faturamento_comercial",
            display_name="Faturamento comercial",
            definition="Receita comercial.",
            purpose="Mensurar receita.",
            unit="BRL",
            display_format="currency",
            aggregation_semantics="SUM",
            grain=official.grain,
            frequency="DAILY",
            authoritative_source=official.source,
            formula_reference=official.key,
            formula_fingerprint="0" * 64,
        )
        asset, draft = await service.create_asset(
            user=author,
            request=KnowledgeAssetCreateV2(
                canonical_key="faturamento_comercial",
                asset_type=KnowledgeAssetType.METRIC,
                domain="Vendas",
                owner_user_id=author.id,
                accountable_area="Comercial",
                steward_label="Controladoria",
                content=content,
            ),
        )
        submitted = await service.submit_review(
            user=author,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=0,
        )
        approved, _ = await service.review(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            decision=KnowledgeApprovalDecision.APPROVED,
            comment="Sem alteração do cálculo.",
            expected_lock_version=submitted.lock_version,
        )
        with pytest.raises(KnowledgeBindingError):
            await service.publish(
                user=publisher,
                asset_id=asset.asset_id,
                version_id=draft.version_id,
                expected_lock_version=approved.lock_version,
            )
        assert METRIC_DEFINITIONS["faturamento_comercial"].formula == official.formula
        event_count = await db.scalar(
            select(func.count()).select_from(EnterpriseKnowledgeEvent).where(
                EnterpriseKnowledgeEvent.event_type == "BINDING_CONFLICT"
            )
        )
        assert event_count == 1


@pytest.mark.asyncio
async def test_import_dry_run_has_zero_writes_and_export_is_published_only() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        service = EnterpriseKnowledgeService(db, import_enabled=True, export_enabled=True)
        request = KnowledgeImportRequestV2(
            source_format="JSON",
            items=[
                KnowledgeImportItemV2(
                    canonical_key="desconto",
                    asset_type=KnowledgeAssetType.BUSINESS_TERM,
                    domain="Vendas",
                    owner_user_id=author.id,
                    content=term_content(key="desconto", display="Desconto"),
                )
            ],
            dry_run=True,
            idempotency_key="import-test-001",
        )
        result = await service.import_assets(user=publisher, request=request)
        assert result.import_id is None
        assert await db.scalar(select(func.count()).select_from(EnterpriseKnowledgeImport)) == 0
        assert await db.scalar(select(func.count()).select_from(EnterpriseKnowledgeAsset)) == 0

        await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="faturamento",
            display="=Faturamento",
            aliases=["receita"],
        )
        exported = await service.export_published(
            user=publisher,
            export_format=KnowledgeExportFormat.CSV,
        )
        assert len(exported.records) == 1
        assert "'=Faturamento" in (exported.csv_content or "")
        assert await db.scalar(select(func.count()).select_from(EnterpriseKnowledgeImport)) == 0


@pytest.mark.asyncio
async def test_soft_delete_is_limited_to_never_published_assets() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        publisher = await user(db, TECH_ADMIN_A)
        reviewer = await user(db, ADMIN_A)
        service = EnterpriseKnowledgeService(db)
        draft_asset, _ = await create_term(service, author=author, key="desconto")
        await service.soft_delete(user=publisher, asset_id=draft_asset.asset_id)
        with pytest.raises(KnowledgeNotFoundError):
            await service._asset(user=publisher, asset_id=draft_asset.asset_id)

        published_asset, _, _ = await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="faturamento",
            display="Faturamento",
            aliases=["receita"],
        )
        with pytest.raises(KnowledgeLifecycleError, match="histórico publicado"):
            await service.soft_delete(user=publisher, asset_id=published_asset.asset_id)


@pytest.mark.asyncio
async def test_semantic_relation_is_materialized_only_at_publication() -> None:
    async with AsyncSessionLocal() as db:
        author = await user(db, GESTOR_A)
        reviewer = await user(db, ADMIN_A)
        publisher = await user(db, TECH_ADMIN_A)
        service = EnterpriseKnowledgeService(db)
        await publish_term(
            service,
            author=author,
            reviewer=reviewer,
            publisher=publisher,
            key="faturamento",
            display="Faturamento",
            aliases=["receita"],
        )
        content = SemanticRelationContentV2(
            kind=KnowledgeAssetType.SEMANTIC_RELATION,
            display_name="Receita relacionada a faturamento",
            source_canonical_key="receita_faturamento",
            target_canonical_key="faturamento",
            relation_type=KnowledgeRelationType.RELATED_TO,
            description="Relaciona o termo de receita ao faturamento publicado.",
        )
        asset, draft = await service.create_asset(
            user=author,
            request=KnowledgeAssetCreateV2(
                canonical_key="receita_faturamento",
                asset_type=KnowledgeAssetType.SEMANTIC_RELATION,
                domain="Vendas",
                owner_user_id=author.id,
                accountable_area="Comercial",
                steward_label="Gestão comercial",
                content=content,
            ),
        )
        assert await db.scalar(select(func.count()).select_from(EnterpriseKnowledgeRelation)) == 0
        submitted = await service.submit_review(
            user=author,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=0,
        )
        approved, _ = await service.review(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            decision=KnowledgeApprovalDecision.APPROVED,
            comment="Relação validada.",
            expected_lock_version=submitted.lock_version,
        )
        await service.publish(
            user=publisher,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=approved.lock_version,
        )
        relation = await db.scalar(select(EnterpriseKnowledgeRelation))
        assert relation is not None
        assert relation.tenant_id == author.tenant_id
        assert relation.relation_type == "RELATED_TO"
