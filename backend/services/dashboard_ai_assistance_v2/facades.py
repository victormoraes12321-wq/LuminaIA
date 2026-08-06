"""Small domain facades kept separate from orchestration and persistence concerns."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiEvaluationCaseV2,
    DashboardAiEvaluationResultV2,
    DashboardAiFeedbackReferenceV2,
    DashboardAiProposalEvidenceV2,
)

from .integrity import checksum
from .repositories import DashboardAiAuditRepositoryV2, DashboardAiClarificationRepositoryV2, DashboardAiEvidenceRepositoryV2
from .resolution import DashboardDesignSpecServiceV2
from .synthesis import DashboardBlueprintSynthesisService
from .validation import DashboardAiProposalValidationServiceV2


class DashboardAiClarificationServiceV2:
    def __init__(self, repository: DashboardAiClarificationRepositoryV2): self.repository = repository


class DashboardAiBlueprintProposalServiceV2:
    def __init__(self) -> None:
        self.synthesizer = DashboardBlueprintSynthesisService()
        self.validator = DashboardAiProposalValidationServiceV2()
    def propose(self, design):
        blueprint = self.synthesizer.synthesize(design)
        return self.validator.validate_blueprint(blueprint, design)


class DashboardAiEvidenceServiceV2:
    def __init__(self, repository: DashboardAiEvidenceRepositoryV2): self.repository = repository
    async def list(self, tenant_id: str, proposal_id: str): return await self.repository.list(tenant_id, proposal_id)


class DashboardAiAuditServiceV2:
    def __init__(self, repository: DashboardAiAuditRepositoryV2): self.repository = repository


class DashboardAiFeedbackServiceV2:
    """Creates only a reference to the existing supervised workflow; it never learns automatically."""
    @staticmethod
    def reference(*, feedback_id: str, proposal_id: str, proposal_version: int, status: str) -> DashboardAiFeedbackReferenceV2:
        return DashboardAiFeedbackReferenceV2(feedback_id=feedback_id, proposal_id=proposal_id, proposal_version=proposal_version, supervised_feedback_status=status)


class DashboardAiEvaluationServiceV2:
    @staticmethod
    def evaluate(case: DashboardAiEvaluationCaseV2, *, actual_status, canonical_ids: tuple[str, ...]) -> DashboardAiEvaluationResultV2:
        passed = actual_status == case.expected_status and set(case.expected_canonical_ids).issubset(canonical_ids)
        basis = {"case": case.case_id, "actual": actual_status.value, "canonical": canonical_ids, "passed": passed}
        return DashboardAiEvaluationResultV2(
            result_id=f"result.{checksum(basis)[:24]}", case_id=case.case_id, passed=passed,
            actual_status=actual_status, evidence_codes=("DETERMINISTIC_EVALUATION",),
            result_checksum=checksum(basis), executed_at=datetime.now(timezone.utc),
        )
