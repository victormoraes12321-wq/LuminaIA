from __future__ import annotations

from contracts.dashboard_ai_assistance_v2 import DashboardAiSemanticChangeIntentV2
from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardPatchOperationKindV2,
    DashboardPatchOperationV2,
    DashboardSemanticPatchV2,
)
from services.dashboard_blueprint_v2.canonicalizer import DashboardBlueprintCanonicalizer

from .resolution import _METRICS
from .integrity import normalized_key


class DashboardAiSemanticPatchCompilerV2:
    """Pure allowlisted compiler; it never accepts a patch produced by a provider."""

    def compile(self, *, base: DashboardBlueprintV2, intent: DashboardAiSemanticChangeIntentV2) -> DashboardSemanticPatchV2:
        if len(intent.metric_mentions) != 1:
            raise ValueError("DASHBOARD_AI_SEMANTIC_METRIC_REQUIRED")
        row = _METRICS.get(normalized_key(intent.metric_mentions[0]))
        if row is None:
            raise ValueError("DASHBOARD_AI_UNKNOWN_METRIC")
        canonical = DashboardBlueprintCanonicalizer.canonicalize(base)
        return DashboardSemanticPatchV2(
            blueprint_id=base.identity.blueprint_id,
            base_blueprint_checksum=canonical.checksums.blueprint_checksum,
            base_semantic_checksum=canonical.checksums.semantic_checksum,
            base_semantic_revision=base.version.revision.semantic_revision,
            target_semantic_revision=base.version.revision.semantic_revision + 1,
            requires_revalidation=True,
            operations=(DashboardPatchOperationV2(
                operation=DashboardPatchOperationKindV2.REPLACE,
                path="/data_bindings/0/metrics/0/metric_id",
                value=row[0],
            ),),
        )

