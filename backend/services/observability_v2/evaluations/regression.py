"""Regression detection engine comparing evaluation results against certified baselines."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from contracts.observability_v2 import (
    EvaluationOutcomeV2,
    EvaluationRegressionV2,
    EvaluationResultV2,
    RegressionTypeV2,
)
from services.observability_v2.evaluations.baseline import EvaluationBaselineServiceV2


class EvaluationRegressionServiceV2:
    def detect_regressions(
        self,
        results: tuple[EvaluationResultV2, ...] | list[EvaluationResultV2],
    ) -> tuple[EvaluationRegressionV2, ...]:
        regressions: list[EvaluationRegressionV2] = []
        now = datetime.now(timezone.utc)

        for res in results:
            baseline = EvaluationBaselineServiceV2.get_certified_baseline(res.suite)
            if res.outcome == EvaluationOutcomeV2.FAIL:
                reg_type = RegressionTypeV2.PASS_TO_FAIL
                if res.suite.value in {"SECURITY", "TENANT_ISOLATION"}:
                    reg_type = RegressionTypeV2.SECURITY_INVARIANT_VIOLATION

                reg_id = f"reg_{uuid.uuid4().hex[:12]}"
                regressions.append(
                    EvaluationRegressionV2(
                        regression_id=reg_id,
                        case_id=res.case_id,
                        suite=res.suite,
                        regression_type=reg_type,
                        description=f"Regression detected in case {res.case_id}: {res.outcome.value}",
                        detected_at=now,
                        baseline_checksum=baseline.checksum,
                        current_checksum=res.checksum,
                    )
                )

        return tuple(regressions)
