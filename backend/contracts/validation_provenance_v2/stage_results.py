"""
LuminaAI Governed Validation & Provenance V2 - Stage Result Typed Contracts
Version: lumina.validation-provenance/1.0
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from .identity import CompletenessStatus, ValidationStatus


class MetricValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_metric_id: str = Field(...)
    formula_fingerprint: str = Field(...)
    registry_fingerprint_match: bool = Field(...)
    unit: Optional[str] = Field(default=None)
    status: ValidationStatus = Field(...)


class TemporalValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_period_start: str = Field(...)
    normalized_period_end: str = Field(...)
    timezone: str = Field(default="UTC")
    granularity: str = Field(...)
    status: ValidationStatus = Field(...)


class NumericValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decimal_valid: bool = Field(...)
    finite_values_only: bool = Field(...)
    zero_denominator_handled: bool = Field(...)
    status: ValidationStatus = Field(...)


class ComparisonValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_period: str = Field(...)
    target_period: str = Field(...)
    baseline_value_decimal: str = Field(...)
    target_value_decimal: str = Field(...)
    calculated_delta_decimal: str = Field(...)
    calculated_percentage: str = Field(...)
    direction_correct: bool = Field(...)
    sign_correct: bool = Field(...)
    status: ValidationStatus = Field(...)


class ShapeValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shape_type: str = Field(...)
    row_count: int = Field(...)
    duplicate_keys_found: int = Field(default=0)
    status: ValidationStatus = Field(...)


class CompletenessValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completeness_status: CompletenessStatus = Field(...)
    truncated: bool = Field(default=False)
    row_limit: Optional[int] = Field(default=None)
    status: ValidationStatus = Field(...)


class FreshnessValidationResultV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_sync_version: str = Field(...)
    source_freshness_timestamp: str = Field(...)
    age_seconds: int = Field(...)
    stale: bool = Field(default=False)
    status: ValidationStatus = Field(...)


class ToolResultValidationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(...)
    invocation_checksum: str = Field(...)
    checksum_valid: bool = Field(...)
    status: ValidationStatus = Field(...)


class OrchestrationValidationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orchestration_run_id: str = Field(...)
    step_budget_respected: bool = Field(...)
    token_budget_respected: bool = Field(...)
    status: ValidationStatus = Field(...)


class ResponseValidationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_text_present: bool = Field(...)
    facts_count: int = Field(...)
    claims_count: int = Field(...)
    all_claims_supported: bool = Field(...)
    status: ValidationStatus = Field(...)
