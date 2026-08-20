from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

_CONTRACT_VERSION = "lumina.ai-tool-registry/1.0"


class AIToolType(str, Enum):
    DOMAIN_READ = "DOMAIN_READ"
    DOMAIN_WRITE = "DOMAIN_WRITE"
    ANALYTICAL_READ = "ANALYTICAL_READ"
    ANALYTICAL_PLAN = "ANALYTICAL_PLAN"
    ANALYTICAL_EXECUTION = "ANALYTICAL_EXECUTION"
    METADATA_READ = "METADATA_READ"
    CONTEXT_READ = "CONTEXT_READ"
    PROFILE_READ = "PROFILE_READ"
    KNOWLEDGE_READ = "KNOWLEDGE_READ"
    SEMANTIC_SEARCH = "SEMANTIC_SEARCH"
    VALIDATION = "VALIDATION"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    EXTERNAL = "EXTERNAL"
    SYSTEM_INTERNAL = "SYSTEM_INTERNAL"


class AIToolCapability(str, Enum):
    READ_ENTERPRISE_KNOWLEDGE = "READ_ENTERPRISE_KNOWLEDGE"
    SEARCH_ENTERPRISE_KNOWLEDGE = "SEARCH_ENTERPRISE_KNOWLEDGE"
    READ_METRIC_DEFINITION = "READ_METRIC_DEFINITION"
    NORMALIZE_TEMPORAL_EXPRESSION = "NORMALIZE_TEMPORAL_EXPRESSION"
    SEARCH_SEMANTIC_INDEX = "SEARCH_SEMANTIC_INDEX"
    RESOLVE_ENTITY = "RESOLVE_ENTITY"
    READ_CONVERSATION_CONTEXT = "READ_CONVERSATION_CONTEXT"
    READ_USER_PROFILE_SUMMARY = "READ_USER_PROFILE_SUMMARY"
    VALIDATE_QUERY_INTENT = "VALIDATE_QUERY_INTENT"
    PLAN_COMPARISON = "PLAN_COMPARISON"
    VALIDATE_COMPARISON_PLAN = "VALIDATE_COMPARISON_PLAN"
    READ_PUBLIC_PROVENANCE = "READ_PUBLIC_PROVENANCE"
    BUILD_CLARIFICATION_OPTIONS = "BUILD_CLARIFICATION_OPTIONS"
    ANALYTICAL_POSTGRESQL_READ = "ANALYTICAL_POSTGRESQL_READ"  # Reserved / Prompt 15
    EXECUTE_GOVERNED_ANALYTICAL_PLAN = "EXECUTE_GOVERNED_ANALYTICAL_PLAN"  # Reserved / Prompt 15
    ADMINISTER_REGISTRY = "ADMINISTER_REGISTRY"
    INSPECT_TOOL_INVOCATION = "INSPECT_TOOL_INVOCATION"


class AIToolRiskClass(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    FORBIDDEN = "FORBIDDEN"


class AIToolSideEffect(str, Enum):
    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    CACHE_ONLY = "CACHE_ONLY"
    STATEFUL_IDEMPOTENT = "STATEFUL_IDEMPOTENT"
    STATEFUL_NON_IDEMPOTENT = "STATEFUL_NON_IDEMPOTENT"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    DESTRUCTIVE = "DESTRUCTIVE"
    FORBIDDEN = "FORBIDDEN"


class AIToolNetworkClass(str, Enum):
    NO_NETWORK = "NO_NETWORK"
    INTERNAL_SERVICE_ONLY = "INTERNAL_SERVICE_ONLY"
    ALLOWLISTED_EXTERNAL = "ALLOWLISTED_EXTERNAL"
    ARBITRARY_EXTERNAL = "ARBITRARY_EXTERNAL"
    FORBIDDEN = "FORBIDDEN"


class AIToolDataClass(str, Enum):
    PUBLIC_METADATA = "PUBLIC_METADATA"
    TENANT_METADATA = "TENANT_METADATA"
    TENANT_BUSINESS_DATA = "TENANT_BUSINESS_DATA"
    RESTRICTED_BUSINESS_DATA = "RESTRICTED_BUSINESS_DATA"
    PERSONAL_DATA = "PERSONAL_DATA"
    SENSITIVE_PERSONAL_DATA = "SENSITIVE_PERSONAL_DATA"
    SECRET = "SECRET"
    FORBIDDEN = "FORBIDDEN"


class AIToolLifecycle(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class AIToolCircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class AIToolRetryPolicyMode(str, Enum):
    NEVER = "NEVER"
    SAFE_READ_ONLY = "SAFE_READ_ONLY"
    IDEMPOTENT_ONLY = "IDEMPOTENT_ONLY"
    MANUAL_ONLY = "MANUAL_ONLY"


class AIToolSnapshotStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class AIToolRegistryMode(str, Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW_REGISTRY = "SHADOW_REGISTRY"
    V2_CATALOG = "V2_CATALOG"
    V2_GOVERNED_INVOCATION = "V2_GOVERNED_INVOCATION"


# ── Base Model Configuration ───────────────────────────────────────

class _BaseContract(BaseModel):
    model_config = ConfigDict(extra="forbid", freeze=True)


# ── Core Sub-Policy Contracts ──────────────────────────────────────

class AIToolInputContractV2(_BaseContract):
    json_schema: Dict[str, Any] = Field(..., description="JSON Schema object for arguments validation.")
    max_payload_bytes: int = Field(default=32768, ge=64, le=1048576)
    max_nested_depth: int = Field(default=5, ge=1, le=10)
    requires_idempotency_key: bool = Field(default=False)
    checksum: str = Field(..., min_length=1)


class AIToolOutputContractV2(_BaseContract):
    json_schema: Dict[str, Any] = Field(..., description="JSON Schema object for tool output validation.")
    max_payload_bytes: int = Field(default=131072, ge=64, le=5242880)
    max_collection_items: int = Field(default=200, ge=1, le=5000)
    allowed_data_class: AIToolDataClass = Field(default=AIToolDataClass.TENANT_BUSINESS_DATA)
    redaction_keys: List[str] = Field(default_factory=list)
    checksum: str = Field(..., min_length=1)


class AIToolTimeoutPolicyV2(_BaseContract):
    timeout_seconds: float = Field(default=5.0, ge=0.1, le=60.0)
    hard_deadline_seconds: float = Field(default=10.0, ge=0.2, le=120.0)
    fail_closed: bool = Field(default=True)


class AIToolRetryPolicyV2(_BaseContract):
    mode: AIToolRetryPolicyMode = Field(default=AIToolRetryPolicyMode.SAFE_READ_ONLY)
    max_retries: int = Field(default=2, ge=0, le=5)
    backoff_base_seconds: float = Field(default=0.5, ge=0.1, le=5.0)
    jitter: bool = Field(default=True)


class AIToolRateLimitPolicyV2(_BaseContract):
    requests_per_minute: int = Field(default=100, ge=1, le=10000)
    burst_limit: int = Field(default=20, ge=1, le=2000)
    window_seconds: int = Field(default=60, ge=1, le=3600)


class AIToolCachePolicyV2(_BaseContract):
    cacheable: bool = Field(default=False)
    ttl_seconds: int = Field(default=60, ge=0, le=86400)
    vary_by_tenant: bool = Field(default=True)
    vary_by_permissions: bool = Field(default=True)


class AIToolPermissionPolicyV2(_BaseContract):
    required_permissions: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=lambda: ["ADMIN", "GESTOR", "CONSULTA"])
    requires_system_admin: bool = Field(default=False)


class AIToolDataPolicyV2(_BaseContract):
    input_data_classes: List[AIToolDataClass] = Field(default_factory=lambda: [AIToolDataClass.PUBLIC_METADATA, AIToolDataClass.TENANT_METADATA, AIToolDataClass.TENANT_BUSINESS_DATA])
    output_data_class_ceiling: AIToolDataClass = Field(default=AIToolDataClass.TENANT_BUSINESS_DATA)
    prohibit_secrets: bool = Field(default=True)
    prohibit_raw_sql: bool = Field(default=True)
    allow_llm_exposure: bool = Field(default=True)


class AIToolExecutionPolicyV2(_BaseContract):
    timeout_policy: AIToolTimeoutPolicyV2 = Field(default_factory=AIToolTimeoutPolicyV2)
    retry_policy: AIToolRetryPolicyV2 = Field(default_factory=AIToolRetryPolicyV2)
    rate_limit_policy: AIToolRateLimitPolicyV2 = Field(default_factory=AIToolRateLimitPolicyV2)
    cache_policy: AIToolCachePolicyV2 = Field(default_factory=AIToolCachePolicyV2)
    permission_policy: AIToolPermissionPolicyV2 = Field(default_factory=AIToolPermissionPolicyV2)
    data_policy: AIToolDataPolicyV2 = Field(default_factory=AIToolDataPolicyV2)
    concurrency_limit: int = Field(default=10, ge=1, le=100)
    circuit_failure_threshold: int = Field(default=5, ge=1, le=50)
    circuit_recovery_seconds: int = Field(default=30, ge=1, le=600)


class AIToolDependencyV2(_BaseContract):
    target_tool_id: str = Field(..., min_length=3, max_length=128)
    min_version: str = Field(default="1.0.0")
    max_version: Optional[str] = Field(default=None)
    dependency_type: str = Field(default="REQUIRED")
    checksum: str = Field(..., min_length=1)


# ── Identity & Version Contracts ────────────────────────────────────

class AIToolIdentityV2(_BaseContract):
    tool_id: str = Field(..., min_length=3, max_length=128)
    canonical_name: str = Field(..., min_length=3, max_length=128)
    display_name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., min_length=5, max_length=1024)
    domain: str = Field(default="business_intelligence")
    tool_type: AIToolType = Field(default=AIToolType.DOMAIN_READ)
    capabilities: List[AIToolCapability] = Field(..., min_items=1)
    risk_class: AIToolRiskClass = Field(default=AIToolRiskClass.LOW)
    side_effect: AIToolSideEffect = Field(default=AIToolSideEffect.READ_ONLY)
    network_class: AIToolNetworkClass = Field(default=AIToolNetworkClass.INTERNAL_SERVICE_ONLY)
    data_class: AIToolDataClass = Field(default=AIToolDataClass.TENANT_BUSINESS_DATA)
    owner: str = Field(default="system")
    tenant_id: str = Field(default="system")
    scope: str = Field(default="SYSTEM")
    created_at: str = Field(...)
    checksum: str = Field(..., min_length=1)
    contract_version: str = Field(default=_CONTRACT_VERSION)

    @field_validator("tenant_id", "owner", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v: Any) -> Any:
        if v is not None:
            return str(v)
        return v


class AIToolVersionV2(_BaseContract):
    tool_id: str = Field(..., min_length=3, max_length=128)
    version: str = Field(..., min_length=1, max_length=32)
    adapter_id: str = Field(..., min_length=3, max_length=128)
    input_contract: AIToolInputContractV2 = Field(...)
    output_contract: AIToolOutputContractV2 = Field(...)
    execution_policy: AIToolExecutionPolicyV2 = Field(...)
    dependencies: List[AIToolDependencyV2] = Field(default_factory=list)
    lifecycle: AIToolLifecycle = Field(default=AIToolLifecycle.DRAFT)
    author_id: str = Field(...)
    reviewer_id: Optional[str] = Field(default=None)
    published_by: Optional[str] = Field(default=None)
    effective_from: Optional[str] = Field(default=None)
    effective_to: Optional[str] = Field(default=None)
    lock_version: int = Field(default=1, ge=1)
    checksum: str = Field(..., min_length=1)
    created_at: str = Field(...)
    contract_version: str = Field(default=_CONTRACT_VERSION)


class AIToolDefinitionV2(_BaseContract):
    identity: AIToolIdentityV2 = Field(...)
    active_version: Optional[AIToolVersionV2] = Field(default=None)
    versions: List[AIToolVersionV2] = Field(default_factory=list)
    contract_version: str = Field(default=_CONTRACT_VERSION)


# ── Registry & Snapshot Contracts ───────────────────────────────────

class AIToolRegistrySnapshotV2(_BaseContract):
    snapshot_id: str = Field(..., min_length=3, max_length=128)
    version: str = Field(..., min_length=1, max_length=32)
    status: AIToolSnapshotStatus = Field(default=AIToolSnapshotStatus.READY)
    active_tool_versions: Dict[str, str] = Field(..., description="Mapping of tool_id to active version string.")
    disabled_tool_ids: List[str] = Field(default_factory=list)
    dependency_graph_checksum: str = Field(..., min_length=1)
    created_by: str = Field(...)
    published_by: Optional[str] = Field(default=None)
    created_at: str = Field(...)
    published_at: Optional[str] = Field(default=None)
    previous_snapshot_id: Optional[str] = Field(default=None)
    checksum: str = Field(..., min_length=1)
    contract_version: str = Field(default=_CONTRACT_VERSION)


class AIToolRegistryManifestV2(_BaseContract):
    snapshot: AIToolRegistrySnapshotV2 = Field(...)
    tool_definitions: List[AIToolDefinitionV2] = Field(...)
    total_tools_count: int = Field(..., ge=0)
    manifest_checksum: str = Field(..., min_length=1)
    contract_version: str = Field(default=_CONTRACT_VERSION)


# ── Catalog Contracts (Minimized for LLM / Orchestrator) ───────────

class AIToolCatalogItemV2(_BaseContract):
    tool_id: str = Field(...)
    canonical_name: str = Field(...)
    display_name: str = Field(...)
    description: str = Field(...)
    version: str = Field(...)
    tool_type: AIToolType = Field(...)
    capabilities: List[AIToolCapability] = Field(...)
    risk_class: AIToolRiskClass = Field(...)
    side_effect: AIToolSideEffect = Field(...)
    input_json_schema: Dict[str, Any] = Field(...)


class AIToolCatalogV2(_BaseContract):
    snapshot_version: str = Field(...)
    items: List[AIToolCatalogItemV2] = Field(...)
    catalog_checksum: str = Field(...)
    contract_version: str = Field(default=_CONTRACT_VERSION)


# ── Invocation & Execution Contracts ────────────────────────────────

class AIToolInvocationContextV2(_BaseContract):
    request_id: str = Field(...)
    correlation_id: str = Field(...)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    user_role: str = Field(...)
    user_permissions: List[str] = Field(default_factory=list)
    session_id: str = Field(...)
    locale: str = Field(default="pt_BR")
    timezone: str = Field(default="America/Sao_Paulo")
    reference_time: str = Field(...)
    snapshot_version: str = Field(...)
    tool_id: str = Field(...)
    tool_version: str = Field(...)
    rollout_mode: AIToolRegistryMode = Field(default=AIToolRegistryMode.LEGACY_ONLY)
    idempotency_key: Optional[str] = Field(default=None)
    data_classification_ceiling: AIToolDataClass = Field(default=AIToolDataClass.TENANT_BUSINESS_DATA)
    contract_version: str = Field(default=_CONTRACT_VERSION)

    @field_validator("tenant_id", "user_id", mode="before")
    @classmethod
    def _coerce_uuid_to_str(cls, v: Any) -> Any:
        if v is not None:
            return str(v)
        return v


class AIToolInvocationRequestV2(_BaseContract):
    tool_id: str = Field(..., min_length=3, max_length=128)
    requested_version: Optional[str] = Field(default=None)
    raw_arguments: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None)


class AIToolValidatedArgumentsV2(_BaseContract):
    tool_id: str = Field(...)
    version: str = Field(...)
    validated_args: Dict[str, Any] = Field(...)
    args_checksum: str = Field(...)


class AIToolInvocationErrorV2(_BaseContract):
    error_code: str = Field(...)
    message: str = Field(...)
    details: Dict[str, Any] = Field(default_factory=dict)
    retryable: bool = Field(default=False)


class AIToolInvocationResultV2(_BaseContract):
    success: bool = Field(...)
    data: Optional[Dict[str, Any]] = Field(default=None)
    error: Optional[AIToolInvocationErrorV2] = Field(default=None)
    execution_time_ms: float = Field(..., ge=0.0)
    cache_hit: bool = Field(default=False)
    redacted_keys_count: int = Field(default=0, ge=0)
    output_checksum: str = Field(..., min_length=1)


class AIToolOutputEnvelopeV2(_BaseContract):
    tool_id: str = Field(...)
    tool_version: str = Field(...)
    adapter_id: str = Field(...)
    result: AIToolInvocationResultV2 = Field(...)
    invocation_context_checksum: str = Field(...)
    envelope_checksum: str = Field(...)
    contract_version: str = Field(default=_CONTRACT_VERSION)


# ── Decision & Operations Contracts ─────────────────────────────────

class AIToolAccessDecisionV2(_BaseContract):
    allowed: bool = Field(...)
    decision_code: str = Field(...)
    reason: str = Field(...)
    required_capability: Optional[AIToolCapability] = Field(default=None)


class AIToolCircuitBreakerStateV2(_BaseContract):
    tool_id: str = Field(...)
    adapter_id: str = Field(...)
    state: AIToolCircuitState = Field(default=AIToolCircuitState.CLOSED)
    failure_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    last_failure_at: Optional[str] = Field(default=None)
    last_state_change: str = Field(...)


class AIToolAuditEventV2(_BaseContract):
    event_id: str = Field(...)
    event_type: str = Field(...)
    tenant_id: str = Field(...)
    user_id: str = Field(...)
    tool_id: str = Field(...)
    version: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(...)
    contract_version: str = Field(default=_CONTRACT_VERSION)


class AIToolRegistrationRequestV2(_BaseContract):
    tool_id: str = Field(..., min_length=3, max_length=128)
    canonical_name: str = Field(..., min_length=3, max_length=128)
    display_name: str = Field(..., min_length=3, max_length=128)
    description: str = Field(..., min_length=5, max_length=1024)
    adapter_id: str = Field(..., min_length=3, max_length=128)
    version: str = Field(default="1.0.0")
    domain: str = Field(default="business_intelligence")
    tool_type: AIToolType = Field(default=AIToolType.DOMAIN_READ)
    capabilities: List[AIToolCapability] = Field(..., min_items=1)
    risk_class: AIToolRiskClass = Field(default=AIToolRiskClass.LOW)
    side_effect: AIToolSideEffect = Field(default=AIToolSideEffect.READ_ONLY)
    network_class: AIToolNetworkClass = Field(default=AIToolNetworkClass.INTERNAL_SERVICE_ONLY)
    data_class: AIToolDataClass = Field(default=AIToolDataClass.TENANT_BUSINESS_DATA)
    input_schema: Dict[str, Any] = Field(...)
    output_schema: Dict[str, Any] = Field(...)
    execution_policy: Optional[AIToolExecutionPolicyV2] = Field(default=None)


class AIToolReviewV2(_BaseContract):
    tool_id: str = Field(...)
    version: str = Field(...)
    reviewer_id: str = Field(...)
    approved: bool = Field(...)
    review_notes: str = Field(default="")
    timestamp: str = Field(...)


class AIToolPublicationV2(_BaseContract):
    tool_id: str = Field(...)
    version: str = Field(...)
    published_by: str = Field(...)
    publication_notes: str = Field(default="")
    timestamp: str = Field(...)


class AIToolDeprecationV2(_BaseContract):
    tool_id: str = Field(...)
    version: str = Field(...)
    deprecated_by: str = Field(...)
    reason: str = Field(...)
    replacement_tool_id: Optional[str] = Field(default=None)
    timestamp: str = Field(...)


class AIToolDiffV2(_BaseContract):
    tool_id: str = Field(...)
    from_version: str = Field(...)
    to_version: str = Field(...)
    changes: List[str] = Field(default_factory=list)


class AIToolEvaluationCaseV2(_BaseContract):
    case_id: str = Field(...)
    tool_id: str = Field(...)
    name: str = Field(...)
    description: str = Field(...)
    input_fixture: Dict[str, Any] = Field(...)
    expected_output_fixture: Optional[Dict[str, Any]] = Field(default=None)
    expected_error_code: Optional[str] = Field(default=None)


class AIToolEvaluationResultV2(_BaseContract):
    case_id: str = Field(...)
    tool_id: str = Field(...)
    version: str = Field(...)
    passed: bool = Field(...)
    execution_time_ms: float = Field(...)
    details: str = Field(default="")
    executed_at: str = Field(...)
