from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from contracts.semantic_retrieval_v2 import (
    EntityResolutionDecisionType,
    EntityMentionV2,
    EntityResolutionRequestV2,
    IndexBuildRequestV2,
    IndexRollbackV2,
    SemanticDataClassification,
    SemanticDocumentType,
    SemanticEntityType,
    SemanticEvaluationCaseV2,
    SemanticRetrievalChannel,
    SemanticSearchContextV2,
    SemanticSearchRequestV2,
    SemanticSourceType,
)
from database import AsyncSessionLocal
from models.semantic_retrieval import SemanticEvaluationCase
from models.user import User
from services.semantic_retrieval.cache import SemanticRetrievalCache
from services.semantic_retrieval.clarification import SemanticClarificationService
from services.semantic_retrieval.errors import SemanticRetrievalError
from services.semantic_retrieval.evaluation import SemanticEvaluationService
from services.semantic_retrieval.indexing import SemanticIndexLifecycleService
from services.semantic_retrieval.permissions import permission_fingerprint
from services.semantic_retrieval.repository import SemanticRetrievalRepository
from services.semantic_retrieval.resolution import (
    GovernedEntityResolutionService,
    resolution_context,
)
from services.semantic_retrieval.retrieval import SemanticRetrievalService
from services.semantic_retrieval.sources import (
    SemanticSourceRecord,
    SemanticSourceSnapshot,
)
from services.semantic_retrieval.checksums import checksum_for
from testing.test_database import (
    CONSULTA_A,
    CONSULTA_B,
    TECH_ADMIN_A,
)


class GovernedTestProvider:
    def __init__(self, records: tuple[SemanticSourceRecord, ...], version: str = "1") -> None:
        self.records = records
        self.version = version

    async def load(self, *, tenant_id: uuid.UUID, at: datetime) -> SemanticSourceSnapshot:
        del at
        return SemanticSourceSnapshot(
            source_type=SemanticSourceType.ENTERPRISE_KNOWLEDGE,
            source_id="test-published-knowledge",
            source_version=self.version,
            source_checksum="1" * 64,
            tenant_scoped=True,
            records=self.records,
        )


def records() -> tuple[SemanticSourceRecord, ...]:
    common = {
        "description": "Referencia empresarial publicada para testes.",
        "domain": "sales",
        "source_type": SemanticSourceType.ENTERPRISE_KNOWLEDGE,
        "source_version": "1",
        "source_checksum": "2" * 64,
        "classification": SemanticDataClassification.TENANT_BUSINESS_METADATA,
    }
    return (
        SemanticSourceRecord(
            canonical_id="faturamento_comercial",
            document_type=SemanticDocumentType.METRIC,
            entity_type=SemanticEntityType.METRIC,
            display_label="Faturamento",
            aliases=("receita de vendas", "receita comercial"),
            source_id="knowledge-faturamento",
            **common,
        ),
        SemanticSourceRecord(
            canonical_id="branch.centro",
            document_type=SemanticDocumentType.ENTITY_TYPE,
            entity_type=SemanticEntityType.BRANCH,
            display_label="Filial Centro",
            aliases=("centro",),
            source_id="knowledge-filial-centro",
            **common,
        ),
        SemanticSourceRecord(
            canonical_id="region.centro",
            document_type=SemanticDocumentType.ENTITY_TYPE,
            entity_type=SemanticEntityType.REGION,
            display_label="Regiao Centro",
            aliases=("centro",),
            source_id="knowledge-regiao-centro",
            **common,
        ),
        SemanticSourceRecord(
            canonical_id="metric.legacy",
            document_type=SemanticDocumentType.METRIC,
            entity_type=SemanticEntityType.METRIC,
            display_label="Metrica Legada",
            aliases=("indicador antigo",),
            source_id="knowledge-metric-legacy",
            deprecated=True,
            **common,
        ),
    )


async def load_user(db, user_id: uuid.UUID) -> User:
    row = await db.scalar(select(User).where(User.id == user_id))
    assert row is not None
    return row


async def published_runtime(db):
    admin = await load_user(db, TECH_ADMIN_A)
    repository = SemanticRetrievalRepository(db)
    cache = SemanticRetrievalCache(enabled=True, ttl_seconds=60)
    lifecycle = SemanticIndexLifecycleService(
        repository,
        providers=(GovernedTestProvider(records()),),
        cache=cache,
    )
    definition = await lifecycle.create_default_definition(user=admin)
    build = await lifecycle.build(
        user=admin,
        request=IndexBuildRequestV2(
            index_id=definition.id,
            expected_definition_lock_version=definition.lock_version,
            idempotency_key="build-test-v1",
        ),
    )
    replay = await lifecycle.build(
        user=admin,
        request=IndexBuildRequestV2(
            index_id=definition.id,
            expected_definition_lock_version=definition.lock_version,
            idempotency_key="build-test-v1",
        ),
    )
    assert replay.version.version_id == build.version.version_id
    assert replay.warnings == ("IDEMPOTENT_BUILD_REPLAY",)
    publication = await lifecycle.publish(
        user=admin,
        index_id=definition.id,
        version_id=build.version.version_id,
        expected_definition_lock_version=definition.lock_version,
        reason="Publicacao de teste",
    )
    return admin, repository, cache, lifecycle, definition, build, publication


@pytest.mark.asyncio
async def test_build_publish_search_alias_ambiguity_and_clarification() -> None:
    async with AsyncSessionLocal() as db:
        admin, repository, cache, lifecycle, definition, build, publication = (
            await published_runtime(db)
        )
        del admin, lifecycle
        assert build.version.lifecycle.value == "READY"
        assert build.version.document_count == 4
        assert publication.version_id == build.version.version_id
        consulta = await load_user(db, CONSULTA_A)
        retrieval = SemanticRetrievalService(repository, cache=cache)
        permission = permission_fingerprint(consulta.role)
        alias = await retrieval.search(
            user=consulta,
            request=SemanticSearchRequestV2(
                query="receita de vendas",
                index_id=definition.id,
                context=SemanticSearchContextV2(
                    expected_entity_types=(SemanticEntityType.METRIC,),
                    permission_fingerprint=permission,
                ),
            ),
        )
        assert alias.decision.value == "RESOLVED"
        assert alias.selected is not None
        assert alias.selected.canonical_reference.canonical_id == "faturamento_comercial"
        assert alias.selected.breakdown.channels == ()

        ambiguous = await retrieval.search(
            user=consulta,
            request=SemanticSearchRequestV2(
                query="centro",
                index_id=definition.id,
                context=SemanticSearchContextV2(permission_fingerprint=permission),
            ),
        )
        assert ambiguous.decision.value == "AMBIGUOUS"
        assert len(ambiguous.candidates) == 2

        wrong_type = await retrieval.search(
            user=consulta,
            request=SemanticSearchRequestV2(
                query="faturamento",
                index_id=definition.id,
                context=SemanticSearchContextV2(
                    expected_entity_types=(SemanticEntityType.SELLER,),
                    permission_fingerprint=permission,
                ),
            ),
        )
        assert wrong_type.decision.value == "UNRESOLVED"
        assert wrong_type.candidates == ()

        deprecated = await retrieval.search(
            user=consulta,
            request=SemanticSearchRequestV2(
                query="indicador antigo",
                index_id=definition.id,
                context=SemanticSearchContextV2(
                    expected_entity_types=(SemanticEntityType.METRIC,),
                    permission_fingerprint=permission,
                ),
            ),
        )
        assert deprecated.decision.value == "UNRESOLVED"
        assert deprecated.candidates == ()

        clarification_service = SemanticClarificationService(
            repository,
            signing_secret="test-semantic-signing-secret-32-characters",
        )
        resolver = GovernedEntityResolutionService(
            retrieval, clarification=clarification_service
        )
        mention_value = EntityMentionV2(
            mention_id=uuid.uuid4(),
            text="centro",
            normalized_text="centro",
            start=0,
            end=6,
            expected_entity_type=SemanticEntityType.UNKNOWN,
            source="EXPLICIT",
            confidence=1.0,
        )
        session_id = uuid.uuid4()
        result = await resolver.resolve(
            user=consulta,
            request=EntityResolutionRequestV2(
                mentions=(mention_value,),
                index_id=definition.id,
                context=resolution_context(
                    tenant_id=consulta.tenant_id,
                    user_id=consulta.id,
                    session_id=session_id,
                    permission_fingerprint=permission,
                ),
            ),
        )
        assert result.readiness == "CLARIFICATION_REQUIRED"
        assert result.clarification is not None
        option = result.clarification.options[0]
        with pytest.raises(SemanticRetrievalError) as forged:
            await clarification_service.resolve(
                user=consulta,
                session_id=session_id,
                clarification_id=result.clarification.clarification_id,
                option_token=(
                    option.option_token[:-1]
                    + ("A" if option.option_token[-1] != "A" else "B")
                ),
            )
        assert forged.value.code == "ENTITY_CLARIFICATION_INVALID_OPTION"

        document_id = await clarification_service.resolve(
            user=consulta,
            session_id=session_id,
            clarification_id=result.clarification.clarification_id,
            option_token=option.option_token,
        )
        assert document_id in {candidate.document_id for candidate in ambiguous.candidates}
        with pytest.raises(SemanticRetrievalError) as replay:
            await clarification_service.resolve(
                user=consulta,
                session_id=session_id,
                clarification_id=result.clarification.clarification_id,
                option_token=option.option_token,
            )
        assert replay.value.code == "ENTITY_CLARIFICATION_EXPIRED"


@pytest.mark.asyncio
async def test_search_is_deterministic_restart_safe_and_tenant_isolated() -> None:
    async with AsyncSessionLocal() as db:
        _, repository, _, _, definition, _, _ = await published_runtime(db)
        consulta_a = await load_user(db, CONSULTA_A)
        consulta_b = await load_user(db, CONSULTA_B)
        request_a = SemanticSearchRequestV2(
            query="faturamento",
            index_id=definition.id,
            context=SemanticSearchContextV2(
                expected_entity_types=(SemanticEntityType.METRIC,),
                permission_fingerprint=permission_fingerprint(consulta_a.role),
            ),
        )
        first = await SemanticRetrievalService(repository).search(
            user=consulta_a, request=request_a
        )
        second = await SemanticRetrievalService(
            SemanticRetrievalRepository(db)
        ).search(user=consulta_a, request=request_a)
        assert first == second
        cross_tenant = await SemanticRetrievalService(repository).search(
            user=consulta_b,
            request=request_a.model_copy(
                update={
                    "context": request_a.context.model_copy(
                        update={
                            "permission_fingerprint": permission_fingerprint(
                                consulta_b.role
                            )
                        }
                    )
                }
            ),
        )
        assert cross_tenant.decision.value == "NOT_FOUND"
        assert cross_tenant.candidates == ()


@pytest.mark.asyncio
async def test_publication_cas_and_rollback_preserve_history() -> None:
    async with AsyncSessionLocal() as db:
        admin, repository, cache, lifecycle, definition, build_v1, _ = (
            await published_runtime(db)
        )
        refreshed = await repository.get_definition(
            tenant_id=admin.tenant_id, index_id=definition.id
        )
        assert refreshed is not None
        lifecycle_v2 = SemanticIndexLifecycleService(
            repository,
            providers=(GovernedTestProvider(records(), version="2"),),
            cache=cache,
        )
        stale_sources = await lifecycle_v2.inspect_stale_sources(
            user=admin,
            index_id=definition.id,
        )
        assert len(stale_sources) == 1
        assert stale_sources[0].stale is True
        still_active = await repository.get_active_version(
            tenant_id=admin.tenant_id,
            index_id=definition.id,
        )
        assert still_active is not None
        assert still_active[1].id == build_v1.version.version_id

        build_v2 = await lifecycle_v2.build(
            user=admin,
            request=IndexBuildRequestV2(
                index_id=definition.id,
                expected_definition_lock_version=refreshed.lock_version,
                idempotency_key="build-test-v2",
            ),
        )
        publication_v2 = await lifecycle_v2.publish(
            user=admin,
            index_id=definition.id,
            version_id=build_v2.version.version_id,
            expected_definition_lock_version=refreshed.lock_version,
            reason="Segunda publicacao",
        )
        after_v2 = await repository.get_definition(
            tenant_id=admin.tenant_id, index_id=definition.id
        )
        assert after_v2 is not None
        rollback = await lifecycle_v2.rollback(
            user=admin,
            request=IndexRollbackV2(
                index_id=definition.id,
                target_version_id=build_v1.version.version_id,
                expected_definition_lock_version=after_v2.lock_version,
                reason="Rollback de teste",
            ),
        )
        assert rollback.previous_version_id == publication_v2.version_id
        active = await repository.get_active_version(
            tenant_id=admin.tenant_id, index_id=definition.id
        )
        assert active is not None
        assert active[1].id == build_v1.version.version_id

        with pytest.raises(SemanticRetrievalError) as conflict:
            await lifecycle_v2.publish(
                user=admin,
                index_id=definition.id,
                version_id=build_v2.version.version_id,
                expected_definition_lock_version=0,
                reason="Publicacao concorrente obsoleta",
            )
        assert conflict.value.code in {
            "SEMANTIC_INDEX_NOT_READY",
            "SEMANTIC_INDEX_VERSION_CONFLICT",
        }


@pytest.mark.asyncio
async def test_forged_clarification_and_resolution_scope_are_rejected() -> None:
    async with AsyncSessionLocal() as db:
        _, repository, _, _, definition, _, _ = await published_runtime(db)
        consulta = await load_user(db, CONSULTA_A)
        other = await load_user(db, CONSULTA_B)
        resolver = GovernedEntityResolutionService(SemanticRetrievalService(repository))
        with pytest.raises(SemanticRetrievalError) as denied:
            await resolver.resolve(
                user=other,
                request=EntityResolutionRequestV2(
                    mentions=(),
                    index_id=definition.id,
                    context=resolution_context(
                        tenant_id=consulta.tenant_id,
                        user_id=consulta.id,
                        permission_fingerprint=permission_fingerprint(consulta.role),
                    ),
                ),
            )
        assert denied.value.code == "ENTITY_RESOLUTION_FORBIDDEN"


@pytest.mark.asyncio
async def test_offline_evaluation_validates_decisions_channels_and_repeatability() -> None:
    async with AsyncSessionLocal() as db:
        admin, repository, cache, _, definition, build, _ = await published_runtime(db)
        corpus_version = "semantic-synthetic-v1"
        cases = (
            SemanticEvaluationCaseV2(
                case_id="alias.faturamento",
                tenant_id=admin.tenant_id,
                normalized_query="receita de vendas",
                expected_decision=EntityResolutionDecisionType.RESOLVED,
                expected_canonical_ids=("faturamento_comercial",),
                expected_entity_types=(SemanticEntityType.METRIC,),
                required_channels=(SemanticRetrievalChannel.EXACT_ALIAS,),
                corpus_version=corpus_version,
            ),
            SemanticEvaluationCaseV2(
                case_id="unresolved.synthetic",
                tenant_id=admin.tenant_id,
                normalized_query="termo inexistente xyz",
                expected_decision=EntityResolutionDecisionType.UNRESOLVED,
                expected_canonical_ids=(),
                expected_entity_types=(SemanticEntityType.METRIC,),
                corpus_version=corpus_version,
            ),
        )
        for case in cases:
            await repository.add_evaluation_case(
                tenant_id=admin.tenant_id,
                row=SemanticEvaluationCase(
                    tenant_id=admin.tenant_id,
                    corpus_version=corpus_version,
                    case_key=case.case_id,
                    case_data=case.model_dump(mode="json"),
                    checksum=checksum_for(case.model_dump(mode="json")),
                ),
            )

        result = await SemanticEvaluationService(
            repository,
            SemanticRetrievalService(repository, cache=cache),
        ).run(
            user=admin,
            index_id=definition.id,
            corpus_version=corpus_version,
        )

        assert result.index_version_id == build.version.version_id
        assert result.case_count == 2
        assert result.passed is True
        metrics = {item.name: item.value for item in result.metrics}
        assert metrics["TOP_1_ACCURACY"] == 1.0
        assert metrics["TOP_K_RECALL"] == 1.0
        assert metrics["ALIAS_RESOLUTION"] == 1.0
        assert metrics["FORBIDDEN_LEAKAGE"] == 0.0
        assert metrics["CROSS_TENANT_LEAKAGE"] == 0.0
        assert metrics["DETERMINISTIC_REPEATABILITY"] == 1.0
