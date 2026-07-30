from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.semantic_retrieval_v2 import (
    EntityIndexPolicyV2,
    IndexBuildRequestV2,
    IndexBuildResultV2,
    IndexPublicationV2,
    IndexRollbackV2,
    SemanticAuditEventType,
    SemanticDataClassification,
    SemanticDocumentType,
    SemanticEntityType,
    SemanticIndexLifecycle,
    SemanticIndexSourceV2,
    SemanticIndexVersionV2,
    SemanticPermission,
    SemanticRepresentationType,
    SemanticSourceManifestV2,
    SemanticSourceType,
)
from models.semantic_retrieval import (
    SemanticDocument,
    SemanticDocumentAlias,
    SemanticDocumentRelation,
    SemanticDocumentRepresentation,
    SemanticDocumentTerm,
    SemanticIndexDefinition,
    SemanticIndexEvent,
    SemanticIndexPublication,
    SemanticIndexVersion,
)
from models.user import User
from services.semantic_retrieval.cache import SemanticRetrievalCache
from services.semantic_retrieval.checksums import checksum_for, fingerprint_text
from services.semantic_retrieval.errors import semantic_error
from services.semantic_retrieval.normalization import normalize_semantic_text
from services.semantic_retrieval.observability import semantic_observability
from services.semantic_retrieval.permissions import require_permission
from services.semantic_retrieval.policies import (
    default_ranking_policy,
    default_threshold_policy,
)
from services.semantic_retrieval.privacy import inspect_semantic_content
from services.semantic_retrieval.repository import SemanticRetrievalRepository
from services.semantic_retrieval.representation import (
    DeterministicFeatureEmbeddingProvider,
)
from services.semantic_retrieval.sources import (
    SemanticIndexSourceProvider,
    SemanticSourceRecord,
    SemanticSourceSnapshot,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_entity_policies() -> tuple[EntityIndexPolicyV2, ...]:
    return tuple(
        EntityIndexPolicyV2(
            entity_type=entity_type,
            enabled=entity_type != SemanticEntityType.UNKNOWN,
            classification=SemanticDataClassification.TENANT_BUSINESS_METADATA,
            required_permission=None,
            allow_vector_representation=entity_type
            in {
                SemanticEntityType.METRIC,
                SemanticEntityType.DIMENSION,
                SemanticEntityType.BUSINESS_CONCEPT,
            },
        )
        for entity_type in SemanticEntityType
    )


def _version_contract(row: SemanticIndexVersion) -> SemanticIndexVersionV2:
    return SemanticIndexVersionV2(
        version_id=row.id,
        tenant_id=row.tenant_id,
        index_id=row.index_id,
        version=row.version,
        lifecycle=row.lifecycle,
        source_manifest=SemanticSourceManifestV2.model_validate(row.source_manifest),
        document_count=row.document_count,
        entity_count=row.entity_count,
        alias_count=row.alias_count,
        relation_count=row.relation_count,
        representation_version=row.representation_version,
        build_mode=row.build_mode,
        watermark=row.watermark,
        build_started_at=row.build_started_at,
        build_completed_at=row.build_completed_at,
        checksum=row.checksum,
        created_by=row.created_by,
        reviewed_by=row.reviewed_by,
        published_by=row.published_by,
        published_at=row.published_at,
        superseded_version_id=row.superseded_version_id,
        failure_summary=row.failure_summary,
        lock_version=row.lock_version,
    )


class SemanticIndexLifecycleService:
    def __init__(
        self,
        repository: SemanticRetrievalRepository,
        *,
        providers: tuple[SemanticIndexSourceProvider, ...],
        cache: SemanticRetrievalCache | None = None,
        representation_provider: DeterministicFeatureEmbeddingProvider | None = None,
    ) -> None:
        self.repository = repository
        self.providers = providers
        self.cache = cache
        self.representation_provider = (
            representation_provider or DeterministicFeatureEmbeddingProvider()
        )

    async def _event(
        self,
        *,
        user: User,
        event_type: SemanticAuditEventType,
        reason_code: str,
        index_id: uuid.UUID | None = None,
        version_id: uuid.UUID | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        structural = metadata or {}
        await self.repository.add_event(
            tenant_id=user.tenant_id,
            row=SemanticIndexEvent(
                tenant_id=user.tenant_id,
                index_id=index_id,
                version_id=version_id,
                actor_user_id=user.id,
                event_type=event_type.value,
                reason_code=reason_code,
                structural_fingerprint=checksum_for(structural),
                event_metadata=structural,
            ),
        )

    async def create_default_definition(
        self,
        *,
        user: User,
        name: str = "Indice semantico empresarial",
    ) -> SemanticIndexDefinition:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.MANAGE_INDEX,
        )
        existing = await self.repository.get_default_definition(
            tenant_id=user.tenant_id
        )
        if existing is not None:
            return existing
        ranking = default_ranking_policy()
        thresholds = default_threshold_policy()
        policies = _default_entity_policies()
        row = SemanticIndexDefinition(
            tenant_id=user.tenant_id,
            name=name,
            locale="pt-BR",
            document_types=[item.value for item in SemanticDocumentType],
            entity_policies=[item.model_dump(mode="json") for item in policies],
            source_policies=[
                SemanticSourceType.ENTERPRISE_KNOWLEDGE.value,
                SemanticSourceType.METRIC_REGISTRY.value,
            ],
            classification_policy=[
                SemanticDataClassification.PUBLIC_BUSINESS_METADATA.value,
                SemanticDataClassification.TENANT_BUSINESS_METADATA.value,
            ],
            representation_provider=SemanticRepresentationType.DETERMINISTIC_FEATURE_HASH.value,
            representation_version=self.representation_provider.provider_info().version,
            representation_dimension=self.representation_provider.provider_info().dimension,
            ranking_policy=ranking.model_dump(mode="json"),
            threshold_policy=thresholds.model_dump(mode="json"),
            owner_user_id=user.id,
        )
        await self.repository.create_definition(tenant_id=user.tenant_id, row=row)
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_DEFINITION_CREATED,
            reason_code="DEFAULT_DEFINITION_CREATED",
            index_id=row.id,
            metadata={"source_count": 2, "document_type_count": len(SemanticDocumentType)},
        )
        return row

    async def _load_sources(
        self,
        *,
        tenant_id: uuid.UUID,
        at: datetime,
        allowed_sources: set[str],
    ) -> tuple[SemanticSourceSnapshot, ...]:
        snapshots: list[SemanticSourceSnapshot] = []
        for provider in self.providers:
            snapshot = await provider.load(tenant_id=tenant_id, at=at)
            if snapshot.source_type.value not in allowed_sources:
                continue
            if not snapshot.tenant_scoped:
                raise semantic_error(
                    "SEMANTIC_INDEX_BUILD_FAILED",
                    "Uma fonte sem isolamento de tenant foi recusada.",
                )
            snapshots.append(snapshot)
        return tuple(sorted(snapshots, key=lambda item: (item.source_type.value, item.source_id)))

    @staticmethod
    def _deduplicate(
        snapshots: tuple[SemanticSourceSnapshot, ...],
    ) -> tuple[SemanticSourceRecord, ...]:
        priority = {
            SemanticSourceType.ENTERPRISE_KNOWLEDGE: 0,
            SemanticSourceType.METRIC_REGISTRY: 1,
            SemanticSourceType.TECHNICAL_CATALOG: 2,
            SemanticSourceType.ANALYTICAL_ENTITY: 3,
            SemanticSourceType.APPROVED_TRAINING_EXAMPLE: 4,
            SemanticSourceType.SYSTEM_CURATED: 5,
        }
        records = [
            record
            for snapshot in snapshots
            for record in snapshot.records
        ]
        records.sort(
            key=lambda item: (
                item.canonical_id,
                item.document_type.value,
                priority[item.source_type],
                item.source_id,
            )
        )
        selected: dict[tuple[str, str], SemanticSourceRecord] = {}
        for record in records:
            selected.setdefault(
                (record.canonical_id, record.document_type.value),
                record,
            )
        return tuple(selected[key] for key in sorted(selected))

    async def build(
        self,
        *,
        user: User,
        request: IndexBuildRequestV2,
    ) -> IndexBuildResultV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.BUILD_INDEX,
        )
        definition = await self.repository.get_definition(
            tenant_id=user.tenant_id,
            index_id=request.index_id,
            for_update=True,
        )
        if definition is None:
            raise semantic_error("SEMANTIC_INDEX_NOT_FOUND", "Indice semantico nao encontrado.")
        if definition.lock_version != request.expected_definition_lock_version:
            raise semantic_error(
                "SEMANTIC_INDEX_VERSION_CONFLICT",
                "A definicao do indice foi alterada por outra operacao.",
            )
        if request.build_mode == "INCREMENTAL" and definition.active_version_id is None:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "Build incremental exige uma versao publicada anterior.",
            )
        idempotency_key_hash = fingerprint_text(request.idempotency_key)
        replay = await self.repository.get_version_by_idempotency_key(
            tenant_id=user.tenant_id,
            index_id=definition.id,
            idempotency_key_hash=idempotency_key_hash,
        )
        if replay is not None:
            if replay.lifecycle in {"READY", "PUBLISHED", "DEPRECATED"}:
                return IndexBuildResultV2(
                    version=_version_contract(replay),
                    validation_passed=True,
                    blocked_document_count=0,
                    warnings=("IDEMPOTENT_BUILD_REPLAY",),
                )
            raise semantic_error(
                "SEMANTIC_INDEX_VERSION_CONFLICT",
                "Ja existe um build em andamento ou falho para esta requisicao.",
            )

        self.representation_provider.validate_configuration()
        started = utc_now()
        snapshots = await self._load_sources(
            tenant_id=user.tenant_id,
            at=started,
            allowed_sources=set(definition.source_policies),
        )
        source_contracts = tuple(
            SemanticIndexSourceV2(
                source_type=item.source_type,
                source_id=item.source_id,
                source_version=item.source_version,
                source_checksum=item.source_checksum,
                tenant_scoped=item.tenant_scoped,
                effective_at=started,
                watermark=item.watermark,
            )
            for item in snapshots
        )
        manifest_payload = [item.model_dump(mode="json") for item in source_contracts]
        manifest = SemanticSourceManifestV2(
            sources=source_contracts,
            checksum=checksum_for(manifest_payload),
        )
        version = SemanticIndexVersion(
            tenant_id=user.tenant_id,
            index_id=definition.id,
            version=await self.repository.next_version_number(
                tenant_id=user.tenant_id, index_id=definition.id
            ),
            lifecycle=SemanticIndexLifecycle.BUILDING.value,
            source_manifest=manifest.model_dump(mode="json"),
            representation_version=definition.representation_version,
            build_mode=request.build_mode,
            idempotency_key_hash=idempotency_key_hash,
            watermark=max(
                (item.watermark for item in snapshots if item.watermark),
                default=None,
            ),
            build_started_at=started,
            created_by=user.id,
        )
        await self.repository.create_version(tenant_id=user.tenant_id, row=version)
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_BUILD_STARTED,
            reason_code=f"{request.build_mode}_BUILD_STARTED",
            index_id=definition.id,
            version_id=version.id,
            metadata={"source_count": len(snapshots), "build_mode": request.build_mode},
        )

        allowed_classifications = set(definition.classification_policy)
        enabled_entity_types = {
            policy["entity_type"]
            for policy in definition.entity_policies
            if policy.get("enabled")
        }
        records = self._deduplicate(snapshots)
        documents: list[SemanticDocument] = []
        aliases: list[SemanticDocumentAlias] = []
        terms: list[SemanticDocumentTerm] = []
        representations: list[SemanticDocumentRepresentation] = []
        canonical_to_document: dict[str, uuid.UUID] = {}
        blocked = 0

        for record in records:
            if record.classification.value not in allowed_classifications:
                blocked += 1
                continue
            if record.entity_type.value not in enabled_entity_types:
                continue
            inspection = inspect_semantic_content(
                (record.display_label, record.description, *record.aliases),
                classification=record.classification,
            )
            if not inspection.allowed:
                blocked += 1
                await self._event(
                    user=user,
                    event_type=SemanticAuditEventType.FORBIDDEN_CONTENT_BLOCKED,
                    reason_code=inspection.reason_codes[0],
                    index_id=definition.id,
                    version_id=version.id,
                    metadata={"reason_count": len(inspection.reason_codes)},
                )
                continue
            normalized = normalize_semantic_text(record.display_label, locale=definition.locale)
            normalized_aliases = tuple(
                sorted(
                    {
                        normalize_semantic_text(value, locale=definition.locale).normalized
                        for value in record.aliases
                        if value.strip()
                    }
                )
            )
            document_id = uuid.uuid5(
                version.id,
                f"{record.document_type.value}:{record.canonical_id}",
            )
            canonical_to_document[record.canonical_id] = document_id
            vector = self.representation_provider.encode_document(
                normalized,
                aliases=normalized_aliases,
                domain=record.domain,
                entity_type=record.entity_type.value,
                classification=record.classification,
            )
            content = (
                {
                    "kind": "ENTITY",
                    "code": record.code,
                    "business_label": record.display_label,
                }
                if record.document_type == SemanticDocumentType.ENTITY_INSTANCE
                else {
                    "kind": "BUSINESS",
                    "definition": record.description,
                    "unit": record.unit,
                    "allowed_dimensions": list(record.allowed_dimensions),
                }
            )
            provenance = {
                "source_type": record.source_type.value,
                "source_id": record.source_id,
                "source_version": record.source_version,
                "source_checksum": record.source_checksum,
                "indexed_by": str(user.id),
                "indexed_at": started.isoformat(),
            }
            document_checksum = checksum_for(
                {
                    "canonical_id": record.canonical_id,
                    "document_type": record.document_type.value,
                    "label": record.display_label,
                    "aliases": normalized_aliases,
                    "source_checksum": record.source_checksum,
                    "representation_checksum": vector.checksum,
                }
            )
            documents.append(
                SemanticDocument(
                    id=document_id,
                    tenant_id=user.tenant_id,
                    index_id=definition.id,
                    index_version_id=version.id,
                    document_type=record.document_type.value,
                    canonical_key=record.canonical_id,
                    display_label=record.display_label,
                    normalized_label=normalized.normalized,
                    locale=definition.locale,
                    domain=record.domain,
                    entity_type=record.entity_type.value,
                    description=record.description,
                    source_type=record.source_type.value,
                    source_id=record.source_id,
                    source_version=record.source_version,
                    source_checksum=record.source_checksum,
                    lifecycle="DEPRECATED" if record.deprecated else "ACTIVE",
                    valid_from=record.valid_from,
                    valid_to=record.valid_to,
                    classification=record.classification.value,
                    permission_requirement=(
                        record.permission_requirement.value
                        if record.permission_requirement
                        else None
                    ),
                    representation_version=definition.representation_version,
                    content=content,
                    provenance=provenance,
                    checksum=document_checksum,
                )
            )
            for alias in normalized_aliases:
                aliases.append(
                    SemanticDocumentAlias(
                        id=uuid.uuid5(version.id, f"alias:{document_id}:{alias}"),
                        tenant_id=user.tenant_id,
                        index_version_id=version.id,
                        document_id=document_id,
                        alias=next(
                            (
                                raw
                                for raw in record.aliases
                                if normalize_semantic_text(
                                    raw, locale=definition.locale
                                ).normalized
                                == alias
                            ),
                            alias,
                        ),
                        normalized_alias=alias,
                        locale=definition.locale,
                        checksum=checksum_for((str(document_id), alias)),
                    )
                )
            term_values = set(normalized.significant_tokens)
            for alias in normalized_aliases:
                term_values.update(
                    normalize_semantic_text(alias, locale=definition.locale).significant_tokens
                )
            for term in sorted(term_values):
                terms.append(
                    SemanticDocumentTerm(
                        id=uuid.uuid5(version.id, f"term:{document_id}:{term}"),
                        tenant_id=user.tenant_id,
                        index_version_id=version.id,
                        document_id=document_id,
                        term=term,
                        term_kind="TOKEN",
                        weight=1.0,
                    )
                )
            representations.append(
                SemanticDocumentRepresentation(
                    id=uuid.uuid5(version.id, f"vector:{document_id}"),
                    tenant_id=user.tenant_id,
                    index_version_id=version.id,
                    document_id=document_id,
                    representation_type="DETERMINISTIC_FEATURE_HASH",
                    representation_version=definition.representation_version,
                    dimension=vector.dimension,
                    representation=vector.model_dump(mode="json"),
                    checksum=vector.checksum,
                )
            )

        relation_rows: list[SemanticDocumentRelation] = []
        for record in records:
            source_id = canonical_to_document.get(record.canonical_id)
            if source_id is None:
                continue
            for related_id in sorted(set(record.related_canonical_ids)):
                target_id = canonical_to_document.get(related_id)
                if target_id is None or target_id == source_id:
                    continue
                relation_rows.append(
                    SemanticDocumentRelation(
                        id=uuid.uuid5(
                            version.id, f"relation:{source_id}:{target_id}:RELATED_TO"
                        ),
                        tenant_id=user.tenant_id,
                        index_version_id=version.id,
                        source_document_id=source_id,
                        target_document_id=target_id,
                        relation_type="RELATED_TO",
                    )
                )

        await self.repository.add_documents(
            tenant_id=user.tenant_id, version_id=version.id, documents=documents
        )
        await self.repository.add_aliases(
            tenant_id=user.tenant_id, version_id=version.id, aliases=aliases
        )
        await self.repository.add_terms(
            tenant_id=user.tenant_id, version_id=version.id, terms=terms
        )
        await self.repository.add_representations(
            tenant_id=user.tenant_id,
            version_id=version.id,
            representations=representations,
        )
        await self.repository.add_relations(
            tenant_id=user.tenant_id,
            version_id=version.id,
            relations=relation_rows,
        )
        completed = utc_now()
        version_checksum = checksum_for(
            {
                "manifest": manifest.checksum,
                "documents": sorted(item.checksum for item in documents),
                "aliases": sorted(item.checksum for item in aliases),
                "relations": sorted(
                    f"{item.source_document_id}:{item.target_document_id}:{item.relation_type}"
                    for item in relation_rows
                ),
                "provider": self.representation_provider.deterministic_fingerprint(),
            }
        )
        updated = await self.repository.update_version_cas(
            tenant_id=user.tenant_id,
            index_id=definition.id,
            version_id=version.id,
            expected_lock_version=version.lock_version,
            expected_lifecycles=("BUILDING",),
            values={
                "lifecycle": "READY",
                "document_count": len(documents),
                "entity_count": sum(
                    item.document_type == SemanticDocumentType.ENTITY_INSTANCE.value
                    for item in documents
                ),
                "alias_count": len(aliases),
                "relation_count": len(relation_rows),
                "build_completed_at": completed,
                "checksum": version_checksum,
                "reviewed_by": user.id,
            },
        )
        if not updated:
            raise semantic_error(
                "SEMANTIC_INDEX_VERSION_CONFLICT",
                "A versao do indice foi alterada durante o build.",
            )
        version = await self.repository.get_version(
            tenant_id=user.tenant_id,
            index_id=definition.id,
            version_id=version.id,
        )
        assert version is not None
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_VERSION_READY,
            reason_code="BUILD_VALIDATED",
            index_id=definition.id,
            version_id=version.id,
            metadata={
                "document_count": len(documents),
                "alias_count": len(aliases),
                "blocked_count": blocked,
            },
        )
        semantic_observability.increment("build")
        return IndexBuildResultV2(
            version=_version_contract(version),
            validation_passed=True,
            blocked_document_count=blocked,
            warnings=(
                ("FORBIDDEN_DOCUMENTS_BLOCKED",)
                if blocked
                else ()
            ),
        )

    async def publish(
        self,
        *,
        user: User,
        index_id: uuid.UUID,
        version_id: uuid.UUID,
        expected_definition_lock_version: int,
        reason: str,
    ) -> IndexPublicationV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.PUBLISH_INDEX,
        )
        definition = await self.repository.get_definition(
            tenant_id=user.tenant_id, index_id=index_id, for_update=True
        )
        version = await self.repository.get_version(
            tenant_id=user.tenant_id,
            index_id=index_id,
            version_id=version_id,
            for_update=True,
        )
        if definition is None or version is None:
            raise semantic_error("SEMANTIC_INDEX_NOT_FOUND", "Indice ou versao nao encontrado.")
        if version.lifecycle != "READY" or not version.checksum:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY", "Somente uma versao READY pode ser publicada."
            )
        manifest = SemanticSourceManifestV2.model_validate(version.source_manifest)
        if (
            version.document_count <= 0
            or version.build_completed_at is None
            or not manifest.sources
            or any(not item.tenant_scoped for item in manifest.sources)
            or version.representation_version != definition.representation_version
            or version.reviewed_by is None
        ):
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "A versao nao passou por todas as validacoes obrigatorias.",
            )
        if definition.lock_version != expected_definition_lock_version:
            raise semantic_error(
                "SEMANTIC_INDEX_VERSION_CONFLICT", "A definicao do indice foi alterada."
            )
        previous_id = definition.active_version_id
        now = utc_now()
        version_updated = await self.repository.update_version_cas(
            tenant_id=user.tenant_id,
            index_id=index_id,
            version_id=version_id,
            expected_lock_version=version.lock_version,
            expected_lifecycles=("READY",),
            values={
                "lifecycle": "PUBLISHED",
                "published_by": user.id,
                "published_at": now,
                "superseded_version_id": previous_id,
            },
        )
        definition_updated = await self.repository.update_definition_cas(
            tenant_id=user.tenant_id,
            index_id=index_id,
            expected_lock_version=expected_definition_lock_version,
            values={"active_version_id": version_id},
        )
        if not version_updated or not definition_updated:
            raise semantic_error(
                "SEMANTIC_INDEX_VERSION_CONFLICT", "A publicacao perdeu a disputa de versao."
            )
        if previous_id and previous_id != version_id:
            previous = await self.repository.get_version(
                tenant_id=user.tenant_id,
                index_id=index_id,
                version_id=previous_id,
            )
            if previous is not None and previous.lifecycle == "PUBLISHED":
                await self.repository.update_version_cas(
                    tenant_id=user.tenant_id,
                    index_id=index_id,
                    version_id=previous.id,
                    expected_lock_version=previous.lock_version,
                    expected_lifecycles=("PUBLISHED",),
                    values={"lifecycle": "DEPRECATED"},
                )
        publication_id = uuid.uuid4()
        publication_checksum = checksum_for(
            {
                "publication_id": str(publication_id),
                "tenant_id": str(user.tenant_id),
                "index_id": str(index_id),
                "version_id": str(version_id),
                "previous_version_id": str(previous_id) if previous_id else None,
                "version_checksum": version.checksum,
                "published_by": str(user.id),
                "published_at": now,
            }
        )
        await self.repository.add_publication(
            tenant_id=user.tenant_id,
            row=SemanticIndexPublication(
                id=publication_id,
                tenant_id=user.tenant_id,
                index_id=index_id,
                version_id=version_id,
                previous_version_id=previous_id,
                published_by=user.id,
                published_at=now,
                reason=reason,
                checksum=publication_checksum,
            ),
        )
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_VERSION_PUBLISHED,
            reason_code="EXPLICIT_PUBLICATION",
            index_id=index_id,
            version_id=version_id,
            metadata={"had_previous_version": previous_id is not None},
        )
        if self.cache:
            self.cache.invalidate(tenant_id=user.tenant_id, index_id=index_id)
        semantic_observability.increment("publication")
        return IndexPublicationV2(
            publication_id=publication_id,
            tenant_id=user.tenant_id,
            index_id=index_id,
            version_id=version_id,
            previous_version_id=previous_id,
            expected_definition_lock_version=expected_definition_lock_version,
            published_by=user.id,
            published_at=now,
            checksum=publication_checksum,
        )

    async def rollback(
        self,
        *,
        user: User,
        request: IndexRollbackV2,
    ) -> IndexPublicationV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.ROLLBACK_INDEX,
        )
        target = await self.repository.get_version(
            tenant_id=user.tenant_id,
            index_id=request.index_id,
            version_id=request.target_version_id,
        )
        if target is None or target.lifecycle not in {"DEPRECATED", "PUBLISHED"}:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "Rollback exige uma versao anteriormente publicada.",
            )
        if target.lifecycle == "DEPRECATED":
            promoted = await self.repository.update_version_cas(
                tenant_id=user.tenant_id,
                index_id=request.index_id,
                version_id=target.id,
                expected_lock_version=target.lock_version,
                expected_lifecycles=("DEPRECATED",),
                values={"lifecycle": "READY"},
            )
            if not promoted:
                raise semantic_error(
                    "SEMANTIC_INDEX_VERSION_CONFLICT", "A versao alvo foi alterada."
                )
        result = await self.publish(
            user=user,
            index_id=request.index_id,
            version_id=request.target_version_id,
            expected_definition_lock_version=request.expected_definition_lock_version,
            reason=request.reason,
        )
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_VERSION_ROLLED_BACK,
            reason_code="EXPLICIT_ROLLBACK",
            index_id=request.index_id,
            version_id=request.target_version_id,
            metadata={"target_version_id": str(request.target_version_id)},
        )
        semantic_observability.increment("rollback")
        return result

    async def inspect_stale_sources(
        self,
        *,
        user: User,
        index_id: uuid.UUID,
    ) -> tuple[SemanticIndexSourceV2, ...]:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.AUDIT_READ,
        )
        active = await self.repository.get_active_version(
            tenant_id=user.tenant_id,
            index_id=index_id,
        )
        if active is None:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "A verificacao de fontes exige uma versao publicada ativa.",
            )
        definition, version = active
        checked_at = utc_now()
        current = await self._load_sources(
            tenant_id=user.tenant_id,
            at=checked_at,
            allowed_sources=set(definition.source_policies),
        )
        current_by_key = {
            (item.source_type, item.source_id): item
            for item in current
        }
        manifest = SemanticSourceManifestV2.model_validate(version.source_manifest)
        inspected = tuple(
            source.model_copy(
                update={
                    "stale": (
                        (source.source_type, source.source_id) not in current_by_key
                        or current_by_key[
                            (source.source_type, source.source_id)
                        ].source_version
                        != source.source_version
                        or current_by_key[
                            (source.source_type, source.source_id)
                        ].source_checksum
                        != source.source_checksum
                    )
                }
            )
            for source in manifest.sources
        )
        if any(item.stale for item in inspected):
            semantic_observability.increment("stale_source")
        return inspected

    async def deprecate(
        self,
        *,
        user: User,
        index_id: uuid.UUID,
        version_id: uuid.UUID,
        reason: str,
    ) -> SemanticIndexVersionV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.DEPRECATE_INDEX,
        )
        definition = await self.repository.get_definition(
            tenant_id=user.tenant_id,
            index_id=index_id,
        )
        version = await self.repository.get_version(
            tenant_id=user.tenant_id,
            index_id=index_id,
            version_id=version_id,
        )
        if definition is None or version is None:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_FOUND",
                "Indice ou versao nao encontrado.",
            )
        if definition.active_version_id == version_id:
            raise semantic_error(
                "SEMANTIC_INDEX_IMMUTABLE",
                "A versao ativa nao pode ser depreciada antes de outra publicacao.",
            )
        if version.lifecycle not in {"READY", "DEPRECATED"}:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "Somente uma versao READY pode ser depreciada.",
            )
        if version.lifecycle == "READY":
            updated = await self.repository.update_version_cas(
                tenant_id=user.tenant_id,
                index_id=index_id,
                version_id=version_id,
                expected_lock_version=version.lock_version,
                expected_lifecycles=("READY",),
                values={"lifecycle": "DEPRECATED"},
            )
            if not updated:
                raise semantic_error(
                    "SEMANTIC_INDEX_VERSION_CONFLICT",
                    "A versao foi alterada por outra operacao.",
                )
        row = await self.repository.get_version(
            tenant_id=user.tenant_id,
            index_id=index_id,
            version_id=version_id,
        )
        assert row is not None
        await self._event(
            user=user,
            event_type=SemanticAuditEventType.INDEX_VERSION_DEPRECATED,
            reason_code=reason,
            index_id=index_id,
            version_id=version_id,
        )
        return _version_contract(row)
