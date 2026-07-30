from __future__ import annotations

import uuid

import pytest

from comparison_planner_fixtures import confidence, metric
from contracts.analytical_v2 import (
    ContractMetadata,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    IntentKind,
    PipelineKind,
    QueryIntentV2,
)
from contracts.semantic_retrieval_v2 import (
    EntityCanonicalReferenceV2,
    EntityMentionV2,
    EntityResolutionPatchOperationV2,
    EntityResolutionPatchV2,
    EntityResolutionResultV2,
    SemanticEntityType,
    SemanticSourceType,
)
from services.semantic_retrieval.integration import apply_resolution_patch
from services.semantic_retrieval.mentions import SemanticMentionExtractor


pytestmark = pytest.mark.no_database


def _reference(
    canonical_id: str,
    *,
    entity_type: SemanticEntityType,
    label: str,
) -> EntityCanonicalReferenceV2:
    return EntityCanonicalReferenceV2(
        canonical_id=canonical_id,
        entity_type=entity_type,
        display_label=label,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        domain="sales",
        source_type=SemanticSourceType.ENTERPRISE_KNOWLEDGE,
        source_id=f"knowledge.{canonical_id}",
        source_version="1",
    )


def _mention(
    text: str,
    *,
    source: str,
    entity_type: SemanticEntityType,
    candidate_field: str,
) -> EntityMentionV2:
    return EntityMentionV2(
        mention_id=uuid.uuid4(),
        text=text,
        normalized_text=text.casefold(),
        start=0,
        end=len(text),
        expected_entity_type=entity_type,
        candidate_field=candidate_field,
        source=source,
        confidence=1.0,
    )


def test_resolution_patch_applies_alias_and_filter_field_value_by_identity() -> None:
    metric_mention = _mention(
        "Receita",
        source="INTENT",
        entity_type=SemanticEntityType.METRIC,
        candidate_field="metric_refs",
    )
    field_mention = _mention(
        "filial",
        source="FILTER_FIELD",
        entity_type=SemanticEntityType.DIMENSION,
        candidate_field="filter.branch",
    )
    value_mention = _mention(
        "Centro",
        source="FILTER_VALUE",
        entity_type=SemanticEntityType.UNKNOWN,
        candidate_field="filial",
    )
    original_metric = metric("receita")
    original_metric = original_metric.model_copy(update={"display_name": "Receita"})
    original_filter = FilterSpecification(
        filter_id="filter.branch",
        field_id="filial",
        operator=FilterOperator.EQ,
        value="Centro",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        is_explicit=True,
    )
    intent = QueryIntentV2(
        contract=ContractMetadata(pipeline=PipelineKind.NEW),
        intent_kind=IntentKind.METRIC,
        readiness=ExecutionReadiness.READY,
        raw_question="Receita da filial Centro",
        normalized_question="receita da filial centro",
        metric_refs=[original_metric],
        filters=[original_filter],
        confidence=confidence(),
        field_origins={
            "raw_question": FieldOrigin.EXPLICIT_USER,
            "intent_kind": FieldOrigin.SYSTEM_GENERATED,
        },
    )
    operations = (
        EntityResolutionPatchOperationV2(
            operation="SET_CANONICAL_METRIC",
            mention_id=metric_mention.mention_id,
            canonical_reference=_reference(
                "faturamento_comercial",
                entity_type=SemanticEntityType.METRIC,
                label="Faturamento",
            ),
            reason_code="TEST",
        ),
        EntityResolutionPatchOperationV2(
            operation="SET_CANONICAL_FILTER_FIELD",
            mention_id=field_mention.mention_id,
            canonical_reference=_reference(
                "branch_id",
                entity_type=SemanticEntityType.DIMENSION,
                label="Filial",
            ),
            reason_code="TEST",
        ),
        EntityResolutionPatchOperationV2(
            operation="SET_CANONICAL_FILTER_VALUE",
            mention_id=value_mention.mention_id,
            canonical_reference=_reference(
                "branch.centro",
                entity_type=SemanticEntityType.BRANCH,
                label="Filial Centro",
            ),
            reason_code="TEST",
        ),
    )
    result = EntityResolutionResultV2(
        readiness="READY",
        decisions=(),
        resolved_references=tuple(
            operation.canonical_reference
            for operation in operations
            if operation.canonical_reference is not None
        ),
        ambiguities=(),
        unresolved_mentions=(),
        patch=EntityResolutionPatchV2(
            operations=operations,
            checksum="a" * 64,
        ),
        provenance_checksum="b" * 64,
    )

    resolved = apply_resolution_patch(
        intent,
        result,
        (metric_mention, field_mention, value_mention),
    )

    assert resolved.metric_refs[0].metric_id == "faturamento_comercial"
    assert resolved.metric_refs[0].display_name == "Faturamento"
    assert resolved.filters[0].field_id == "branch_id"
    assert resolved.filters[0].value == "branch.centro"
    assert resolved.filters[0].operator == FilterOperator.EQ
    assert resolved.filters[0].is_explicit is True
    assert resolved.field_origins["metric_refs"] == FieldOrigin.TENANT_KNOWLEDGE
    assert resolved.field_origins["filters"] == FieldOrigin.TENANT_KNOWLEDGE


def test_resolution_patch_does_not_rewrite_unrelated_filter_values() -> None:
    value_mention = _mention(
        "Centro",
        source="FILTER_VALUE",
        entity_type=SemanticEntityType.UNKNOWN,
        candidate_field="filial",
    )
    source_filter = FilterSpecification(
        filter_id="filter.branch",
        field_id="filial",
        operator=FilterOperator.IN,
        values=["Centro", "Norte"],
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        is_explicit=True,
    )
    intent = QueryIntentV2(
        contract=ContractMetadata(pipeline=PipelineKind.NEW),
        intent_kind=IntentKind.METRIC,
        readiness=ExecutionReadiness.READY,
        raw_question="Faturamento das filiais Centro e Norte",
        normalized_question="faturamento das filiais centro e norte",
        metric_refs=[metric("faturamento_comercial")],
        filters=[source_filter],
        confidence=confidence(),
        field_origins={
            "raw_question": FieldOrigin.EXPLICIT_USER,
            "intent_kind": FieldOrigin.SYSTEM_GENERATED,
        },
    )
    reference = _reference(
        "branch.centro",
        entity_type=SemanticEntityType.BRANCH,
        label="Filial Centro",
    )
    operation = EntityResolutionPatchOperationV2(
        operation="SET_CANONICAL_FILTER_VALUE",
        mention_id=value_mention.mention_id,
        canonical_reference=reference,
        reason_code="TEST",
    )
    result = EntityResolutionResultV2(
        readiness="READY",
        decisions=(),
        resolved_references=(reference,),
        ambiguities=(),
        unresolved_mentions=(),
        patch=EntityResolutionPatchV2(
            operations=(operation,),
            checksum="c" * 64,
        ),
        provenance_checksum="d" * 64,
    )

    resolved = apply_resolution_patch(intent, result, (value_mention,))

    assert resolved.filters[0].values == ["branch.centro", "Norte"]
    assert resolved.filters[0].operator == FilterOperator.IN


def test_mention_extraction_separates_filter_field_value_and_ignores_period() -> None:
    source_filter = FilterSpecification(
        filter_id="filter.branch",
        field_id="filial",
        operator=FilterOperator.EQ,
        value="Centro",
        origin=FieldOrigin.EXPLICIT_USER,
        confidence=confidence(),
        is_explicit=True,
    )
    intent = QueryIntentV2(
        contract=ContractMetadata(pipeline=PipelineKind.NEW),
        intent_kind=IntentKind.METRIC,
        readiness=ExecutionReadiness.READY,
        raw_question="Faturamento da filial Centro em julho de 2026",
        normalized_question="faturamento da filial centro em julho de 2026",
        metric_refs=[metric("faturamento")],
        filters=[source_filter],
        confidence=confidence(),
        field_origins={
            "raw_question": FieldOrigin.EXPLICIT_USER,
            "intent_kind": FieldOrigin.SYSTEM_GENERATED,
        },
    )

    mentions = SemanticMentionExtractor().extract(intent)
    by_source = {item.source: item for item in mentions}

    assert by_source["FILTER_FIELD"].candidate_field == "filter.branch"
    assert by_source["FILTER_VALUE"].candidate_field == "filial"
    assert by_source["FILTER_VALUE"].text == "Centro"
    assert all("2026" not in item.text for item in mentions)
    assert all("julho" not in item.text.casefold() for item in mentions)
