"""Strict public contracts for governed dashboard AI assistance."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.dashboard_blueprint_v2 import (
    DashboardBlueprintV2,
    DashboardSemanticPatchV2,
    DashboardVisualPatchV2,
)

DASHBOARD_AI_ASSISTANCE_CONTRACT_VERSION = "lumina.dashboard-ai-assistance/1.0"
ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{2,127}$"
CHECKSUM_PATTERN = r"^[a-f0-9]{64}$"


class StrictDashboardAiModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class DashboardAiRequestOriginV2(str, Enum):
    CREATION_WIZARD = "CREATION_WIZARD"
    DASHBOARD_EDITOR = "DASHBOARD_EDITOR"
    SIDE_CHAT = "SIDE_CHAT"
    API = "API"


class DashboardAiOperationV2(str, Enum):
    CREATE_DASHBOARD = "CREATE_DASHBOARD"
    PROPOSE_VISUAL_CHANGE = "PROPOSE_VISUAL_CHANGE"
    PROPOSE_SEMANTIC_CHANGE = "PROPOSE_SEMANTIC_CHANGE"
    REVISE_PROPOSAL = "REVISE_PROPOSAL"
    EXPLAIN_PROPOSAL = "EXPLAIN_PROPOSAL"
    CANCEL_PROPOSAL = "CANCEL_PROPOSAL"


class DashboardAiProposalStatusV2(str, Enum):
    RECEIVED = "RECEIVED"
    ANALYZING = "ANALYZING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    RESOLVING = "RESOLVING"
    SYNTHESIZING = "SYNTHESIZING"
    VALIDATING = "VALIDATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class DashboardAiObjectiveV2(StrictDashboardAiModel):
    summary: str = Field(min_length=3, max_length=500)
    template_hint: str | None = Field(default=None, min_length=3, max_length=64)


class DashboardAiConstraintV2(StrictDashboardAiModel):
    constraint_type: Literal["WIDGET_LIMIT", "LAYOUT", "VISUAL", "ACCESSIBILITY", "OTHER"]
    value: str = Field(min_length=1, max_length=240)


class DashboardAiAudienceV2(StrictDashboardAiModel):
    audience_type: Literal["EXECUTIVE", "MANAGEMENT", "OPERATIONAL", "GENERAL"]
    locale: Literal["pt-BR"] = "pt-BR"


class DashboardAiMetricCandidateV2(StrictDashboardAiModel):
    mention_id: str = Field(pattern=ID_PATTERN)
    text: str = Field(min_length=1, max_length=160)
    canonical_id: str | None = Field(default=None, pattern=ID_PATTERN)
    confidence: float = Field(ge=0, le=1)


class DashboardAiDimensionCandidateV2(DashboardAiMetricCandidateV2):
    pass


class DashboardAiEntityCandidateV2(DashboardAiMetricCandidateV2):
    entity_type: Literal["BRANCH", "PRODUCT", "SELLER", "CATEGORY", "CUSTOMER", "OTHER"]


class DashboardAiPeriodCandidateV2(StrictDashboardAiModel):
    text: str = Field(min_length=1, max_length=160)
    canonical_period_id: str | None = Field(default=None, pattern=ID_PATTERN)
    start_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    confidence: float = Field(ge=0, le=1)


class DashboardAiFilterCandidateV2(StrictDashboardAiModel):
    field_text: str = Field(min_length=1, max_length=160)
    value_texts: tuple[str, ...] = Field(min_length=1, max_length=20)
    canonical_field_id: str | None = Field(default=None, pattern=ID_PATTERN)


class DashboardAiWidgetIntentV2(StrictDashboardAiModel):
    purpose: str = Field(min_length=3, max_length=240)
    visual_hint: str | None = Field(default=None, min_length=3, max_length=48)
    metric_mentions: tuple[str, ...] = Field(default=(), max_length=8)
    dimension_mentions: tuple[str, ...] = Field(default=(), max_length=8)


class DashboardAiDesignIntentV2(StrictDashboardAiModel):
    objective: DashboardAiObjectiveV2
    audience: DashboardAiAudienceV2
    metric_mentions: tuple[str, ...] = Field(default=(), max_length=16)
    dimension_mentions: tuple[str, ...] = Field(default=(), max_length=16)
    period_mentions: tuple[str, ...] = Field(default=(), max_length=8)
    filter_mentions: tuple[str, ...] = Field(default=(), max_length=16)
    widget_intents: tuple[DashboardAiWidgetIntentV2, ...] = Field(default=(), max_length=32)
    constraints: tuple[DashboardAiConstraintV2, ...] = Field(default=(), max_length=16)


class DashboardAiSemanticChangeIntentV2(StrictDashboardAiModel):
    objective: str = Field(min_length=3, max_length=500)
    target_dashboard_id: str = Field(pattern=ID_PATTERN)
    target_revision_id: str = Field(pattern=ID_PATTERN)
    metric_mentions: tuple[str, ...] = Field(default=(), max_length=16)
    dimension_mentions: tuple[str, ...] = Field(default=(), max_length=16)
    period_mentions: tuple[str, ...] = Field(default=(), max_length=8)
    filter_mentions: tuple[str, ...] = Field(default=(), max_length=16)


class DashboardAiIntentV2(StrictDashboardAiModel):
    operation: DashboardAiOperationV2
    design: DashboardAiDesignIntentV2 | None = None
    semantic_change: DashboardAiSemanticChangeIntentV2 | None = None

    @model_validator(mode="after")
    def one_intent(self) -> "DashboardAiIntentV2":
        if (self.design is None) == (self.semantic_change is None):
            raise ValueError("exactly one intent payload is required")
        return self


class DashboardAiAssistanceContextV2(StrictDashboardAiModel):
    session_id: str | None = Field(default=None, pattern=ID_PATTERN)
    target_dashboard_id: str | None = Field(default=None, pattern=ID_PATTERN)
    target_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    locale: Literal["pt-BR"] = "pt-BR"
    timezone: str = Field(default="America/Sao_Paulo", min_length=3, max_length=64)
    expected_lock_version: int | None = Field(default=None, ge=1)


class DashboardAiAssistanceRequestV2(StrictDashboardAiModel):
    operation: DashboardAiOperationV2
    origin: DashboardAiRequestOriginV2
    instruction: str = Field(min_length=3, max_length=4_000)
    context: DashboardAiAssistanceContextV2
    client_request_id: str = Field(pattern=ID_PATTERN)


class DashboardAiClarificationOptionV2(StrictDashboardAiModel):
    option_id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=300)
    canonical_reference: str | None = Field(default=None, pattern=ID_PATTERN)


class DashboardAiClarificationQuestionV2(StrictDashboardAiModel):
    question_id: str = Field(pattern=ID_PATTERN)
    kind: Literal["OBJECTIVE", "METRIC", "DIMENSION", "PERIOD", "DATASET", "FILTER", "TOP_N"]
    prompt: str = Field(min_length=3, max_length=400)
    options: tuple[DashboardAiClarificationOptionV2, ...] = Field(min_length=2, max_length=10)
    allow_multiple: bool = False


class DashboardAiClarificationRequestV2(StrictDashboardAiModel):
    proposal_id: str = Field(pattern=ID_PATTERN)
    proposal_version: int = Field(ge=1)
    questions: tuple[DashboardAiClarificationQuestionV2, ...] = Field(min_length=1, max_length=8)
    expires_at: datetime
    lock_version: int = Field(ge=1)


class DashboardAiClarificationResponseV2(StrictDashboardAiModel):
    question_id: str = Field(pattern=ID_PATTERN)
    selected_option_ids: tuple[str, ...] = Field(min_length=1, max_length=10)
    expected_lock_version: int = Field(ge=1)


class DashboardAiReviseRequestV2(StrictDashboardAiModel):
    instruction: str = Field(min_length=3, max_length=4_000)
    expected_proposal_version: int = Field(ge=1)
    expected_lock_version: int = Field(ge=1)
    client_request_id: str = Field(pattern=ID_PATTERN)


class DashboardWidgetDesignSpecV2(StrictDashboardAiModel):
    widget_key: str = Field(pattern=ID_PATTERN)
    purpose: str = Field(min_length=3, max_length=240)
    widget_type: Literal["KPI", "LINE", "BAR", "TABLE", "RANKING", "COMPARISON", "STATUS"]
    metric_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    dimension_ids: tuple[str, ...] = Field(default=(), max_length=8)
    top_n: int | None = Field(default=None, ge=1, le=100)


class DashboardLayoutDesignSpecV2(StrictDashboardAiModel):
    columns: int = Field(default=12, ge=4, le=24)
    density: Literal["COMPACT", "COMFORTABLE", "SPACIOUS"] = "COMFORTABLE"
    section_titles: tuple[str, ...] = Field(default=("Visão geral",), min_length=1, max_length=12)


class DashboardDesignSpecV2(StrictDashboardAiModel):
    design_spec_id: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=8, max_length=1_000)
    template_id: Literal["EXECUTIVE_OVERVIEW", "SALES_PERFORMANCE", "FINANCIAL_OVERVIEW", "PRODUCT_RANKING", "RECEIVABLES", "INVENTORY", "COMPARATIVE_ANALYSIS", "CUSTOM"]
    audience: DashboardAiAudienceV2
    metric_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    dimension_ids: tuple[str, ...] = Field(default=(), max_length=16)
    canonical_period_id: str = Field(pattern=ID_PATTERN)
    widgets: tuple[DashboardWidgetDesignSpecV2, ...] = Field(min_length=1, max_length=32)
    layout: DashboardLayoutDesignSpecV2
    resolution_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAiProposalEvidenceV2(StrictDashboardAiModel):
    evidence_id: str = Field(pattern=ID_PATTERN)
    evidence_type: Literal["METRIC_REGISTRY", "KNOWLEDGE", "SEMANTIC_RETRIEVAL", "TEMPORAL", "CATALOG", "VALIDATION"]
    canonical_reference: str = Field(pattern=ID_PATTERN)
    public_label: str = Field(min_length=1, max_length=160)
    authority_version: str = Field(min_length=3, max_length=96)
    checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAiProposalWarningV2(StrictDashboardAiModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    message: str = Field(min_length=3, max_length=400)


class DashboardAiProposalRiskV2(StrictDashboardAiModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    severity: Literal["LOW", "MEDIUM", "HIGH", "BLOCKING"]
    message: str = Field(min_length=3, max_length=400)


class DashboardAiPublicRationaleV2(StrictDashboardAiModel):
    summary: str = Field(min_length=3, max_length=600)
    decisions: tuple[str, ...] = Field(default=(), max_length=12)
    omitted_details_notice: Literal["Raciocínio interno do modelo não é armazenado nem exibido."] = "Raciocínio interno do modelo não é armazenado nem exibido."


class DashboardAiBlueprintProposalV2(StrictDashboardAiModel):
    design_spec: DashboardDesignSpecV2
    blueprint: DashboardBlueprintV2
    blueprint_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    semantic_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    visual_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAiSemanticPatchProposalV2(StrictDashboardAiModel):
    intent: DashboardAiSemanticChangeIntentV2
    patch: DashboardSemanticPatchV2
    patch_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAiVisualPatchProposalV2(StrictDashboardAiModel):
    objective: str = Field(min_length=3, max_length=500)
    patch: DashboardVisualPatchV2
    patch_checksum: str = Field(pattern=CHECKSUM_PATTERN)


class DashboardAiProposalVersionV2(StrictDashboardAiModel):
    proposal_id: str = Field(pattern=ID_PATTERN)
    version: int = Field(ge=1)
    status: DashboardAiProposalStatusV2
    blueprint_proposal: DashboardAiBlueprintProposalV2 | None = None
    semantic_proposal: DashboardAiSemanticPatchProposalV2 | None = None
    visual_proposal: DashboardAiVisualPatchProposalV2 | None = None
    rationale: DashboardAiPublicRationaleV2
    evidence: tuple[DashboardAiProposalEvidenceV2, ...] = Field(default=(), max_length=64)
    warnings: tuple[DashboardAiProposalWarningV2, ...] = Field(default=(), max_length=32)
    risks: tuple[DashboardAiProposalRiskV2, ...] = Field(default=(), max_length=32)
    content_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    created_at: datetime

    @model_validator(mode="after")
    def one_payload(self) -> "DashboardAiProposalVersionV2":
        if sum(item is not None for item in (self.blueprint_proposal, self.semantic_proposal, self.visual_proposal)) != 1:
            raise ValueError("proposal version requires exactly one proposal payload")
        return self


class DashboardAiProposalV2(StrictDashboardAiModel):
    contract_version: Literal["lumina.dashboard-ai-assistance/1.0"] = DASHBOARD_AI_ASSISTANCE_CONTRACT_VERSION
    proposal_id: str = Field(pattern=ID_PATTERN)
    operation: DashboardAiOperationV2
    origin: DashboardAiRequestOriginV2
    status: DashboardAiProposalStatusV2
    current_version: int = Field(ge=1)
    lock_version: int = Field(ge=1)
    latest: DashboardAiProposalVersionV2 | None = None
    clarification: DashboardAiClarificationRequestV2 | None = None
    target_dashboard_id: str | None = Field(default=None, pattern=ID_PATTERN)
    target_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    applied_dashboard_id: str | None = Field(default=None, pattern=ID_PATTERN)
    applied_revision_id: str | None = Field(default=None, pattern=ID_PATTERN)
    created_at: datetime
    updated_at: datetime


class DashboardAiProposalDecisionV2(StrictDashboardAiModel):
    decision_id: str = Field(pattern=ID_PATTERN)
    proposal_id: str = Field(pattern=ID_PATTERN)
    proposal_version: int = Field(ge=1)
    decision: Literal["ACCEPT", "REJECT"]
    comment: str = Field(min_length=3, max_length=1_000)
    decided_by_user_id: str = Field(pattern=ID_PATTERN)
    decided_at: datetime


class DashboardAiApplyRequestV2(StrictDashboardAiModel):
    proposal_version: int = Field(ge=1)
    expected_lock_version: int = Field(ge=1)
    confirmation: Literal["APPLY_ACCEPTED_DASHBOARD_AI_PROPOSAL"]


class DashboardAiApplyResultV2(StrictDashboardAiModel):
    proposal_id: str = Field(pattern=ID_PATTERN)
    proposal_version: int = Field(ge=1)
    status: Literal["APPLIED"]
    dashboard_id: str = Field(pattern=ID_PATTERN)
    revision_id: str = Field(pattern=ID_PATTERN)
    replayed: bool = False


class DashboardAiRunBudgetV2(StrictDashboardAiModel):
    maximum_input_characters: int = Field(default=4_000, ge=128, le=20_000)
    maximum_output_tokens: int = Field(default=1_200, ge=64, le=4_000)
    maximum_tool_calls: int = Field(default=12, ge=0, le=32)
    maximum_duration_ms: int = Field(default=15_000, ge=100, le=60_000)
    maximum_widgets: int = Field(default=32, ge=1, le=64)


class DashboardAiRunV2(StrictDashboardAiModel):
    run_id: str = Field(pattern=ID_PATTERN)
    proposal_id: str = Field(pattern=ID_PATTERN)
    status: Literal["RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED"]
    provider: Literal["fake", "openai"]
    model: str = Field(min_length=2, max_length=64)
    budget: DashboardAiRunBudgetV2
    input_fingerprint: str = Field(pattern=CHECKSUM_PATTERN)
    started_at: datetime
    completed_at: datetime | None = None


class DashboardAiRunSummaryV2(StrictDashboardAiModel):
    run_id: str = Field(pattern=ID_PATTERN)
    status: str = Field(min_length=3, max_length=24)
    duration_ms: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class DashboardAiAuditEventV2(StrictDashboardAiModel):
    event_id: str = Field(pattern=ID_PATTERN)
    proposal_id: str = Field(pattern=ID_PATTERN)
    event_type: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    outcome: Literal["SUCCESS", "DENIED", "CONFLICT", "FAILED"]
    actor_user_id: str = Field(pattern=ID_PATTERN)
    metadata_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    occurred_at: datetime


class DashboardAiFeedbackReferenceV2(StrictDashboardAiModel):
    feedback_id: str = Field(pattern=ID_PATTERN)
    proposal_id: str = Field(pattern=ID_PATTERN)
    proposal_version: int = Field(ge=1)
    supervised_feedback_status: str = Field(min_length=3, max_length=32)


class DashboardAiEvaluationCaseV2(StrictDashboardAiModel):
    case_id: str = Field(pattern=ID_PATTERN)
    case_key: str = Field(pattern=ID_PATTERN)
    category: str = Field(min_length=3, max_length=64)
    input_text: str = Field(min_length=3, max_length=4_000)
    expected_status: DashboardAiProposalStatusV2
    expected_canonical_ids: tuple[str, ...] = Field(default=(), max_length=32)


class DashboardAiEvaluationResultV2(StrictDashboardAiModel):
    result_id: str = Field(pattern=ID_PATTERN)
    case_id: str = Field(pattern=ID_PATTERN)
    passed: bool
    actual_status: DashboardAiProposalStatusV2
    evidence_codes: tuple[str, ...] = Field(default=(), max_length=32)
    result_checksum: str = Field(pattern=CHECKSUM_PATTERN)
    executed_at: datetime
