from __future__ import annotations

from dataclasses import dataclass

from contracts.enterprise_knowledge_v2 import (
    KnowledgeAssetType,
    KnowledgeBindingStatus,
    MetricKnowledgeContentV2,
)
from services.enterprise_knowledge.normalization import compute_checksum, normalize_lexical
from services.metric_registry import METRIC_DEFINITIONS, MetricDefinition


@dataclass(frozen=True)
class MetricBindingResult:
    status: KnowledgeBindingStatus
    canonical_metric_id: str
    official_formula_fingerprint: str | None
    reason_code: str


def official_formula_fingerprint(definition: MetricDefinition) -> str:
    return compute_checksum(
        {
            "key": definition.key,
            "source": definition.source,
            "formula": definition.formula,
            "default_filters": list(definition.default_filters),
            "grain": definition.grain,
        }
    )


def validate_metric_binding(
    *,
    asset_type: KnowledgeAssetType,
    content: object,
) -> MetricBindingResult:
    if asset_type not in {KnowledgeAssetType.METRIC, KnowledgeAssetType.KPI}:
        return MetricBindingResult(
            status=KnowledgeBindingStatus.DESCRIPTION_ONLY,
            canonical_metric_id="",
            official_formula_fingerprint=None,
            reason_code="NON_NUMERIC_ASSET",
        )
    if not isinstance(content, MetricKnowledgeContentV2):
        return MetricBindingResult(
            status=KnowledgeBindingStatus.BLOCKED,
            canonical_metric_id="",
            official_formula_fingerprint=None,
            reason_code="INVALID_METRIC_CONTENT",
        )
    definition = METRIC_DEFINITIONS.get(content.canonical_metric_id)
    if definition is None:
        return MetricBindingResult(
            status=KnowledgeBindingStatus.MISSING_REGISTRY_ENTRY,
            canonical_metric_id=content.canonical_metric_id,
            official_formula_fingerprint=None,
            reason_code="METRIC_NOT_IN_REGISTRY",
        )
    fingerprint = official_formula_fingerprint(definition)
    if content.formula_fingerprint and content.formula_fingerprint != fingerprint:
        return MetricBindingResult(
            status=KnowledgeBindingStatus.CONFLICT,
            canonical_metric_id=content.canonical_metric_id,
            official_formula_fingerprint=fingerprint,
            reason_code="FORMULA_FINGERPRINT_MISMATCH",
        )
    if normalize_lexical(content.authoritative_source) != normalize_lexical(definition.source):
        return MetricBindingResult(
            status=KnowledgeBindingStatus.CONFLICT,
            canonical_metric_id=content.canonical_metric_id,
            official_formula_fingerprint=fingerprint,
            reason_code="AUTHORITATIVE_SOURCE_MISMATCH",
        )
    return MetricBindingResult(
        status=KnowledgeBindingStatus.VALID,
        canonical_metric_id=content.canonical_metric_id,
        official_formula_fingerprint=fingerprint,
        reason_code="METRIC_REGISTRY_MATCH",
    )
