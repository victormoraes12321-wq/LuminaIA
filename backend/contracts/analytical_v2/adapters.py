from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, NAMESPACE_URL, uuid5

from pydantic import JsonValue

from .enums import (
    AnalyticalErrorCode,
    ColumnDataType,
    ComparisonKind,
    ConfidenceLevel,
    DataClassification,
    DataSourceKind,
    DimensionRole,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    IntentKind,
    LegacyReadiness,
    OutOfScopeReason,
    PipelineKind,
    PlanOperation,
    ValidationSeverity,
    ValidationStatus,
    VisualizationKind,
)
from .models import (
    AnalyticalColumn,
    AnalyticalDataset,
    AnalyticalError,
    AnalyticalResponseV2,
    ClarificationRequest,
    ComparisonOperand,
    ComparisonSpecification,
    ConfidenceAssessment,
    ContractMetadata,
    DimensionReference,
    ExecutionProvenance,
    ExecutionScope,
    FilterSpecification,
    LegacyCompatibility,
    MetricReference,
    PlanSummary,
    QueryIntentV2,
    QueryPlanV2,
    ScopeSummary,
    SourceReference,
    ValidationCheck,
    ValidationReport,
    VisualizationSpecification,
)
from .parsing import (
    comparison_requested,
    default_comparison_calculations,
    extract_time_windows,
    extract_visualizations,
    normalize_analytical_text,
)


METRIC_REGISTRY_VERSION = "2026-07-20-rb-devolucao-transferencias"
_METRIC_ALIASES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    (
        "quantidade_pedidos",
        (
            "quantidade de pedidos",
            "numero de pedidos",
            "quantos pedidos",
            "total de pedidos",
        ),
        "COUNT",
        "COUNT_DISTINCT",
    ),
    (
        "clientes_distintos",
        (
            "quantidade de clientes",
            "numero de clientes",
            "quantos clientes",
            "total de clientes",
        ),
        "COUNT",
        "COUNT_DISTINCT",
    ),
    (
        "unidades_vendidas",
        (
            "quantidade de unidades",
            "numero de unidades",
            "quantas unidades",
            "quantos unidades",
            "total de unidades",
            "unidades vendidas",
            "quantidade vendida",
        ),
        "COUNT",
        "SUM",
    ),
    ("ticket_medio", ("ticket medio", "ticket"), "BRL", "AVG"),
    ("desconto_medio", ("desconto medio",), "BRL", "AVG"),
    ("desconto_total", ("total de desconto", "desconto", "descontos"), "BRL", "SUM"),
    ("saida_rb", ("venda rb", "vendas rb", "saida rb", " rb "), "BRL", "SUM"),
    ("devolucao", ("devolucao", "devolucoes", "devolvido"), "BRL", "SUM"),
    ("ranking_vendedores", ("ranking de vendedores", "ranking vendedores"), "BRL", "SUM"),
    ("ranking_clientes", ("ranking de clientes", "top clientes"), "BRL", "SUM"),
    (
        "faturamento_comercial",
        ("faturamento", "faturado", "receita", "vendas", "venda"),
        "BRL",
        "SUM",
    ),
)
_DISPLAY_NAMES = {
    "faturamento_comercial": "Faturamento comercial",
    "ticket_medio": "Ticket medio",
    "desconto_total": "Total de desconto",
    "desconto_medio": "Desconto medio",
    "saida_rb": "Saida RB",
    "devolucao": "Devolucao",
    "ranking_vendedores": "Ranking de vendedores",
    "ranking_clientes": "Ranking de clientes",
    "unidades_vendidas": "Unidades vendidas",
    "quantidade_pedidos": "Quantidade de pedidos",
    "clientes_distintos": "Clientes distintos",
}
_V1_TO_V2_VISUALIZATION = {
    "TABLE": VisualizationKind.DATA_TABLE,
    "BAR": VisualizationKind.BAR_CHART,
    "LINE": VisualizationKind.LINE_CHART,
    "AREA": VisualizationKind.AREA_CHART,
    "PIE": VisualizationKind.PIE_CHART,
    "DONUT": VisualizationKind.DONUT_CHART,
    "KPI": VisualizationKind.KPI_CARD,
    "KPI_CARD": VisualizationKind.KPI_CARD,
    "SCATTER": VisualizationKind.SCATTER_CHART,
    "HEATMAP": VisualizationKind.HEATMAP,
    "TREEMAP": VisualizationKind.TREEMAP,
    "FUNNEL": VisualizationKind.FUNNEL,
}
_V2_TO_V1_VISUALIZATION = {
    value: key
    for key, value in _V1_TO_V2_VISUALIZATION.items()
    if key != "KPI_CARD"
}


class AnalyticalContractAdapterError(ValueError):
    pass


def explicit_confidence(reason: str) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=[reason],
        requires_confirmation=False,
    )


def adapter_confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.MEDIUM,
        score=Decimal("0.75"),
        reasons=["Campo convertido de um contrato legado validado."],
        requires_confirmation=False,
    )


def build_intent_v2(
    question: str,
    *,
    pipeline: PipelineKind,
    legacy_status: str | None = None,
    adapter_used: str | None = None,
    inherited: bool = False,
    temporal_context: object | None = None,
    temporal_result: object | None = None,
) -> QueryIntentV2:
    normalized = normalize_analytical_text(question)
    origin = (
        FieldOrigin.INHERITED_CONVERSATION
        if inherited
        else FieldOrigin.EXPLICIT_USER
    )
    metric_refs = _metric_refs_from_text(normalized, origin=origin)
    entity_filters = _entity_filters_from_text(normalized, origin=origin)
    if (
        not metric_refs
        and "total" in normalized
        and any(item.field_id in {"vendedor", "filial", "produto"} for item in entity_filters)
    ):
        metric_refs = [_metric_ref("faturamento_comercial", origin=FieldOrigin.DETERMINISTIC_DEFAULT)]
    from services.temporal import (
        TemporalContext,
        TemporalNormalizationResult,
        TemporalNormalizer,
        TemporalRelation,
        default_temporal_context,
    )

    if temporal_context is None:
        resolved_temporal_context = default_temporal_context(origin=origin)
    elif isinstance(temporal_context, TemporalContext):
        resolved_temporal_context = temporal_context.model_copy(update={"origin": origin})
    else:
        raise TypeError("temporal_context must be a TemporalContext")
    if temporal_result is None:
        resolved_temporal_result = TemporalNormalizer().normalize(
            question,
            resolved_temporal_context,
        )
    elif isinstance(temporal_result, TemporalNormalizationResult):
        resolved_temporal_result = temporal_result
    else:
        raise TypeError("temporal_result must be a TemporalNormalizationResult")
    time_windows = list(resolved_temporal_result.windows)
    visualizations = extract_visualizations(
        question,
        metric_ids=[metric.metric_id for metric in metric_refs],
        origin=origin,
    )
    status = _readiness_from_legacy_status(legacy_status)
    wants_comparison = (
        resolved_temporal_result.relation == TemporalRelation.COMPARISON
    )
    intent_kind = _intent_kind_from_text(normalized, wants_comparison=wants_comparison)
    comparison = None
    clarification = None
    out_of_scope_reason = None

    if status == ExecutionReadiness.OUT_OF_SCOPE:
        intent_kind = IntentKind.OUT_OF_SCOPE
        metric_refs = []
        time_windows = []
        visualizations = []
        out_of_scope_reason = OutOfScopeReason.UNRELATED_DOMAIN
    elif (
        resolved_temporal_result.readiness
        == ExecutionReadiness.CLARIFICATION_REQUIRED
    ):
        status = ExecutionReadiness.CLARIFICATION_REQUIRED
        intent_kind = IntentKind.CLARIFICATION
        clarification = resolved_temporal_result.clarification
    elif wants_comparison and len(time_windows) >= 2:
        intent_kind = IntentKind.COMPARISON
        comparison = _comparison_from_windows(metric_refs, time_windows, origin=origin)
    elif wants_comparison:
        status = ExecutionReadiness.CLARIFICATION_REQUIRED
        intent_kind = IntentKind.CLARIFICATION
        clarification = _clarification(
            "Qual e o segundo periodo que deve ser comparado?",
            ["time_windows"],
            "A comparacao precisa de pelo menos dois periodos reconhecidos.",
        )

    if status == ExecutionReadiness.CLARIFICATION_REQUIRED and clarification is None:
        clarification = _clarification(
            "Qual informacao deseja confirmar antes da consulta?",
            ["analytical_intent"],
            "O contrato legado classificou a pergunta como ambigua ou incompleta.",
        )

    if (
        status == ExecutionReadiness.READY
        and not metric_refs
        and intent_kind not in {IntentKind.DETAIL, IntentKind.METADATA, IntentKind.FOLLOW_UP}
    ):
        status = ExecutionReadiness.CLARIFICATION_REQUIRED
        if intent_kind != IntentKind.COMPARISON:
            intent_kind = IntentKind.CLARIFICATION
        clarification = _clarification(
            "Qual metrica empresarial voce deseja analisar?",
            ["metric_refs"],
            "Nenhuma metrica oficial foi reconhecida sem inferencia silenciosa.",
        )

    if not visualizations and status == ExecutionReadiness.READY:
        visualizations = extract_visualizations(
            "tabela",
            metric_ids=[metric.metric_id for metric in metric_refs],
            origin=FieldOrigin.DETERMINISTIC_DEFAULT,
        )

    confidence = (
        explicit_confidence("Intencao reconhecida por regras deterministicas.")
        if origin == FieldOrigin.EXPLICIT_USER
        else adapter_confidence()
    )
    return QueryIntentV2(
        contract=ContractMetadata(
            pipeline=pipeline,
            adapter_used=adapter_used,
            extensions={
                "temporal": {
                    "normalizer_version": resolved_temporal_result.normalizer_version,
                    "timezone": resolved_temporal_result.timezone,
                    "relation": resolved_temporal_result.relation.value,
                    "rule_ids": list(resolved_temporal_result.rule_ids),
                    "warnings": list(resolved_temporal_result.warnings),
                    "readiness": resolved_temporal_result.readiness.value,
                }
            },
        ),
        intent_kind=intent_kind,
        readiness=status,
        raw_question=question,
        normalized_question=normalized,
        metric_refs=metric_refs,
        dimension_refs=_dimension_refs_from_text(
            normalized,
            origin=origin,
            metric_ids={metric.metric_id for metric in metric_refs},
        ),
        filters=entity_filters,
        time_windows=time_windows,
        comparison=comparison,
        requested_visualizations=visualizations,
        confidence=confidence,
        clarification=clarification,
        out_of_scope_reason=out_of_scope_reason,
        field_origins={
            "raw_question": origin,
            "intent_kind": (
                FieldOrigin.LEGACY_ADAPTER
                if legacy_status
                else FieldOrigin.SYSTEM_GENERATED
            ),
            "time_windows": origin,
            "requested_visualizations": origin,
            "filters": origin,
        },
    )


def build_plan_v2(
    intent: QueryIntentV2,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    user_role: str,
    session_id: str | None,
    allowed_source_ids: list[str],
    pipeline: PipelineKind,
    comparison_planner_enabled: bool = True,
    comparison_planner_shadow_mode: bool = True,
) -> QueryPlanV2:
    legacy_plan = _build_plan_v2_legacy(
        intent,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        allowed_source_ids=allowed_source_ids,
        pipeline=pipeline,
    )
    if intent.comparison is None:
        return legacy_plan
    from services.comparison_planning import (
        ComparisonPlannerFeaturePolicy,
        ComparisonPlannerGateway,
        build_trusted_planning_context,
    )

    context = build_trusted_planning_context(
        intent,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        allowed_source_ids=allowed_source_ids,
        permission_fingerprint=legacy_plan.scope.permission_fingerprint,
        feature_flags={
            "enabled": comparison_planner_enabled,
            "shadow_mode": comparison_planner_shadow_mode,
        },
    )
    result = ComparisonPlannerGateway(
        policy=ComparisonPlannerFeaturePolicy(
            enabled=comparison_planner_enabled,
            shadow_mode=comparison_planner_shadow_mode,
        )
    ).plan(intent, context, legacy_plan=legacy_plan)
    return result.plan if result is not None and result.plan is not None else legacy_plan


def _build_plan_v2_legacy(
    intent: QueryIntentV2,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    user_role: str,
    session_id: str | None,
    allowed_source_ids: list[str],
    pipeline: PipelineKind,
) -> QueryPlanV2:
    fingerprint_seed = f"{tenant_id}:{user_id}:{user_role}:{','.join(allowed_source_ids)}"
    permission_fingerprint = hashlib.sha256(fingerprint_seed.encode("utf-8")).hexdigest()
    scope = ExecutionScope(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        allowed_source_ids=allowed_source_ids,
        permission_fingerprint=permission_fingerprint,
        origin=FieldOrigin.SYSTEM_GENERATED,
    )
    operation = _operation_for_intent(intent)
    source_kind = (
        DataSourceKind.LEGACY_PIPELINE
        if pipeline == PipelineKind.LEGACY
        else DataSourceKind.ANALYTICAL_CLONE
    )
    source_refs = [
        SourceReference(
            source_id=source_id,
            source_kind=source_kind,
            origin=FieldOrigin.LEGACY_ADAPTER,
        )
        for source_id in allowed_source_ids
    ]
    return QueryPlanV2(
        contract=ContractMetadata(
            pipeline=pipeline,
            adapter_used="build_plan_v2",
        ),
        scope=scope,
        intent=intent,
        operation=operation,
        metric_refs=list(intent.metric_refs),
        dimension_refs=list(intent.dimension_refs),
        filters=list(intent.filters),
        time_windows=list(intent.time_windows),
        comparison=intent.comparison,
        visualizations=list(intent.requested_visualizations),
        source_refs=source_refs,
        limit=None,
        ordering=[],
        confidence=intent.confidence,
        validation_requirements=["tenant_scope", "mathematical_consistency"],
        cache_identity=None,
        legacy_context={},
    )


def legacy_payload_to_v2(
    payload: Mapping[str, object],
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    user_role: str,
    session_id: str | None,
    pipeline: PipelineKind,
    embed_rows: bool = False,
    comparison_planner_enabled: bool = True,
    comparison_planner_shadow_mode: bool = True,
) -> AnalyticalResponseV2:
    existing = payload.get("analytical_contract")
    if existing is not None:
        return AnalyticalResponseV2.model_validate_json(
            json.dumps(existing, ensure_ascii=False, default=str)
        )

    question = str(payload.get("pergunta_original") or payload.get("goal") or "Consulta analitica")
    legacy_status = str(payload.get("status") or "FULL_RENDERING")
    intent = build_intent_v2(
        question,
        pipeline=pipeline,
        legacy_status=legacy_status,
        adapter_used="legacy_payload_to_v2",
    )
    view_name = _logical_id(payload.get("view_name"), fallback="legacy_source")
    allowed_sources = [view_name]
    plan = build_plan_v2(
        intent,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        allowed_source_ids=allowed_sources,
        pipeline=pipeline,
        comparison_planner_enabled=comparison_planner_enabled,
        comparison_planner_shadow_mode=comparison_planner_shadow_mode,
    )
    intent = plan.intent

    datasets = _datasets_from_legacy(payload, embed_rows=embed_rows)
    visualizations = _visualizations_from_legacy(
        payload,
        intent=intent,
        dataset_id=datasets[0].dataset_id if datasets else None,
    )
    if visualizations:
        intent = intent.model_copy(update={"requested_visualizations": visualizations})
        plan = plan.model_copy(update={"intent": intent, "visualizations": visualizations})

    validation = _validation_from_legacy(payload)
    executed = bool(datasets) and intent.readiness == ExecutionReadiness.READY
    provenance = (
        [
            ExecutionProvenance(
                tenant_id=tenant_id,
                source_id=view_name,
                source_kind=(
                    DataSourceKind.LEGACY_PIPELINE
                    if pipeline == PipelineKind.LEGACY
                    else DataSourceKind.ANALYTICAL_CLONE
                ),
                view_ids=[view_name] if payload.get("view_name") else [],
                metric_versions={
                    metric.metric_id: metric.metric_version
                    for metric in intent.metric_refs
                },
                filter_fingerprint=None,
                periods=list(intent.time_windows),
                executed_at=datetime.now(timezone.utc) if executed else None,
                sync_version=None,
                cache_status="UNKNOWN",
                pipeline=pipeline,
                query_fingerprint=_fingerprint(intent.normalized_question),
                reconciliation_status=None,
                tenant_isolation_verified=False,
                tenant_isolation_evidence=None,
            )
        ]
        if executed
        else []
    )
    errors = _errors_for_readiness(intent.readiness)
    compatibility_warnings: list[str] = []
    if intent.comparison and len(intent.comparison.operands) > 1:
        compatibility_warnings.append(
            "O payload V1 nao representa todos os operandos; consulte analytical_contract."
        )

    return AnalyticalResponseV2(
        contract=ContractMetadata(
            request_id=_uuid_or_none(payload.get("request_id") or payload.get("query_id")),
            trace_id=_uuid_or_none(payload.get("trace_id")),
            pipeline=pipeline,
            adapter_used="legacy_payload_to_v2",
            extensions={
                "comparison_planner": plan.contract.extensions.get(
                    "comparison_planner",
                    {},
                )
            }
            if plan.contract.extensions.get("comparison_planner")
            else {},
        ),
        scope_summary=ScopeSummary(
            tenant_id=tenant_id,
            user_role=user_role,
            session_id=session_id,
        ),
        intent=intent,
        plan_summary=PlanSummary(
            operation=plan.operation,
            metric_ids=[metric.metric_id for metric in plan.metric_refs],
            dimension_ids=[dimension.dimension_id for dimension in plan.dimension_refs],
            source_ids=[source.source_id for source in plan.source_refs],
            periods=list(plan.time_windows),
        ),
        datasets=datasets,
        visualizations=visualizations,
        provenance=provenance,
        validation=validation,
        summary=_optional_text(payload.get("resposta_direta") or payload.get("mensagem")),
        insights=_string_list(payload.get("insights")),
        warnings=_string_list(payload.get("warnings")),
        errors=errors,
        clarification=intent.clarification,
        legacy_compatibility=LegacyCompatibility(
            compatible=not compatibility_warnings,
            primary_chart_type=_optional_text(payload.get("chart_type")),
            warnings=compatibility_warnings,
        ),
    )


def v2_response_to_legacy(
    response: AnalyticalResponseV2,
    *,
    legacy_payload: Mapping[str, object] | None = None,
) -> dict[str, JsonValue]:
    result = _json_object(legacy_payload or {})
    deterministic_id = uuid5(
        NAMESPACE_URL,
        f"{response.scope_summary.tenant_id}:{response.intent.normalized_question}",
    )
    query_id = response.contract.request_id or deterministic_id
    primary = next(
        (item for item in response.visualizations if item.is_primary),
        response.visualizations[0] if response.visualizations else None,
    )
    result.setdefault("query_id", str(query_id))
    result.setdefault("request_id", str(query_id))
    result.setdefault("view_catalog_id", None)
    result.setdefault("view_name", None)
    result.setdefault("parametros_extraidos", {})
    result.setdefault("ia_confianca", float(response.intent.confidence.score))
    result.setdefault("ia_justificativa", None)
    result.setdefault("pergunta_original", response.intent.raw_question)
    result.setdefault("pode_favoritar", False)
    result.setdefault("mensagem", response.summary)
    result.setdefault("resposta_direta", response.summary)
    result["status"] = _legacy_status_for_readiness(response.intent.readiness)

    if primary is not None:
        result["chart_type"] = _V2_TO_V1_VISUALIZATION.get(primary.kind, "TABLE")
    else:
        result.setdefault("chart_type", None)

    if "chart_data" not in result and response.datasets:
        dataset = response.datasets[0]
        result["chart_data"] = {
            "columns": [
                {
                    "key": column.column_id,
                    "label": column.label,
                    "type": column.data_type.value.lower(),
                }
                for column in dataset.columns
            ],
            "rows": dataset.rows,
            "total_rows": dataset.row_count,
            "resumo": {
                key: str(value)
                for key, value in dataset.numeric_metadata.items()
            },
        }
    else:
        result.setdefault("chart_data", None)

    result.setdefault("visualizations", None)
    if response.errors:
        result["chart_data"] = None
        result["visualizations"] = None
        result["mensagem"] = response.errors[0].message
        result["resposta_direta"] = response.errors[0].message
    result["analytical_contract"] = _json_value(response.model_dump(mode="json"))
    return result


def attach_v2_sidecar(
    payload: Mapping[str, object],
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    user_role: str,
    session_id: str | None,
    pipeline: PipelineKind,
    comparison_planner_enabled: bool = True,
    comparison_planner_shadow_mode: bool = True,
) -> dict[str, JsonValue]:
    response = legacy_payload_to_v2(
        payload,
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        pipeline=pipeline,
        embed_rows=False,
        comparison_planner_enabled=comparison_planner_enabled,
        comparison_planner_shadow_mode=comparison_planner_shadow_mode,
    )
    return v2_response_to_legacy(response, legacy_payload=payload)


def _metric_refs_from_text(text: str, *, origin: FieldOrigin) -> list[MetricReference]:
    refs: list[MetricReference] = []
    for metric_id, aliases, unit, aggregation in _METRIC_ALIASES:
        if any(
            re.search(rf"(?<!\w){re.escape(alias.strip())}(?!\w)", text)
            for alias in aliases
        ):
            refs.append(_metric_ref(metric_id, origin=origin, unit=unit, aggregation=aggregation))
    if any(metric.metric_id == "ranking_vendedores" for metric in refs):
        refs = [metric for metric in refs if metric.metric_id != "faturamento_comercial"]
    return refs


def _metric_ref(
    metric_id: str,
    *,
    origin: FieldOrigin,
    unit: str | None = None,
    aggregation: str | None = None,
) -> MetricReference:
    definition = next(
        (item for item in _METRIC_ALIASES if item[0] == metric_id),
        None,
    )
    if definition is None:
        raise AnalyticalContractAdapterError(f"Unknown governed metric: {metric_id}")
    return MetricReference(
        metric_id=metric_id,
        metric_version=METRIC_REGISTRY_VERSION,
        display_name=_DISPLAY_NAMES[metric_id],
        unit=unit or definition[2],
        aggregation=aggregation or definition[3],
        origin=origin,
        confidence=explicit_confidence(
            "Metrica reconhecida por alias ou default deterministico do registro oficial."
        ),
    )


_ENTITY_FILTER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("vendedor", re.compile(r"\b(?:do|da|de|pelo|pela)\s+vendedor\s+(\d{1,20})\b")),
    ("filial", re.compile(r"\b(?:da|do|de|na|no)\s+filial\s+(\d{1,20})\b")),
    ("produto", re.compile(r"\b(?:do|da|de|com)\s+produto\s+(\d{1,20})\b")),
)


def _entity_filters_from_text(
    text: str,
    *,
    origin: FieldOrigin,
) -> list[FilterSpecification]:
    filters: list[FilterSpecification] = []
    for field_id, pattern in _ENTITY_FILTER_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        filters.append(
            FilterSpecification(
                filter_id=f"explicit_{field_id}",
                field_id=field_id,
                operator=FilterOperator.EQ,
                value=match.group(1),
                origin=origin,
                confidence=explicit_confidence(
                    "Filtro de entidade reconhecido explicitamente no texto do usuario."
                ),
                is_explicit=True,
            )
        )
    return filters


def _dimension_refs_from_text(
    text: str,
    *,
    origin: FieldOrigin,
    metric_ids: set[str] | None = None,
) -> list[DimensionReference]:
    metric_ids = metric_ids or set()
    dimensions: list[tuple[str, str, DimensionRole]] = []
    if "vendedor" in text:
        dimensions.append(("vendedor", "Vendedor", DimensionRole.GROUPING))
    if "cliente" in text and "clientes_distintos" not in metric_ids:
        dimensions.append(("cliente", "Cliente", DimensionRole.GROUPING))
    if "produto" in text:
        dimensions.append(("produto", "Produto", DimensionRole.GROUPING))
    if "filial" in text or "loja" in text:
        dimensions.append(("filial", "Filial", DimensionRole.GROUPING))
    return [
        DimensionReference(
            dimension_id=dimension_id,
            display_name=display_name,
            role=role,
            origin=origin,
            confidence=explicit_confidence(
                "Dimensao reconhecida diretamente no texto do usuario."
            ),
        )
        for dimension_id, display_name, role in dimensions
    ]


def _comparison_from_windows(
    metric_refs: list[MetricReference],
    time_windows: list,
    *,
    origin: FieldOrigin,
) -> ComparisonSpecification:
    operands = [
        ComparisonOperand(
            operand_id=f"operand_{index}",
            label=window.label,
            metric_refs=list(metric_refs),
            time_windows=[window],
            filters=[],
            entity_refs=[],
            origin=origin,
        )
        for index, window in enumerate(time_windows, start=1)
    ]
    return ComparisonSpecification(
        comparison_id="comparison_1",
        kind=(
            ComparisonKind.PERIOD_VS_PERIOD
            if len(operands) == 2
            else ComparisonKind.MULTI_PERIOD
        ),
        operands=operands,
        calculations=default_comparison_calculations(),
        baseline_operand_id=operands[0].operand_id,
        alignment_dimensions=[],
        requested_sort=None,
        origin=origin,
        confidence=explicit_confidence(
            "Todos os operandos temporais foram reconhecidos no texto."
        ),
    )


def _intent_kind_from_text(text: str, *, wants_comparison: bool) -> IntentKind:
    if wants_comparison:
        return IntentKind.COMPARISON
    if any(term in text for term in ("ranking", "top ", "maior", "mais vendeu")):
        return IntentKind.RANKING
    if any(term in text for term in ("por filial", "por vendedor", "por produto", "separe")):
        return IntentKind.BREAKDOWN
    if any(term in text for term in ("liste", "listar", "detalhe", "documentos")):
        return IntentKind.DETAIL
    return IntentKind.METRIC


def _readiness_from_legacy_status(status: str | None) -> ExecutionReadiness:
    normalized = str(status or LegacyReadiness.FULL_RENDERING.value).upper()
    if normalized in {"AMBIGUOUS", "MISSING_INFORMATION"}:
        return ExecutionReadiness.CLARIFICATION_REQUIRED
    if normalized == "OUT_OF_SCOPE":
        return ExecutionReadiness.OUT_OF_SCOPE
    if normalized in {"UNSUPPORTED", "NEEDS_REPLANNING", "INVALID_PLAN"}:
        return ExecutionReadiness.UNSUPPORTED
    if normalized in {
        "ERROR",
        "DATABASE_ERROR",
        "SECURITY_VIOLATION",
        "EMPTY_ANOMALY",
        "INTENT_ENGINE_ERROR",
    }:
        return ExecutionReadiness.ERROR
    return ExecutionReadiness.READY


def _operation_for_intent(intent: QueryIntentV2) -> PlanOperation:
    if intent.readiness != ExecutionReadiness.READY:
        return PlanOperation.NONE
    return {
        IntentKind.METRIC: PlanOperation.AGGREGATE,
        IntentKind.RANKING: PlanOperation.RANK,
        IntentKind.BREAKDOWN: PlanOperation.AGGREGATE,
        IntentKind.COMPARISON: PlanOperation.COMPARE,
        IntentKind.DETAIL: PlanOperation.QUERY,
        IntentKind.METADATA: PlanOperation.DESCRIBE,
        IntentKind.FOLLOW_UP: PlanOperation.QUERY,
    }.get(intent.intent_kind, PlanOperation.NONE)


def _clarification(
    question: str,
    missing_fields: list[str],
    reason: str,
) -> ClarificationRequest:
    return ClarificationRequest(
        question=question,
        missing_fields=missing_fields,
        candidate_options=[],
        reason=reason,
        confidence=ConfidenceAssessment(
            level=ConfidenceLevel.LOW,
            score=Decimal("0.25"),
            reasons=["Informacao insuficiente para execucao deterministica."],
            requires_confirmation=True,
        ),
    )


def _datasets_from_legacy(
    payload: Mapping[str, object],
    *,
    embed_rows: bool,
) -> list[AnalyticalDataset]:
    chart_data = payload.get("chart_data")
    if not isinstance(chart_data, Mapping):
        return []
    raw_rows = chart_data.get("rows")
    rows = (
        [_json_object(row) for row in raw_rows if isinstance(row, Mapping)]
        if embed_rows and isinstance(raw_rows, list)
        else []
    )
    raw_columns = chart_data.get("columns")
    columns: list[AnalyticalColumn] = []
    if isinstance(raw_columns, list):
        for index, raw_column in enumerate(raw_columns, start=1):
            if not isinstance(raw_column, Mapping):
                continue
            column_id = _logical_id(raw_column.get("key"), fallback=f"column_{index}")
            columns.append(
                AnalyticalColumn(
                    column_id=column_id,
                    label=str(raw_column.get("label") or column_id),
                    data_type=_column_type(raw_column.get("type")),
                    unit=None,
                    nullable=True,
                )
            )
    row_count = int(
        chart_data.get("total_rows")
        or (len(raw_rows) if isinstance(raw_rows, list) else 0)
        or 0
    )
    return [
        AnalyticalDataset(
            dataset_id="primary_dataset",
            columns=columns,
            rows=rows,
            row_count=row_count,
            truncated=not embed_rows and row_count > 0,
            numeric_metadata={},
            data_classification=DataClassification.INTERNAL,
        )
    ]


def _visualizations_from_legacy(
    payload: Mapping[str, object],
    *,
    intent: QueryIntentV2,
    dataset_id: str | None,
) -> list[VisualizationSpecification]:
    if dataset_id is None:
        return []
    requested: list[VisualizationKind] = []
    raw_visualizations = payload.get("visualizations")
    if isinstance(raw_visualizations, list):
        for item in raw_visualizations:
            if isinstance(item, Mapping):
                kind = _V1_TO_V2_VISUALIZATION.get(
                    str(item.get("chart_type") or "").upper()
                )
                if kind and kind not in requested:
                    requested.append(kind)
    primary_kind = _V1_TO_V2_VISUALIZATION.get(
        str(payload.get("chart_type") or "").upper()
    )
    if primary_kind and primary_kind not in requested:
        requested.insert(0, primary_kind)
    for visualization in intent.requested_visualizations:
        if visualization.kind not in requested:
            requested.append(visualization.kind)

    return [
        VisualizationSpecification(
            visualization_id=f"visual_{index}",
            kind=kind,
            title=_visualization_title(kind),
            metric_ids=[metric.metric_id for metric in intent.metric_refs],
            dimension_ids=[
                dimension.dimension_id for dimension in intent.dimension_refs
            ],
            data_reference=dataset_id,
            priority=100 - index,
            is_primary=index == 1,
            origin=FieldOrigin.LEGACY_ADAPTER,
            options={},
        )
        for index, kind in enumerate(requested, start=1)
    ]


def _validation_from_legacy(payload: Mapping[str, object]) -> ValidationReport:
    summary = payload.get("validation_summary")
    checks: list[ValidationCheck] = []
    if isinstance(summary, Mapping):
        raw_checks = summary.get("checks")
        if isinstance(raw_checks, list):
            for index, item in enumerate(raw_checks, start=1):
                if not isinstance(item, Mapping):
                    continue
                status = (
                    ValidationStatus.PASSED
                    if str(item.get("status") or "").upper() in {"PASS", "PASSED"}
                    else ValidationStatus.FAILED
                )
                checks.append(
                    ValidationCheck(
                        check_id=_logical_id(
                            item.get("code"),
                            fallback=f"legacy_check_{index}",
                        ),
                        name=str(item.get("code") or f"Legacy check {index}"),
                        status=status,
                        severity=(
                            ValidationSeverity.ERROR
                            if status == ValidationStatus.FAILED
                            else ValidationSeverity.INFO
                        ),
                        message="Validacao matematica convertida do pipeline legado.",
                        evidence_reference=None,
                        required=bool(item.get("required", True)),
                    )
                )
    if not checks:
        return ValidationReport(
            status=ValidationStatus.NOT_EXECUTED,
            checks=[],
            validated_at=None,
            validator_version="legacy-adapter-2.0",
        )
    failed = any(
        check.required and check.status == ValidationStatus.FAILED
        for check in checks
    )
    return ValidationReport(
        status=ValidationStatus.FAILED if failed else ValidationStatus.PASSED,
        checks=checks,
        validated_at=datetime.now(timezone.utc),
        validator_version="legacy-adapter-2.0",
    )


def _errors_for_readiness(readiness: ExecutionReadiness) -> list[AnalyticalError]:
    if readiness == ExecutionReadiness.OUT_OF_SCOPE:
        return [
            AnalyticalError(
                code=AnalyticalErrorCode.OUT_OF_SCOPE,
                message="A pergunta esta fora do escopo analitico empresarial.",
                retryable=False,
            )
        ]
    if readiness == ExecutionReadiness.ERROR:
        return [
            AnalyticalError(
                code=AnalyticalErrorCode.EXECUTION_NOT_PERFORMED,
                message="A execucao analitica nao foi realizada.",
                retryable=True,
            )
        ]
    if readiness == ExecutionReadiness.UNSUPPORTED:
        return [
            AnalyticalError(
                code=AnalyticalErrorCode.INVALID_CONTRACT,
                message="A operacao solicitada ainda nao possui executor compativel.",
                retryable=False,
            )
        ]
    return []


def _legacy_status_for_readiness(readiness: ExecutionReadiness) -> str:
    return {
        ExecutionReadiness.READY: "FULL_RENDERING",
        ExecutionReadiness.CLARIFICATION_REQUIRED: "AMBIGUOUS",
        ExecutionReadiness.OUT_OF_SCOPE: "OUT_OF_SCOPE",
        ExecutionReadiness.UNSUPPORTED: "UNSUPPORTED",
        ExecutionReadiness.BLOCKED: "SECURITY_VIOLATION",
        ExecutionReadiness.ERROR: "ERROR",
    }[readiness]


def _column_type(value: object) -> ColumnDataType:
    normalized = str(value or "string").upper()
    return {
        "NUMBER": ColumnDataType.DECIMAL,
        "CURRENCY": ColumnDataType.DECIMAL,
        "DECIMAL": ColumnDataType.DECIMAL,
        "INTEGER": ColumnDataType.INTEGER,
        "BOOLEAN": ColumnDataType.BOOLEAN,
        "DATE": ColumnDataType.DATE,
        "DATETIME": ColumnDataType.DATETIME,
    }.get(normalized, ColumnDataType.STRING)


def _logical_id(value: object, *, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(value or fallback)).strip("_")
    if not normalized or not normalized[0].isalpha():
        normalized = f"id_{normalized or fallback}"
    return normalized[:128]


def _uuid_or_none(value: object) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:500] for item in value if str(item).strip()]


def _json_value(value: object) -> JsonValue:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _json_object(value: Mapping[str, object]) -> dict[str, JsonValue]:
    converted = _json_value(dict(value))
    return converted if isinstance(converted, dict) else {}


def _visualization_title(kind: VisualizationKind) -> str:
    return {
        VisualizationKind.DATA_TABLE: "Tabela de dados",
        VisualizationKind.BAR_CHART: "Grafico de barras",
        VisualizationKind.LINE_CHART: "Grafico de linhas",
        VisualizationKind.AREA_CHART: "Grafico de area",
        VisualizationKind.PIE_CHART: "Grafico de pizza",
        VisualizationKind.DONUT_CHART: "Grafico de rosca",
        VisualizationKind.KPI_CARD: "Indicador principal",
        VisualizationKind.SUMMARY_CARD: "Resumo",
        VisualizationKind.SCATTER_CHART: "Grafico de dispersao",
        VisualizationKind.HEATMAP: "Mapa de calor",
        VisualizationKind.TREEMAP: "Mapa hierarquico",
        VisualizationKind.FUNNEL: "Funil",
        VisualizationKind.INSIGHTS_LIST: "Insights",
    }[kind]
