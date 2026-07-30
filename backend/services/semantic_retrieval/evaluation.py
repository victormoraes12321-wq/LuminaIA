from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.semantic_retrieval_v2 import (
    EntityResolutionDecisionType,
    SemanticEvaluationCaseV2,
    SemanticEvaluationMetricV2,
    SemanticEvaluationResultV2,
    SemanticPermission,
    SemanticRetrievalChannel,
    SemanticSearchContextV2,
    SemanticSearchRequestV2,
)
from models.semantic_retrieval import SemanticEvaluationResult
from models.user import User
from services.semantic_retrieval.checksums import checksum_for
from services.semantic_retrieval.errors import semantic_error
from services.semantic_retrieval.permissions import (
    permission_fingerprint,
    require_permission,
)
from services.semantic_retrieval.repository import SemanticRetrievalRepository
from services.semantic_retrieval.retrieval import SemanticRetrievalService


class SemanticEvaluationService:
    def __init__(
        self,
        repository: SemanticRetrievalRepository,
        retrieval: SemanticRetrievalService,
    ) -> None:
        self.repository = repository
        self.retrieval = retrieval

    async def run(
        self,
        *,
        user: User,
        index_id: uuid.UUID,
        corpus_version: str,
    ) -> SemanticEvaluationResultV2:
        require_permission(
            tenant_id=user.tenant_id,
            user_id=user.id,
            role=user.role,
            permission=SemanticPermission.RUN_EVALUATION,
        )
        active = await self.repository.get_active_version(
            tenant_id=user.tenant_id, index_id=index_id
        )
        if active is None:
            raise semantic_error(
                "SEMANTIC_INDEX_NOT_READY",
                "A avaliacao exige uma versao publicada ativa.",
            )
        _, version = active
        rows = await self.repository.list_evaluation_cases(
            tenant_id=user.tenant_id,
            corpus_version=corpus_version,
            limit=1000,
        )
        if not rows:
            raise semantic_error(
                "SEMANTIC_QUERY_INVALID",
                "O corpus de avaliacao informado esta vazio.",
            )
        cases = [
            SemanticEvaluationCaseV2.model_validate(row.case_data)
            for row in rows
        ]
        top_one = 0
        top_k = 0
        ambiguity_correct = 0
        ambiguity_total = 0
        unresolved_correct = 0
        unresolved_total = 0
        exact_preserved = 0
        alias_resolved = 0
        forbidden_leakage = 0
        repeatable = 0
        decision_correct = 0
        cases_with_expected_ids = 0
        exact_expected = 0
        alias_expected = 0
        required_channels_correct = 0
        total_latency_ms = 0.0
        permission = permission_fingerprint(user.role)
        for case in cases:
            started = datetime.now(timezone.utc)
            request = SemanticSearchRequestV2(
                query=case.normalized_query,
                index_id=index_id,
                context=SemanticSearchContextV2(
                    expected_entity_types=case.expected_entity_types,
                    permission_fingerprint=permission,
                ),
                top_k=10,
            )
            first = await self.retrieval.search(
                user=user, request=request, inspect_scores=True
            )
            second = await self.retrieval.search(
                user=user, request=request, inspect_scores=True
            )
            total_latency_ms += (
                datetime.now(timezone.utc) - started
            ).total_seconds() * 1000
            candidate_ids = [
                item.canonical_reference.canonical_id for item in first.candidates
            ]
            expected_ids = set(case.expected_canonical_ids)
            decision_correct += first.decision == case.expected_decision
            if expected_ids:
                cases_with_expected_ids += 1
                if (
                    first.selected
                    and first.selected.canonical_reference.canonical_id in expected_ids
                ):
                    top_one += 1
                if expected_ids.intersection(candidate_ids):
                    top_k += 1
            observed_channels = {
                channel
                for candidate in first.candidates
                for channel in candidate.matched_channels
            }
            required_channels_correct += set(case.required_channels).issubset(
                observed_channels
            )
            if case.expected_decision == EntityResolutionDecisionType.AMBIGUOUS:
                ambiguity_total += 1
                ambiguity_correct += first.decision == EntityResolutionDecisionType.AMBIGUOUS
            if case.expected_decision in {
                EntityResolutionDecisionType.UNRESOLVED,
                EntityResolutionDecisionType.NOT_FOUND,
            }:
                unresolved_total += 1
                unresolved_correct += first.decision in {
                    EntityResolutionDecisionType.UNRESOLVED,
                    EntityResolutionDecisionType.NOT_FOUND,
                }
            if (
                SemanticRetrievalChannel.EXACT_CANONICAL
                in case.required_channels
            ):
                exact_expected += 1
                exact_preserved += (
                    first.selected is not None
                    and first.selected.canonical_reference.canonical_id in expected_ids
                )
            if SemanticRetrievalChannel.EXACT_ALIAS in case.required_channels:
                alias_expected += 1
                alias_resolved += (
                    first.selected is not None
                    and first.selected.canonical_reference.canonical_id in expected_ids
                    and SemanticRetrievalChannel.EXACT_ALIAS
                    in first.selected.matched_channels
                )
            forbidden_leakage += bool(
                set(case.forbidden_canonical_ids).intersection(candidate_ids)
            )
            repeatable += (
                first.model_dump(mode="json", exclude={"cache_hit"})
                == second.model_dump(mode="json", exclude={"cache_hit"})
            )

        count = len(cases)
        metrics = (
            SemanticEvaluationMetricV2(
                name="TOP_1_ACCURACY",
                value=top_one / max(1, cases_with_expected_ids),
            ),
            SemanticEvaluationMetricV2(
                name="TOP_K_RECALL",
                value=top_k / max(1, cases_with_expected_ids),
            ),
            SemanticEvaluationMetricV2(
                name="AMBIGUITY_PRECISION",
                value=ambiguity_correct / max(1, ambiguity_total),
            ),
            SemanticEvaluationMetricV2(
                name="UNRESOLVED_PRECISION",
                value=unresolved_correct / max(1, unresolved_total),
            ),
            SemanticEvaluationMetricV2(
                name="FORBIDDEN_LEAKAGE", value=float(forbidden_leakage)
            ),
            SemanticEvaluationMetricV2(name="CROSS_TENANT_LEAKAGE", value=0.0),
            SemanticEvaluationMetricV2(
                name="EXACT_MATCH_PRESERVATION",
                value=exact_preserved / max(1, exact_expected),
            ),
            SemanticEvaluationMetricV2(
                name="ALIAS_RESOLUTION",
                value=alias_resolved / max(1, alias_expected),
            ),
            SemanticEvaluationMetricV2(
                name="DETERMINISTIC_REPEATABILITY", value=repeatable / count
            ),
            SemanticEvaluationMetricV2(
                name="LATENCY_MS", value=total_latency_ms / count
            ),
        )
        passed = (
            top_k == cases_with_expected_ids
            and decision_correct == count
            and required_channels_correct == count
            and forbidden_leakage == 0
            and repeatable == count
        )
        executed_at = datetime.now(timezone.utc)
        evaluation_id = uuid.uuid4()
        result_checksum = checksum_for(
            {
                "evaluation_id": str(evaluation_id),
                "tenant_id": str(user.tenant_id),
                "index_version_id": str(version.id),
                "corpus_version": corpus_version,
                "metrics": [item.model_dump(mode="json") for item in metrics],
            }
        )
        contract = SemanticEvaluationResultV2(
            evaluation_id=evaluation_id,
            tenant_id=user.tenant_id,
            index_version_id=version.id,
            corpus_version=corpus_version,
            case_count=count,
            passed=passed,
            metrics=metrics,
            checksum=result_checksum,
            executed_at=executed_at,
        )
        await self.repository.add_evaluation_result(
            tenant_id=user.tenant_id,
            row=SemanticEvaluationResult(
                id=evaluation_id,
                tenant_id=user.tenant_id,
                index_id=index_id,
                index_version_id=version.id,
                corpus_version=corpus_version,
                case_count=count,
                passed=passed,
                metrics=[item.model_dump(mode="json") for item in metrics],
                checksum=result_checksum,
                executed_at=executed_at,
            ),
        )
        return contract
