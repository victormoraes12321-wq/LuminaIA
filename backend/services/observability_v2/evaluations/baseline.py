"""Immutable baseline management for certified evaluation suites."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from contracts.observability_v2 import EvaluationBaselineV2, EvaluationSuiteKindV2

_CERTIFIED_COMMIT_REF = "880477a980aeaef840ac0a5c66f8541eb6c7c349"
_CORPUS_VERSION = "2026.08.01"


class EvaluationBaselineServiceV2:
    @staticmethod
    def get_certified_baseline(suite: EvaluationSuiteKindV2) -> EvaluationBaselineV2:
        ck_source = f"{suite.value}:{_CERTIFIED_COMMIT_REF}:{_CORPUS_VERSION}"
        baseline_ck = hashlib.sha256(ck_source.encode()).hexdigest()
        case_ck = hashlib.sha256(f"cases:{suite.value}".encode()).hexdigest()

        return EvaluationBaselineV2(
            baseline_id=f"bsl_{suite.value.lower()}_v1",
            suite=suite,
            version="1.0",
            source_commit_reference=_CERTIFIED_COMMIT_REF,
            corpus_version=_CORPUS_VERSION,
            case_checksums=((suite.value.lower(), case_ck),),
            created_at=datetime(2026, 8, 7, 10, 0, 0, tzinfo=timezone.utc),
            checksum=baseline_ck,
        )

    @staticmethod
    def list_all_baselines() -> tuple[EvaluationBaselineV2, ...]:
        return tuple(
            EvaluationBaselineServiceV2.get_certified_baseline(kind)
            for kind in EvaluationSuiteKindV2
        )
