"""Schema-version compatibility and bounded drift evaluation."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    GovernedFeatureV2,
    MigrationCompatibilityV2,
    SchemaCompatibilityStateV2,
    SchemaManifestV2,
)

from .registry import GovernedFeatureRegistryV2

CURRENT_SCHEMA_VERSION = 26
MINIMUM_SUPPORTED_SCHEMA_VERSION = 12
MAXIMUM_TESTED_SCHEMA_VERSION = 26

_CRITICAL_TABLES: dict[int, tuple[str, ...]] = {
    22: ("dashboards_v2", "dashboard_revisions_v2", "dashboard_publications_v2"),
    23: ("dashboard_ai_proposals_v2", "dashboard_ai_proposal_versions_v2"),
    24: ("post_sync_insights_v2", "post_sync_insight_outbox_v2"),
    25: ("operational_metric_rollups_v2", "observability_trace_summaries_v2", "evaluation_runs_v2"),
    26: ("governed_work_queue_jobs_v2", "governed_work_queue_workers_v2", "performance_runs_v2"),
}


class MigrationCompatibilityServiceV2:
    @staticmethod
    def required_objects(required_version: int) -> tuple[str, ...]:
        return tuple(
            table
            for version, tables in sorted(_CRITICAL_TABLES.items())
            if version <= required_version
            for table in tables
        )

    @classmethod
    def evaluate(
        cls,
        *,
        current_schema_version: int,
        required_schema_version: int = CURRENT_SCHEMA_VERSION,
        manifest: SchemaManifestV2 | None = None,
    ) -> MigrationCompatibilityV2:
        missing: tuple[str, ...] = ()
        if current_schema_version <= 0:
            state = SchemaCompatibilityStateV2.UNKNOWN
            reason = "schema version is absent or unknown"
        elif current_schema_version > MAXIMUM_TESTED_SCHEMA_VERSION:
            state = SchemaCompatibilityStateV2.DATABASE_TOO_NEW
            reason = "database schema is newer than the maximum tested application contract"
        elif current_schema_version < MINIMUM_SUPPORTED_SCHEMA_VERSION:
            state = SchemaCompatibilityStateV2.UPGRADE_REQUIRED
            reason = "database schema predates the minimum supported application baseline"
        elif current_schema_version < required_schema_version:
            state = SchemaCompatibilityStateV2.UPGRADE_REQUIRED
            reason = "required additive migration has not been applied"
        else:
            state = SchemaCompatibilityStateV2.COMPATIBLE
            reason = "schema version is inside the tested compatibility window"

        if state is SchemaCompatibilityStateV2.COMPATIBLE and manifest is not None:
            expected = set(cls.required_objects(required_schema_version))
            missing = tuple(sorted(expected - set(manifest.tables)))
            if missing:
                state = SchemaCompatibilityStateV2.BLOCKED
                reason = "critical governed schema objects are missing"

        return MigrationCompatibilityV2(
            current_schema_version=current_schema_version,
            minimum_supported_schema_version=MINIMUM_SUPPORTED_SCHEMA_VERSION,
            maximum_tested_schema_version=MAXIMUM_TESTED_SCHEMA_VERSION,
            required_schema_version=required_schema_version,
            application_contract_version="lumina.security-migration-rollout/1.0",
            state=state,
            missing_objects=missing,
            reason=reason,
        )

    @classmethod
    def evaluate_feature(cls, feature: GovernedFeatureV2, current_schema_version: int, manifest: SchemaManifestV2 | None = None) -> MigrationCompatibilityV2:
        required = GovernedFeatureRegistryV2.get_policy(feature).required_migration
        return cls.evaluate(current_schema_version=current_schema_version, required_schema_version=required, manifest=manifest)
