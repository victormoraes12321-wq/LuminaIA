from __future__ import annotations

import uuid

from contracts.supervised_feedback_v2 import (
    FeedbackCategoryV2,
    FeedbackCorrectionV2,
    FeedbackPriority,
    FeedbackSeverity,
    FeedbackTargetV2,
    FeedbackTriageResultV2,
)
from services.supervised_feedback.checksums import checksum


class FeedbackTriageEngine:
    RULE_VERSION = "lumina.feedback-triage/1.0"

    _DATA_INTEGRITY = frozenset(
        {
            FeedbackCategoryV2.INCORRECT_VALUE,
            FeedbackCategoryV2.INCORRECT_FILTER,
            FeedbackCategoryV2.INCORRECT_PERIOD,
            FeedbackCategoryV2.INCORRECT_METRIC,
            FeedbackCategoryV2.INCORRECT_ENTITY,
            FeedbackCategoryV2.INCORRECT_DIMENSION,
            FeedbackCategoryV2.INCORRECT_COMPARISON,
        }
    )
    _CONTEXT = frozenset(
        {
            FeedbackCategoryV2.MISSING_CONTEXT,
            FeedbackCategoryV2.UNWANTED_INHERITANCE,
            FeedbackCategoryV2.MISSING_INHERITANCE,
            FeedbackCategoryV2.AMBIGUOUS,
        }
    )

    def triage(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        target: FeedbackTargetV2,
        category: FeedbackCategoryV2,
        correction: FeedbackCorrectionV2 | None,
        sensitive_content_detected: bool,
    ) -> FeedbackTriageResultV2:
        if category is FeedbackCategoryV2.UNSAFE_OUTPUT:
            severity, priority, queue = (
                FeedbackSeverity.CRITICAL,
                FeedbackPriority.P1,
                "SECURITY",
            )
            rules = ["TRIAGE_UNSAFE_OUTPUT_P1"]
        elif category in self._DATA_INTEGRITY:
            severity, priority, queue = (
                FeedbackSeverity.HIGH,
                FeedbackPriority.P2,
                "DATA_INTEGRITY",
            )
            rules = ["TRIAGE_OFFICIAL_DATA_P2"]
        elif category in self._CONTEXT:
            severity, priority, queue = (
                FeedbackSeverity.MEDIUM,
                FeedbackPriority.P3,
                "CONTEXT",
            )
            rules = ["TRIAGE_CONTEXT_P3"]
        elif category is FeedbackCategoryV2.INCORRECT_VISUALIZATION:
            severity, priority, queue = (
                FeedbackSeverity.LOW,
                FeedbackPriority.P4,
                "VISUALIZATION",
            )
            rules = ["TRIAGE_VISUALIZATION_P4"]
        elif category is FeedbackCategoryV2.PERFORMANCE:
            severity, priority, queue = (
                FeedbackSeverity.MEDIUM,
                FeedbackPriority.P3,
                "PERFORMANCE",
            )
            rules = ["TRIAGE_PERFORMANCE_P3"]
        else:
            severity, priority, queue = (
                FeedbackSeverity.LOW,
                FeedbackPriority.P4,
                "GENERAL",
            )
            rules = ["TRIAGE_GENERAL_P4"]

        duplicate_payload = {
            "tenant_id": tenant_id,
            "response_checksum": target.response_checksum,
            "category": category,
            "correction": correction,
            "contract_version": self.RULE_VERSION,
        }
        duplicate_fingerprint = checksum(duplicate_payload)
        payload = {
            "category": category,
            "severity": severity,
            "priority": priority,
            "review_queue": queue,
            "duplicate_fingerprint": duplicate_fingerprint,
            "suspected_security": category is FeedbackCategoryV2.UNSAFE_OUTPUT,
            "suspected_formula_conflict": category
            in {FeedbackCategoryV2.INCORRECT_VALUE, FeedbackCategoryV2.INCORRECT_METRIC},
            "suspected_tenant_issue": False,
            "needs_specialist": category
            in {
                FeedbackCategoryV2.UNSAFE_OUTPUT,
                FeedbackCategoryV2.INCORRECT_VALUE,
                FeedbackCategoryV2.INCORRECT_METRIC,
            },
            "classification_confidence": 100,
            "rule_ids": [self.RULE_VERSION, *rules],
            "warnings": ["SENSITIVE_INPUT_REDACTED"] if sensitive_content_detected else [],
        }
        return FeedbackTriageResultV2(
            triage_id=uuid.uuid4(),
            **payload,
            checksum=checksum(payload),
        )
