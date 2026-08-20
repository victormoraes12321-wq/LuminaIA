from __future__ import annotations

import enum
import re
import uuid
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)


CONTRACT_VERSION = "lumina.enterprise-knowledge/1.0"
SafeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
CanonicalKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        pattern=r"^[a-z0-9][a-z0-9_.-]{1,127}$",
    ),
]
Locale = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")]


class StrictKnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("*")
    @classmethod
    def reject_unsafe_text(cls, value: object) -> object:
        def validate_text(text: str) -> str:
            if "\x00" in text:
                raise ValueError("null bytes are forbidden")
            if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
                raise ValueError("control characters are forbidden")
            if re.search(r"<\s*/?\s*(script|iframe|object|embed|style)\b", text, re.IGNORECASE):
                raise ValueError("active HTML is forbidden")
            return text

        if isinstance(value, str):
            return validate_text(value)
        if isinstance(value, list):
            return [validate_text(item) if isinstance(item, str) else item for item in value]
        return value


class KnowledgeAssetType(str, enum.Enum):
    BUSINESS_TERM = "BUSINESS_TERM"
    METRIC = "METRIC"
    KPI = "KPI"
    DIMENSION = "DIMENSION"
    ENTITY = "ENTITY"
    BUSINESS_RULE = "BUSINESS_RULE"
    ALIAS_SET = "ALIAS_SET"
    CALENDAR_POLICY = "CALENDAR_POLICY"
    DATA_QUALITY_POLICY = "DATA_QUALITY_POLICY"
    SEMANTIC_RELATION = "SEMANTIC_RELATION"


class KnowledgeLifecycle(str, enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class KnowledgeAssetStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class KnowledgeApprovalDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class KnowledgePermission(str, enum.Enum):
    READ = "knowledge:read"
    CREATE = "knowledge:create"
    EDIT = "knowledge:edit"
    SUBMIT = "knowledge:submit"
    REVIEW = "knowledge:review"
    APPROVE = "knowledge:approve"
    PUBLISH = "knowledge:publish"
    REJECT = "knowledge:reject"
    DEPRECATE = "knowledge:deprecate"
    ARCHIVE = "knowledge:archive"
    ROLLBACK = "knowledge:rollback"
    TRANSFER_OWNERSHIP = "knowledge:transfer_ownership"
    IMPORT = "knowledge:import"
    EXPORT = "knowledge:export"
    AUDIT_READ = "knowledge:audit_read"


class KnowledgeRelationType(str, enum.Enum):
    SYNONYM_OF = "SYNONYM_OF"
    BROADER_THAN = "BROADER_THAN"
    NARROWER_THAN = "NARROWER_THAN"
    RELATED_TO = "RELATED_TO"
    CALCULATED_FROM = "CALCULATED_FROM"
    ALLOWED_DIMENSION = "ALLOWED_DIMENSION"
    INCOMPATIBLE_WITH = "INCOMPATIBLE_WITH"
    OWNED_BY = "OWNED_BY"
    SUPERSEDES = "SUPERSEDES"
    DEPENDS_ON = "DEPENDS_ON"


class KnowledgeMatchType(str, enum.Enum):
    CANONICAL_EXACT = "CANONICAL_EXACT"
    ALIAS_EXACT = "ALIAS_EXACT"
    DISPLAY_EXACT = "DISPLAY_EXACT"
    ALIAS_PREFIX = "ALIAS_PREFIX"
    DISPLAY_PREFIX = "DISPLAY_PREFIX"
    TOKEN_OVERLAP = "TOKEN_OVERLAP"
    DESCRIPTION = "DESCRIPTION"


class KnowledgeBindingStatus(str, enum.Enum):
    VALID = "VALID"
    DESCRIPTION_ONLY = "DESCRIPTION_ONLY"
    CONFLICT = "CONFLICT"
    MISSING_REGISTRY_ENTRY = "MISSING_REGISTRY_ENTRY"
    DEPRECATED = "DEPRECATED"
    BLOCKED = "BLOCKED"


class KnowledgeRolloutMode(str, enum.Enum):
    LEGACY_ONLY = "LEGACY_ONLY"
    SHADOW_READ = "SHADOW_READ"
    V2_READ = "V2_READ"
    V2_READ_WRITE = "V2_READ_WRITE"


class KnowledgeExportFormat(str, enum.Enum):
    JSON = "JSON"
    CSV = "CSV"


class KnowledgeAuditEventType(str, enum.Enum):
    ASSET_CREATED = "ASSET_CREATED"
    DRAFT_CREATED = "DRAFT_CREATED"
    DRAFT_UPDATED = "DRAFT_UPDATED"
    REVIEW_SUBMITTED = "REVIEW_SUBMITTED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    VERSION_PUBLISHED = "VERSION_PUBLISHED"
    VERSION_DEPRECATED = "VERSION_DEPRECATED"
    ASSET_ARCHIVED = "ASSET_ARCHIVED"
    ROLLBACK_CREATED = "ROLLBACK_CREATED"
    OWNERSHIP_TRANSFERRED = "OWNERSHIP_TRANSFERRED"
    IMPORT_DRY_RUN = "IMPORT_DRY_RUN"
    IMPORT_COMPLETED = "IMPORT_COMPLETED"
    EXPORT_COMPLETED = "EXPORT_COMPLETED"
    ACCESS_DENIED = "ACCESS_DENIED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    BINDING_CONFLICT = "BINDING_CONFLICT"


class KnowledgeSourceReferenceV2(StrictKnowledgeModel):
    reference_type: Literal["POLICY", "SYSTEM", "DOCUMENT", "CATALOG", "OWNER_ATTESTATION"]
    title: ShortText
    authority: ShortText
    reference_uri: str | None = Field(default=None, max_length=1000)
    reference_version: str | None = Field(default=None, max_length=128)
    verified_at: datetime | None = None

    @field_validator("reference_uri")
    @classmethod
    def validate_uri(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "urn"}:
            raise ValueError("only https or urn references are allowed")
        if parsed.username or parsed.password:
            raise ValueError("credentials in references are forbidden")
        return value


class KnowledgeOwnershipV2(StrictKnowledgeModel):
    owner_user_id: uuid.UUID
    steward_label: ShortText
    accountable_area: ShortText
    transferred_at: datetime | None = None


class BusinessTermContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.BUSINESS_TERM]
    canonical_name: CanonicalKey
    display_name: ShortText
    definition: SafeText
    domain: ShortText
    short_description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    full_description: SafeText
    allowed_examples: list[SafeText] = Field(default_factory=list, max_length=30)
    incorrect_examples: list[SafeText] = Field(default_factory=list, max_length=30)
    aliases: list[ShortText] = Field(default_factory=list, max_length=100)
    related_terms: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    source_references: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)
    locale: Locale = "pt-BR"
    tags: list[ShortText] = Field(default_factory=list, max_length=30)


class MetricKnowledgeContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.METRIC, KnowledgeAssetType.KPI]
    canonical_metric_id: CanonicalKey
    display_name: ShortText
    definition: SafeText
    purpose: SafeText
    unit: ShortText
    display_format: ShortText
    aggregation_semantics: ShortText
    inclusions: list[SafeText] = Field(default_factory=list, max_length=50)
    exclusions: list[SafeText] = Field(default_factory=list, max_length=50)
    allowed_dimensions: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    incompatible_dimensions: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    grain: ShortText
    frequency: ShortText
    authoritative_source: ShortText
    formula_reference: ShortText
    formula_fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    caveats: list[SafeText] = Field(default_factory=list, max_length=50)
    aliases: list[ShortText] = Field(default_factory=list, max_length=100)
    source_references: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)


class DimensionKnowledgeContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.DIMENSION]
    canonical_dimension_id: CanonicalKey
    display_name: ShortText
    definition: SafeText
    entity_type: ShortText
    cardinality_class: Literal["LOW", "MEDIUM", "HIGH", "UNBOUNDED"]
    hierarchy: list[CanonicalKey] = Field(default_factory=list, max_length=30)
    parent_dimension: CanonicalKey | None = None
    allowed_metrics: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    incompatible_metrics: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    aliases: list[ShortText] = Field(default_factory=list, max_length=100)
    source_references: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)


class EntityKnowledgeContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.ENTITY]
    canonical_entity_id: CanonicalKey
    display_name: ShortText
    definition: SafeText
    business_identity: SafeText
    attributes: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    relationships: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    allowed_metrics: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    aliases: list[ShortText] = Field(default_factory=list, max_length=100)
    source_references: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)


class BusinessRuleContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.BUSINESS_RULE]
    display_name: ShortText
    statement: SafeText
    rationale: SafeText
    scope: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    inclusions: list[SafeText] = Field(default_factory=list, max_length=50)
    exclusions: list[SafeText] = Field(default_factory=list, max_length=50)
    exceptions: list[SafeText] = Field(default_factory=list, max_length=50)
    source_references: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)


class AliasSetContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.ALIAS_SET]
    display_name: ShortText
    canonical_target_key: CanonicalKey
    aliases: list[ShortText] = Field(min_length=1, max_length=100)
    locale: Locale = "pt-BR"
    domain: ShortText


class CalendarPolicyContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.CALENDAR_POLICY]
    display_name: ShortText
    timezone: ShortText
    week_start: Literal["MONDAY", "SUNDAY"]
    fiscal_year_start_month: int = Field(ge=1, le=12)
    holidays_policy: SafeText
    closing_policy: SafeText
    locale: Locale = "pt-BR"


class DataQualityPolicyContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.DATA_QUALITY_POLICY]
    display_name: ShortText
    definition: SafeText
    severity: Literal["INFO", "WARNING", "BLOCKING"]
    governed_fields: list[CanonicalKey] = Field(default_factory=list, max_length=100)
    acceptance_criteria: list[SafeText] = Field(min_length=1, max_length=50)


class SemanticRelationContentV2(StrictKnowledgeModel):
    kind: Literal[KnowledgeAssetType.SEMANTIC_RELATION]
    display_name: ShortText
    source_canonical_key: CanonicalKey
    target_canonical_key: CanonicalKey
    relation_type: KnowledgeRelationType
    description: SafeText


EnterpriseKnowledgeContentV2 = Annotated[
    BusinessTermContentV2
    | MetricKnowledgeContentV2
    | DimensionKnowledgeContentV2
    | EntityKnowledgeContentV2
    | BusinessRuleContentV2
    | AliasSetContentV2
    | CalendarPolicyContentV2
    | DataQualityPolicyContentV2
    | SemanticRelationContentV2,
    Field(discriminator="kind"),
]


class EnterpriseKnowledgeAssetV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    asset_id: uuid.UUID
    tenant_id: uuid.UUID
    canonical_key: CanonicalKey
    asset_type: KnowledgeAssetType
    domain: ShortText
    ownership: KnowledgeOwnershipV2
    status: KnowledgeAssetStatus
    current_published_version_id: uuid.UUID | None = None
    lock_version: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class EnterpriseKnowledgeVersionV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    version_id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID
    version_number: int = Field(ge=1)
    lifecycle: KnowledgeLifecycle
    content: EnterpriseKnowledgeContentV2
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    author_user_id: uuid.UUID
    previous_version_id: uuid.UUID | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    lock_version: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_effective_period(self) -> "EnterpriseKnowledgeVersionV2":
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        if self.asset_type_from_content is None:
            raise ValueError("content kind is required")
        return self

    @property
    def asset_type_from_content(self) -> KnowledgeAssetType | None:
        return self.content.kind


class KnowledgeApprovalV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    approval_id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID
    version_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    decision: KnowledgeApprovalDecision
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    policy_version: ShortText
    version_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class KnowledgePublicationV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    publication_id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID
    version_id: uuid.UUID
    publisher_user_id: uuid.UUID
    effective_at: datetime
    published_at: datetime
    superseded_version_id: uuid.UUID | None = None


class KnowledgeSearchRequestV2(StrictKnowledgeModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
    asset_types: list[KnowledgeAssetType] = Field(default_factory=list, max_length=10)
    domains: list[ShortText] = Field(default_factory=list, max_length=20)
    locale: Locale = "pt-BR"
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=512)
    at: datetime | None = None


class KnowledgeResolutionCandidateV2(StrictKnowledgeModel):
    asset_id: uuid.UUID
    version_id: uuid.UUID
    canonical_key: CanonicalKey
    asset_type: KnowledgeAssetType
    display_name: ShortText
    domain: ShortText
    score: int = Field(ge=0, le=1000)
    match_type: KnowledgeMatchType
    matched_field: ShortText
    matched_text: ShortText
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    provenance: list[KnowledgeSourceReferenceV2] = Field(default_factory=list, max_length=30)


class KnowledgeSearchResultV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    query_normalized: str
    candidates: list[KnowledgeResolutionCandidateV2]
    next_cursor: str | None = None
    ambiguous: bool = False
    duration_ms: float = Field(ge=0)


class KnowledgeResolutionResultV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    query: str
    candidates: list[KnowledgeResolutionCandidateV2]
    selected: KnowledgeResolutionCandidateV2 | None = None
    ambiguous: bool = False
    clarification_required: bool = False


class KnowledgeDiffV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    asset_id: uuid.UUID
    from_version: int = Field(ge=1)
    to_version: int = Field(ge=1)
    added_fields: list[str] = Field(default_factory=list)
    removed_fields: list[str] = Field(default_factory=list)
    changed_fields: list[str] = Field(default_factory=list)
    from_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    to_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class KnowledgeImportItemV2(StrictKnowledgeModel):
    canonical_key: CanonicalKey
    asset_type: KnowledgeAssetType
    domain: ShortText
    owner_user_id: uuid.UUID
    content: EnterpriseKnowledgeContentV2
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class KnowledgeImportRequestV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    source_format: Literal["JSON", "CSV", "LEGACY"]
    items: list[KnowledgeImportItemV2] = Field(min_length=1, max_length=500)
    dry_run: bool = True
    idempotency_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=128)]


class KnowledgeImportResultV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    import_id: uuid.UUID | None = None
    dry_run: bool
    source_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)
    created_asset_ids: list[uuid.UUID] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, max_length=500)
    idempotent_replay: bool = False


class KnowledgeExportV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    tenant_id: uuid.UUID
    export_format: KnowledgeExportFormat
    generated_at: datetime
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    records: list[EnterpriseKnowledgeVersionV2] = Field(default_factory=list, max_length=1000)
    csv_content: str | None = Field(default=None, max_length=2_000_000)


class KnowledgeAuditEventV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    event_id: uuid.UUID
    tenant_id: uuid.UUID
    asset_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID
    event_type: KnowledgeAuditEventType
    reason_code: ShortText
    metadata: dict[str, JsonValue] = Field(default_factory=dict, max_length=30)
    created_at: datetime


class KnowledgeAccessDecisionV2(StrictKnowledgeModel):
    schema_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    permission: KnowledgePermission
    allowed: bool
    reason_code: ShortText


class KnowledgeAssetCreateV2(StrictKnowledgeModel):
    canonical_key: CanonicalKey
    asset_type: KnowledgeAssetType
    domain: ShortText
    owner_user_id: uuid.UUID
    accountable_area: ShortText
    steward_label: ShortText
    content: EnterpriseKnowledgeContentV2
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def validate_content_type(self) -> "KnowledgeAssetCreateV2":
        if self.content.kind != self.asset_type:
            raise ValueError("asset_type must match content kind")
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return self


class KnowledgeVersionUpdateV2(StrictKnowledgeModel):
    content: EnterpriseKnowledgeContentV2
    expected_lock_version: int = Field(ge=0)
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def validate_effective_period(self) -> "KnowledgeVersionUpdateV2":
        if self.effective_from and self.effective_to and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")
        return self
