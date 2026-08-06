from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiBlueprintProposalV2,
    DashboardAiProposalEvidenceV2,
    DashboardAiProposalRiskV2,
    DashboardAiProposalWarningV2,
)
from contracts.dashboard_blueprint_v2 import DashboardValidationStatusV2
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer
from services.dashboard_blueprint_v2.validation_service import DashboardBlueprintValidationService

from .integrity import checksum


class DashboardAiProposalValidationServiceV2:
    def validate_blueprint(self, blueprint, design_spec) -> tuple[DashboardAiBlueprintProposalV2, tuple[DashboardAiProposalEvidenceV2, ...], tuple[DashboardAiProposalWarningV2, ...], tuple[DashboardAiProposalRiskV2, ...]]:
        validation = DashboardBlueprintValidationService.validate_payload(blueprint)
        if validation.status not in {DashboardValidationStatusV2.VALID, DashboardValidationStatusV2.VALID_WITH_WARNINGS}:
            raise ValueError("DASHBOARD_AI_BLUEPRINT_VALIDATION_BLOCKED")
        canonical = DashboardBlueprintCanonicalizer.canonicalize(blueprint)
        proposal = DashboardAiBlueprintProposalV2(
            design_spec=design_spec, blueprint=blueprint,
            blueprint_checksum=canonical.checksums.blueprint_checksum,
            semantic_checksum=canonical.checksums.semantic_checksum,
            visual_checksum=canonical.checksums.visual_checksum,
        )
        basis = {"status": validation.status.value, "blueprint": canonical.checksums.blueprint_checksum}
        evidence = (DashboardAiProposalEvidenceV2(
            evidence_id=f"evidence.{checksum(basis)[:24]}", evidence_type="VALIDATION",
            canonical_reference=blueprint.identity.blueprint_id, public_label="Blueprint V2 validado",
            authority_version="lumina.dashboard-blueprint/2.0", checksum=checksum(basis),
        ),)
        warnings = tuple(DashboardAiProposalWarningV2(code=issue.code, message=issue.message) for issue in validation.issues if not issue.blocking)
        return proposal, evidence, warnings, ()

