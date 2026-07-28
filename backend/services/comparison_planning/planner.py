from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Iterable
from decimal import Decimal

from contracts.analytical_v2 import (
    ClarificationRequest,
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    ConfidenceAssessment,
    ConfidenceLevel,
    ContractMetadata,
    DataSourceKind,
    DimensionReference,
    ExecutionReadiness,
    ExecutionScope,
    FieldOrigin,
    FilterSpecification,
    IntentKind,
    OrderingSpecification,
    PlanOperation,
    QueryIntentV2,
    QueryPlanV2,
    SourceReference,
)

from .models import (
    AlignmentCompatibility,
    COMPARISON_PLANNER_VERSION,
    ComparisonAlignmentSpecification,
    ComparisonExecutionPlanDefinition,
    ComparisonFilterPartition,
    ComparisonOperandPlan,
    ComparisonPlanComplexity,
    ComparisonPlanningContext,
    ComparisonPlanningIssue,
    ComparisonPlanningResult,
    ComparisonStrategyHint,
    MissingBucketPolicy,
    NullValuePolicy,
    PlanComplexityClassification,
    PlanningIssueSeverity,
)
from .providers import (
    ComparisonCatalogProvider,
    default_comparison_catalog,
    metric_reference_matches_catalog,
)


logger = logging.getLogger("luminaai.services.comparison_planning")

_RULE_KIND = "comparison.kind.structure.v1"
_RULE_OPERANDS = "comparison.operands.preserve-order.v1"
_RULE_FILTERS = "comparison.filters.partition.v1"
_RULE_BASELINE = "comparison.baseline.explicit-or-first.v1"
_RULE_CALCULATIONS = "comparison.calculations.compatibility.v1"
_RULE_ALIGNMENT = "comparison.alignment.canonical-ids.v1"
_RULE_COMPLEXITY = "comparison.complexity.bounded.v1"
_RULE_SECURITY = "comparison.security.fail-closed.v1"
_SQL_MARKER = re.compile(
    r"(?:--|/\*|\*/|;|\b(?:select|insert|update|delete|drop|alter|create|grant|revoke|union)\b)",
    re.IGNORECASE,
)


class ComparisonPlanner:
    def __init__(
        self,
        *,
        catalog: ComparisonCatalogProvider | None = None,
    ) -> None:
        self._catalog = catalog or default_comparison_catalog()

    def plan(
        self,
        intent: QueryIntentV2,
        context: ComparisonPlanningContext,
    ) -> ComparisonPlanningResult:
        started = time.perf_counter()
        issues: list[ComparisonPlanningIssue] = []
        warnings: list[str] = []
        rule_ids = [
            _RULE_KIND,
            _RULE_OPERANDS,
            _RULE_FILTERS,
            _RULE_BASELINE,
            _RULE_CALCULATIONS,
            _RULE_ALIGNMENT,
            _RULE_COMPLEXITY,
            _RULE_SECURITY,
        ]

        if len(intent.raw_question) > context.maximum_text_length:
            issues.append(
                self._issue(
                    "TEXT_LIMIT_EXCEEDED",
                    "A pergunta excede o limite seguro do planner.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="intent.raw_question",
                    requires_clarification=True,
                    blocks_execution=True,
                )
            )

        comparison = self._comparison_from_intent(intent, issues)
        if comparison is None:
            complexity = self._complexity(0, 0, 0, context)
            readiness = self._readiness(intent, issues)
            clarification = self._clarification(intent, issues, readiness)
            return ComparisonPlanningResult(
                plan=None,
                definition=None,
                readiness=readiness,
                confidence=self._confidence(intent, issues),
                clarification=clarification,
                issues=tuple(issues),
                warnings=tuple(warnings),
                strategy_hint=ComparisonStrategyHint.UNDECIDED,
                complexity=complexity,
                rule_ids=tuple(rule_ids),
                duration_ms=(time.perf_counter() - started) * 1000,
            )

        self._validate_security_context(context, issues)
        partition = self._partition_filters(intent, comparison, context, issues)
        operands, source_ids = self._build_operands(
            intent,
            comparison,
            context,
            partition,
            issues,
        )
        resolved_kind = self._resolve_kind(comparison, operands, issues)
        calculations = self._resolve_calculations(
            comparison,
            operands,
            resolved_kind,
            context,
            issues,
            warnings,
        )
        baseline_id = self._select_baseline(comparison, operands, calculations, issues)
        dimensions = self._validate_dimensions(intent, context, issues)
        alignment = self._build_alignment(
            comparison,
            operands,
            dimensions,
            context,
            issues,
            warnings,
        )
        metric_count = len(
            {
                metric.metric_id
                for operand in operands
                for metric in operand.metric_refs
            }
        )
        complexity = self._complexity(
            len(operands),
            metric_count,
            len(dimensions),
            context,
        )
        if complexity.limit_exceeded:
            issues.append(
                self._issue(
                    "PLAN_COMPLEXITY_EXCEEDED",
                    "A comparação excede os limites seguros; reduza operandos, métricas ou dimensões.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="complexity",
                    requires_clarification=True,
                    blocks_execution=True,
                )
            )

        confidence = self._confidence(intent, issues)
        normalized_comparison = ComparisonSpecification(
            comparison_id=comparison.comparison_id,
            kind=resolved_kind,
            operands=[
                ComparisonOperand(
                    operand_id=operand.operand_id,
                    label=operand.label,
                    metric_refs=list(operand.metric_refs),
                    time_windows=list(operand.time_windows),
                    filters=list(operand.specific_filters),
                    entity_refs=list(
                        next(
                            original.entity_refs
                            for original in comparison.operands
                            if original.operand_id == operand.operand_id
                        )
                    ),
                    origin=operand.origin,
                )
                for operand in operands
            ],
            calculations=list(calculations),
            baseline_operand_id=baseline_id,
            alignment_dimensions=[
                dimension.dimension_id
                for dimension in alignment.alignment_dimensions
            ],
            requested_sort=comparison.requested_sort,
            origin=comparison.origin,
            confidence=confidence,
        )
        readiness = self._readiness(intent, issues)
        clarification = self._clarification(intent, issues, readiness)
        strategy = self._strategy(resolved_kind, operands, dimensions)
        ordering = self._ordering(comparison)
        validation_requirements = (
            "tenant_scope",
            "metric_registry",
            "dimension_allowlist",
            "operand_integrity",
            "filter_partition",
            "mathematical_consistency",
        )
        definition = ComparisonExecutionPlanDefinition(
            comparison=normalized_comparison,
            shared_metric_refs=tuple(intent.metric_refs),
            shared_dimensions=tuple(dimensions),
            shared_filters=partition.shared_filters,
            operand_plans=tuple(operands),
            filter_partition=partition,
            alignment=alignment,
            calculations=tuple(calculations),
            baseline_operand_id=baseline_id,
            ordering=tuple(ordering),
            limit=None,
            strategy_hint=strategy,
            validation_requirements=validation_requirements,
            complexity=complexity,
            readiness=readiness,
        )
        cache_identity = self._cache_identity(
            context,
            definition,
            intent.contract.extensions.get("temporal"),
        )
        normalized_intent = QueryIntentV2.model_validate(
            {
                **intent.model_dump(mode="python"),
                "intent_kind": IntentKind.COMPARISON,
                "readiness": readiness,
                "comparison": normalized_comparison,
                "clarification": clarification,
                "confidence": confidence,
            }
        )
        scope = (
            ExecutionScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                user_role=context.user_role,
                session_id=context.session_id,
                allowed_source_ids=list(source_ids),
                permission_fingerprint=context.permission_fingerprint,
                origin=FieldOrigin.SYSTEM_GENERATED,
            )
            if context.tenant_id is not None
            else None
        )
        source_kind = (
            DataSourceKind.LEGACY_PIPELINE
            if intent.contract.pipeline.value == "LEGACY"
            else DataSourceKind.ANALYTICAL_CLONE
        )
        planner_metadata = {
            "planner_version": COMPARISON_PLANNER_VERSION,
            "kind": resolved_kind.value,
            "operand_count": len(operands),
            "metric_count": metric_count,
            "dimension_count": len(dimensions),
            "complexity": complexity.classification.value,
            "complexity_score": complexity.complexity_score,
            "readiness": readiness.value,
            "issue_codes": [issue.code for issue in issues],
            "strategy_hint": strategy.value,
            "rule_ids": rule_ids,
            "cache_identity": cache_identity,
        }
        plan = QueryPlanV2(
            contract=ContractMetadata(
                pipeline=intent.contract.pipeline,
                adapter_used="comparison_planner_v2",
                created_at=intent.contract.created_at,
                extensions={"comparison_planner": planner_metadata},
            ),
            scope=scope,
            intent=normalized_intent,
            operation=(
                PlanOperation.COMPARE
                if readiness == ExecutionReadiness.READY
                else PlanOperation.NONE
            ),
            metric_refs=list(
                self._ordered_unique_metrics(operands)
            ),
            dimension_refs=list(dimensions),
            filters=list(partition.shared_filters),
            time_windows=list(intent.time_windows),
            comparison=normalized_comparison,
            visualizations=list(intent.requested_visualizations),
            source_refs=[
                SourceReference(
                    source_id=source_id,
                    source_kind=source_kind,
                    origin=FieldOrigin.SYSTEM_GENERATED,
                )
                for source_id in source_ids
            ],
            limit=None,
            ordering=ordering,
            confidence=confidence,
            validation_requirements=list(validation_requirements),
            cache_identity=cache_identity,
            legacy_context={
                "comparison_planner": {
                    "version": COMPARISON_PLANNER_VERSION,
                    "strategy_hint": strategy.value,
                    "readiness": readiness.value,
                    "issue_codes": [issue.code for issue in issues],
                }
            },
        )
        duration_ms = (time.perf_counter() - started) * 1000
        self._log_result(
            context=context,
            comparison=normalized_comparison,
            complexity=complexity,
            readiness=readiness,
            issues=issues,
            strategy=strategy,
            duration_ms=duration_ms,
        )
        return ComparisonPlanningResult(
            plan=plan,
            definition=definition,
            readiness=readiness,
            confidence=confidence,
            clarification=clarification,
            issues=tuple(issues),
            warnings=tuple(warnings),
            strategy_hint=strategy,
            complexity=complexity,
            rule_ids=tuple(rule_ids),
            cache_identity=cache_identity,
            duration_ms=duration_ms,
        )

    def _comparison_from_intent(
        self,
        intent: QueryIntentV2,
        issues: list[ComparisonPlanningIssue],
    ) -> ComparisonSpecification | None:
        if intent.readiness == ExecutionReadiness.OUT_OF_SCOPE:
            issues.append(
                self._issue(
                    "OUT_OF_SCOPE_INTENT",
                    "A intenção está fora do domínio analítico.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="intent.readiness",
                    blocks_execution=True,
                )
            )
            return None
        if intent.comparison is not None:
            return intent.comparison
        if len(intent.time_windows) < 2:
            issues.append(
                self._issue(
                    "INCOMPLETE_COMPARISON",
                    "A comparação precisa de pelo menos dois operandos resolvidos.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="intent.comparison",
                    requires_clarification=True,
                    blocks_execution=True,
                )
            )
            return None
        operands = [
            ComparisonOperand(
                operand_id=f"operand_{index}",
                label=window.label,
                metric_refs=list(intent.metric_refs),
                time_windows=[window],
                filters=[],
                entity_refs=[],
                origin=window.origin,
            )
            for index, window in enumerate(intent.time_windows, start=1)
        ]
        return ComparisonSpecification(
            comparison_id="comparison_1",
            kind=(
                ComparisonKind.PERIOD_VS_PERIOD
                if len(operands) == 2
                else ComparisonKind.MULTI_PERIOD
            ),
            operands=operands,
            calculations=[
                ComparisonCalculation.VALUE,
                ComparisonCalculation.ABSOLUTE_DIFFERENCE,
                ComparisonCalculation.PERCENTAGE_DIFFERENCE,
                ComparisonCalculation.DIRECTION,
            ],
            baseline_operand_id=operands[0].operand_id,
            alignment_dimensions=[],
            requested_sort=None,
            origin=FieldOrigin.SYSTEM_GENERATED,
            confidence=intent.confidence,
        )

    def _validate_security_context(
        self,
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
    ) -> None:
        if context.tenant_id is None:
            issues.append(
                self._issue(
                    "MISSING_TRUSTED_TENANT",
                    "O escopo autenticado do tenant é obrigatório.",
                    severity=PlanningIssueSeverity.CRITICAL,
                    field_path="context.tenant_id",
                    blocks_execution=True,
                )
            )
        if any("oracle" in source.lower() for source in context.allowed_source_ids):
            issues.append(
                self._issue(
                    "ORACLE_SOURCE_BLOCKED",
                    "Oracle não é uma fonte permitida para consultas de usuário.",
                    severity=PlanningIssueSeverity.CRITICAL,
                    field_path="context.allowed_source_ids",
                    blocks_execution=True,
                )
            )
        if not context.allowed_source_ids:
            issues.append(
                self._issue(
                    "NO_ALLOWED_SOURCE",
                    "Nenhuma fonte analítica autorizada foi fornecida.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="context.allowed_source_ids",
                    blocks_execution=True,
                )
            )

    def _partition_filters(
        self,
        intent: QueryIntentV2,
        comparison: ComparisonSpecification,
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
    ) -> ComparisonFilterPartition:
        shared = tuple(intent.filters)
        specific = {
            operand.operand_id: tuple(operand.filters)
            for operand in comparison.operands
        }
        conflicts: list[str] = []
        unresolved: list[str] = []
        for filter_spec in shared:
            self._validate_filter(
                filter_spec,
                None,
                context,
                issues,
                unresolved,
            )
        for operand in comparison.operands:
            shared_by_field = {item.field_id: item for item in shared}
            for filter_spec in operand.filters:
                self._validate_filter(
                    filter_spec,
                    operand.operand_id,
                    context,
                    issues,
                    unresolved,
                )
                common = shared_by_field.get(filter_spec.field_id)
                if common is not None and self._filter_identity(common) != self._filter_identity(
                    filter_spec
                ):
                    conflict = f"{operand.operand_id}:{filter_spec.field_id}"
                    conflicts.append(conflict)
                    if not (
                        common.origin == FieldOrigin.INHERITED_CONVERSATION
                        and filter_spec.origin == FieldOrigin.EXPLICIT_USER
                    ):
                        issues.append(
                            self._issue(
                                "CONFLICTING_FILTERS",
                                "Filtros compartilhado e específico entram em conflito.",
                                severity=PlanningIssueSeverity.ERROR,
                                field_path=f"comparison.operands.{operand.operand_id}.filters",
                                operand_id=operand.operand_id,
                                requires_clarification=True,
                                blocks_execution=True,
                            )
                        )
        return ComparisonFilterPartition(
            shared_filters=shared,
            operand_specific_filters=specific,
            conflicting_filters=tuple(conflicts),
            unresolved_filters=tuple(unresolved),
            partition_rule_ids=(_RULE_FILTERS,),
        )

    def _validate_filter(
        self,
        filter_spec: FilterSpecification,
        operand_id: str | None,
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
        unresolved: list[str],
    ) -> None:
        if filter_spec.field_id.lower() in {"tenant", "tenant_id"}:
            issues.append(
                self._issue(
                    "TENANT_AS_FREE_FILTER",
                    "Tenant é derivado da autenticação e não pode ser um filtro livre.",
                    severity=PlanningIssueSeverity.CRITICAL,
                    field_path="filters",
                    operand_id=operand_id,
                    blocks_execution=True,
                )
            )
        allowed_filter_fields = {
            *context.allowed_dimension_ids,
            *context.allowed_entity_types,
            "periodo",
            "data",
        }
        if filter_spec.field_id not in allowed_filter_fields:
            unresolved.append(filter_spec.filter_id)
            issues.append(
                self._issue(
                    "FILTER_FIELD_NOT_PERMITTED",
                    "O identificador lógico do filtro não está autorizado.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="filters",
                    operand_id=operand_id,
                    blocks_execution=True,
                )
            )
        values = [filter_spec.value, *filter_spec.values]
        if any(
            isinstance(value, str) and _SQL_MARKER.search(value)
            for value in values
        ):
            unresolved.append(filter_spec.filter_id)
            issues.append(
                self._issue(
                    "UNSAFE_FILTER_VALUE",
                    "O filtro contém conteúdo não permitido.",
                    severity=PlanningIssueSeverity.CRITICAL,
                    field_path="filters",
                    operand_id=operand_id,
                    blocks_execution=True,
                )
            )

    def _build_operands(
        self,
        intent: QueryIntentV2,
        comparison: ComparisonSpecification,
        context: ComparisonPlanningContext,
        partition: ComparisonFilterPartition,
        issues: list[ComparisonPlanningIssue],
    ) -> tuple[list[ComparisonOperandPlan], tuple[str, ...]]:
        operands: list[ComparisonOperandPlan] = []
        source_ids: list[str] = []
        semantic_fingerprints: set[str] = set()
        tenant_id = context.tenant_id
        for operand in comparison.operands:
            metrics = tuple(operand.metric_refs or intent.metric_refs)
            if not metrics:
                issues.append(
                    self._issue(
                        "MISSING_OPERAND_METRIC",
                        "Cada operando precisa de uma métrica oficial.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="comparison.operands.metric_refs",
                        operand_id=operand.operand_id,
                        requires_clarification=True,
                        blocks_execution=True,
                    )
                )
            operand_sources: list[str] = []
            for metric in metrics:
                if (
                    context.allowed_metric_ids
                    and metric.metric_id not in context.allowed_metric_ids
                ):
                    issues.append(
                        self._issue(
                            "METRIC_NOT_PERMITTED",
                            "A métrica solicitada não está autorizada para este contexto.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="metric_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
                    continue
                entry = (
                    self._catalog.metric(metric.metric_id, tenant_id)
                    if tenant_id is not None
                    else None
                )
                if entry is None:
                    issues.append(
                        self._issue(
                            "UNKNOWN_METRIC",
                            "A métrica solicitada não existe no registro oficial.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="metric_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
                    continue
                if not entry.supported:
                    issues.append(
                        self._issue(
                            "UNSUPPORTED_METRIC",
                            "A métrica existe, mas não possui fonte analítica executável.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="metric_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
                if not metric_reference_matches_catalog(metric, entry):
                    issues.append(
                        self._issue(
                            "METRIC_CONTRACT_MISMATCH",
                            "A versão, unidade ou agregação da métrica diverge do registro oficial.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="metric_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
                for source_id in entry.allowed_source_ids:
                    if source_id in context.allowed_source_ids:
                        operand_sources.append(source_id)
                        source_ids.append(source_id)
            for entity in operand.entity_refs:
                entry = (
                    self._catalog.entity(entity.entity_id, tenant_id)
                    if tenant_id is not None
                    else None
                )
                if entry is None:
                    issues.append(
                        self._issue(
                            "UNKNOWN_OR_CROSS_TENANT_ENTITY",
                            "A entidade não foi resolvida no escopo autenticado.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="entity_refs",
                            operand_id=operand.operand_id,
                            requires_clarification=True,
                            blocks_execution=True,
                        )
                    )
                    continue
                if entry.entity_type not in context.allowed_entity_types:
                    issues.append(
                        self._issue(
                            "ENTITY_TYPE_NOT_PERMITTED",
                            "O tipo de entidade não está autorizado.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="entity_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
                if context.user_role not in entry.permitted_roles:
                    issues.append(
                        self._issue(
                            "ENTITY_NOT_PERMITTED",
                            "A entidade não está autorizada para o perfil autenticado.",
                            severity=PlanningIssueSeverity.ERROR,
                            field_path="entity_refs",
                            operand_id=operand.operand_id,
                            blocks_execution=True,
                        )
                    )
            inherited = tuple(
                item
                for item in partition.shared_filters
                if item.origin == FieldOrigin.INHERITED_CONVERSATION
            )
            confidence = self._operand_confidence(intent, operand)
            resolved_windows = tuple(operand.time_windows)
            if (
                not resolved_windows
                and comparison.kind
                not in {
                    ComparisonKind.PERIOD_VS_PERIOD,
                    ComparisonKind.MULTI_PERIOD,
                }
            ):
                resolved_windows = tuple(intent.time_windows)
            operand_plan = ComparisonOperandPlan(
                operand_id=operand.operand_id,
                label=operand.label,
                metric_refs=metrics,
                time_windows=resolved_windows,
                entity_filters=tuple(
                    item
                    for item in operand.filters
                    if item.field_id in context.allowed_entity_types
                ),
                specific_filters=tuple(operand.filters),
                inherited_filters=inherited,
                dimension_refs=tuple(intent.dimension_refs),
                source_refs=tuple(dict.fromkeys(operand_sources)),
                origin=operand.origin,
                confidence=confidence,
                validation_requirements=(
                    "metric_registry",
                    "entity_scope",
                    "filter_safety",
                ),
            )
            fingerprint = self._operand_identity(operand_plan, operand.entity_refs)
            if fingerprint in semantic_fingerprints:
                issues.append(
                    self._issue(
                        "DUPLICATE_OPERAND",
                        "Dois operandos representam o mesmo escopo comparativo.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="comparison.operands",
                        operand_id=operand.operand_id,
                        requires_clarification=True,
                        blocks_execution=True,
                    )
                )
            semantic_fingerprints.add(fingerprint)
            operands.append(operand_plan)
        resolved_sources = tuple(dict.fromkeys(source_ids))
        if not resolved_sources:
            issues.append(
                self._issue(
                    "SOURCE_NOT_PERMITTED",
                    "Nenhuma fonte autorizada é compatível com as métricas do plano.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="source_refs",
                    blocks_execution=True,
                )
            )
        return operands, resolved_sources

    def _resolve_kind(
        self,
        comparison: ComparisonSpecification,
        operands: list[ComparisonOperandPlan],
        issues: list[ComparisonPlanningIssue],
    ) -> ComparisonKind:
        period_keys = {
            (window.start, window.end)
            for operand in operands
            for window in operand.time_windows
        }
        entity_count = len(
            {
                entity.entity_id
                for original in comparison.operands
                for entity in original.entity_refs
            }
        )
        metric_count = len(
            {
                metric.metric_id
                for operand in operands
                for metric in operand.metric_refs
            }
        )
        if comparison.kind == ComparisonKind.ACTUAL_VS_TARGET:
            resolved = ComparisonKind.ACTUAL_VS_TARGET
        elif metric_count >= 2 and len(period_keys) <= 1 and entity_count <= 1:
            resolved = ComparisonKind.METRIC_VS_METRIC
        elif entity_count >= 2 and len(period_keys) <= 1 and metric_count <= 1:
            resolved = (
                ComparisonKind.ENTITY_VS_ENTITY
                if len(operands) == 2
                else ComparisonKind.MULTI_ENTITY
            )
        elif len(period_keys) >= 2:
            resolved = (
                ComparisonKind.PERIOD_VS_PERIOD
                if len(operands) == 2
                else ComparisonKind.MULTI_PERIOD
            )
        else:
            resolved = comparison.kind
        if resolved != comparison.kind:
            issues.append(
                self._issue(
                    "COMPARISON_KIND_NORMALIZED",
                    "O tipo comparativo foi ajustado à estrutura resolvida.",
                    severity=PlanningIssueSeverity.WARNING,
                    field_path="comparison.kind",
                )
            )
        return resolved

    def _resolve_calculations(
        self,
        comparison: ComparisonSpecification,
        operands: list[ComparisonOperandPlan],
        kind: ComparisonKind,
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
        warnings: list[str],
    ) -> tuple[ComparisonCalculation, ...]:
        calculations = list(dict.fromkeys(comparison.calculations))
        if ComparisonCalculation.VALUE not in calculations:
            calculations.insert(0, ComparisonCalculation.VALUE)
        units = {
            metric.unit
            for operand in operands
            for metric in operand.metric_refs
        }
        if len(units) > 1:
            incompatible = {
                ComparisonCalculation.ABSOLUTE_DIFFERENCE,
                ComparisonCalculation.PERCENTAGE_DIFFERENCE,
                ComparisonCalculation.DIRECTION,
                ComparisonCalculation.SHARE,
            }
            removed = [item for item in calculations if item in incompatible]
            if removed:
                calculations = [item for item in calculations if item not in incompatible]
                warnings.append(
                    "Métricas com unidades diferentes serão exibidas lado a lado sem diferença direta."
                )
                issues.append(
                    self._issue(
                        "INCOMPATIBLE_METRIC_UNITS",
                        "Cálculos diferenciais foram removidos porque as unidades não são comparáveis.",
                        severity=PlanningIssueSeverity.WARNING,
                        field_path="comparison.calculations",
                    )
                )
        if kind == ComparisonKind.ACTUAL_VS_TARGET:
            actual_metrics = [
                metric.metric_id
                for metric in operands[0].metric_refs
            ] if operands else []
            target_metrics = [
                metric.metric_id
                for metric in operands[1].metric_refs
            ] if len(operands) > 1 else []
            tenant_id = context.tenant_id
            target = (
                self._catalog.target(actual_metrics[0], tenant_id)
                if actual_metrics and tenant_id is not None
                else None
            )
            if (
                target is None
                or not target.official
                or target.source_id not in context.allowed_source_ids
                or context.user_role not in target.permitted_roles
                or not target_metrics
                or target.target_metric_id != target_metrics[0]
                or (
                    len(operands) > 1
                    and operands[1].metric_refs
                    and target.unit != operands[1].metric_refs[0].unit
                )
            ):
                issues.append(
                    self._issue(
                        "OFFICIAL_TARGET_NOT_AVAILABLE",
                        "Não existe fonte oficial de meta autorizada para essa comparação.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="comparison.kind",
                        blocks_execution=True,
                    )
                )
        return tuple(calculations)

    def _select_baseline(
        self,
        comparison: ComparisonSpecification,
        operands: list[ComparisonOperandPlan],
        calculations: tuple[ComparisonCalculation, ...],
        issues: list[ComparisonPlanningIssue],
    ) -> str | None:
        operand_ids = [operand.operand_id for operand in operands]
        baseline = comparison.baseline_operand_id
        if baseline is not None and baseline not in operand_ids:
            issues.append(
                self._issue(
                    "UNKNOWN_BASELINE",
                    "O operando base indicado não existe.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="comparison.baseline_operand_id",
                    requires_clarification=True,
                    blocks_execution=True,
                )
            )
            return None
        baseline_required = any(
            calculation
            in {
                ComparisonCalculation.ABSOLUTE_DIFFERENCE,
                ComparisonCalculation.PERCENTAGE_DIFFERENCE,
                ComparisonCalculation.DIRECTION,
            }
            for calculation in calculations
        )
        if baseline is None and baseline_required and operands:
            baseline = operands[0].operand_id
        if baseline is None and baseline_required:
            issues.append(
                self._issue(
                    "MISSING_BASELINE",
                    "Os cálculos solicitados exigem um operando base.",
                    severity=PlanningIssueSeverity.ERROR,
                    field_path="comparison.baseline_operand_id",
                    requires_clarification=True,
                    blocks_execution=True,
                )
            )
        return baseline

    def _validate_dimensions(
        self,
        intent: QueryIntentV2,
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
    ) -> tuple[DimensionReference, ...]:
        dimensions: list[DimensionReference] = []
        for dimension in intent.dimension_refs:
            if (
                context.allowed_dimension_ids
                and dimension.dimension_id not in context.allowed_dimension_ids
            ):
                issues.append(
                    self._issue(
                        "DIMENSION_NOT_PERMITTED",
                        "A dimensão solicitada não está autorizada.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="dimension_refs",
                        blocks_execution=True,
                    )
                )
                continue
            entry = (
                self._catalog.dimension(dimension.dimension_id, context.tenant_id)
                if context.tenant_id is not None
                else None
            )
            if entry is None:
                issues.append(
                    self._issue(
                        "UNKNOWN_DIMENSION",
                        "A dimensão não existe no catálogo governado.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="dimension_refs",
                        blocks_execution=True,
                    )
                )
                continue
            dimensions.append(dimension)
        return tuple(dimensions)

    def _build_alignment(
        self,
        comparison: ComparisonSpecification,
        operands: list[ComparisonOperandPlan],
        dimensions: tuple[DimensionReference, ...],
        context: ComparisonPlanningContext,
        issues: list[ComparisonPlanningIssue],
        warnings: list[str],
    ) -> ComparisonAlignmentSpecification:
        by_id = {dimension.dimension_id: dimension for dimension in dimensions}
        requested = comparison.alignment_dimensions
        alignment_dimensions: list[DimensionReference] = []
        for dimension_id in requested:
            dimension = by_id.get(dimension_id)
            if dimension is None:
                issues.append(
                    self._issue(
                        "UNRESOLVED_ALIGNMENT_DIMENSION",
                        "Uma dimensão de alinhamento não foi resolvida ou autorizada.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="comparison.alignment_dimensions",
                        requires_clarification=True,
                        blocks_execution=True,
                    )
                )
            else:
                alignment_dimensions.append(dimension)
        if not requested:
            alignment_dimensions = list(dimensions)
        granularities = {
            window.granularity
            for operand in operands
            for window in operand.time_windows
        }
        temporal_granularity = next(iter(granularities)) if len(granularities) == 1 else None
        compatibility = AlignmentCompatibility.COMPATIBLE
        alignment_warnings: list[str] = []
        if len(granularities) > 1:
            temporal_dimensions = {"dia", "mes", "ano"}
            if temporal_dimensions.intersection(
                dimension.dimension_id for dimension in alignment_dimensions
            ):
                compatibility = AlignmentCompatibility.INCOMPATIBLE
                issues.append(
                    self._issue(
                        "INCOMPATIBLE_TEMPORAL_GRANULARITY",
                        "As séries possuem granularidades temporais incompatíveis.",
                        severity=PlanningIssueSeverity.ERROR,
                        field_path="alignment.temporal_granularity",
                        requires_clarification=True,
                        blocks_execution=True,
                    )
                )
            else:
                compatibility = AlignmentCompatibility.COMPATIBLE_WITH_WARNINGS
                alignment_warnings.append(
                    "Operandos com granularidades diferentes serão comparados como totais."
                )
                warnings.extend(alignment_warnings)
        series_identity = tuple(
            dict.fromkeys(
                [
                    *(dimension.dimension_id for dimension in alignment_dimensions),
                    *(
                        metric.metric_id
                        for operand in operands
                        for metric in operand.metric_refs
                    ),
                ]
            )
        )
        return ComparisonAlignmentSpecification(
            alignment_dimensions=tuple(alignment_dimensions),
            temporal_granularity=temporal_granularity,
            entity_granularity=(
                next(
                    (
                        dimension.dimension_id
                        for dimension in alignment_dimensions
                        if dimension.dimension_id in context.allowed_entity_types
                    ),
                    None,
                )
            ),
            missing_bucket_policy=MissingBucketPolicy.PRESERVE_NULL,
            null_policy=NullValuePolicy.PRESERVE,
            ordering=tuple(self._ordering(comparison)),
            series_identity=series_identity,
            compatibility_status=compatibility,
            warnings=tuple(alignment_warnings),
        )

    def _complexity(
        self,
        operand_count: int,
        metric_count: int,
        dimension_count: int,
        context: ComparisonPlanningContext,
    ) -> ComparisonPlanComplexity:
        estimated_series = operand_count * max(metric_count, 1) * max(dimension_count, 1)
        estimated_queries = max(1, operand_count)
        score = (
            operand_count * 5
            + metric_count * 8
            + dimension_count * 13
            + estimated_series
            + estimated_queries * 2
        )
        exceeded = (
            operand_count > context.maximum_operands
            or metric_count > context.maximum_metrics
            or dimension_count > context.maximum_dimensions
            or estimated_series > context.maximum_series
            or score > context.maximum_plan_complexity
        )
        if exceeded:
            classification = PlanComplexityClassification.REJECTED
        elif score <= 40:
            classification = PlanComplexityClassification.LOW
        elif score <= 150:
            classification = PlanComplexityClassification.MEDIUM
        else:
            classification = PlanComplexityClassification.HIGH
        return ComparisonPlanComplexity(
            operand_count=operand_count,
            metric_count=metric_count,
            dimension_count=dimension_count,
            estimated_series_count=estimated_series,
            estimated_query_count=estimated_queries,
            complexity_score=score,
            classification=classification,
            limit_exceeded=exceeded,
        )

    def _strategy(
        self,
        kind: ComparisonKind,
        operands: list[ComparisonOperandPlan],
        dimensions: tuple[DimensionReference, ...],
    ) -> ComparisonStrategyHint:
        if kind == ComparisonKind.ACTUAL_VS_TARGET:
            return ComparisonStrategyHint.TARGET_JOIN
        if kind in {ComparisonKind.ENTITY_VS_ENTITY, ComparisonKind.MULTI_ENTITY}:
            return (
                ComparisonStrategyHint.GROUPED_SERIES
                if dimensions
                else ComparisonStrategyHint.CONDITIONAL_AGGREGATION
            )
        if kind == ComparisonKind.METRIC_VS_METRIC:
            return ComparisonStrategyHint.SINGLE_AGGREGATION
        if kind == ComparisonKind.MULTI_PERIOD:
            return (
                ComparisonStrategyHint.PIVOT
                if dimensions
                else ComparisonStrategyHint.CONDITIONAL_AGGREGATION
            )
        if kind == ComparisonKind.PERIOD_VS_PERIOD:
            return (
                ComparisonStrategyHint.GROUPED_SERIES
                if dimensions
                else ComparisonStrategyHint.CONDITIONAL_AGGREGATION
            )
        return ComparisonStrategyHint.UNDECIDED

    def _readiness(
        self,
        intent: QueryIntentV2,
        issues: list[ComparisonPlanningIssue],
    ) -> ExecutionReadiness:
        if intent.readiness in {
            ExecutionReadiness.OUT_OF_SCOPE,
            ExecutionReadiness.ERROR,
            ExecutionReadiness.CLARIFICATION_REQUIRED,
            ExecutionReadiness.BLOCKED,
            ExecutionReadiness.UNSUPPORTED,
        }:
            return intent.readiness
        blocking_codes = {issue.code for issue in issues if issue.blocks_execution}
        if blocking_codes.intersection(
            {
                "MISSING_TRUSTED_TENANT",
                "ORACLE_SOURCE_BLOCKED",
                "NO_ALLOWED_SOURCE",
                "TENANT_AS_FREE_FILTER",
                "UNSAFE_FILTER_VALUE",
                "FILTER_FIELD_NOT_PERMITTED",
                "METRIC_NOT_PERMITTED",
                "ENTITY_TYPE_NOT_PERMITTED",
                "ENTITY_NOT_PERMITTED",
            }
        ):
            return ExecutionReadiness.BLOCKED
        if blocking_codes.intersection(
            {
                "UNKNOWN_METRIC",
                "UNSUPPORTED_METRIC",
                "METRIC_CONTRACT_MISMATCH",
                "OFFICIAL_TARGET_NOT_AVAILABLE",
                "UNKNOWN_DIMENSION",
            }
        ):
            return ExecutionReadiness.UNSUPPORTED
        if "SOURCE_NOT_PERMITTED" in blocking_codes:
            return ExecutionReadiness.BLOCKED
        if any(issue.requires_clarification for issue in issues if issue.blocks_execution):
            return ExecutionReadiness.CLARIFICATION_REQUIRED
        if any(issue.blocks_execution for issue in issues):
            return ExecutionReadiness.UNSUPPORTED
        return ExecutionReadiness.READY

    def _clarification(
        self,
        intent: QueryIntentV2,
        issues: list[ComparisonPlanningIssue],
        readiness: ExecutionReadiness,
    ) -> ClarificationRequest | None:
        if readiness != ExecutionReadiness.CLARIFICATION_REQUIRED:
            return None
        if intent.clarification is not None:
            return intent.clarification
        relevant = [issue for issue in issues if issue.requires_clarification]
        first = relevant[0] if relevant else None
        question = {
            "INCOMPLETE_COMPARISON": "Qual é o segundo item ou período que deseja comparar?",
            "DUPLICATE_OPERAND": "Os operandos são iguais. Qual item diferente deseja comparar?",
            "PLAN_COMPLEXITY_EXCEEDED": "A comparação é muito ampla. Quais operandos deseja manter?",
            "CONFLICTING_FILTERS": "Qual filtro deve prevalecer em cada operando?",
            "UNKNOWN_OR_CROSS_TENANT_ENTITY": "Qual entidade autorizada deseja comparar?",
            "UNRESOLVED_ALIGNMENT_DIMENSION": "Por qual dimensão os resultados devem ser alinhados?",
            "INCOMPATIBLE_TEMPORAL_GRANULARITY": "Qual granularidade temporal comum deseja usar?",
        }.get(first.code if first else "", "Qual informação deseja confirmar para a comparação?")
        missing = [
            self._logical_issue_field(issue)
            for issue in relevant
        ] or ["comparison"]
        return ClarificationRequest(
            question=question,
            missing_fields=list(dict.fromkeys(missing)),
            candidate_options=[],
            reason=first.message if first else "A comparação ainda não está completa.",
            confidence=ConfidenceAssessment(
                level=ConfidenceLevel.LOW,
                score=Decimal("0.25"),
                reasons=["Há informação crítica que precisa ser confirmada."],
                requires_confirmation=True,
            ),
        )

    def _confidence(
        self,
        intent: QueryIntentV2,
        issues: list[ComparisonPlanningIssue],
    ) -> ConfidenceAssessment:
        if any(issue.blocks_execution for issue in issues):
            return ConfidenceAssessment(
                level=ConfidenceLevel.LOW,
                score=Decimal("0.30"),
                reasons=["O plano possui itens críticos não resolvidos."],
                requires_confirmation=True,
            )
        warning_count = sum(
            issue.severity == PlanningIssueSeverity.WARNING
            for issue in issues
        )
        if warning_count:
            return ConfidenceAssessment(
                level=ConfidenceLevel.MEDIUM,
                score=min(intent.confidence.score, Decimal("0.80")),
                reasons=["O plano foi resolvido com avisos não bloqueantes."],
                requires_confirmation=False,
            )
        return intent.confidence

    def _operand_confidence(
        self,
        intent: QueryIntentV2,
        operand: ComparisonOperand,
    ) -> ConfidenceAssessment:
        scores = [
            intent.confidence.score,
            *(
                metric.confidence.score
                for metric in (operand.metric_refs or intent.metric_refs)
            ),
            *(window.confidence.score for window in operand.time_windows),
        ]
        score = min(scores) if scores else intent.confidence.score
        level = (
            ConfidenceLevel.HIGH
            if score >= Decimal("0.85")
            else ConfidenceLevel.MEDIUM
            if score >= Decimal("0.60")
            else ConfidenceLevel.LOW
        )
        return ConfidenceAssessment(
            level=level,
            score=score,
            reasons=["Operando composto apenas por referências governadas."],
            requires_confirmation=level == ConfidenceLevel.LOW,
        )

    def _ordering(
        self,
        comparison: ComparisonSpecification,
    ) -> list[OrderingSpecification]:
        value = comparison.requested_sort
        if not value:
            return []
        match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_.:-]*)(?::|\s+)(ASC|DESC)",
            value.strip(),
            re.IGNORECASE,
        )
        if not match:
            return []
        return [
            OrderingSpecification(
                field_id=match.group(1),
                direction=match.group(2).upper(),
            )
        ]

    def _cache_identity(
        self,
        context: ComparisonPlanningContext,
        definition: ComparisonExecutionPlanDefinition,
        temporal_metadata: object,
    ) -> str:
        temporal_version = (
            str(temporal_metadata.get("normalizer_version"))
            if isinstance(temporal_metadata, dict)
            else "unknown"
        )
        payload = {
            "tenant_id": str(context.tenant_id),
            "permission_fingerprint": context.permission_fingerprint,
            "planner_version": COMPARISON_PLANNER_VERSION,
            "temporal_version": temporal_version,
            "comparison": {
                "kind": definition.comparison.kind.value,
                "operands": [
                    {
                        "operand_id": operand.operand_id,
                        "metric_ids": [
                            [metric.metric_id, metric.metric_version]
                            for metric in operand.metric_refs
                        ],
                        "periods": [
                            [
                                window.start.isoformat(),
                                window.end.isoformat(),
                                window.granularity.value,
                            ]
                            for window in operand.time_windows
                        ],
                        "filters": [
                            self._filter_identity(item)
                            for item in operand.filters
                        ],
                        "entity_ids": [
                            entity.entity_id
                            for entity in operand.entity_refs
                        ],
                    }
                    for operand in definition.comparison.operands
                ],
                "calculations": [
                    item.value
                    for item in definition.comparison.calculations
                ],
                "baseline_operand_id": definition.comparison.baseline_operand_id,
                "alignment_dimensions": list(
                    definition.comparison.alignment_dimensions
                ),
            },
            "shared_filters": [
                self._filter_identity(item)
                for item in definition.shared_filters
            ],
            "dimensions": [
                item.dimension_id
                for item in definition.shared_dimensions
            ],
            "ordering": [
                item.model_dump(mode="json")
                for item in definition.ordering
            ],
            "limit": definition.limit,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return "cmp:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _operand_identity(
        self,
        operand: ComparisonOperandPlan,
        entities: Iterable,
    ) -> str:
        payload = {
            "metrics": [metric.metric_id for metric in operand.metric_refs],
            "windows": [
                [window.start.isoformat(), window.end.isoformat()]
                for window in operand.time_windows
            ],
            "filters": [
                self._filter_identity(item)
                for item in operand.specific_filters
            ],
            "entities": [entity.entity_id for entity in entities],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _ordered_unique_metrics(
        self,
        operands: list[ComparisonOperandPlan],
    ) -> tuple:
        seen: set[str] = set()
        ordered = []
        for operand in operands:
            for metric in operand.metric_refs:
                if metric.metric_id not in seen:
                    seen.add(metric.metric_id)
                    ordered.append(metric)
        return tuple(ordered)

    def _filter_identity(self, item: FilterSpecification) -> str:
        return json.dumps(
            {
                "field_id": item.field_id,
                "operator": item.operator.value,
                "value": item.value,
                "values": item.values,
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _logical_issue_field(self, issue: ComparisonPlanningIssue) -> str:
        value = (issue.field_path or "comparison").replace(".", "_")
        value = re.sub(r"[^A-Za-z0-9_.:-]", "_", value)
        if not re.match(r"^[A-Za-z]", value):
            value = f"field_{value}"
        return value[:100]

    def _issue(
        self,
        code: str,
        message: str,
        *,
        severity: PlanningIssueSeverity,
        field_path: str | None = None,
        operand_id: str | None = None,
        requires_clarification: bool = False,
        blocks_execution: bool = False,
    ) -> ComparisonPlanningIssue:
        suffix = f":{operand_id}" if operand_id else ""
        return ComparisonPlanningIssue(
            issue_id=f"issue_{code.lower()}{suffix}".replace("_", "-"),
            code=code,
            severity=severity,
            message=message,
            field_path=field_path,
            operand_id=operand_id,
            requires_clarification=requires_clarification,
            blocks_execution=blocks_execution,
        )

    def _log_result(
        self,
        *,
        context: ComparisonPlanningContext,
        comparison: ComparisonSpecification,
        complexity: ComparisonPlanComplexity,
        readiness: ExecutionReadiness,
        issues: list[ComparisonPlanningIssue],
        strategy: ComparisonStrategyHint,
        duration_ms: float,
    ) -> None:
        tenant_fingerprint = hashlib.sha256(
            str(context.tenant_id).encode("utf-8")
        ).hexdigest()[:16]
        logger.info(
            "comparison_plan version=%s kind=%s operands=%d metrics=%d dimensions=%d "
            "complexity=%s readiness=%s issues=%s strategy=%s duration_ms=%.3f "
            "tenant_fp=%s permission_fp=%s flags=%s",
            COMPARISON_PLANNER_VERSION,
            comparison.kind.value,
            complexity.operand_count,
            complexity.metric_count,
            complexity.dimension_count,
            complexity.classification.value,
            readiness.value,
            ",".join(issue.code for issue in issues),
            strategy.value,
            duration_ms,
            tenant_fingerprint,
            context.permission_fingerprint[:16],
            ",".join(
                f"{key}:{int(value)}"
                for key, value in sorted(context.feature_flags.items())
            ),
        )
