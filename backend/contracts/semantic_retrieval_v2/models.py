from __future__ import annotations

import enum
import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


CONTRACT_VERSION = "lumina.semantic-retrieval/1.0"
NORMALIZER_VERSION = "lumina.semantic-normalizer.pt-BR/1.0"
RANKING_POLICY_VERSION = "lumina.semantic-ranking/1.0"
THRESHOLD_POLICY_VERSION = "lumina.semantic-thresholds/1.0"
PROVIDER_VERSION = "lumina.deterministic-feature-hash/1.0"

ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)
]
SafeText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
QueryText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
CanonicalKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}$",
    ),
]
Checksum = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Locale = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
]


class StrictSemanticModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
        str_strip_whitespace=True,
    )

    @field_validator("*")
    @classmethod
    def reject_unsafe_text(cls, value: object) -> object:
        def validate(text: str) -> str:
            if "\x00" in text:
                raise ValueError("null bytes are forbidden")
            if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
                raise ValueError("control characters are forbidden")
            if re.search(
                r"<\s*/?\s*(script|iframe|object|embed|style)\b",
                text,
                re.IGNORECASE,
            ):
                raise ValueError("active HTML is forbidden")
            return text

        if isinstance(value, str):
            return validate(value)
        if isinstance(value, list):
            return [validate(item) if isinstance(item, str) else item for item in value]
        if isinstance(value, tuple):
            return tuple(validate(item) if isinstance(item, str) else item for item in value)
        return value


class SemanticDocumentType(str, enum.Enum):
    BUSINESS_TERM = "BUSINESS_TERM"
    METRIC = "METRIC"
    KPI = "KPI"
    DIMENSION = "DIMENSION"
    ENTITY_TYPE = "ENTITY_TYPE"
    ENTITY_INSTANCE = "ENTITY_INSTANCE"
    BUSINESS_RULE = "BUSINESS_RULE"
    ALIAS = "ALIAS"
    RELATION = "RELATION"
    CALENDAR_POLICY = "CALENDAR_POLICY"
    APPROVED_TRAINING_EXAMPLE = "APPROVED_TRAINING_EXAMPLE"
    SYSTEM_CONCEPT = "SYSTEM_CONCEPT"


class SemanticEntityType(str, enum.Enum):
    METRIC = "METRIC"
    DIMENSION = "DIMENSION"
    BUSINESS_CONCEPT = "BUSINESS_CONCEPT"
    BRANCH = "BRANCH"
    PRODUCT = "PRODUCT"
    PRODUCT_GROUP = "PRODUCT_GROUP"
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    SELLER = "SELLER"
    REGION = "REGION"
    CITY = "CITY"
    STATE = "STATE"
    COST_CENTER = "COST_CENTER"
    WAREHOUSE = "WAREHOUSE"
    PAYMENT_METHOD = "PAYMENT_METHOD"
    RECEIVABLE_STATUS = "RECEIVABLE_STATUS"
    STOCK_LOCATION = "STOCK_LOCATION"
    UNKNOWN = "UNKNOWN"


class SemanticDataClassification(str, enum.Enum):
    PUBLIC_BUSINESS_METADATA = "PUBLIC_BUSINESS_METADATA"
    TENANT_BUSINESS_METADATA = "TENANT_BUSINESS_METADATA"
    RESTRICTED_BUSINESS_METADATA = "RESTRICTED_BUSINESS_METADATA"
    PERSONAL_DATA = "PERSONAL_DATA"
    SENSITIVE_PERSONAL_DATA = "SENSITIVE_PERSONAL_DATA"
    FORBIDDEN = "FORBIDDEN"


class SemanticSourceType(str, enum.Enum):
    ENTERPRISE_KNOWLEDGE = "ENTERPRISE_KNOWLEDGE"
    METRIC_REGISTRY = "METRIC_REGISTRY"
    TECHNICAL_CATALOG = "TECHNICAL_CATALOG"
    ANALYTICAL_ENTITY = "ANALYTICAL_ENTITY"
    APPROVED_TRAINING_EXAMPLE = "APPROVED_TRAINING_EXAMPLE"
    SYSTEM_CURATED = "SYSTEM_CURATED"


class SemanticIndexLifecycle(str, enum.Enum):
    DRAFT = "DRAFT"
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class SemanticDocumentLifecycle(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    TOMBSTONED = "TOMBSTONED"


class SemanticRepresentationType(str, enum.Enum):
    LEXICAL = "LEXICAL"
    DETERMINISTIC_FEATURE_HASH = "DETERMINISTIC_FEATURE_HASH"


class SemanticRetrievalChannel(str, enum.Enum):
    EXACT_CANONICAL = "EXACT_CANONICAL"
    EXACT_ALIAS = "EXACT_ALIAS"
    EXACT_LABEL = "EXACT_LABEL"
    NORMALIZED_EXACT = "NORMALIZED_EXACT"
    PREFIX = "PREFIX"
    TOKEN_OVERLAP = "TOKEN_OVERLAP"
    CHARACTER_SIMILARITY = "CHARACTER_SIMILARITY"
    RELATION_EXPANSION = "RELATION_EXPANSION"
    VECTOR_SIMILARITY = "VECTOR_SIMILARITY"
    CONTEXT_COMPATIBILITY = "CONTEXT_COMPATIBILITY"
    DOMAIN_COMPATIBILITY = "DOMAIN_COMPATIBILITY"
    TYPE_COMPATIBILITY = "TYPE_COMPATIBILITY"
    PROFILE_TIE_BREAKER = "PROFILE_TIE_BREAKER"
    LEGACY_FALLBACK = "LEGACY_FALLBACK"


class EntityResolutionDecisionType(str, enum.Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    BLOCKED = "BLOCKED"
    NOT_FOUND = "NOT_FOUND"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    STALE_INDEX = "STALE_INDEX"
    PERMISSION_DENIED = "PERMISSION_DENIED"


class SemanticRolloutMode(str, enum.Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW = "SHADOW"
    HYBRID_READ = "HYBRID_READ"
    V2_AUTHORITATIVE = "V2_AUTHORITATIVE"


class SemanticPermission(str, enum.Enum):
    SEARCH = "semantic:search"
    RESOLVE = "semantic:resolve"
    READ_PUBLIC_CANDIDATE = "semantic:read_public_candidate"
    INSPECT_SCORES = "semantic:inspect_scores"
    MANAGE_INDEX = "semantic:manage_index"
    BUILD_INDEX = "semantic:build_index"
    VALIDATE_INDEX = "semantic:validate_index"
    PUBLISH_INDEX = "semantic:publish_index"
    ROLLBACK_INDEX = "semantic:rollback_index"
    DEPRECATE_INDEX = "semantic:deprecate_index"
    RUN_EVALUATION = "semantic:run_evaluation"
    AUDIT_READ = "semantic:audit_read"
    READ_RESTRICTED_ENTITY = "semantic:read_restricted_entity"


class SemanticAuditEventType(str, enum.Enum):
    INDEX_DEFINITION_CREATED = "INDEX_DEFINITION_CREATED"
    INDEX_DEFINITION_UPDATED = "INDEX_DEFINITION_UPDATED"
    INDEX_BUILD_STARTED = "INDEX_BUILD_STARTED"
    INDEX_SOURCE_LOADED = "INDEX_SOURCE_LOADED"
    INDEX_DOCUMENT_CREATED = "INDEX_DOCUMENT_CREATED"
    INDEX_BUILD_VALIDATED = "INDEX_BUILD_VALIDATED"
    INDEX_BUILD_FAILED = "INDEX_BUILD_FAILED"
    INDEX_VERSION_READY = "INDEX_VERSION_READY"
    INDEX_VERSION_PUBLISHED = "INDEX_VERSION_PUBLISHED"
    INDEX_VERSION_ROLLED_BACK = "INDEX_VERSION_ROLLED_BACK"
    INDEX_VERSION_DEPRECATED = "INDEX_VERSION_DEPRECATED"
    INDEX_SOURCE_STALE = "INDEX_SOURCE_STALE"
    SEMANTIC_SEARCH_EXECUTED = "SEMANTIC_SEARCH_EXECUTED"
    ENTITY_RESOLUTION_SUCCEEDED = "ENTITY_RESOLUTION_SUCCEEDED"
    ENTITY_RESOLUTION_AMBIGUOUS = "ENTITY_RESOLUTION_AMBIGUOUS"
    ENTITY_RESOLUTION_UNRESOLVED = "ENTITY_RESOLUTION_UNRESOLVED"
    ENTITY_RESOLUTION_BLOCKED = "ENTITY_RESOLUTION_BLOCKED"
    CLARIFICATION_CREATED = "CLARIFICATION_CREATED"
    CLARIFICATION_RESOLVED = "CLARIFICATION_RESOLVED"
    EVALUATION_EXECUTED = "EVALUATION_EXECUTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    FORBIDDEN_CONTENT_BLOCKED = "FORBIDDEN_CONTENT_BLOCKED"


class SemanticIndexSourceV2(StrictSemanticModel):
    source_type: SemanticSourceType
    source_id: CanonicalKey
    source_version: ShortText
    source_checksum: Checksum
    tenant_scoped: bool
    effective_at: datetime | None = None
    watermark: ShortText | None = None
    stale: bool = False


class EntityIndexPolicyV2(StrictSemanticModel):
    entity_type: SemanticEntityType
    enabled: bool
    classification: SemanticDataClassification
    required_permission: SemanticPermission | None = None
    maximum_documents: int = Field(default=10_000, ge=1, le=1_000_000)
    allow_vector_representation: bool = False
    allowed_source_ids: tuple[CanonicalKey, ...] = ()
    allowed_label_fields: tuple[CanonicalKey, ...] = ()
    allowed_code_fields: tuple[CanonicalKey, ...] = ()

    @model_validator(mode="after")
    def validate_sensitive_policy(self) -> "EntityIndexPolicyV2":
        if self.classification in {
            SemanticDataClassification.SENSITIVE_PERSONAL_DATA,
            SemanticDataClassification.FORBIDDEN,
        } and self.enabled:
            raise ValueError("sensitive or forbidden entity policy cannot be enabled")
        if (
            self.classification
            in {
                SemanticDataClassification.RESTRICTED_BUSINESS_METADATA,
                SemanticDataClassification.PERSONAL_DATA,
            }
            and self.required_permission is None
        ):
            raise ValueError("restricted or personal entity policy requires permission")
        return self


class SemanticRankingWeightV2(StrictSemanticModel):
    channel: SemanticRetrievalChannel
    weight: float = Field(ge=-1.0, le=1.0)


class SemanticRankingPolicyV2(StrictSemanticModel):
    policy_version: str = RANKING_POLICY_VERSION
    weights: tuple[SemanticRankingWeightV2, ...]
    deprecated_penalty: float = Field(default=0.25, ge=0.0, le=1.0)
    stale_penalty: float = Field(default=0.15, ge=0.0, le=1.0)
    profile_tie_breaker_cap: float = Field(default=0.02, ge=0.0, le=0.05)
    score_precision: int = Field(default=6, ge=2, le=9)
    checksum: Checksum

    @model_validator(mode="after")
    def validate_weights(self) -> "SemanticRankingPolicyV2":
        channels = [item.channel for item in self.weights]
        if len(channels) != len(set(channels)):
            raise ValueError("ranking channels must be unique")
        return self


class SemanticConfidenceBandV2(StrictSemanticModel):
    label: Literal["LOW", "MEDIUM", "HIGH", "EXACT"]
    minimum: float = Field(ge=0.0, le=1.0)


class SemanticThresholdPolicyV2(StrictSemanticModel):
    policy_version: str = THRESHOLD_POLICY_VERSION
    minimum_retrieval_score: float = Field(default=0.30, ge=0.0, le=1.0)
    minimum_automatic_resolution_score: float = Field(
        default=0.72, ge=0.0, le=1.0
    )
    ambiguity_margin: float = Field(default=0.08, ge=0.0, le=1.0)
    maximum_candidates: int = Field(default=10, ge=1, le=50)
    maximum_relation_expansion: int = Field(default=10, ge=0, le=100)
    maximum_lexical_candidates: int = Field(default=50, ge=1, le=500)
    maximum_vector_candidates: int = Field(default=20, ge=0, le=100)
    maximum_total_candidates: int = Field(default=100, ge=1, le=1000)
    stale_index_tolerance_seconds: int = Field(default=3600, ge=0, le=604800)
    confidence_bands: tuple[SemanticConfidenceBandV2, ...]
    checksum: Checksum


class SemanticIndexDefinitionV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    index_id: uuid.UUID
    tenant_id: uuid.UUID
    name: ShortText
    locale: Locale = "pt-BR"
    document_types: tuple[SemanticDocumentType, ...]
    entity_policies: tuple[EntityIndexPolicyV2, ...]
    source_policies: tuple[SemanticSourceType, ...]
    allowed_classifications: tuple[SemanticDataClassification, ...]
    representation_provider: SemanticRepresentationType
    representation_version: str = PROVIDER_VERSION
    ranking_policy: SemanticRankingPolicyV2
    threshold_policy: SemanticThresholdPolicyV2
    status: Literal["ACTIVE", "DISABLED", "ARCHIVED"] = "ACTIVE"
    owner_user_id: uuid.UUID
    lock_version: int = Field(default=0, ge=0)
    active_version_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class SemanticSourceManifestV2(StrictSemanticModel):
    sources: tuple[SemanticIndexSourceV2, ...]
    checksum: Checksum


class SemanticIndexVersionV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    version_id: uuid.UUID
    tenant_id: uuid.UUID
    index_id: uuid.UUID
    version: int = Field(ge=1)
    lifecycle: SemanticIndexLifecycle
    source_manifest: SemanticSourceManifestV2
    document_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)
    alias_count: int = Field(default=0, ge=0)
    relation_count: int = Field(default=0, ge=0)
    representation_version: str = PROVIDER_VERSION
    build_mode: Literal["FULL", "INCREMENTAL"] = "FULL"
    watermark: ShortText | None = None
    build_started_at: datetime
    build_completed_at: datetime | None = None
    checksum: Checksum | None = None
    created_by: uuid.UUID
    reviewed_by: uuid.UUID | None = None
    published_by: uuid.UUID | None = None
    published_at: datetime | None = None
    superseded_version_id: uuid.UUID | None = None
    failure_summary: ShortText | None = None
    lock_version: int = Field(default=0, ge=0)


class EntityCanonicalReferenceV2(StrictSemanticModel):
    canonical_id: CanonicalKey
    entity_type: SemanticEntityType
    display_label: ShortText
    tenant_id: uuid.UUID
    domain: ShortText
    source_type: SemanticSourceType
    source_id: CanonicalKey
    source_version: ShortText
    permission_requirement: SemanticPermission | None = None


class SemanticEffectivePeriodV2(StrictSemanticModel):
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "SemanticEffectivePeriodV2":
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must follow valid_from")
        return self


class SemanticRelationReferenceV2(StrictSemanticModel):
    relation_type: Literal[
        "SYNONYM_OF",
        "BROADER_THAN",
        "NARROWER_THAN",
        "RELATED_TO",
        "ALLOWED_DIMENSION",
        "INCOMPATIBLE_WITH",
    ]
    target_canonical_id: CanonicalKey


class SemanticDocumentProvenanceV2(StrictSemanticModel):
    source_type: SemanticSourceType
    source_id: CanonicalKey
    source_version: ShortText
    source_checksum: Checksum
    canonical_reference: EntityCanonicalReferenceV2
    indexed_by: uuid.UUID
    indexed_at: datetime


class BusinessSemanticContentV2(StrictSemanticModel):
    kind: Literal["BUSINESS"] = "BUSINESS"
    definition: SafeText
    unit: ShortText | None = None
    allowed_dimensions: tuple[CanonicalKey, ...] = ()


class EntitySemanticContentV2(StrictSemanticModel):
    kind: Literal["ENTITY"] = "ENTITY"
    code: ShortText | None = None
    business_label: ShortText


class AliasSemanticContentV2(StrictSemanticModel):
    kind: Literal["ALIAS"] = "ALIAS"
    alias: ShortText
    target_canonical_id: CanonicalKey


class RelationSemanticContentV2(StrictSemanticModel):
    kind: Literal["RELATION"] = "RELATION"
    relation_type: ShortText
    source_canonical_id: CanonicalKey
    target_canonical_id: CanonicalKey


class TrainingExampleSemanticContentV2(StrictSemanticModel):
    kind: Literal["APPROVED_EXAMPLE"] = "APPROVED_EXAMPLE"
    normalized_mention: ShortText
    expected_canonical_id: CanonicalKey
    evaluation_only: bool = True


class SystemSemanticContentV2(StrictSemanticModel):
    kind: Literal["SYSTEM"] = "SYSTEM"
    definition: SafeText


SemanticDocumentContentV2 = Annotated[
    BusinessSemanticContentV2
    | EntitySemanticContentV2
    | AliasSemanticContentV2
    | RelationSemanticContentV2
    | TrainingExampleSemanticContentV2
    | SystemSemanticContentV2,
    Field(discriminator="kind"),
]


class LexicalRepresentationV2(StrictSemanticModel):
    kind: Literal["LEXICAL"] = "LEXICAL"
    normalized_label: ShortText
    normalized_aliases: tuple[ShortText, ...]
    tokens: tuple[ShortText, ...]
    character_ngrams: tuple[ShortText, ...]
    normalizer_version: str = NORMALIZER_VERSION
    checksum: Checksum


class VectorRepresentationV2(StrictSemanticModel):
    kind: Literal["DETERMINISTIC_FEATURE_HASH"] = "DETERMINISTIC_FEATURE_HASH"
    provider_type: Literal["DETERMINISTIC_FEATURE_HASH"] = "DETERMINISTIC_FEATURE_HASH"
    provider_version: str = PROVIDER_VERSION
    dimension: int = Field(ge=32, le=4096)
    l2_normalized: bool = True
    deterministic: bool = True
    network_required: bool = False
    vector: tuple[float, ...]
    checksum: Checksum

    @model_validator(mode="after")
    def validate_dimension(self) -> "VectorRepresentationV2":
        if len(self.vector) != self.dimension:
            raise ValueError("vector length must match dimension")
        return self


SemanticRepresentationV2 = Annotated[
    LexicalRepresentationV2 | VectorRepresentationV2,
    Field(discriminator="kind"),
]


class SemanticDocumentV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    document_id: uuid.UUID
    tenant_id: uuid.UUID
    index_version_id: uuid.UUID
    document_type: SemanticDocumentType
    canonical_reference: EntityCanonicalReferenceV2
    canonical_key: CanonicalKey
    display_label: ShortText
    normalized_label: ShortText
    locale: Locale
    domain: ShortText
    entity_type: SemanticEntityType
    published_aliases: tuple[ShortText, ...] = ()
    description: SafeText | None = None
    relations: tuple[SemanticRelationReferenceV2, ...] = ()
    provenance: SemanticDocumentProvenanceV2
    lifecycle: SemanticDocumentLifecycle
    effective_period: SemanticEffectivePeriodV2
    classification: SemanticDataClassification
    permission_requirement: SemanticPermission | None = None
    content: SemanticDocumentContentV2
    representations: tuple[SemanticRepresentationV2, ...]
    representation_version: str = PROVIDER_VERSION
    created_at: datetime
    checksum: Checksum

    @model_validator(mode="after")
    def validate_scope(self) -> "SemanticDocumentV2":
        if self.canonical_reference.tenant_id != self.tenant_id:
            raise ValueError("canonical reference tenant mismatch")
        if self.classification in {
            SemanticDataClassification.SENSITIVE_PERSONAL_DATA,
            SemanticDataClassification.FORBIDDEN,
        }:
            raise ValueError("sensitive or forbidden documents cannot be indexed")
        return self


class SemanticSearchContextV2(StrictSemanticModel):
    expected_entity_types: tuple[SemanticEntityType, ...] = ()
    expected_domain: ShortText | None = None
    active_canonical_ids: tuple[CanonicalKey, ...] = ()
    profile_favorite_ids: tuple[CanonicalKey, ...] = ()
    permission_fingerprint: Checksum
    profile_tie_breaker_enabled: bool = False


class SemanticSearchRequestV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    query: QueryText
    locale: Locale = "pt-BR"
    index_id: uuid.UUID | None = None
    context: SemanticSearchContextV2
    top_k: int = Field(default=10, ge=1, le=20)
    include_public_explanation: bool = True


class SemanticChannelScoreV2(StrictSemanticModel):
    channel: SemanticRetrievalChannel
    raw_score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=-1.0, le=1.0)
    contribution: float = Field(ge=-1.0, le=1.0)
    reason_code: ShortText
    evidence_reference: ShortText | None = None
    penalty: bool = False
    policy_version: str = RANKING_POLICY_VERSION


class SemanticScoreBreakdownV2(StrictSemanticModel):
    channels: tuple[SemanticChannelScoreV2, ...]
    positive_score: float = Field(ge=0.0)
    penalties: float = Field(ge=0.0)
    final_score: float = Field(ge=0.0, le=1.0)
    policy_version: str = RANKING_POLICY_VERSION


class SemanticSearchCandidateV2(StrictSemanticModel):
    document_id: uuid.UUID
    canonical_reference: EntityCanonicalReferenceV2
    public_label: ShortText
    entity_type: SemanticEntityType
    domain: ShortText
    score: float = Field(ge=0.0, le=1.0)
    confidence_band: Literal["LOW", "MEDIUM", "HIGH", "EXACT"]
    matched_channels: tuple[SemanticRetrievalChannel, ...]
    breakdown: SemanticScoreBreakdownV2
    index_version_id: uuid.UUID
    allowed: bool = True
    warnings: tuple[ShortText, ...] = ()


class SemanticAmbiguityV2(StrictSemanticModel):
    reason_code: ShortText
    top_score: float = Field(ge=0.0, le=1.0)
    runner_up_score: float = Field(ge=0.0, le=1.0)
    margin: float = Field(ge=0.0, le=1.0)
    required_margin: float = Field(ge=0.0, le=1.0)
    candidate_ids: tuple[uuid.UUID, ...]


class SemanticSearchResultV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    decision: EntityResolutionDecisionType
    normalized_query: QueryText
    candidates: tuple[SemanticSearchCandidateV2, ...]
    selected: SemanticSearchCandidateV2 | None = None
    ambiguity: SemanticAmbiguityV2 | None = None
    public_explanation: ShortText
    index_version_id: uuid.UUID | None = None
    ranking_policy_version: str = RANKING_POLICY_VERSION
    threshold_policy_version: str = THRESHOLD_POLICY_VERSION
    query_fingerprint: Checksum
    warnings: tuple[ShortText, ...] = ()
    cache_hit: bool = False


class EntityMentionV2(StrictSemanticModel):
    mention_id: uuid.UUID
    text: ShortText
    normalized_text: ShortText
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    expected_entity_type: SemanticEntityType = SemanticEntityType.UNKNOWN
    candidate_field: CanonicalKey | None = None
    source: Literal["EXPLICIT", "INTENT", "FILTER_FIELD", "FILTER_VALUE", "CONTEXT"]
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_span(self) -> "EntityMentionV2":
        if self.end <= self.start:
            raise ValueError("mention end must follow start")
        return self


class EntityResolutionContextV2(StrictSemanticModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID | None = None
    expected_entity_types: tuple[SemanticEntityType, ...] = ()
    domain: ShortText | None = None
    active_canonical_ids: tuple[CanonicalKey, ...] = ()
    removed_canonical_ids: tuple[CanonicalKey, ...] = ()
    profile_favorite_ids: tuple[CanonicalKey, ...] = ()
    permission_fingerprint: Checksum
    profile_tie_breaker_enabled: bool = False


class EntityResolutionRequestV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    mentions: tuple[EntityMentionV2, ...]
    context: EntityResolutionContextV2
    index_id: uuid.UUID | None = None


class EntityResolutionCandidateV2(StrictSemanticModel):
    mention_id: uuid.UUID
    candidate: SemanticSearchCandidateV2
    type_compatible: bool
    domain_compatible: bool
    permission_allowed: bool


class EntityResolutionDecisionV2(StrictSemanticModel):
    mention_id: uuid.UUID
    decision: EntityResolutionDecisionType
    reason_code: ShortText
    candidate_count: int = Field(ge=0)
    selected_candidate: SemanticSearchCandidateV2 | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    margin: float | None = Field(default=None, ge=0.0, le=1.0)
    index_version_id: uuid.UUID | None = None
    policy_version: str = RANKING_POLICY_VERSION
    warnings: tuple[ShortText, ...] = ()


class EntityResolutionPatchOperationV2(StrictSemanticModel):
    operation: Literal[
        "SET_CANONICAL_METRIC",
        "SET_CANONICAL_DIMENSION",
        "SET_CANONICAL_ENTITY",
        "SET_CANONICAL_FILTER_FIELD",
        "SET_CANONICAL_FILTER_VALUE",
        "ATTACH_PROVENANCE",
        "CREATE_CLARIFICATION",
        "MARK_UNRESOLVED",
    ]
    mention_id: uuid.UUID
    canonical_reference: EntityCanonicalReferenceV2 | None = None
    reason_code: ShortText


class EntityResolutionPatchV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    operations: tuple[EntityResolutionPatchOperationV2, ...]
    checksum: Checksum


class SemanticClarificationOptionV2(StrictSemanticModel):
    option_token: str = Field(min_length=32, max_length=512)
    public_label: ShortText
    entity_type: SemanticEntityType
    domain: ShortText
    provenance_summary: ShortText


class SemanticClarificationV2(StrictSemanticModel):
    clarification_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    mention_id: uuid.UUID
    question: ShortText
    options: tuple[SemanticClarificationOptionV2, ...]
    expires_at: datetime


class EntityResolutionResultV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    readiness: Literal["READY", "CLARIFICATION_REQUIRED", "BLOCKED"]
    decisions: tuple[EntityResolutionDecisionV2, ...]
    resolved_references: tuple[EntityCanonicalReferenceV2, ...]
    ambiguities: tuple[SemanticAmbiguityV2, ...]
    unresolved_mentions: tuple[uuid.UUID, ...]
    patch: EntityResolutionPatchV2
    clarification: SemanticClarificationV2 | None = None
    index_version_id: uuid.UUID | None = None
    provenance_checksum: Checksum


class IndexBuildRequestV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    index_id: uuid.UUID
    expected_definition_lock_version: int = Field(ge=0)
    build_mode: Literal["FULL", "INCREMENTAL"] = "FULL"
    idempotency_key: str = Field(min_length=8, max_length=128)


class IndexBuildResultV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    version: SemanticIndexVersionV2
    validation_passed: bool
    blocked_document_count: int = Field(ge=0)
    warnings: tuple[ShortText, ...] = ()


class IndexPublicationV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    publication_id: uuid.UUID
    tenant_id: uuid.UUID
    index_id: uuid.UUID
    version_id: uuid.UUID
    previous_version_id: uuid.UUID | None = None
    expected_definition_lock_version: int = Field(ge=0)
    published_by: uuid.UUID
    published_at: datetime
    checksum: Checksum


class IndexRollbackV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    index_id: uuid.UUID
    target_version_id: uuid.UUID
    expected_definition_lock_version: int = Field(ge=0)
    reason: ShortText


class IndexDiffCountV2(StrictSemanticModel):
    category: Literal["DOCUMENT", "ALIAS", "RELATION", "ENTITY", "SOURCE"]
    added: int = Field(ge=0)
    changed: int = Field(ge=0)
    removed: int = Field(ge=0)


class IndexDiffV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    tenant_id: uuid.UUID
    index_id: uuid.UUID
    from_version_id: uuid.UUID
    to_version_id: uuid.UUID
    counts: tuple[IndexDiffCountV2, ...]
    checksum: Checksum


class IndexAuditEventV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    event_id: uuid.UUID
    tenant_id: uuid.UUID
    index_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID
    event_type: SemanticAuditEventType
    reason_code: ShortText
    structural_fingerprint: Checksum
    created_at: datetime


class SemanticAccessDecisionV2(StrictSemanticModel):
    allowed: bool
    permission: SemanticPermission
    reason_code: ShortText
    permission_fingerprint: Checksum


class SemanticCacheKeyV2(StrictSemanticModel):
    tenant_id: uuid.UUID
    user_permission_fingerprint: Checksum
    index_id: uuid.UUID
    index_version_id: uuid.UUID
    ranking_policy_version: str
    threshold_policy_version: str
    locale: Locale
    normalized_query_fingerprint: Checksum
    expected_entity_types: tuple[SemanticEntityType, ...]
    domain_fingerprint: Checksum
    context_fingerprint: Checksum
    profile_fingerprint: Checksum
    top_k: int = Field(ge=1, le=20)
    checksum: Checksum


class SemanticEvaluationCaseV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    case_id: CanonicalKey
    tenant_id: uuid.UUID
    normalized_query: ShortText
    expected_decision: EntityResolutionDecisionType
    expected_canonical_ids: tuple[CanonicalKey, ...]
    expected_entity_types: tuple[SemanticEntityType, ...]
    required_channels: tuple[SemanticRetrievalChannel, ...] = ()
    forbidden_canonical_ids: tuple[CanonicalKey, ...] = ()
    corpus_version: ShortText


class SemanticEvaluationMetricV2(StrictSemanticModel):
    name: Literal[
        "TOP_1_ACCURACY",
        "TOP_K_RECALL",
        "AMBIGUITY_PRECISION",
        "UNRESOLVED_PRECISION",
        "FORBIDDEN_LEAKAGE",
        "CROSS_TENANT_LEAKAGE",
        "EXACT_MATCH_PRESERVATION",
        "ALIAS_RESOLUTION",
        "DETERMINISTIC_REPEATABILITY",
        "LATENCY_MS",
    ]
    value: float = Field(ge=0.0)


class SemanticEvaluationResultV2(StrictSemanticModel):
    schema_version: str = CONTRACT_VERSION
    evaluation_id: uuid.UUID
    tenant_id: uuid.UUID
    index_version_id: uuid.UUID
    corpus_version: ShortText
    case_count: int = Field(ge=1)
    passed: bool
    metrics: tuple[SemanticEvaluationMetricV2, ...]
    checksum: Checksum
    executed_at: datetime
