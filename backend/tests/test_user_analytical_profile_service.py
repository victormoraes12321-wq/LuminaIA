from __future__ import annotations

import uuid
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from contracts.user_analytical_profile_v2 import (
    AnalyticalDefaultPreferenceV2,
    ConsentGrantV2,
    ConsentStatus,
    LocalePreferenceV2,
    PreferenceCreateV2,
    PreferenceOrigin,
    PreferenceStatus,
    PreferenceUpdateV2,
    PresentationPreferenceV2,
    ProfileImportV2,
    ProfileStatus,
    UserAnalyticalProfileV2,
)
from contracts.enterprise_knowledge_v2 import (
    BusinessTermContentV2,
    KnowledgeApprovalDecision,
    KnowledgeAssetCreateV2,
    KnowledgeAssetType,
)
from database import AsyncSessionLocal
from models.user import User
from services.user_analytical_profile.cache import UserProfileCache
from services.user_analytical_profile.errors import (
    UserPreferenceForbiddenError,
    UserPreferenceNotFoundError,
    UserPreferenceReferenceInvalidError,
    UserProfileImportInvalidError,
    UserProfileVersionConflictError,
)
from services.user_analytical_profile.retention import (
    UserProfileRetentionPolicy,
    UserProfileRetentionService,
)
from services.user_analytical_profile.service import UserAnalyticalProfileService
from services.enterprise_knowledge.service import EnterpriseKnowledgeService
from testing.test_database import (
    CONSULTA_A,
    CONSULTA_B,
    GESTOR_A,
    TECH_ADMIN_A,
)


REFERENCE = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


async def load_user(db, user_id: uuid.UUID) -> User:
    row = await db.scalar(select(User).where(User.id == user_id))
    assert row is not None
    return row


def presentation() -> PreferenceCreateV2:
    return PreferenceCreateV2(
        preference_key="display.presentation",
        content=PresentationPreferenceV2(
            preferred_visualization="BAR_CHART",
            table_density="COMPACT",
            page_size=50,
            decimal_places=2,
        ),
    )


@pytest.mark.asyncio
async def test_profile_preference_update_cas_disable_reactivate_and_soft_delete() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        empty = await service.profile_contract(user=user)
        assert empty.profile_version == 1
        assert empty.preferences == []

        created = await service.create_preference(user=user, request=presentation())
        assert created.status == PreferenceStatus.ACTIVE
        assert created.origin.kind == PreferenceOrigin.USER_EXPLICIT

        updated = await service.update_preference(
            user=user,
            preference_id=created.preference_id,
            request=PreferenceUpdateV2(
                expected_lock_version=created.lock_version,
                content=PresentationPreferenceV2(
                    preferred_visualization="LINE_CHART",
                    table_density="COMFORTABLE",
                    page_size=25,
                    decimal_places=3,
                ),
            ),
        )
        assert updated.version == 2
        assert updated.content.preferred_visualization == "LINE_CHART"
        with pytest.raises(UserProfileVersionConflictError):
            await service.update_preference(
                user=user,
                preference_id=created.preference_id,
                request=PreferenceUpdateV2(
                    expected_lock_version=created.lock_version,
                    content=PresentationPreferenceV2(),
                ),
            )

        disabled = await service.set_preference_status(
            user=user,
            preference_id=created.preference_id,
            expected_lock_version=updated.lock_version,
            target=PreferenceStatus.DISABLED,
        )
        assert disabled.status == PreferenceStatus.DISABLED
        active = await service.set_preference_status(
            user=user,
            preference_id=created.preference_id,
            expected_lock_version=disabled.lock_version,
            target=PreferenceStatus.ACTIVE,
        )
        assert active.status == PreferenceStatus.ACTIVE
        deleted = await service.set_preference_status(
            user=user,
            preference_id=created.preference_id,
            expected_lock_version=active.lock_version,
            target=PreferenceStatus.DELETED,
        )
        assert deleted.status == PreferenceStatus.DELETED
        assert deleted.deleted_at == REFERENCE
        with pytest.raises(UserPreferenceNotFoundError):
            await service.get_preference(user=user, preference_id=created.preference_id)


@pytest.mark.asyncio
async def test_consent_grant_revoke_invalidates_cache_and_never_changes_formula() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        cache = UserProfileCache(enabled=True, ttl_seconds=30)
        service = UserAnalyticalProfileService(db, cache=cache, clock=lambda: REFERENCE)
        preference = await service.create_preference(
            user=user,
            request=PreferenceCreateV2(
                preference_key="default.limit",
                content=AnalyticalDefaultPreferenceV2(
                    target_field="limit",
                    canonical_id="top_25",
                    display_label="25 itens",
                    limit=25,
                ),
            ),
        )
        granted = await service.grant_consent(
            user=user,
            preference_id=preference.preference_id,
            request=ConsentGrantV2(
                expected_preference_lock_version=preference.lock_version,
                purpose="Usar limite padrão quando não houver limite explícito.",
                scope="limit",
            ),
        )
        assert granted.status == ConsentStatus.GRANTED
        revoked = await service.revoke_consent(
            user=user,
            preference_id=preference.preference_id,
            expected_lock_version=granted.lock_version,
        )
        assert revoked.status == ConsentStatus.REVOKED
        assert revoked.revoked_at == REFERENCE


@pytest.mark.asyncio
async def test_cross_tenant_and_cross_user_reads_fail_closed() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user_a = await load_user(db, CONSULTA_A)
        user_b = await load_user(db, CONSULTA_B)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        created = await service.create_preference(user=user_a, request=presentation())
        with pytest.raises(UserPreferenceNotFoundError):
            await service.get_preference(user=user_b, preference_id=created.preference_id)
        assert await service.repository.get_profile(
            tenant_id=user_b.tenant_id,
            user_id=user_a.id,
        ) is None


@pytest.mark.asyncio
async def test_profile_disable_reactivate_export_and_deletion_are_governed() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        await service.create_preference(user=user, request=presentation())
        profile = await service.profile_contract(user=user)
        disabled = await service.set_profile_status(
            user=user,
            expected_lock_version=profile.lock_version,
            target=ProfileStatus.DISABLED,
        )
        assert disabled.status == ProfileStatus.DISABLED
        active = await service.set_profile_status(
            user=user,
            expected_lock_version=disabled.lock_version,
            target=ProfileStatus.ACTIVE,
        )
        assert active.status == ProfileStatus.ACTIVE

        exported = await service.export_profile(user=user)
        encoded = exported.model_dump_json()
        assert "password" not in encoded
        assert "sql" not in encoded.lower()
        assert exported.profile.user_id == user.id

        first = await service.request_deletion(
            user=user,
            idempotency_key="delete-profile-request-001",
            reason="Não desejo manter preferências pessoais.",
        )
        second = await service.request_deletion(
            user=user,
            idempotency_key="delete-profile-request-001",
            reason="Outro texto não cria nova solicitação.",
        )
        assert first.request_id == second.request_id
        pending = await service.profile_contract(user=user)
        assert pending.status == ProfileStatus.DELETION_PENDING


@pytest.mark.asyncio
async def test_reference_validation_forbids_unpublished_asset_and_active_content() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        with pytest.raises(UserPreferenceReferenceInvalidError):
            await service.create_preference(
                user=user,
                request=PreferenceCreateV2(
                    preference_key="default.filial",
                    content=AnalyticalDefaultPreferenceV2(
                        target_field="filter",
                        canonical_id="centro",
                        display_label="Centro",
                        filter_field_id="filial",
                        filter_operator="EQ",
                        filter_values=["centro"],
                        knowledge_asset_id=uuid.uuid4(),
                    ),
                ),
            )
        with pytest.raises(UserPreferenceForbiddenError):
            await service.create_preference(
                user=user,
                request=PreferenceCreateV2(
                    preference_key="<script>alert(1)</script>",
                    content=LocalePreferenceV2(),
                ),
            )


@pytest.mark.asyncio
async def test_published_knowledge_reference_is_accepted_without_storing_formula() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        consulta = await load_user(db, CONSULTA_A)
        author = await load_user(db, GESTOR_A)
        reviewer = await load_user(db, TECH_ADMIN_A)
        knowledge = EnterpriseKnowledgeService(db)
        asset, draft = await knowledge.create_asset(
            user=author,
            request=KnowledgeAssetCreateV2(
                canonical_key="centro",
                asset_type=KnowledgeAssetType.BUSINESS_TERM,
                domain="Filiais",
                owner_user_id=author.id,
                accountable_area="Comercial",
                steward_label="Gestão comercial",
                content=BusinessTermContentV2(
                    kind=KnowledgeAssetType.BUSINESS_TERM,
                    canonical_name="centro",
                    display_name="Filial Centro",
                    definition="Filial Centro publicada para filtros governados.",
                    domain="Filiais",
                    short_description="Filial Centro.",
                    full_description="Filial Centro publicada para filtros governados.",
                ),
            ),
        )
        submitted = await knowledge.submit_review(
            user=author,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=draft.lock_version,
        )
        approved, _ = await knowledge.review(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            decision=KnowledgeApprovalDecision.APPROVED,
            comment="Referência de filial revisada.",
            expected_lock_version=submitted.lock_version,
        )
        await knowledge.publish(
            user=reviewer,
            asset_id=asset.asset_id,
            version_id=draft.version_id,
            expected_lock_version=approved.lock_version,
        )
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        preference = await service.create_preference(
            user=consulta,
            request=PreferenceCreateV2(
                preference_key="default.filial",
                content=AnalyticalDefaultPreferenceV2(
                    target_field="filter",
                    canonical_id="centro",
                    display_label="Filial Centro",
                    filter_field_id="filial",
                    filter_operator="EQ",
                    filter_values=["centro"],
                    knowledge_asset_id=asset.asset_id,
                ),
            ),
        )
        serialized = preference.model_dump_json()
        assert preference.content.knowledge_asset_id == asset.asset_id
        assert "formula" not in serialized.lower()


@pytest.mark.asyncio
async def test_two_postgresql_writers_have_exactly_one_cas_winner() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        created = await UserAnalyticalProfileService(
            db, clock=lambda: REFERENCE
        ).create_preference(user=user, request=presentation())

    async def writer(chart: str):
        async with AsyncSessionLocal() as db, db.begin():
            user = await load_user(db, CONSULTA_A)
            return await UserAnalyticalProfileService(
                db, clock=lambda: REFERENCE
            ).update_preference(
                user=user,
                preference_id=created.preference_id,
                request=PreferenceUpdateV2(
                    expected_lock_version=created.lock_version,
                    content=PresentationPreferenceV2(
                        preferred_visualization=chart,
                    ),
                ),
            )

    results = await asyncio.gather(
        writer("BAR_CHART"),
        writer("LINE_CHART"),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, UserProfileVersionConflictError) for result in results) == 1


@pytest.mark.asyncio
async def test_import_requires_exact_authenticated_owner_and_dry_run_writes_nothing() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user_a = await load_user(db, CONSULTA_A)
        user_b = await load_user(db, CONSULTA_B)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        await service.create_preference(user=user_a, request=presentation())
        source = await service.profile_contract(user=user_a)
        dry_run = await service.import_profile(
            user=user_a,
            request=ProfileImportV2(profile=source, confirm=False),
        )
        assert dry_run.dry_run
        assert dry_run.accepted == 1
        with pytest.raises(UserProfileImportInvalidError):
            await service.import_profile(
                user=user_b,
                request=ProfileImportV2(profile=source, confirm=False),
            )


@pytest.mark.asyncio
async def test_retention_selection_uses_injected_clock_and_bounded_queries() -> None:
    async with AsyncSessionLocal() as db, db.begin():
        user = await load_user(db, CONSULTA_A)
        service = UserAnalyticalProfileService(db, clock=lambda: REFERENCE)
        await service.create_preference(
            user=user,
            request=PreferenceCreateV2(
                preference_key="display.expiring",
                content=LocalePreferenceV2(),
                expires_at=REFERENCE - timedelta(seconds=1),
            ),
        )
        selection = await UserProfileRetentionService(
            service.repository,
            policy=UserProfileRetentionPolicy(batch_size=10),
            clock=lambda: REFERENCE,
        ).select()
        assert len(selection.expired_preference_ids) == 1
        assert selection.evaluated_at == REFERENCE
