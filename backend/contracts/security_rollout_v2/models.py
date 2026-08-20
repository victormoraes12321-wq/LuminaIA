"""Strict immutable contracts for Prompt 26 security and rollout evidence."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    CapabilityDecisionV2,
    ConfigurationReadinessStateV2,
    DeploymentCompatibilityStateV2,
    FeatureRolloutStageV2,
    GateOutcomeV2,
    GovernedFeatureV2,
    IncidentReadinessStateV2,
    KillSwitchStateV2,
    OperationalReadinessStateV2,
    RollbackTypeV2,
    RolloutDecisionV2,
    RolloutReadinessStateV2,
    SchemaCompatibilityStateV2,
    SecurityControlStatusV2,
    SecuritySeverityV2,
    ThreatSurfaceKindV2,
)

CONTRACT_VERSION = "lumina.security-migration-rollout/1.0"
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$"
CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SecurityControlV2(StrictFrozenModel):
    control_id: str = Field(pattern=ID_PATTERN)
    surface: ThreatSurfaceKindV2
    status: SecurityControlStatusV2
    severity: SecuritySeverityV2
    title: str = Field(min_length=3, max_length=160)
    evidence: str = Field(min_length=3, max_length=1000)
    justification: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_not_applicable_justification(self) -> "SecurityControlV2":
        if self.status is SecurityControlStatusV2.NOT_APPLICABLE and not self.justification:
            raise ValueError("NOT_APPLICABLE requires a deterministic justification")
        return self


class SecurityFindingV2(StrictFrozenModel):
    finding_id: str = Field(pattern=ID_PATTERN)
    severity: SecuritySeverityV2
    affected_component: str = Field(min_length=2, max_length=160)
    evidence: str = Field(min_length=3, max_length=1000)
    remediation: str = Field(min_length=3, max_length=1000)
    status: SecurityControlStatusV2


class ThreatSurfaceV2(StrictFrozenModel):
    surface: ThreatSurfaceKindV2
    trust_authority: str = Field(min_length=3, max_length=300)
    untrusted_inputs: tuple[str, ...] = Field(max_length=32)
    threats: tuple[str, ...] = Field(max_length=32)
    controls: tuple[str, ...] = Field(max_length=32)


class TenantIsolationCheckV2(StrictFrozenModel):
    subsystem: str = Field(pattern=ID_PATTERN)
    disclosure_count: int = Field(ge=0)
    mutation_count: int = Field(ge=0)
    status: SecurityControlStatusV2


class CapabilityCheckV2(StrictFrozenModel):
    role: str = Field(pattern=r"^(ADMIN|GESTOR|CONSULTA)$")
    capability: str = Field(pattern=ID_PATTERN)
    decision: CapabilityDecisionV2
    authority_source: str = Field(min_length=3, max_length=200)


class SecurityReadinessV2(StrictFrozenModel):
    contract_version: str = Field(default=CONTRACT_VERSION, pattern=r"^lumina\.security-migration-rollout/1\.0$")
    controls: tuple[SecurityControlV2, ...]
    findings: tuple[SecurityFindingV2, ...] = ()
    tenant_checks: tuple[TenantIsolationCheckV2, ...] = ()
    total_controls: int = Field(ge=0)
    passed_controls: int = Field(ge=0)
    failed_controls: int = Field(ge=0)
    critical_failures: int = Field(ge=0)
    ready: bool


class FeatureConfigurationV2(StrictFrozenModel):
    feature: GovernedFeatureV2
    mode: str = Field(min_length=1, max_length=64)
    stage: FeatureRolloutStageV2 = FeatureRolloutStageV2.DISABLED
    api_enabled: bool = False
    worker_enabled: bool = False
    execution_enabled: bool = False
    kill_switch_active: bool = True


class ConfigurationSnapshotV2(StrictFrozenModel):
    environment: str = Field(pattern=r"^(development|staging|production|test)$")
    testing_enabled: bool
    external_network_disabled: bool
    mock_oracle: bool
    mock_openai: bool
    global_emergency_disable: bool
    rollout_execution_enabled: bool
    canary_percentage: int = Field(ge=0, le=100)
    canary_tenant_count: int = Field(ge=0)
    features: tuple[FeatureConfigurationV2, ...]


class ConfigurationReadinessV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    state: ConfigurationReadinessStateV2
    controls: tuple[SecurityControlV2, ...]
    blocking_reasons: tuple[str, ...] = ()


class SchemaManifestV2(StrictFrozenModel):
    schema_version: int = Field(ge=0)
    migration_ids: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    indexes: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()


class MigrationCompatibilityV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    current_schema_version: int = Field(ge=0)
    minimum_supported_schema_version: int = Field(ge=0)
    maximum_tested_schema_version: int = Field(ge=0)
    required_schema_version: int = Field(ge=0)
    application_contract_version: str = Field(min_length=3, max_length=128)
    state: SchemaCompatibilityStateV2
    missing_objects: tuple[str, ...] = ()
    reason: str = Field(min_length=3, max_length=500)


class MigrationReadinessV2(StrictFrozenModel):
    compatibility: MigrationCompatibilityV2
    advisory_lock_available: bool
    historical_migrations_intact: bool
    drift_detected: bool
    ready: bool


class FeatureDependencyV2(StrictFrozenModel):
    dependency_id: str = Field(pattern=ID_PATTERN)
    required: bool = True
    satisfied: bool
    evidence: str = Field(min_length=3, max_length=300)


class KillSwitchV2(StrictFrozenModel):
    feature: GovernedFeatureV2 | None = None
    state: KillSwitchStateV2
    source: str = Field(pattern=r"^(SERVER_CONFIGURATION|TEST_SIMULATION)$")
    reason_code: str = Field(pattern=ID_PATTERN)


class CanaryPolicyV2(StrictFrozenModel):
    policy_version: str = Field(pattern=ID_PATTERN)
    percentage: int = Field(ge=0, le=100)
    explicit_internal_tenants: tuple[str, ...] = ()
    allowed_environments: tuple[str, ...] = ("test", "staging")
    real_tenant_count: int = Field(default=0, ge=0)


class CanaryAssignmentV2(StrictFrozenModel):
    policy_version: str = Field(pattern=ID_PATTERN)
    bucket: int = Field(ge=0, le=9999)
    eligible: bool
    reason_code: str = Field(pattern=ID_PATTERN)


class RolloutGateV2(StrictFrozenModel):
    gate_id: str = Field(pattern=ID_PATTERN)
    outcome: GateOutcomeV2
    reason_code: str = Field(pattern=ID_PATTERN)
    critical: bool = False


class FeatureRolloutPolicyV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    feature: GovernedFeatureV2
    required_migration: int = Field(ge=0)
    dependency_ids: tuple[str, ...]
    allowed_environments: tuple[str, ...]
    rollback_types: tuple[RollbackTypeV2, ...]
    kill_switch_required: bool = True


class RolloutEvidenceV2(StrictFrozenModel):
    environment: str = Field(pattern=r"^(development|staging|production|test)$")
    requested_stage: FeatureRolloutStageV2
    migration_compatible: bool
    security_ready: bool
    tenant_isolation_pass: bool
    openapi_reproducible: bool
    evaluations_pass: bool
    observability_ready: bool
    error_budget_available: bool
    error_budget_exhausted: bool
    performance_structural_pass: bool
    queue_healthy: bool
    rollback_ready: bool
    dependencies_satisfied: bool
    full_regression_pass: bool
    runbook_ready: bool
    global_kill_switch_active: bool
    feature_kill_switch_active: bool
    tenant_eligible: bool
    user_capability_allowed: bool
    critical_security_failure: bool = False


class RolloutReadinessV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    feature: GovernedFeatureV2
    requested_stage: FeatureRolloutStageV2
    state: RolloutReadinessStateV2
    decision: RolloutDecisionV2
    gates: tuple[RolloutGateV2, ...]
    blocking_reasons: tuple[str, ...] = ()


class RollbackPlanV2(StrictFrozenModel):
    feature: GovernedFeatureV2
    rollback_types: tuple[RollbackTypeV2, ...]
    disable_mechanism: str = Field(min_length=3, max_length=300)
    in_flight_policy: str = Field(min_length=3, max_length=300)
    persistent_data_policy: str = Field(min_length=3, max_length=300)
    previous_app_compatible: bool
    database_down_automatic: bool = False
    validation_steps: tuple[str, ...]


class RollbackReadinessV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    plans: tuple[RollbackPlanV2, ...]
    ready: bool
    blocking_reasons: tuple[str, ...] = ()


class DeploymentCompatibilityV2(StrictFrozenModel):
    scenario_id: str = Field(pattern=ID_PATTERN)
    state: DeploymentCompatibilityStateV2
    reason: str = Field(min_length=3, max_length=500)


class OperationalReadinessV2(StrictFrozenModel):
    state: OperationalReadinessStateV2
    health_alive: bool
    ready_for_traffic: bool
    blocking_reasons: tuple[str, ...] = ()


class IncidentReadinessV2(StrictFrozenModel):
    state: IncidentReadinessStateV2
    runbook_available: bool
    evidence_preservation_available: bool
    break_glass_status: str = Field(pattern=r"^(BREAK_GLASS_NOT_IMPLEMENTED|GOVERNED)$")


class SecurityCertificationV2(StrictFrozenModel):
    contract_version: str = CONTRACT_VERSION
    security: SecurityReadinessV2
    configuration: ConfigurationReadinessV2
    migration: MigrationReadinessV2
    rollout: tuple[RolloutReadinessV2, ...]
    rollback: RollbackReadinessV2
    operational: OperationalReadinessV2
    incident: IncidentReadinessV2
    certified: bool
    evidence_checksum: str = Field(pattern=CHECKSUM_PATTERN)
