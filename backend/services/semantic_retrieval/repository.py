from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.semantic_retrieval import (
    SemanticClarification,
    SemanticDocument,
    SemanticDocumentAlias,
    SemanticDocumentRelation,
    SemanticDocumentRepresentation,
    SemanticDocumentTerm,
    SemanticEvaluationCase,
    SemanticEvaluationResult,
    SemanticIndexDefinition,
    SemanticIndexEvent,
    SemanticIndexPublication,
    SemanticIndexVersion,
)


@dataclass(frozen=True)
class SemanticStoredCandidate:
    document: SemanticDocument
    aliases: tuple[str, ...]
    representation: dict | None
    relation_count: int


class SemanticRetrievalRepository:
    """All public operations require an authenticated tenant scope."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_definition(
        self, *, tenant_id: uuid.UUID, row: SemanticIndexDefinition
    ) -> SemanticIndexDefinition:
        if row.tenant_id != tenant_id:
            raise ValueError("definition tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_definition(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        for_update: bool = False,
    ) -> SemanticIndexDefinition | None:
        stmt = select(SemanticIndexDefinition).where(
            SemanticIndexDefinition.tenant_id == tenant_id,
            SemanticIndexDefinition.id == index_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def get_default_definition(
        self, *, tenant_id: uuid.UUID, for_update: bool = False
    ) -> SemanticIndexDefinition | None:
        stmt = (
            select(SemanticIndexDefinition)
            .where(
                SemanticIndexDefinition.tenant_id == tenant_id,
                SemanticIndexDefinition.status == "ACTIVE",
            )
            .order_by(SemanticIndexDefinition.created_at, SemanticIndexDefinition.id)
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def list_definitions(
        self,
        *,
        tenant_id: uuid.UUID,
        after_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[SemanticIndexDefinition]:
        stmt = select(SemanticIndexDefinition).where(
            SemanticIndexDefinition.tenant_id == tenant_id
        )
        if after_id:
            stmt = stmt.where(SemanticIndexDefinition.id > after_id)
        stmt = stmt.order_by(SemanticIndexDefinition.id).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def update_definition_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        expected_lock_version: int,
        values: dict[str, object],
    ) -> bool:
        result = await self.db.execute(
            update(SemanticIndexDefinition)
            .where(
                SemanticIndexDefinition.tenant_id == tenant_id,
                SemanticIndexDefinition.id == index_id,
                SemanticIndexDefinition.lock_version == expected_lock_version,
            )
            .values(
                **values,
                lock_version=SemanticIndexDefinition.lock_version + 1,
                updated_at=func.now(),
            )
        )
        return result.rowcount == 1

    async def next_version_number(
        self, *, tenant_id: uuid.UUID, index_id: uuid.UUID
    ) -> int:
        value = await self.db.scalar(
            select(func.coalesce(func.max(SemanticIndexVersion.version), 0)).where(
                SemanticIndexVersion.tenant_id == tenant_id,
                SemanticIndexVersion.index_id == index_id,
            )
        )
        return int(value or 0) + 1

    async def get_version_by_idempotency_key(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        idempotency_key_hash: str,
    ) -> SemanticIndexVersion | None:
        return await self.db.scalar(
            select(SemanticIndexVersion).where(
                SemanticIndexVersion.tenant_id == tenant_id,
                SemanticIndexVersion.index_id == index_id,
                SemanticIndexVersion.idempotency_key_hash
                == idempotency_key_hash,
            )
        )

    async def create_version(
        self, *, tenant_id: uuid.UUID, row: SemanticIndexVersion
    ) -> SemanticIndexVersion:
        if row.tenant_id != tenant_id:
            raise ValueError("version tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_version(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        version_id: uuid.UUID,
        for_update: bool = False,
    ) -> SemanticIndexVersion | None:
        stmt = select(SemanticIndexVersion).where(
            SemanticIndexVersion.tenant_id == tenant_id,
            SemanticIndexVersion.index_id == index_id,
            SemanticIndexVersion.id == version_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def list_versions(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        before_version: int | None = None,
        limit: int = 50,
    ) -> list[SemanticIndexVersion]:
        stmt = select(SemanticIndexVersion).where(
            SemanticIndexVersion.tenant_id == tenant_id,
            SemanticIndexVersion.index_id == index_id,
        )
        if before_version is not None:
            stmt = stmt.where(SemanticIndexVersion.version < before_version)
        stmt = stmt.order_by(SemanticIndexVersion.version.desc()).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def update_version_cas(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        version_id: uuid.UUID,
        expected_lock_version: int,
        expected_lifecycles: tuple[str, ...],
        values: dict[str, object],
    ) -> bool:
        result = await self.db.execute(
            update(SemanticIndexVersion)
            .where(
                SemanticIndexVersion.tenant_id == tenant_id,
                SemanticIndexVersion.index_id == index_id,
                SemanticIndexVersion.id == version_id,
                SemanticIndexVersion.lock_version == expected_lock_version,
                SemanticIndexVersion.lifecycle.in_(expected_lifecycles),
            )
            .values(
                **values,
                lock_version=SemanticIndexVersion.lock_version + 1,
                updated_at=func.now(),
            )
        )
        return result.rowcount == 1

    async def add_documents(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        documents: list[SemanticDocument],
    ) -> None:
        if any(
            row.tenant_id != tenant_id or row.index_version_id != version_id
            for row in documents
        ):
            raise ValueError("document batch scope mismatch")
        self.db.add_all(documents)
        await self.db.flush()

    async def add_aliases(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        aliases: list[SemanticDocumentAlias],
    ) -> None:
        if any(
            row.tenant_id != tenant_id or row.index_version_id != version_id
            for row in aliases
        ):
            raise ValueError("alias batch scope mismatch")
        self.db.add_all(aliases)
        await self.db.flush()

    async def add_terms(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        terms: list[SemanticDocumentTerm],
    ) -> None:
        if any(
            row.tenant_id != tenant_id or row.index_version_id != version_id
            for row in terms
        ):
            raise ValueError("term batch scope mismatch")
        self.db.add_all(terms)
        await self.db.flush()

    async def add_representations(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        representations: list[SemanticDocumentRepresentation],
    ) -> None:
        if any(
            row.tenant_id != tenant_id or row.index_version_id != version_id
            for row in representations
        ):
            raise ValueError("representation batch scope mismatch")
        self.db.add_all(representations)
        await self.db.flush()

    async def add_relations(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        relations: list[SemanticDocumentRelation],
    ) -> None:
        if any(
            row.tenant_id != tenant_id or row.index_version_id != version_id
            for row in relations
        ):
            raise ValueError("relation batch scope mismatch")
        self.db.add_all(relations)
        await self.db.flush()

    async def get_active_version(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID | None = None,
    ) -> tuple[SemanticIndexDefinition, SemanticIndexVersion] | None:
        definition = (
            await self.get_definition(tenant_id=tenant_id, index_id=index_id)
            if index_id
            else await self.get_default_definition(tenant_id=tenant_id)
        )
        if definition is None or definition.active_version_id is None:
            return None
        version = await self.get_version(
            tenant_id=tenant_id,
            index_id=definition.id,
            version_id=definition.active_version_id,
        )
        if version is None or version.lifecycle != "PUBLISHED":
            return None
        return definition, version

    async def get_document(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> SemanticDocument | None:
        return await self.db.scalar(
            select(SemanticDocument).where(
                SemanticDocument.tenant_id == tenant_id,
                SemanticDocument.index_version_id == version_id,
                SemanticDocument.id == document_id,
            )
        )

    async def find_candidate_documents(
        self,
        *,
        tenant_id: uuid.UUID,
        version_id: uuid.UUID,
        normalized_query: str,
        terms: tuple[str, ...],
        now: datetime,
        limit: int,
    ) -> list[SemanticStoredCandidate]:
        active_filter = and_(
            SemanticDocument.tenant_id == tenant_id,
            SemanticDocument.index_version_id == version_id,
            SemanticDocument.lifecycle == "ACTIVE",
            or_(SemanticDocument.valid_from.is_(None), SemanticDocument.valid_from <= now),
            or_(SemanticDocument.valid_to.is_(None), SemanticDocument.valid_to > now),
        )
        exact_ids = select(SemanticDocument.id).where(
            active_filter,
            or_(
                func.lower(SemanticDocument.canonical_key) == normalized_query,
                SemanticDocument.normalized_label == normalized_query,
            ),
        )
        alias_ids = select(SemanticDocumentAlias.document_id).where(
            SemanticDocumentAlias.tenant_id == tenant_id,
            SemanticDocumentAlias.index_version_id == version_id,
            SemanticDocumentAlias.normalized_alias == normalized_query,
        )
        prefix_ids = select(SemanticDocument.id).where(
            active_filter,
            SemanticDocument.normalized_label.startswith(normalized_query),
        )
        term_ids = (
            select(SemanticDocumentTerm.document_id)
            .where(
                SemanticDocumentTerm.tenant_id == tenant_id,
                SemanticDocumentTerm.index_version_id == version_id,
                SemanticDocumentTerm.term.in_(terms or ("__none__",)),
            )
            .group_by(SemanticDocumentTerm.document_id)
            .order_by(func.count().desc(), SemanticDocumentTerm.document_id)
        )
        candidate_ids = exact_ids.union(alias_ids, prefix_ids, term_ids).limit(limit)
        rows = list(
            (
                await self.db.scalars(
                    select(SemanticDocument)
                    .where(active_filter, SemanticDocument.id.in_(candidate_ids))
                    .order_by(SemanticDocument.canonical_key, SemanticDocument.id)
                )
            ).all()
        )
        if not rows:
            # Character/vector fallback remains bounded and never scans more than limit.
            rows = list(
                (
                    await self.db.scalars(
                        select(SemanticDocument)
                        .where(active_filter)
                        .order_by(SemanticDocument.normalized_label, SemanticDocument.id)
                        .limit(limit)
                    )
                ).all()
            )
        document_ids = [row.id for row in rows]
        aliases_by_document: dict[uuid.UUID, list[str]] = {}
        if document_ids:
            alias_rows = await self.db.execute(
                select(
                    SemanticDocumentAlias.document_id,
                    SemanticDocumentAlias.normalized_alias,
                ).where(
                    SemanticDocumentAlias.tenant_id == tenant_id,
                    SemanticDocumentAlias.index_version_id == version_id,
                    SemanticDocumentAlias.document_id.in_(document_ids),
                )
            )
            for document_id, alias in alias_rows:
                aliases_by_document.setdefault(document_id, []).append(alias)
        representation_by_document: dict[uuid.UUID, dict] = {}
        if document_ids:
            representation_rows = await self.db.execute(
                select(
                    SemanticDocumentRepresentation.document_id,
                    SemanticDocumentRepresentation.representation,
                ).where(
                    SemanticDocumentRepresentation.tenant_id == tenant_id,
                    SemanticDocumentRepresentation.index_version_id == version_id,
                    SemanticDocumentRepresentation.document_id.in_(document_ids),
                    SemanticDocumentRepresentation.representation_type
                    == "DETERMINISTIC_FEATURE_HASH",
                )
            )
            representation_by_document = {
                document_id: representation
                for document_id, representation in representation_rows
            }
        relation_counts: dict[uuid.UUID, int] = {}
        if document_ids:
            relation_rows = await self.db.execute(
                select(
                    SemanticDocumentRelation.source_document_id,
                    func.count(),
                )
                .where(
                    SemanticDocumentRelation.tenant_id == tenant_id,
                    SemanticDocumentRelation.index_version_id == version_id,
                    SemanticDocumentRelation.source_document_id.in_(document_ids),
                )
                .group_by(SemanticDocumentRelation.source_document_id)
            )
            relation_counts = {
                document_id: int(count) for document_id, count in relation_rows
            }
        return [
            SemanticStoredCandidate(
                document=row,
                aliases=tuple(sorted(aliases_by_document.get(row.id, []))),
                representation=representation_by_document.get(row.id),
                relation_count=relation_counts.get(row.id, 0),
            )
            for row in rows
        ]

    async def add_publication(
        self,
        *,
        tenant_id: uuid.UUID,
        row: SemanticIndexPublication,
    ) -> SemanticIndexPublication:
        if row.tenant_id != tenant_id:
            raise ValueError("publication tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def add_event(
        self, *, tenant_id: uuid.UUID, row: SemanticIndexEvent
    ) -> SemanticIndexEvent:
        if row.tenant_id != tenant_id:
            raise ValueError("event tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_events(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID | None,
        before: datetime | None = None,
        limit: int = 100,
    ) -> list[SemanticIndexEvent]:
        stmt = select(SemanticIndexEvent).where(
            SemanticIndexEvent.tenant_id == tenant_id
        )
        if index_id:
            stmt = stmt.where(SemanticIndexEvent.index_id == index_id)
        if before:
            stmt = stmt.where(SemanticIndexEvent.created_at < before)
        stmt = stmt.order_by(
            SemanticIndexEvent.created_at.desc(), SemanticIndexEvent.id.desc()
        ).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def mark_sources_stale(
        self,
        *,
        tenant_id: uuid.UUID,
        source_type: str,
        source_id: str,
        current_source_version: str,
    ) -> int:
        """Count stale active documents without mutating a published version."""
        active_versions = select(SemanticIndexDefinition.active_version_id).where(
            SemanticIndexDefinition.tenant_id == tenant_id,
            SemanticIndexDefinition.active_version_id.is_not(None),
        )
        value = await self.db.scalar(
            select(func.count(SemanticDocument.id)).where(
                SemanticDocument.tenant_id == tenant_id,
                SemanticDocument.index_version_id.in_(active_versions),
                SemanticDocument.source_type == source_type,
                SemanticDocument.source_id == source_id,
                SemanticDocument.source_version != current_source_version,
                SemanticDocument.lifecycle == "ACTIVE",
            )
        )
        return int(value or 0)

    async def add_evaluation_case(
        self, *, tenant_id: uuid.UUID, row: SemanticEvaluationCase
    ) -> SemanticEvaluationCase:
        if row.tenant_id != tenant_id:
            raise ValueError("evaluation case tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_evaluation_cases(
        self,
        *,
        tenant_id: uuid.UUID,
        corpus_version: str,
        limit: int = 1000,
    ) -> list[SemanticEvaluationCase]:
        return list(
            (
                await self.db.scalars(
                    select(SemanticEvaluationCase)
                    .where(
                        SemanticEvaluationCase.tenant_id == tenant_id,
                        SemanticEvaluationCase.corpus_version == corpus_version,
                    )
                    .order_by(SemanticEvaluationCase.case_key)
                    .limit(limit)
                )
            ).all()
        )

    async def add_evaluation_result(
        self, *, tenant_id: uuid.UUID, row: SemanticEvaluationResult
    ) -> SemanticEvaluationResult:
        if row.tenant_id != tenant_id:
            raise ValueError("evaluation result tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_evaluation_results(
        self,
        *,
        tenant_id: uuid.UUID,
        index_id: uuid.UUID,
        before: datetime | None = None,
        limit: int = 50,
    ) -> list[SemanticEvaluationResult]:
        stmt = select(SemanticEvaluationResult).where(
            SemanticEvaluationResult.tenant_id == tenant_id,
            SemanticEvaluationResult.index_id == index_id,
        )
        if before is not None:
            stmt = stmt.where(SemanticEvaluationResult.executed_at < before)
        stmt = stmt.order_by(
            SemanticEvaluationResult.executed_at.desc(),
            SemanticEvaluationResult.id.desc(),
        ).limit(limit)
        return list((await self.db.scalars(stmt)).all())

    async def create_clarification(
        self, *, tenant_id: uuid.UUID, row: SemanticClarification
    ) -> SemanticClarification:
        if row.tenant_id != tenant_id:
            raise ValueError("clarification tenant mismatch")
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_clarification(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        clarification_id: uuid.UUID,
        for_update: bool = False,
    ) -> SemanticClarification | None:
        stmt = select(SemanticClarification).where(
            SemanticClarification.tenant_id == tenant_id,
            SemanticClarification.user_id == user_id,
            SemanticClarification.id == clarification_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

    async def resolve_clarification(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        clarification_id: uuid.UUID,
        resolved_document_id: uuid.UUID,
        now: datetime,
    ) -> bool:
        result = await self.db.execute(
            update(SemanticClarification)
            .where(
                SemanticClarification.tenant_id == tenant_id,
                SemanticClarification.user_id == user_id,
                SemanticClarification.session_id == session_id,
                SemanticClarification.id == clarification_id,
                SemanticClarification.status == "PENDING",
                SemanticClarification.expires_at > now,
            )
            .values(
                status="RESOLVED",
                resolved_document_id=resolved_document_id,
                resolved_at=now,
            )
        )
        return result.rowcount == 1
