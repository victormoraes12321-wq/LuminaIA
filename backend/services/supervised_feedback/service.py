from __future__ import annotations

import json
import hashlib
import tempfile
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from contracts.supervised_feedback_v2 import (
    SUPERVISED_FEEDBACK_VERSION,
    ApprovedTrainingExampleV2,
    CandidateStatus,
    DatasetStatus,
    ExampleQualityStatus,
    FeedbackCategoryV2,
    FeedbackCorrectionV2,
    FeedbackExportV2,
    GovernedImportDryRunRequestV2,
    GovernedImportDryRunResultV2,
    FeedbackLifecycle,
    FeedbackPermission,
    FeedbackRecordV2,
    FeedbackRedactionManifestV2,
    FeedbackReviewDecisionV2,
    FeedbackReviewV2,
    FeedbackShadowEvaluationV2,
    FeedbackSubmissionV2,
    FeedbackTargetV2,
    FeedbackTriageResultV2,
    TrainingDatasetExportV2,
    TrainingDatasetManifestV2,
    TrainingDatasetSnapshotV2,
    TrainingExampleCandidateV2,
    TrainingExampleExpectedOutputV2,
    TrainingExampleInputV2,
)
from models.supervised_feedback import (
    FeedbackDeletionRequest,
    GovernedFeedbackCorrection,
    GovernedFeedbackEvent,
    GovernedFeedbackRecord,
    GovernedFeedbackRedaction,
    GovernedFeedbackReview,
    SupervisedTrainingCandidate,
    SupervisedTrainingExample,
    TrainingDatasetExport,
    TrainingDatasetMember,
    TrainingDatasetSnapshot,
)
from models.user import User
from services.conversation_state.content_protector import (
    ConversationContentError,
    ConversationContentProtector,
)
from services.supervised_feedback.checksums import checksum, hash_idempotency_key
from services.supervised_feedback.cache import FeedbackMetadataCache
from services.supervised_feedback.errors import (
    FeedbackAlreadyWithdrawnError,
    FeedbackInvalidTransitionError,
    FeedbackNotFoundError,
    FeedbackSelfReviewForbiddenError,
    FeedbackTargetChecksumMismatchError,
    FeedbackTargetNotFoundError,
    FeedbackVersionConflictError,
    TrainingCandidateInvalidError,
    TrainingCandidateNotFoundError,
    TrainingDatasetImmutableError,
    TrainingDatasetVersionConflictError,
    TrainingExampleBlockedError,
)
from services.supervised_feedback.lifecycle import (
    FEEDBACK_TRANSITIONS,
    require_candidate_transition,
    require_transition,
)
from services.supervised_feedback.imports import GovernedImportDryRunValidator
from services.supervised_feedback.observability import FeedbackCounters
from services.supervised_feedback.permissions import require_permission
from services.supervised_feedback.redaction import FeedbackRedactionEngine
from services.supervised_feedback.repository import GovernedFeedbackRepository
from services.supervised_feedback.triage import FeedbackTriageEngine


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GovernedFeedbackService:
    """Governed feedback authority. It never calls AI, Oracle or analytical SQL."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        redaction: FeedbackRedactionEngine | None = None,
        triage: FeedbackTriageEngine | None = None,
        clock: Callable[[], datetime] = utc_now,
        protector: ConversationContentProtector | None = None,
        cache: FeedbackMetadataCache | None = None,
        counters: FeedbackCounters | None = None,
        import_validator: GovernedImportDryRunValidator | None = None,
    ) -> None:
        self.db = db
        self.repo = GovernedFeedbackRepository(db)
        self.redaction = redaction or FeedbackRedactionEngine()
        self.triage = triage or FeedbackTriageEngine()
        self.clock = clock
        self.protector = protector or ConversationContentProtector(
            key=settings.ENCRYPTION_KEY,
            key_version=settings.CONVERSATION_CONTENT_KEY_VERSION,
            persist_content=settings.CONVERSATION_PERSIST_CONTENT,
            max_content_bytes=settings.CONVERSATION_MAX_CONTENT_BYTES,
        )
        self.cache = cache or FeedbackMetadataCache(
            enabled=settings.SUPERVISED_FEEDBACK_CACHE_ENABLED,
            ttl_seconds=settings.SUPERVISED_FEEDBACK_CACHE_TTL_SECONDS,
        )
        self.counters = counters or FeedbackCounters(
            rollout_mode=settings.SUPERVISED_FEEDBACK_MODE
        )
        self.import_validator = import_validator or GovernedImportDryRunValidator()

    @staticmethod
    def _authorize(user: User, permission: FeedbackPermission) -> None:
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
        event_type: str,
        reason_code: str,
        feedback_id: uuid.UUID | None,
        metadata: dict[str, str | int | bool] | None = None,
        request_id: str | None = None,
    ) -> None:
        payload = {
            "tenant_id": user.tenant_id,
            "feedback_id": feedback_id,
            "actor_user_id": user.id,
            "event_type": event_type,
            "reason_code": reason_code,
            "request_id": request_id,
            "event_metadata": metadata or {},
        }
        await self.repo.record_event(
            GovernedFeedbackEvent(
                **payload,
                checksum=checksum(payload),
            )
        )

    async def _record_contract(
        self, row: GovernedFeedbackRecord
    ) -> FeedbackRecordV2:
        correction_row = await self.repo.get_correction(
            tenant_id=row.tenant_id, feedback_id=row.id
        )
        correction = (
            FeedbackCorrectionV2.model_validate_json(json.dumps(correction_row.correction))
            if correction_row is not None
            else None
        )
        triage = (
            FeedbackTriageResultV2.model_validate_json(json.dumps(row.triage_data))
            if row.triage_data
            else None
        )
        return FeedbackRecordV2(
            feedback_id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            target=FeedbackTargetV2(
                response_node_id=row.response_node_id,
                session_id=row.public_session_id,
                response_checksum=row.response_checksum,
                query_node_id=row.query_node_id,
                response_contract_version=row.response_contract_version,
            ),
            category=FeedbackCategoryV2(row.category),
            correction=correction,
            explanation=row.explanation,
            lifecycle=FeedbackLifecycle(row.lifecycle),
            triage=triage,
            reviewer_user_id=row.reviewer_user_id,
            review_decision=(
                FeedbackReviewDecisionV2(row.review_decision)
                if row.review_decision
                else None
            ),
            duplicate_group=row.duplicate_fingerprint,
            redaction_manifest_id=row.redaction_manifest_id,
            lock_version=row.lock_version,
            checksum=row.checksum,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def submit(
        self,
        *,
        user: User,
        request: FeedbackSubmissionV2,
        request_id: str | None = None,
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.CREATE_OWN)
        key_hash = hash_idempotency_key(request.idempotency_key)
        replay = await self.repo.idempotent_record(
            tenant_id=user.tenant_id,
            user_id=user.id,
            idempotency_key_hash=key_hash,
        )
        if replay is not None:
            self.counters.increment("duplicate_replay")
            return await self._record_contract(replay)

        target = await self.repo.validate_target(
            tenant_id=user.tenant_id,
            user_id=user.id,
            public_session_id=request.target.session_id,
            response_node_id=request.target.response_node_id,
        )
        if target is None:
            raise FeedbackTargetNotFoundError(
                "A resposta informada nao foi encontrada para o usuario autenticado."
            )
        authoritative_checksum = target.response_fingerprint or target.content_fingerprint
        if authoritative_checksum != request.target.response_checksum:
            raise FeedbackTargetChecksumMismatchError(
                "A resposta foi alterada ou o checksum nao corresponde ao registro original."
            )
        if request.target.query_node_id not in {None, target.parent_node_id}:
            raise FeedbackTargetNotFoundError(
                "A pergunta vinculada nao pertence a resposta informada."
            )

        redacted = self.redaction.redact(
            explanation=request.explanation,
            correction=request.correction,
        )
        triage = self.triage.triage(
            tenant_id=user.tenant_id,
            user_id=user.id,
            target=request.target,
            category=request.category,
            correction=redacted.correction,
            sensitive_content_detected=redacted.manifest.sensitive_content_detected,
        )
        feedback_id = uuid.uuid4()
        now = self.clock()
        record_payload = {
            "id": feedback_id,
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "response_node_id": request.target.response_node_id,
            "session_id": target.session_id,
            "public_session_id": request.target.session_id,
            "query_node_id": target.parent_node_id,
            "response_checksum": authoritative_checksum,
            "response_contract_version": request.target.response_contract_version,
            "category": request.category.value,
            "explanation": redacted.explanation,
            "lifecycle": FeedbackLifecycle.TRIAGED.value,
            "severity": triage.severity.value,
            "priority": triage.priority.value,
            "review_queue": triage.review_queue,
            "triage_data": triage.model_dump(mode="json"),
            "duplicate_fingerprint": triage.duplicate_fingerprint,
            "redaction_manifest_id": redacted.manifest.manifest_id,
            "idempotency_key_hash": key_hash,
            "schema_version": SUPERVISED_FEEDBACK_VERSION,
            "retention_at": now + timedelta(days=730),
        }
        row = GovernedFeedbackRecord(
            **record_payload,
            checksum=checksum(record_payload),
            created_at=now,
            updated_at=now,
        )
        correction_row = None
        if redacted.correction is not None:
            correction_payload = redacted.correction.model_dump(mode="json")
            correction_row = GovernedFeedbackCorrection(
                tenant_id=user.tenant_id,
                user_id=user.id,
                feedback_id=feedback_id,
                correction=correction_payload,
                checksum=checksum(correction_payload),
            )
        manifest_payload = redacted.manifest.model_dump(mode="json")
        redaction_row = GovernedFeedbackRedaction(
            id=redacted.manifest.manifest_id,
            tenant_id=user.tenant_id,
            user_id=user.id,
            feedback_id=feedback_id,
            policy_version=redacted.manifest.policy_version,
            manifest=manifest_payload,
            checksum=redacted.manifest.checksum,
        )
        await self.repo.create_feedback(
            row=row, correction=correction_row, redaction=redaction_row
        )
        for event_type in ("FEEDBACK_RECEIVED", "FEEDBACK_VALIDATED", "FEEDBACK_TRIAGED"):
            await self._event(
                user=user,
                event_type=event_type,
                reason_code=event_type,
                feedback_id=feedback_id,
                metadata={
                    "category": request.category.value,
                    "queue": triage.review_queue,
                    "redacted": redacted.manifest.sensitive_content_detected,
                },
                request_id=request_id,
            )
        self.counters.increment("feedback_received")
        category_metric = {
            FeedbackCategoryV2.POSITIVE: "feedback_positive",
            FeedbackCategoryV2.NEGATIVE: "feedback_negative",
            FeedbackCategoryV2.PARTIALLY_CORRECT: "feedback_partially_correct",
        }.get(request.category)
        if category_metric:
            self.counters.increment(category_metric)
        if redacted.manifest.sensitive_content_detected:
            self.counters.increment("redaction_blocks")
        if triage.suspected_security:
            self.counters.increment("security_flags")
        return await self._record_contract(row)

    async def shadow_evaluate(
        self,
        *,
        user: User,
        request: FeedbackSubmissionV2,
    ) -> FeedbackShadowEvaluationV2:
        self._authorize(user, FeedbackPermission.CREATE_OWN)
        target = await self.repo.validate_target(
            tenant_id=user.tenant_id,
            user_id=user.id,
            public_session_id=request.target.session_id,
            response_node_id=request.target.response_node_id,
        )
        target_authorized = target is not None
        authoritative_checksum = (
            (target.response_fingerprint or target.content_fingerprint)
            if target is not None
            else None
        )
        checksum_matches = authoritative_checksum == request.target.response_checksum
        redacted = self.redaction.redact(
            explanation=request.explanation,
            correction=request.correction,
        )
        triage = self.triage.triage(
            tenant_id=user.tenant_id,
            user_id=user.id,
            target=request.target,
            category=request.category,
            correction=redacted.correction,
            sensitive_content_detected=redacted.manifest.sensitive_content_detected,
        )
        reasons: list[str] = []
        if not target_authorized:
            reasons.append("TARGET_NOT_AUTHORIZED")
        if target_authorized and not checksum_matches:
            reasons.append("TARGET_CHECKSUM_MISMATCH")
        if redacted.manifest.sensitive_content_detected:
            reasons.append("SENSITIVE_INPUT_REDACTED")
        if not reasons:
            reasons.append("ELIGIBLE")
        payload = {
            "target_authorized": target_authorized,
            "checksum_matches": checksum_matches,
            "category": request.category,
            "severity": triage.severity,
            "redaction_detected": redacted.manifest.sensitive_content_detected,
            "duplicate_fingerprint": triage.duplicate_fingerprint,
            "eligible_for_collection": target_authorized and checksum_matches,
            "persisted": False,
            "reason_codes": reasons,
            "contract_version": SUPERVISED_FEEDBACK_VERSION,
        }
        return FeedbackShadowEvaluationV2(
            **payload,
            checksum=checksum(payload),
        )

    async def get_own(self, *, user: User, feedback_id: uuid.UUID) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.READ_OWN)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, user_id=user.id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        return await self._record_contract(row)

    async def list_own(
        self,
        *,
        user: User,
        limit: int,
        after_created_at: datetime | None,
        after_id: uuid.UUID | None,
    ) -> list[FeedbackRecordV2]:
        self._authorize(user, FeedbackPermission.READ_OWN)
        rows = await self.repo.list_feedback(
            tenant_id=user.tenant_id,
            user_id=user.id,
            lifecycle=None,
            review_queue=None,
            limit=limit,
            after_created_at=after_created_at,
            after_id=after_id,
        )
        return [await self._record_contract(row) for row in rows]

    async def update_explanation(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        explanation: str,
        expected_lock_version: int,
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.UPDATE_OWN)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, user_id=user.id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        if FeedbackLifecycle(row.lifecycle) not in {
            FeedbackLifecycle.TRIAGED,
            FeedbackLifecycle.NEEDS_INFORMATION,
        }:
            raise FeedbackInvalidTransitionError(
                "A explicacao nao pode ser alterada neste estado."
            )
        clean, _ = self.redaction.sanitize_text(explanation)
        updated_checksum = checksum(
            {
                "feedback_id": row.id,
                "category": row.category,
                "explanation": clean,
                "response_checksum": row.response_checksum,
            }
        )
        swapped = await self.repo.compare_and_swap(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={"explanation": clean, "checksum": updated_checksum},
        )
        if not swapped:
            raise FeedbackVersionConflictError("O feedback foi alterado por outra operacao.")
        await self.db.refresh(row)
        await self._event(
            user=user,
            event_type="FEEDBACK_EXPLANATION_UPDATED",
            reason_code="USER_CORRECTION",
            feedback_id=feedback_id,
        )
        self.counters.increment("withdrawals")
        return await self._record_contract(row)

    async def withdraw(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        expected_lock_version: int,
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.WITHDRAW_OWN)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, user_id=user.id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        current = FeedbackLifecycle(row.lifecycle)
        if current is FeedbackLifecycle.WITHDRAWN:
            raise FeedbackAlreadyWithdrawnError("O feedback ja foi retirado.")
        require_transition(current, FeedbackLifecycle.WITHDRAWN)
        now = self.clock()
        swapped = await self.repo.compare_and_swap(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={"lifecycle": "WITHDRAWN", "withdrawn_at": now},
        )
        if not swapped:
            raise FeedbackVersionConflictError("O feedback foi alterado por outra operacao.")
        await self.db.refresh(row)
        await self._event(
            user=user,
            event_type="FEEDBACK_WITHDRAWN",
            reason_code="USER_REQUEST",
            feedback_id=feedback_id,
        )
        return await self._record_contract(row)

    async def respond_to_information_request(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        explanation: str,
        expected_lock_version: int,
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.UPDATE_OWN)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id,
            user_id=user.id,
            feedback_id=feedback_id,
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        require_transition(
            FeedbackLifecycle(row.lifecycle), FeedbackLifecycle.IN_REVIEW
        )
        clean, _ = self.redaction.sanitize_text(explanation)
        updated_checksum = checksum(
            {
                "feedback_id": row.id,
                "category": row.category,
                "explanation": clean,
                "response_checksum": row.response_checksum,
            }
        )
        swapped = await self.repo.compare_and_swap(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={
                "explanation": clean,
                "checksum": updated_checksum,
                "lifecycle": FeedbackLifecycle.IN_REVIEW.value,
            },
        )
        if not swapped:
            raise FeedbackVersionConflictError(
                "O feedback foi alterado por outra operacao."
            )
        await self.db.refresh(row)
        await self._event(
            user=user,
            event_type="FEEDBACK_INFORMATION_PROVIDED",
            reason_code="USER_RESPONSE",
            feedback_id=feedback_id,
        )
        return await self._record_contract(row)

    async def review_queue(
        self,
        *,
        user: User,
        lifecycle: FeedbackLifecycle | None,
        review_queue: str | None,
        limit: int,
        after_created_at: datetime | None,
        after_id: uuid.UUID | None,
    ) -> list[FeedbackRecordV2]:
        self._authorize(user, FeedbackPermission.TRIAGE)
        rows = await self.repo.list_feedback(
            tenant_id=user.tenant_id,
            user_id=None,
            lifecycle=lifecycle.value if lifecycle else None,
            review_queue=review_queue,
            limit=limit,
            after_created_at=after_created_at,
            after_id=after_id,
        )
        return [await self._record_contract(row) for row in rows]

    async def get_for_review(
        self, *, user: User, feedback_id: uuid.UUID
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.SUPPORT_READ_REDACTED)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        return await self._record_contract(row)

    async def duplicate_group(
        self,
        *,
        user: User,
        duplicate_fingerprint: str,
        limit: int,
    ) -> list[FeedbackRecordV2]:
        self._authorize(user, FeedbackPermission.TRIAGE)
        rows = await self.repo.list_duplicate_group(
            tenant_id=user.tenant_id,
            duplicate_fingerprint=duplicate_fingerprint,
            limit=limit,
        )
        return [await self._record_contract(row) for row in rows]

    async def assign_reviewer(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        expected_lock_version: int,
    ) -> FeedbackRecordV2:
        self._authorize(user, FeedbackPermission.TRIAGE)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        if reviewer_user_id == row.user_id:
            raise FeedbackSelfReviewForbiddenError(
                "O autor do feedback nao pode revisar a propria submissao."
            )
        require_transition(FeedbackLifecycle(row.lifecycle), FeedbackLifecycle.IN_REVIEW)
        swapped = await self.repo.assign_reviewer(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            reviewer_user_id=reviewer_user_id,
            expected_lock_version=expected_lock_version,
        )
        if not swapped:
            raise FeedbackVersionConflictError("A fila foi alterada por outro revisor.")
        await self.db.refresh(row)
        await self._event(
            user=user,
            event_type="REVIEWER_ASSIGNED",
            reason_code="ADMIN_ASSIGNMENT",
            feedback_id=feedback_id,
        )
        return await self._record_contract(row)

    async def review(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        decision: FeedbackReviewDecisionV2,
        rationale: str,
        expected_lock_version: int,
    ) -> FeedbackReviewV2:
        self._authorize(user, FeedbackPermission.REVIEW)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        if row.user_id == user.id:
            raise FeedbackSelfReviewForbiddenError(
                "O autor do feedback nao pode revisar a propria submissao."
            )
        if row.reviewer_user_id != user.id or row.lifecycle != "IN_REVIEW":
            raise FeedbackInvalidTransitionError(
                "O feedback nao esta atribuido ao revisor autenticado."
            )
        clean, _ = self.redaction.sanitize_text(rationale)
        review_id = uuid.uuid4()
        now = self.clock()
        payload = {
            "review_id": review_id,
            "feedback_id": feedback_id,
            "reviewer_user_id": user.id,
            "decision": decision,
            "rationale": clean,
            "evidence": [],
            "expected_lock_version": expected_lock_version,
        }
        review_checksum = checksum(payload)
        swapped = await self.repo.compare_and_swap(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={"review_decision": decision.value},
        )
        if not swapped:
            raise FeedbackVersionConflictError("O feedback foi decidido por outro revisor.")
        await self.repo.record_review(
            GovernedFeedbackReview(
                id=review_id,
                tenant_id=user.tenant_id,
                feedback_id=feedback_id,
                reviewer_user_id=user.id,
                decision=decision.value,
                rationale=clean,
                evidence=[],
                checksum=review_checksum,
                created_at=now,
            )
        )
        await self._event(
            user=user,
            event_type="FEEDBACK_REVIEWED",
            reason_code=decision.value,
            feedback_id=feedback_id,
        )
        self.counters.increment("reviews")
        return FeedbackReviewV2(
            **payload,
            created_at=now,
            checksum=review_checksum,
        )

    async def finalize(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        target: FeedbackLifecycle,
        expected_lock_version: int,
    ) -> FeedbackRecordV2:
        permission = {
            FeedbackLifecycle.APPROVED: FeedbackPermission.APPROVE,
            FeedbackLifecycle.REJECTED: FeedbackPermission.REJECT,
            FeedbackLifecycle.NEEDS_INFORMATION: FeedbackPermission.REQUEST_INFORMATION,
        }[target]
        self._authorize(user, permission)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        require_transition(FeedbackLifecycle(row.lifecycle), target)
        if target in {FeedbackLifecycle.APPROVED, FeedbackLifecycle.REJECTED}:
            if row.review_decision is None:
                raise FeedbackInvalidTransitionError(
                    "Uma revisao humana deve ser registrada antes da decisao final."
                )
        swapped = await self.repo.compare_and_swap(
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            expected_lock_version=expected_lock_version,
            values={"lifecycle": target.value},
        )
        if not swapped:
            raise FeedbackVersionConflictError("O feedback foi alterado por outra operacao.")
        await self.db.refresh(row)
        await self._event(
            user=user,
            event_type=f"FEEDBACK_{target.value}",
            reason_code="HUMAN_REVIEW_DECISION",
            feedback_id=feedback_id,
        )
        if target is FeedbackLifecycle.APPROVED:
            self.counters.increment("approvals")
        elif target is FeedbackLifecycle.REJECTED:
            self.counters.increment("rejections")
        return await self._record_contract(row)

    def _decrypt_question(self, node: object | None) -> str | None:
        ciphertext = getattr(node, "content_ciphertext", None)
        key_version = getattr(node, "content_key_version", None)
        if not ciphertext or not key_version:
            return None
        try:
            plain = self.protector.decrypt(ciphertext, key_version=key_version)
        except ConversationContentError:
            return None
        clean, _ = self.redaction.sanitize_text(plain)
        return clean

    async def create_candidate(
        self, *, user: User, feedback_id: uuid.UUID
    ) -> TrainingExampleCandidateV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        existing = await self.repo.get_candidate_by_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if existing is not None:
            return self._candidate_contract(existing)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        if row.lifecycle != "APPROVED" or row.review_decision is None:
            raise TrainingCandidateInvalidError(
                "Somente feedback aprovado por revisao humana pode virar candidato."
            )
        query_node = (
            await self.repo.get_query_node(
                tenant_id=user.tenant_id,
                user_id=row.user_id,
                session_id=row.session_id,
                query_node_id=row.query_node_id,
            )
            if row.query_node_id
            else None
        )
        question = self._decrypt_question(query_node)
        correction_row = await self.repo.get_correction(
            tenant_id=user.tenant_id, feedback_id=feedback_id
        )
        correction = (
            FeedbackCorrectionV2.model_validate_json(json.dumps(correction_row.correction))
            if correction_row
            else None
        )
        input_contract = TrainingExampleInputV2(
            minimized_question=question or "Conteudo indisponivel por politica de retencao.",
            intent_kind="GOVERNED_FEEDBACK",
            metric_ids=[],
            dimension_ids=[],
            entity_ids=[],
            time_windows=[],
            filters=[],
            requested_visualizations=[],
        )
        output_contract = TrainingExampleExpectedOutputV2(
            expected_classification=FeedbackReviewDecisionV2(row.review_decision),
            expected_corrections=correction,
        )
        quality = (
            ExampleQualityStatus.VALID
            if question is not None
            else ExampleQualityStatus.INCOMPLETE
        )
        rules = [
            "FEEDBACK_APPROVED",
            "HUMAN_REVIEW_PRESENT",
            "REDACTION_PRESENT",
            "QUESTION_AVAILABLE" if question else "QUESTION_UNAVAILABLE",
        ]
        candidate_id = uuid.uuid4()
        payload = {
            "candidate_id": candidate_id,
            "feedback_id": feedback_id,
            "tenant_id": user.tenant_id,
            "status": CandidateStatus.CANDIDATE,
            "input": input_contract,
            "expected_output": output_contract,
            "quality_status": quality,
            "quality_rule_ids": rules,
            "lock_version": 0,
        }
        candidate_checksum = checksum(payload)
        now = self.clock()
        candidate = SupervisedTrainingCandidate(
            id=candidate_id,
            tenant_id=user.tenant_id,
            feedback_id=feedback_id,
            created_by_user_id=user.id,
            status=CandidateStatus.CANDIDATE.value,
            input_data=input_contract.model_dump(mode="json"),
            expected_output=output_contract.model_dump(mode="json"),
            quality_status=quality.value,
            quality_rule_ids=rules,
            lock_version=0,
            checksum=candidate_checksum,
            created_at=now,
            updated_at=now,
        )
        await self.repo.create_candidate(candidate)
        await self._event(
            user=user,
            event_type="TRAINING_CANDIDATE_CREATED",
            reason_code="EXPLICIT_CURATION",
            feedback_id=feedback_id,
        )
        self.counters.increment("candidates")
        return TrainingExampleCandidateV2(
            **payload, checksum=candidate_checksum, created_at=now
        )

    @staticmethod
    def _candidate_contract(
        row: SupervisedTrainingCandidate,
    ) -> TrainingExampleCandidateV2:
        return TrainingExampleCandidateV2(
            candidate_id=row.id,
            feedback_id=row.feedback_id,
            tenant_id=row.tenant_id,
            status=CandidateStatus(row.status),
            input=TrainingExampleInputV2.model_validate_json(
                json.dumps(row.input_data)
            ),
            expected_output=TrainingExampleExpectedOutputV2.model_validate_json(
                json.dumps(row.expected_output)
            ),
            quality_status=ExampleQualityStatus(row.quality_status),
            quality_rule_ids=row.quality_rule_ids,
            lock_version=row.lock_version,
            checksum=row.checksum,
            created_at=row.created_at,
        )

    async def validate_candidate(
        self,
        *,
        user: User,
        candidate_id: uuid.UUID,
        expected_lock_version: int,
    ) -> TrainingExampleCandidateV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        candidate = await self.repo.get_candidate(
            tenant_id=user.tenant_id, candidate_id=candidate_id
        )
        if candidate is None:
            raise TrainingCandidateNotFoundError("Candidato nao encontrado.")
        require_candidate_transition(
            CandidateStatus(candidate.status), CandidateStatus.VALIDATED
        )
        if candidate.quality_status != ExampleQualityStatus.VALID.value:
            raise TrainingExampleBlockedError(
                "O candidato nao passou pelas validacoes deterministicas."
            )
        swapped = await self.repo.compare_and_swap_candidate(
            tenant_id=user.tenant_id,
            candidate_id=candidate_id,
            expected_lock_version=expected_lock_version,
            values={
                "status": CandidateStatus.VALIDATED.value,
                "reviewed_by_user_id": user.id,
            },
        )
        if not swapped:
            raise FeedbackVersionConflictError(
                "O candidato foi alterado por outro curador."
            )
        await self.db.refresh(candidate)
        await self._event(
            user=user,
            event_type="TRAINING_CANDIDATE_VALIDATED",
            reason_code="DETERMINISTIC_QUALITY_PASSED",
            feedback_id=candidate.feedback_id,
        )
        return self._candidate_contract(candidate)

    async def reject_candidate(
        self,
        *,
        user: User,
        candidate_id: uuid.UUID,
        expected_lock_version: int,
    ) -> TrainingExampleCandidateV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        candidate = await self.repo.get_candidate(
            tenant_id=user.tenant_id, candidate_id=candidate_id
        )
        if candidate is None:
            raise TrainingCandidateNotFoundError("Candidato nao encontrado.")
        require_candidate_transition(
            CandidateStatus(candidate.status), CandidateStatus.REJECTED
        )
        swapped = await self.repo.compare_and_swap_candidate(
            tenant_id=user.tenant_id,
            candidate_id=candidate_id,
            expected_lock_version=expected_lock_version,
            values={
                "status": CandidateStatus.REJECTED.value,
                "reviewed_by_user_id": user.id,
            },
        )
        if not swapped:
            raise FeedbackVersionConflictError(
                "O candidato foi alterado por outro curador."
            )
        await self.db.refresh(candidate)
        await self._event(
            user=user,
            event_type="TRAINING_CANDIDATE_REJECTED",
            reason_code="CURATOR_DECISION",
            feedback_id=candidate.feedback_id,
        )
        return self._candidate_contract(candidate)

    async def approve_candidate(
        self,
        *,
        user: User,
        candidate_id: uuid.UUID,
        expected_lock_version: int,
        domain: str,
    ) -> ApprovedTrainingExampleV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        candidate = await self.repo.get_candidate(
            tenant_id=user.tenant_id, candidate_id=candidate_id, for_update=True
        )
        if candidate is None:
            raise TrainingCandidateNotFoundError("Candidato nao encontrado.")
        if candidate.lock_version != expected_lock_version:
            raise FeedbackVersionConflictError("O candidato foi alterado por outro curador.")
        if candidate.status != CandidateStatus.VALIDATED.value:
            raise TrainingCandidateInvalidError(
                "O candidato precisa ser validado antes da aprovacao."
            )
        if candidate.quality_status != ExampleQualityStatus.VALID.value:
            raise TrainingExampleBlockedError(
                "O candidato nao passou por todas as validacoes deterministicas."
            )
        feedback = await self.repo.get_feedback(
            tenant_id=user.tenant_id, feedback_id=candidate.feedback_id
        )
        if feedback is None or feedback.reviewer_user_id is None:
            raise TrainingCandidateInvalidError("A revisao humana de origem nao esta disponivel.")
        if feedback.reviewer_user_id == user.id:
            raise FeedbackSelfReviewForbiddenError(
                "O revisor da resposta nao pode aprovar o exemplo supervisionado."
            )
        example_id = uuid.uuid4()
        input_contract = TrainingExampleInputV2.model_validate_json(
            json.dumps(candidate.input_data)
        )
        output_contract = TrainingExampleExpectedOutputV2.model_validate_json(
            json.dumps(candidate.expected_output)
        )
        contract_payload = {
            "example_id": example_id,
            "candidate_id": candidate.id,
            "tenant_scope": user.tenant_id,
            "input": input_contract,
            "expected_output": output_contract,
            "classification": output_contract.expected_classification,
            "applicable_contract_versions": [SUPERVISED_FEEDBACK_VERSION],
            "domain": domain,
            "locale": input_contract.locale,
            "source_feedback_ids": [candidate.feedback_id],
            "redaction_manifest_id": feedback.redaction_manifest_id,
            "reviewer_user_id": feedback.reviewer_user_id,
            "curator_user_id": user.id,
            "quality_score": 100,
            "restrictions": ["TENANT_SCOPED", "OFFLINE_ONLY", "NO_AUTOMATIC_TRAINING"],
            "review_after": self.clock() + timedelta(days=365),
        }
        example_checksum = checksum(contract_payload)
        contract = ApprovedTrainingExampleV2(
            **contract_payload, checksum=example_checksum
        )
        await self.repo.create_example(
            SupervisedTrainingExample(
                id=example_id,
                tenant_id=user.tenant_id,
                candidate_id=candidate.id,
                reviewer_user_id=feedback.reviewer_user_id,
                curator_user_id=user.id,
                example_data=contract.model_dump(mode="json"),
                quality_score=100,
                restrictions=contract.restrictions,
                checksum=example_checksum,
            )
        )
        swapped = await self.repo.compare_and_swap_candidate(
            tenant_id=user.tenant_id,
            candidate_id=candidate.id,
            expected_lock_version=expected_lock_version,
            values={
                "status": CandidateStatus.APPROVED.value,
                "reviewed_by_user_id": user.id,
            },
        )
        if not swapped:
            raise FeedbackVersionConflictError(
                "O candidato foi alterado por outro curador."
            )
        await self._event(
            user=user,
            event_type="TRAINING_CANDIDATE_APPROVED",
            reason_code="CURATOR_APPROVAL",
            feedback_id=candidate.feedback_id,
        )
        await self._event(
            user=user,
            event_type="TRAINING_EXAMPLE_CREATED",
            reason_code="CURATOR_APPROVAL",
            feedback_id=candidate.feedback_id,
        )
        self.counters.increment("approved_examples")
        return contract

    async def list_candidates(
        self,
        *,
        user: User,
        status: CandidateStatus | None,
        limit: int,
    ) -> list[TrainingExampleCandidateV2]:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        rows = await self.repo.list_candidates(
            tenant_id=user.tenant_id,
            status=status.value if status else None,
            limit=limit,
        )
        return [self._candidate_contract(row) for row in rows]

    async def list_examples(
        self, *, user: User, limit: int
    ) -> list[ApprovedTrainingExampleV2]:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        rows = await self.repo.list_examples(
            tenant_id=user.tenant_id, limit=limit
        )
        return [
            ApprovedTrainingExampleV2.model_validate_json(
                json.dumps(row.example_data)
            )
            for row in rows
        ]

    async def create_dataset_snapshot(
        self,
        *,
        user: User,
        dataset_id: uuid.UUID | None,
        version: int,
        name: str,
        description: str,
        purpose: str,
        example_ids: list[uuid.UUID],
    ) -> TrainingDatasetSnapshotV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        examples = await self.repo.get_examples(
            tenant_id=user.tenant_id, example_ids=example_ids
        )
        if len(examples) != len(set(example_ids)):
            raise TrainingExampleBlockedError(
                "Um ou mais exemplos nao pertencem ao tenant ou nao existem."
            )
        actual_dataset_id = dataset_id or uuid.uuid4()
        existing = await self.repo.list_snapshots(
            tenant_id=user.tenant_id, dataset_id=actual_dataset_id, limit=1000
        )
        if any(item.version == version for item in existing):
            raise TrainingDatasetVersionConflictError(
                "Esta versao do dataset ja existe."
            )
        if existing and version != max(item.version for item in existing) + 1:
            raise TrainingDatasetVersionConflictError(
                "A nova versao deve ser exatamente a sucessora da versao mais recente."
            )
        if not existing and version != 1:
            raise TrainingDatasetVersionConflictError(
                "O primeiro snapshot deve usar a versao 1."
            )
        checksums = [item.checksum for item in examples]
        manifest_payload = {
            "dataset_id": actual_dataset_id,
            "version": version,
            "schema_version": "lumina.training-dataset/1.0",
            "contract_version": SUPERVISED_FEEDBACK_VERSION,
            "example_checksums": checksums,
            "redaction_policy_version": self.redaction.POLICY_VERSION,
            "inclusion_criteria": ["HUMAN_REVIEWED", "CURATOR_APPROVED", "TENANT_SCOPED"],
            "exclusion_criteria": ["WITHDRAWN", "SENSITIVE", "INCOMPLETE"],
        }
        manifest = TrainingDatasetManifestV2(
            **manifest_payload, checksum=checksum(manifest_payload)
        )
        snapshot_id = uuid.uuid4()
        now = self.clock()
        snapshot_payload = {
            "snapshot_id": snapshot_id,
            "dataset_id": actual_dataset_id,
            "tenant_id": user.tenant_id,
            "version": version,
            "name": name,
            "description": description,
            "purpose": purpose,
            "status": DatasetStatus.DRAFT,
            "example_ids": [item.id for item in examples],
            "manifest": manifest,
            "created_by_user_id": user.id,
            "created_at": now,
            "lock_version": 0,
        }
        snapshot_checksum = checksum(snapshot_payload)
        snapshot_row = TrainingDatasetSnapshot(
            id=snapshot_id,
            dataset_id=actual_dataset_id,
            tenant_id=user.tenant_id,
            version=version,
            name=name,
            description=description,
            purpose=purpose,
            status=DatasetStatus.DRAFT.value,
            manifest=manifest.model_dump(mode="json"),
            created_by_user_id=user.id,
            lock_version=0,
            checksum=snapshot_checksum,
            created_at=now,
        )
        members = [
            TrainingDatasetMember(
                tenant_id=user.tenant_id,
                snapshot_id=snapshot_id,
                example_id=example.id,
                position=index,
                example_checksum=example.checksum,
            )
            for index, example in enumerate(examples)
        ]
        await self.repo.create_snapshot(snapshot=snapshot_row, members=members)
        self.cache.invalidate_tenant(user.tenant_id)
        self.counters.increment("cache_invalidations")
        self.counters.increment("dataset_snapshots")
        return TrainingDatasetSnapshotV2(
            **snapshot_payload, checksum=snapshot_checksum
        )

    async def list_dataset_snapshots(
        self,
        *,
        user: User,
        dataset_id: uuid.UUID | None,
        limit: int,
    ) -> list[TrainingDatasetSnapshotV2]:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        rows = await self.repo.list_snapshots(
            tenant_id=user.tenant_id,
            dataset_id=dataset_id,
            limit=limit,
        )
        return [await self._snapshot_contract(row) for row in rows]

    async def get_dataset_snapshot(
        self, *, user: User, snapshot_id: uuid.UUID
    ) -> TrainingDatasetSnapshotV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        row = await self.repo.get_snapshot(
            tenant_id=user.tenant_id, snapshot_id=snapshot_id
        )
        if row is None:
            raise FeedbackNotFoundError("Snapshot nao encontrado.")
        return await self._snapshot_contract(row)

    async def publish_snapshot(
        self,
        *,
        user: User,
        snapshot_id: uuid.UUID,
        expected_lock_version: int,
    ) -> TrainingDatasetSnapshotV2:
        self._authorize(user, FeedbackPermission.PUBLISH_DATASET)
        row = await self.repo.get_snapshot(
            tenant_id=user.tenant_id, snapshot_id=snapshot_id, for_update=True
        )
        if row is None:
            raise FeedbackNotFoundError("Snapshot nao encontrado.")
        if row.status == DatasetStatus.PUBLISHED.value:
            raise TrainingDatasetImmutableError("Snapshot publicado e imutavel.")
        if row.lock_version != expected_lock_version:
            raise TrainingDatasetVersionConflictError("O snapshot foi alterado.")
        if row.status != DatasetStatus.APPROVED.value:
            raise FeedbackInvalidTransitionError(
                "Somente snapshot aprovado pode ser publicado."
            )
        row.status = DatasetStatus.PUBLISHED.value
        row.published_at = self.clock()
        row.lock_version += 1
        return await self._snapshot_contract(row)

    async def review_snapshot(
        self,
        *,
        user: User,
        snapshot_id: uuid.UUID,
        target: DatasetStatus,
        expected_lock_version: int,
    ) -> TrainingDatasetSnapshotV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        row = await self.repo.get_snapshot(
            tenant_id=user.tenant_id, snapshot_id=snapshot_id, for_update=True
        )
        if row is None:
            raise FeedbackNotFoundError("Snapshot nao encontrado.")
        if row.status == DatasetStatus.PUBLISHED.value:
            raise TrainingDatasetImmutableError("Snapshot publicado e imutavel.")
        if row.lock_version != expected_lock_version:
            raise TrainingDatasetVersionConflictError("O snapshot foi alterado.")
        allowed = {
            DatasetStatus.DRAFT: {DatasetStatus.IN_REVIEW, DatasetStatus.REJECTED},
            DatasetStatus.IN_REVIEW: {
                DatasetStatus.DRAFT,
                DatasetStatus.APPROVED,
                DatasetStatus.REJECTED,
            },
        }
        current = DatasetStatus(row.status)
        if target not in allowed.get(current, set()):
            raise FeedbackInvalidTransitionError(
                "Transicao de snapshot nao permitida.",
                details={"current": current.value, "target": target.value},
            )
        row.status = target.value
        row.lock_version += 1
        if target is DatasetStatus.IN_REVIEW:
            row.reviewed_by_user_id = user.id
        if target is DatasetStatus.APPROVED:
            row.approved_by_user_id = user.id
        return await self._snapshot_contract(row)

    async def _snapshot_contract(
        self, row: TrainingDatasetSnapshot
    ) -> TrainingDatasetSnapshotV2:
        members = await self.repo.get_members(
            tenant_id=row.tenant_id, snapshot_id=row.id
        )
        manifest = None
        if row.status == DatasetStatus.PUBLISHED.value:
            manifest = self.cache.get_manifest(
                tenant_id=row.tenant_id,
                snapshot_id=row.id,
                version=row.version,
                checksum=row.checksum,
            )
            if self.cache.enabled:
                self.counters.increment("cache_hit" if manifest else "cache_miss")
        if manifest is None:
            manifest = TrainingDatasetManifestV2.model_validate_json(
                json.dumps(row.manifest)
            )
            if row.status == DatasetStatus.PUBLISHED.value:
                self.cache.put_manifest(
                    tenant_id=row.tenant_id,
                    snapshot_id=row.id,
                    version=row.version,
                    checksum=row.checksum,
                    manifest=manifest,
                )
        return TrainingDatasetSnapshotV2(
            snapshot_id=row.id,
            dataset_id=row.dataset_id,
            tenant_id=row.tenant_id,
            version=row.version,
            name=row.name,
            description=row.description,
            purpose=row.purpose,
            status=DatasetStatus(row.status),
            example_ids=[item.example_id for item in members],
            manifest=manifest,
            created_by_user_id=row.created_by_user_id,
            reviewed_by_user_id=row.reviewed_by_user_id,
            approved_by_user_id=row.approved_by_user_id,
            created_at=row.created_at,
            published_at=row.published_at,
            lock_version=row.lock_version,
            checksum=row.checksum,
        )

    async def export_dataset(
        self,
        *,
        user: User,
        snapshot_id: uuid.UUID,
        purpose: str,
    ) -> tuple[TrainingDatasetExportV2, bytes]:
        contract, stream = await self.build_dataset_export(
            user=user,
            snapshot_id=snapshot_id,
            purpose=purpose,
        )
        try:
            return contract, stream.read()
        finally:
            stream.close()

    async def build_dataset_export(
        self,
        *,
        user: User,
        snapshot_id: uuid.UUID,
        purpose: str,
    ) -> tuple[TrainingDatasetExportV2, BinaryIO]:
        self._authorize(user, FeedbackPermission.EXPORT_DATASET)
        row = await self.repo.get_snapshot(
            tenant_id=user.tenant_id, snapshot_id=snapshot_id
        )
        if row is None:
            raise FeedbackNotFoundError("Snapshot nao encontrado.")
        if row.status != DatasetStatus.PUBLISHED.value:
            raise TrainingDatasetImmutableError(
                "Somente uma versao publicada pode ser exportada."
            )
        stream = tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
        digest = hashlib.sha256()
        record_count = 0
        payload_size = 0
        try:
            async for example in self.repo.iter_snapshot_examples(
                tenant_id=user.tenant_id,
                snapshot_id=snapshot_id,
            ):
                line = (
                    json.dumps(
                        example.example_data,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n"
                ).encode("utf-8")
                stream.write(line)
                digest.update(line)
                record_count += 1
                payload_size += len(line)
            stream.seek(0)
        except Exception:
            stream.close()
            raise
        export_id = uuid.uuid4()
        now = self.clock()
        export_contract = TrainingDatasetExportV2(
            export_id=export_id,
            snapshot_id=snapshot_id,
            format="JSONL",
            purpose=purpose,
            record_count=record_count,
            payload_size_bytes=payload_size,
            manifest_checksum=checksum(row.manifest),
            content_checksum=digest.hexdigest(),
            created_at=now,
        )
        await self.repo.record_dataset_export(
            TrainingDatasetExport(
                id=export_id,
                tenant_id=user.tenant_id,
                snapshot_id=snapshot_id,
                created_by_user_id=user.id,
                format="JSONL",
                purpose=purpose,
                record_count=record_count,
                payload_size=payload_size,
                manifest_checksum=export_contract.manifest_checksum,
                content_checksum=export_contract.content_checksum,
                created_at=now,
            )
        )
        self.counters.increment("dataset_exports")
        return export_contract, stream

    def dry_run_import(
        self,
        *,
        user: User,
        request: GovernedImportDryRunRequestV2,
    ) -> GovernedImportDryRunResultV2:
        self._authorize(user, FeedbackPermission.CURATE_TRAINING)
        result = self.import_validator.validate(
            request=request,
            authenticated_tenant_id=user.tenant_id,
        )
        self.counters.increment("import_dry_runs")
        if result.rejected_count:
            self.counters.increment("import_rejections", result.rejected_count)
        return result

    async def export_own(self, *, user: User) -> tuple[FeedbackExportV2, bytes]:
        self._authorize(user, FeedbackPermission.EXPORT_OWN)
        records = await self.list_own(
            user=user, limit=10000, after_created_at=None, after_id=None
        )
        safe_records = [
            {
                "feedback_id": str(item.feedback_id),
                "target_response_id": str(item.target.response_node_id),
                "category": item.category.value,
                "correction": (
                    item.correction.model_dump(mode="json") if item.correction else None
                ),
                "explanation": item.explanation,
                "lifecycle": item.lifecycle.value,
                "created_at": item.created_at.isoformat(),
            }
            for item in records
        ]
        payload = json.dumps(
            {
                "contract_version": SUPERVISED_FEEDBACK_VERSION,
                "records": safe_records,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        now = self.clock()
        contract = FeedbackExportV2(
            export_id=uuid.uuid4(),
            feedback_ids=[item.feedback_id for item in records],
            format="JSON",
            record_count=len(records),
            checksum=checksum(payload.decode("utf-8")),
            created_at=now,
        )
        return contract, payload

    async def request_deletion(
        self,
        *,
        user: User,
        feedback_id: uuid.UUID,
        reason: str | None,
        idempotency_key: str,
    ) -> uuid.UUID:
        self._authorize(user, FeedbackPermission.UPDATE_OWN)
        row = await self.repo.get_feedback(
            tenant_id=user.tenant_id, user_id=user.id, feedback_id=feedback_id
        )
        if row is None:
            raise FeedbackNotFoundError("Feedback nao encontrado.")
        clean_reason = None
        if reason:
            clean_reason, _ = self.redaction.sanitize_text(reason)
        request_id = uuid.uuid4()
        await self.repo.create_deletion_request(
            FeedbackDeletionRequest(
                id=request_id,
                tenant_id=user.tenant_id,
                user_id=user.id,
                feedback_id=feedback_id,
                reason=clean_reason,
                idempotency_key_hash=hash_idempotency_key(idempotency_key),
            )
        )
        await self._event(
            user=user,
            event_type="FEEDBACK_DELETION_REQUESTED",
            reason_code="USER_REQUEST",
            feedback_id=feedback_id,
        )
        return request_id

    async def retention_candidates(
        self, *, user: User, at: datetime, limit: int
    ) -> list[uuid.UUID]:
        self._authorize(user, FeedbackPermission.MANAGE_RETENTION)
        rows = await self.repo.retention_candidates(
            tenant_id=user.tenant_id, at=at, limit=limit
        )
        return [row.id for row in rows]

    async def expire_due(
        self, *, user: User, at: datetime, limit: int
    ) -> list[uuid.UUID]:
        self._authorize(user, FeedbackPermission.MANAGE_RETENTION)
        rows = await self.repo.retention_candidates(
            tenant_id=user.tenant_id, at=at, limit=limit
        )
        expired: list[uuid.UUID] = []
        for row in rows:
            current = FeedbackLifecycle(row.lifecycle)
            target = (
                FeedbackLifecycle.EXPIRED
                if FeedbackLifecycle.EXPIRED
                in FEEDBACK_TRANSITIONS[current]
                else FeedbackLifecycle.ARCHIVED
            )
            require_transition(current, target)
            swapped = await self.repo.compare_and_swap(
                tenant_id=user.tenant_id,
                feedback_id=row.id,
                expected_lock_version=row.lock_version,
                values={"lifecycle": target.value},
            )
            if not swapped:
                self.counters.increment("version_conflicts")
                continue
            await self._event(
                user=user,
                event_type=f"FEEDBACK_{target.value}",
                reason_code="RETENTION_POLICY",
                feedback_id=row.id,
            )
            expired.append(row.id)
        return expired
