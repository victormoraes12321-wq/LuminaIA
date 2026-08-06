from __future__ import annotations

from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardPatchOperationKindV2,
    DashboardPatchOperationV2,
    DashboardVisualPatchV2,
)
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer

from .integrity import assert_safe_untrusted_text


class DashboardAiVisualProposalServiceV2:
    """Compiles a Prompt 21 compatible visual patch from a bounded objective."""

    def propose_title(self, *, base: DashboardBlueprintV2, title: str) -> DashboardVisualPatchV2:
        safe_title = assert_safe_untrusted_text(title, field="visual_title")
        canonical = DashboardBlueprintCanonicalizer.canonicalize(base)
        return DashboardVisualPatchV2(
            blueprint_id=base.identity.blueprint_id,
            base_blueprint_checksum=canonical.checksums.blueprint_checksum,
            base_semantic_checksum=canonical.checksums.semantic_checksum,
            base_visual_revision=base.version.revision.visual_revision,
            target_visual_revision=base.version.revision.visual_revision + 1,
            operations=(DashboardPatchOperationV2(operation=DashboardPatchOperationKindV2.REPLACE, path="/identity/title", value=safe_title),),
        )

