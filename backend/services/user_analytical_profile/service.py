from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contracts.user_analytical_profile_v2 import (
    AnalyticalDefaultPreferenceV2,
    ConsentGrantV2,
    ConsentStatus,
    FavoriteAssetPreferenceV2,
    PreferenceAuditEventV2,
    PreferenceConsentV2,
    PreferenceCreateV2,
    PreferenceOrigin,
    PreferenceOriginV2,
    PreferenceRisk,
    PreferenceStatus,
    PreferenceUpdateV2,
    ProfileAuditEventType,
    ProfileDeletionRequestV2,
    ProfileExportV2,
    ProfileImportResultV2,
    ProfileImportV2,
    ProfilePermission,
    ProfileStatus,
    SavedReferencePreferenceV2,
    USER_ANALYTICAL_PROFILE_VERSION,
    UserAnalyticalProfileSummaryV2,
    UserAnalyticalProfileV2,
    UserPreferenceContentV2,
    UserPreferenceItemV2,
    UserPreferenceType,
)
from models.enterprise_knowledge import EnterpriseKnowledgeAsset
from models.user import User
from models.user_analytical_profile import (
    UserAnalyticalProfile,
    UserPreferenceConsent,
    UserPreferenceItem,
    UserProfileDeletionRequest,
    UserProfileEvent,
    UserProfileExport,
)

from .cache import UserProfileCache
from .errors import (
    UserPreferenceForbiddenError,
    UserPreferenceInvalidError,
    UserPreferenceNotFoundError,
    UserPreferenceReferenceInvalidError,
    UserProfileDeletionConflictError,
    UserProfileImportInvalidError,
    UserProfileNotFoundError,
    UserProfilePayloadTooLargeError,
    UserProfileVersionConflictError,
)
from .observability import UserProfileCounters
from .permissions import require_permission
from .policies import classify_preference
from .repository import UserAnalyticalProfileRepository


ContentAdapter = TypeAdapter(UserPreferenceContentV2)
ReferenceValidator = Callable[
    [User, SavedReferencePreferenceV2],
    Awaitable[bool],
]

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ACTIVE_CONTENT = re.compile(r"<\s*/?\s*(?:script|iframe|object|embed)|javascript:", re.I)
_FORBIDDEN_KEYS = {
    "password",
    "password_hash",
    "token",
    "secret",
    "api_key",
    "connection_string",
    "sql",
    "bind",
    "binds",
    "dataset",
    "conversation",
    "chain_of_thought",
    "tenant_id",
    "user_id",
    "role",
    "permission",
    "formula",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_checksum(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=True)
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _assert_safe(value: object, *, path: str = "content") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in _FORBIDDEN_KEYS:
                raise UserPreferenceForbiddenError(
                    "A preferência contém um campo que não pode ser armazenado.",
                    details={"field": str(key)},
                )
            _assert_safe(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_safe(nested, path=f"{path}[{index}]")
    elif isinstance(value, str):
        if len(value.encode("utf-8")) > 4096:
            raise UserProfilePayloadTooLargeError("Um campo da preferência excede o limite.")
        if _CONTROL.search(value) or _ACTIVE_CONTENT.search(value):
            raise UserPreferenceForbiddenError(
                "A preferência contém texto inseguro.",
                details={"field": path},
            )


def _profile_checksum(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
    profile_version: int,
) -> str:
    return canonical_checksum(
        {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "status": status,
            "profile_version": profile_version,
            "schema_version": USER_ANALYTICAL_PROFILE_VERSION,
        }
    )


def _item_checksum(
    *,
    preference_type: str,
    preference_key: str,
    content: dict[str, object],
    origin: str,
    status: str,
    version: int,
    effective_from: datetime | None,
    effective_to: datetime | None,
    expires_at: datetime | None,
) -> str:
    return canonical_checksum(
        {
            "preference_type": preference_type,
            "preference_key": preference_key,
            "content": content,
            "origin": origin,
            "status": status,
            "version": version,
            "effective_from": effective_from.isoformat() if effective_from else None,
            "effective_to": effective_to.isoformat() if effective_to else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "schema_version": USER_ANALYTICAL_PROFILE_VERSION,
        }
    )


class UserAnalyticalProfileService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        cache: UserProfileCache | None = None,
        counters: UserProfileCounters | None = None,
        clock=utc_now,
        reference_validator: ReferenceValidator | None = None,
        max_import_bytes: int = 1_000_000,
    ) -> None:
        self.db = db
        self.repository = UserAnalyticalProfileRepository(db)
        self.cache = cache or UserProfileCache(enabled=False)
        self.counters = counters
        self.clock = clock
        self.reference_validator = reference_validator
        self.max_import_bytes = max_import_bytes

    @staticmethod
    def _require(user: User, permission: ProfilePermission) -> None:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=permission,
        )

    async def _event(
        self,
        *,
        user: User,
        profile_id: uuid.UUID,
        event_type: ProfileAuditEventType,
        reason_code: str,
        preference_id: uuid.UUID | None = None,
        request_id: str | None = None,
        metadata: dict[str, str | int | bool] | None = None,
    ) -> UserProfileEvent:
        safe_metadata = metadata or {}
        if set(safe_metadata).intersection(_FORBIDDEN_KEYS):
            raise UserPreferenceForbiddenError("Metadados de auditoria não permitidos.")
        row = await self.repository.add_event(
            UserProfileEvent(
                tenant_id=user.tenant_id,
                user_id=user.id,
                profile_id=profile_id,
                preference_id=preference_id,
                actor_user_id=user.id,
                event_type=event_type.value,
                reason_code=reason_code,
                request_id=request_id,
                event_metadata=safe_metadata,
                schema_version=USER_ANALYTICAL_PROFILE_VERSION,
                created_at=self.clock(),
            )
        )
        if self.counters:
            self.counters.increment(event_type.value.lower())
        return row

    async def get_or_create_profile(self, *, user: User) -> UserAnalyticalProfile:
        self._require(user, ProfilePermission.READ_OWN)
        existing = await self.repository.get_profile(
            tenant_id=user.tenant_id,
            user_id=user.id,
        )
        if existing is not None:
            return existing
        now = self.clock()
        row = await self.repository.create_profile(
            UserAnalyticalProfile(
                tenant_id=user.tenant_id,
                user_id=user.id,
                status="ACTIVE",
                profile_version=1,
                lock_version=0,
                checksum=_profile_checksum(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    status="ACTIVE",
                    profile_version=1,
                ),
                schema_version=USER_ANALYTICAL_PROFILE_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        await self._event(
            user=user,
            profile_id=row.id,
            event_type=ProfileAuditEventType.PROFILE_CREATED,
            reason_code="EXPLICIT_PROFILE_ACCESS",
        )
        return row

    async def _profile_row(self, *, user: User) -> UserAnalyticalProfile:
        row = await self.repository.get_profile(
            tenant_id=user.tenant_id,
            user_id=user.id,
        )
        if row is None:
            raise UserProfileNotFoundError("Perfil analítico não encontrado.")
        return row

    async def _item_row(
        self,
        *,
        user: User,
        preference_id: uuid.UUID,
    ) -> UserPreferenceItem:
        row = await self.repository.get_item(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
        )
        if row is None:
            raise UserPreferenceNotFoundError("Preferência não encontrada.")
        return row

    def consent_contract(
        self, row: UserPreferenceConsent | None
    ) -> PreferenceConsentV2 | None:
        if row is None:
            return None
        return PreferenceConsentV2(
            consent_id=row.id,
            preference_id=row.preference_id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            purpose=row.purpose,
            scope=row.scope,
            status=ConsentStatus(row.status),
            granted_at=row.granted_at,
            revoked_at=row.revoked_at,
            policy_version=row.policy_version,
            source=row.source,
            lock_version=row.lock_version,
            checksum=row.checksum,
        )

    async def item_contract(self, row: UserPreferenceItem) -> UserPreferenceItemV2:
        try:
            content = ContentAdapter.validate_json(
                json.dumps(row.content, ensure_ascii=True, sort_keys=True)
            )
        except ValidationError as exc:
            raise UserPreferenceInvalidError(
                "A preferência persistida não corresponde ao contrato atual."
            ) from exc
        consent = await self.repository.get_consent(
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            preference_id=row.id,
        )
        metadata = dict(row.origin_metadata)
        return UserPreferenceItemV2(
            preference_id=row.id,
            profile_id=row.profile_id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            preference_type=UserPreferenceType(row.preference_type),
            preference_key=row.preference_key,
            content=content,
            risk=PreferenceRisk(row.risk),
            origin=PreferenceOriginV2(
                kind=PreferenceOrigin(row.origin),
                source_label=str(metadata.get("source_label") or row.origin),
                source_reference=(
                    str(metadata["source_reference"])
                    if metadata.get("source_reference")
                    else None
                ),
                confirmed_at=(
                    datetime.fromisoformat(str(metadata["confirmed_at"]))
                    if metadata.get("confirmed_at")
                    else None
                ),
            ),
            status=PreferenceStatus(row.status),
            consent=self.consent_contract(consent),
            effective_from=row.effective_from,
            effective_to=row.effective_to,
            expires_at=row.expires_at,
            version=row.version,
            lock_version=row.lock_version,
            checksum=row.checksum,
            created_at=row.created_at,
            updated_at=row.updated_at,
            deleted_at=row.deleted_at,
        )

    async def profile_contract(
        self,
        *,
        user: User,
        include_inactive: bool = True,
    ) -> UserAnalyticalProfileV2:
        self._require(user, ProfilePermission.READ_OWN)
        row = await self.get_or_create_profile(user=user)
        cached = self.cache.get(
            tenant_id=user.tenant_id,
            user_id=user.id,
            profile_version=row.profile_version,
            checksum=row.checksum,
        )
        if cached is not None and include_inactive:
            if self.counters:
                self.counters.increment("cache_hit")
            return cached
        if self.counters:
            self.counters.increment("cache_miss")
        items = await self.repository.list_items(
            tenant_id=user.tenant_id,
            user_id=user.id,
            include_inactive=include_inactive,
            limit=500,
        )
        contract = UserAnalyticalProfileV2(
            profile_id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            status=ProfileStatus(row.status),
            profile_version=row.profile_version,
            lock_version=row.lock_version,
            checksum=row.checksum,
            preferences=[await self.item_contract(item) for item in items],
            created_at=row.created_at,
            updated_at=row.updated_at,
            disabled_at=row.disabled_at,
            deleted_at=row.deleted_at,
        )
        if include_inactive:
            self.cache.put(contract)
        return contract

    async def summary(self, *, user: User) -> UserAnalyticalProfileSummaryV2:
        profile = await self.profile_contract(user=user)
        return UserAnalyticalProfileSummaryV2(
            profile_id=profile.profile_id,
            status=profile.status,
            profile_version=profile.profile_version,
            active_preferences=sum(
                item.status == PreferenceStatus.ACTIVE for item in profile.preferences
            ),
            disabled_preferences=sum(
                item.status == PreferenceStatus.DISABLED for item in profile.preferences
            ),
            pending_confirmation=sum(
                item.status == PreferenceStatus.PENDING_CONFIRMATION
                for item in profile.preferences
            ),
            active_consents=sum(
                item.consent is not None
                and item.consent.status == ConsentStatus.GRANTED
                for item in profile.preferences
            ),
            categories=sorted(
                {item.preference_type for item in profile.preferences},
                key=lambda value: value.value,
            ),
            updated_at=profile.updated_at,
        )

    async def list_preferences(
        self,
        *,
        user: User,
        include_inactive: bool,
        limit: int,
        after_id: uuid.UUID | None,
    ) -> list[UserPreferenceItemV2]:
        self._require(user, ProfilePermission.READ_OWN)
        rows = await self.repository.list_items(
            tenant_id=user.tenant_id,
            user_id=user.id,
            include_inactive=include_inactive,
            limit=limit,
            after_id=after_id,
        )
        return [await self.item_contract(row) for row in rows]

    async def get_preference(
        self, *, user: User, preference_id: uuid.UUID
    ) -> UserPreferenceItemV2:
        self._require(user, ProfilePermission.READ_OWN)
        return await self.item_contract(
            await self._item_row(user=user, preference_id=preference_id)
        )

    async def _validate_reference(self, *, user: User, content) -> None:
        if isinstance(content, (FavoriteAssetPreferenceV2, AnalyticalDefaultPreferenceV2)):
            asset_id = content.knowledge_asset_id
            if asset_id is None:
                if isinstance(content, AnalyticalDefaultPreferenceV2) and content.target_field in {
                    "ordering", "limit", "period"
                }:
                    return
                raise UserPreferenceReferenceInvalidError(
                    "A preferência analítica precisa referenciar um asset publicado."
                )
            asset = await self.db.scalar(
                select(EnterpriseKnowledgeAsset).where(
                    EnterpriseKnowledgeAsset.id == asset_id,
                    EnterpriseKnowledgeAsset.tenant_id == user.tenant_id,
                    EnterpriseKnowledgeAsset.status == "ACTIVE",
                    EnterpriseKnowledgeAsset.current_published_version_id.is_not(None),
                )
            )
            if asset is None:
                raise UserPreferenceReferenceInvalidError(
                    "A referência empresarial não está publicada ou não está disponível."
                )
            canonical_id = getattr(content, "canonical_id", None)
            if canonical_id and canonical_id != asset.canonical_key:
                raise UserPreferenceReferenceInvalidError(
                    "O identificador canônico não corresponde ao asset publicado."
                )
        if isinstance(content, SavedReferencePreferenceV2):
            if self.reference_validator is None or not await self.reference_validator(user, content):
                raise UserPreferenceReferenceInvalidError(
                    "A referência salva não pertence ao usuário e tenant autenticados."
                )

    async def _bump_profile(self, *, user: User, row: UserAnalyticalProfile) -> None:
        next_version = row.profile_version + 1
        changed = await self.repository.bump_profile_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            expected_lock_version=row.lock_version,
            status=None,
            checksum=_profile_checksum(
                tenant_id=user.tenant_id,
                user_id=user.id,
                status=row.status,
                profile_version=next_version,
            ),
            updated_at=self.clock(),
            disabled_at=row.disabled_at,
        )
        if not changed:
            raise UserProfileVersionConflictError(
                "O perfil foi alterado por outra sessão. Recarregue antes de salvar."
            )
        self.cache.invalidate(tenant_id=user.tenant_id, user_id=user.id)

    async def create_preference(
        self,
        *,
        user: User,
        request: PreferenceCreateV2,
        allow_legacy_origin: bool = False,
    ) -> UserPreferenceItemV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        if request.origin != PreferenceOrigin.USER_EXPLICIT and not (
            allow_legacy_origin and request.origin == PreferenceOrigin.LEGACY_IMPORT
        ):
            raise UserPreferenceForbiddenError(
                "A origem da preferência não pode ser definida pelo cliente."
            )
        _assert_safe(request.preference_key, path="preference_key")
        content_json = request.content.model_dump(mode="json", exclude_none=True)
        _assert_safe(content_json)
        if len(json.dumps(content_json).encode("utf-8")) > 64_000:
            raise UserProfilePayloadTooLargeError("A preferência excede o limite permitido.")
        await self._validate_reference(user=user, content=request.content)
        profile = await self.get_or_create_profile(user=user)
        pref_type = UserPreferenceType(request.content.kind)
        existing = await self.repository.get_item_by_key(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_type=pref_type.value,
            preference_key=request.preference_key,
        )
        if existing is not None:
            raise UserPreferenceInvalidError(
                "Já existe uma preferência com esta chave e categoria."
            )
        risk = classify_preference(pref_type)
        status = (
            "PENDING_CONFIRMATION"
            if request.origin == PreferenceOrigin.LEGACY_IMPORT
            and risk.value == "VISIBLE_ANALYTICAL_DEFAULT"
            else "ACTIVE"
        )
        now = self.clock()
        row = await self.repository.create_item(
            UserPreferenceItem(
                tenant_id=user.tenant_id,
                user_id=user.id,
                profile_id=profile.id,
                preference_type=pref_type.value,
                preference_key=request.preference_key,
                content=content_json,
                risk=risk.value,
                origin=request.origin.value,
                origin_metadata={
                    "source_label": (
                        "Definido pelo usuário"
                        if request.origin == PreferenceOrigin.USER_EXPLICIT
                        else "Importação legada"
                    ),
                    "confirmed_at": (
                        now.isoformat()
                        if request.origin == PreferenceOrigin.USER_EXPLICIT
                        else None
                    ),
                },
                status=status,
                created_by_user_id=user.id,
                version=1,
                lock_version=0,
                checksum=_item_checksum(
                    preference_type=pref_type.value,
                    preference_key=request.preference_key,
                    content=content_json,
                    origin=request.origin.value,
                    status=status,
                    version=1,
                    effective_from=request.effective_from,
                    effective_to=request.effective_to,
                    expires_at=request.expires_at,
                ),
                effective_from=request.effective_from,
                effective_to=request.effective_to,
                expires_at=request.expires_at,
                schema_version=USER_ANALYTICAL_PROFILE_VERSION,
                created_at=now,
                updated_at=now,
            )
        )
        await self._bump_profile(user=user, row=profile)
        await self._event(
            user=user,
            profile_id=profile.id,
            preference_id=row.id,
            event_type=ProfileAuditEventType.PREFERENCE_CREATED,
            reason_code=request.origin.value,
            metadata={"preference_type": pref_type.value, "risk": risk.value},
        )
        return await self.item_contract(row)

    async def update_preference(
        self,
        *,
        user: User,
        preference_id: uuid.UUID,
        request: PreferenceUpdateV2,
    ) -> UserPreferenceItemV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        current = await self._item_row(user=user, preference_id=preference_id)
        content_json = request.content.model_dump(mode="json", exclude_none=True)
        _assert_safe(content_json)
        if request.content.kind != current.preference_type:
            raise UserPreferenceInvalidError(
                "A categoria da preferência não pode ser alterada por atualização."
            )
        await self._validate_reference(user=user, content=request.content)
        next_version = current.version + 1
        now = self.clock()
        checksum = _item_checksum(
            preference_type=current.preference_type,
            preference_key=current.preference_key,
            content=content_json,
            origin=current.origin,
            status=current.status,
            version=next_version,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            expires_at=request.expires_at,
        )
        changed = await self.repository.update_item_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
            expected_lock_version=request.expected_lock_version,
            values={
                "content": content_json,
                "version": next_version,
                "lock_version": current.lock_version + 1,
                "checksum": checksum,
                "effective_from": request.effective_from,
                "effective_to": request.effective_to,
                "expires_at": request.expires_at,
                "updated_at": now,
            },
        )
        if not changed:
            await self._event(
                user=user,
                profile_id=current.profile_id,
                preference_id=current.id,
                event_type=ProfileAuditEventType.VERSION_CONFLICT,
                reason_code="STALE_PREFERENCE_LOCK",
            )
            raise UserProfileVersionConflictError(
                "A preferência foi alterada por outra sessão."
            )
        profile = await self._profile_row(user=user)
        await self._bump_profile(user=user, row=profile)
        await self._event(
            user=user,
            profile_id=current.profile_id,
            preference_id=current.id,
            event_type=ProfileAuditEventType.PREFERENCE_UPDATED,
            reason_code="CAS_UPDATE",
            metadata={"version": next_version},
        )
        return await self.get_preference(user=user, preference_id=preference_id)

    async def set_preference_status(
        self,
        *,
        user: User,
        preference_id: uuid.UUID,
        expected_lock_version: int,
        target: PreferenceStatus,
    ) -> UserPreferenceItemV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        current = await self._item_row(user=user, preference_id=preference_id)
        allowed = {
            PreferenceStatus.DISABLED: ProfileAuditEventType.PREFERENCE_DISABLED,
            PreferenceStatus.ACTIVE: ProfileAuditEventType.PREFERENCE_REACTIVATED,
            PreferenceStatus.REVOKED: ProfileAuditEventType.PREFERENCE_REVOKED,
            PreferenceStatus.DELETED: ProfileAuditEventType.PREFERENCE_DELETED,
            PreferenceStatus.EXPIRED: ProfileAuditEventType.PREFERENCE_EXPIRED,
        }
        if target not in allowed:
            raise UserPreferenceInvalidError("Transição de preferência inválida.")
        now = self.clock()
        next_version = current.version + 1
        checksum = _item_checksum(
            preference_type=current.preference_type,
            preference_key=current.preference_key,
            content=current.content,
            origin=current.origin,
            status=target.value,
            version=next_version,
            effective_from=current.effective_from,
            effective_to=current.effective_to,
            expires_at=current.expires_at,
        )
        changed = await self.repository.update_item_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
            expected_lock_version=expected_lock_version,
            values={
                "status": target.value,
                "version": next_version,
                "lock_version": current.lock_version + 1,
                "checksum": checksum,
                "updated_at": now,
                "deleted_at": now if target == PreferenceStatus.DELETED else None,
            },
        )
        if not changed:
            raise UserProfileVersionConflictError("Versão da preferência desatualizada.")
        profile = await self._profile_row(user=user)
        await self._bump_profile(user=user, row=profile)
        await self._event(
            user=user,
            profile_id=current.profile_id,
            preference_id=current.id,
            event_type=allowed[target],
            reason_code=f"EXPLICIT_{target.value}",
        )
        if target == PreferenceStatus.DELETED:
            current.status = target.value
            current.version = next_version
            current.lock_version = expected_lock_version + 1
            current.checksum = checksum
            current.updated_at = now
            current.deleted_at = now
            return await self.item_contract(current)
        return await self.get_preference(user=user, preference_id=preference_id)

    async def grant_consent(
        self,
        *,
        user: User,
        preference_id: uuid.UUID,
        request: ConsentGrantV2,
    ) -> PreferenceConsentV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        item = await self._item_row(user=user, preference_id=preference_id)
        if item.lock_version != request.expected_preference_lock_version:
            raise UserProfileVersionConflictError("Versão da preferência desatualizada.")
        now = self.clock()
        existing = await self.repository.get_consent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
        )
        payload = {
            "preference_id": str(preference_id),
            "tenant_id": str(user.tenant_id),
            "user_id": str(user.id),
            "purpose": request.purpose,
            "scope": request.scope,
            "status": "GRANTED",
            "granted_at": now.isoformat(),
            "policy_version": request.policy_version,
            "source": "USER_ACTION",
        }
        checksum = canonical_checksum(payload)
        if existing is None:
            row = await self.repository.create_consent(
                UserPreferenceConsent(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    profile_id=item.profile_id,
                    preference_id=item.id,
                    purpose=request.purpose,
                    scope=request.scope,
                    status="GRANTED",
                    policy_version=request.policy_version,
                    source="USER_ACTION",
                    granted_at=now,
                    revoked_at=None,
                    lock_version=0,
                    checksum=checksum,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            changed = await self.repository.update_consent_cas(
                tenant_id=user.tenant_id,
                user_id=user.id,
                preference_id=preference_id,
                expected_lock_version=existing.lock_version,
                values={
                    "purpose": request.purpose,
                    "scope": request.scope,
                    "status": "GRANTED",
                    "policy_version": request.policy_version,
                    "source": "USER_ACTION",
                    "granted_at": now,
                    "revoked_at": None,
                    "lock_version": existing.lock_version + 1,
                    "checksum": checksum,
                    "updated_at": now,
                },
            )
            if not changed:
                raise UserProfileVersionConflictError("Consentimento foi alterado.")
            row = await self.repository.get_consent(
                tenant_id=user.tenant_id,
                user_id=user.id,
                preference_id=preference_id,
            )
        self.cache.invalidate(tenant_id=user.tenant_id, user_id=user.id)
        await self._event(
            user=user,
            profile_id=item.profile_id,
            preference_id=item.id,
            event_type=ProfileAuditEventType.CONSENT_GRANTED,
            reason_code="USER_ACTION",
            metadata={"policy_version": request.policy_version},
        )
        return self.consent_contract(row)  # type: ignore[return-value]

    async def revoke_consent(
        self,
        *,
        user: User,
        preference_id: uuid.UUID,
        expected_lock_version: int,
    ) -> PreferenceConsentV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        item = await self._item_row(user=user, preference_id=preference_id)
        row = await self.repository.get_consent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
        )
        if row is None:
            raise UserPreferenceNotFoundError("Consentimento não encontrado.")
        now = self.clock()
        checksum = canonical_checksum(
            {
                "preference_id": str(preference_id),
                "tenant_id": str(user.tenant_id),
                "user_id": str(user.id),
                "status": "REVOKED",
                "granted_at": row.granted_at.isoformat() if row.granted_at else None,
                "revoked_at": now.isoformat(),
                "policy_version": row.policy_version,
            }
        )
        changed = await self.repository.update_consent_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
            expected_lock_version=expected_lock_version,
            values={
                "status": "REVOKED",
                "revoked_at": now,
                "lock_version": row.lock_version + 1,
                "checksum": checksum,
                "updated_at": now,
            },
        )
        if not changed:
            raise UserProfileVersionConflictError("Consentimento foi alterado.")
        self.cache.invalidate(tenant_id=user.tenant_id, user_id=user.id)
        await self._event(
            user=user,
            profile_id=item.profile_id,
            preference_id=item.id,
            event_type=ProfileAuditEventType.CONSENT_REVOKED,
            reason_code="USER_ACTION",
        )
        refreshed = await self.repository.get_consent(
            tenant_id=user.tenant_id,
            user_id=user.id,
            preference_id=preference_id,
        )
        return self.consent_contract(refreshed)  # type: ignore[return-value]

    async def set_profile_status(
        self,
        *,
        user: User,
        expected_lock_version: int,
        target: ProfileStatus,
    ) -> UserAnalyticalProfileV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        if target not in {ProfileStatus.ACTIVE, ProfileStatus.DISABLED}:
            raise UserPreferenceInvalidError("Transição de perfil inválida.")
        row = await self._profile_row(user=user)
        now = self.clock()
        next_version = row.profile_version + 1
        changed = await self.repository.bump_profile_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            expected_lock_version=expected_lock_version,
            status=target.value,
            checksum=_profile_checksum(
                tenant_id=user.tenant_id,
                user_id=user.id,
                status=target.value,
                profile_version=next_version,
            ),
            updated_at=now,
            disabled_at=now if target == ProfileStatus.DISABLED else None,
        )
        if not changed:
            raise UserProfileVersionConflictError("Versão do perfil desatualizada.")
        self.cache.invalidate(tenant_id=user.tenant_id, user_id=user.id)
        await self._event(
            user=user,
            profile_id=row.id,
            event_type=(
                ProfileAuditEventType.PROFILE_DISABLED
                if target == ProfileStatus.DISABLED
                else ProfileAuditEventType.PROFILE_REACTIVATED
            ),
            reason_code="USER_ACTION",
        )
        return await self.profile_contract(user=user)

    async def export_profile(self, *, user: User) -> ProfileExportV2:
        self._require(user, ProfilePermission.EXPORT_OWN)
        profile = await self.profile_contract(user=user)
        generated_at = self.clock()
        export_id = uuid.uuid4()
        body = {
            "export_id": str(export_id),
            "profile": profile.model_dump(mode="json"),
            "consent_count": sum(item.consent is not None for item in profile.preferences),
            "generated_at": generated_at.isoformat(),
            "format": "JSON",
            "schema_version": USER_ANALYTICAL_PROFILE_VERSION,
        }
        checksum = canonical_checksum(body)
        encoded = json.dumps(body, ensure_ascii=True, sort_keys=True).encode("utf-8")
        await self.repository.add_export(
            UserProfileExport(
                id=export_id,
                tenant_id=user.tenant_id,
                user_id=user.id,
                profile_id=profile.profile_id,
                format="JSON",
                checksum=checksum,
                payload_size=len(encoded),
                status="COMPLETED",
                schema_version=USER_ANALYTICAL_PROFILE_VERSION,
                created_at=generated_at,
                expires_at=generated_at + timedelta(days=30),
            )
        )
        await self._event(
            user=user,
            profile_id=profile.profile_id,
            event_type=ProfileAuditEventType.EXPORT_COMPLETED,
            reason_code="USER_REQUEST",
            metadata={"format": "JSON", "preference_count": len(profile.preferences)},
        )
        return ProfileExportV2(
            export_id=export_id,
            profile=profile,
            consent_count=body["consent_count"],
            generated_at=generated_at,
            checksum=checksum,
        )

    async def request_deletion(
        self,
        *,
        user: User,
        idempotency_key: str,
        reason: str | None,
    ) -> ProfileDeletionRequestV2:
        self._require(user, ProfilePermission.DELETE_OWN)
        if not 8 <= len(idempotency_key) <= 256 or _CONTROL.search(idempotency_key):
            raise UserProfileDeletionConflictError("Chave de idempotência inválida.")
        if reason:
            _assert_safe(reason, path="reason")
        profile = await self._profile_row(user=user)
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        existing = await self.repository.get_deletion_request(
            tenant_id=user.tenant_id,
            user_id=user.id,
            idempotency_key_hash=key_hash,
        )
        if existing is not None:
            return self.deletion_contract(existing)
        now = self.clock()
        row = await self.repository.add_deletion_request(
            UserProfileDeletionRequest(
                tenant_id=user.tenant_id,
                user_id=user.id,
                profile_id=profile.id,
                status="PENDING",
                reason=reason,
                idempotency_key_hash=key_hash,
                requested_at=now,
                schema_version=USER_ANALYTICAL_PROFILE_VERSION,
            )
        )
        changed = await self.repository.bump_profile_cas(
            tenant_id=user.tenant_id,
            user_id=user.id,
            expected_lock_version=profile.lock_version,
            status="DELETION_PENDING",
            checksum=_profile_checksum(
                tenant_id=user.tenant_id,
                user_id=user.id,
                status="DELETION_PENDING",
                profile_version=profile.profile_version + 1,
            ),
            updated_at=now,
            disabled_at=None,
        )
        if not changed:
            raise UserProfileVersionConflictError("O perfil foi alterado por outra sessão.")
        self.cache.invalidate(tenant_id=user.tenant_id, user_id=user.id)
        await self._event(
            user=user,
            profile_id=profile.id,
            event_type=ProfileAuditEventType.DELETION_REQUESTED,
            reason_code="USER_REQUEST",
        )
        return self.deletion_contract(row)

    @staticmethod
    def deletion_contract(row: UserProfileDeletionRequest) -> ProfileDeletionRequestV2:
        return ProfileDeletionRequestV2(
            request_id=row.id,
            profile_id=row.profile_id,
            status=row.status,
            requested_at=row.requested_at,
            completed_at=row.completed_at,
            reason=row.reason,
            idempotency_key_hash=row.idempotency_key_hash,
        )

    async def import_profile(
        self,
        *,
        user: User,
        request: ProfileImportV2,
    ) -> ProfileImportResultV2:
        self._require(user, ProfilePermission.UPDATE_OWN)
        raw = request.model_dump_json().encode("utf-8")
        if len(raw) > self.max_import_bytes:
            raise UserProfilePayloadTooLargeError("Importação excede o limite permitido.")
        if request.profile.tenant_id != user.tenant_id or request.profile.user_id != user.id:
            raise UserProfileImportInvalidError(
                "A importação deve pertencer ao usuário e tenant autenticados."
            )
        warnings: list[str] = []
        accepted = 0
        for item in request.profile.preferences:
            _assert_safe(item.content.model_dump(mode="json"))
            if item.origin.kind == PreferenceOrigin.INFERRED_UNCONFIRMED:
                warnings.append(f"{item.preference_key}: inferência não confirmada não será aplicada.")
            accepted += 1
        source_checksum = canonical_checksum(request.profile)
        if request.confirm:
            for item in request.profile.preferences:
                existing = await self.repository.get_item_by_key(
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    preference_type=item.preference_type.value,
                    preference_key=item.preference_key,
                )
                if existing is not None:
                    warnings.append(f"{item.preference_key}: já existe e foi ignorada.")
                    continue
                await self.create_preference(
                    user=user,
                    request=PreferenceCreateV2(
                        preference_key=item.preference_key,
                        content=item.content,
                        origin=PreferenceOrigin.LEGACY_IMPORT,
                        effective_from=item.effective_from,
                        effective_to=item.effective_to,
                        expires_at=item.expires_at,
                    ),
                    allow_legacy_origin=True,
                )
        profile = await self.get_or_create_profile(user=user)
        await self._event(
            user=user,
            profile_id=profile.id,
            event_type=(
                ProfileAuditEventType.IMPORT_COMPLETED
                if request.confirm
                else ProfileAuditEventType.IMPORT_DRY_RUN
            ),
            reason_code="OWN_PROFILE_IMPORT",
            metadata={"accepted": accepted, "warnings": len(warnings)},
        )
        return ProfileImportResultV2(
            accepted=accepted,
            rejected=0,
            warnings=warnings,
            dry_run=not request.confirm,
            source_checksum=source_checksum,
        )
