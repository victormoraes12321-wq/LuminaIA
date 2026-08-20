from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal
from uuid import UUID

from contracts.analytical_v2 import (
    ClarificationRequest,
    ComparisonCalculation,
    ComparisonKind,
    ComparisonOperand,
    ComparisonSpecification,
    ConfidenceAssessment,
    ConfidenceLevel,
    DimensionReference,
    ExecutionReadiness,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    IntentKind,
    MetricReference,
    QueryIntentV2,
    TimeWindow,
    VisualizationSpecification,
)
from contracts.conversation_state_v2 import ConversationStateV2, compute_state_checksum

from .models import (
    CONTEXT_RESOLUTION_VERSION,
    AppendFieldOperation,
    ClearActiveComparisonOperation,
    ClearFieldOperation,
    ConflictSeverity,
    ContextConflict,
    ContextFieldDecision,
    ContextPatchV2,
    ContextRelationship,
    ContextResolutionContext,
    ContextResolutionResult,
    ContextSubjectSignature,
    FieldDecisionAction,
    PublicContextSummary,
    ReplaceFieldOperation,
    ResetContextOperation,
    ResolvePendingClarificationOperation,
    SetActiveComparisonOperation,
    SetActiveHeadReferenceOperation,
    SetActiveSubjectOperation,
    SetPendingClarificationOperation,
    stable_fingerprint,
)


class ContextResolutionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _confidence(reason: str, *, inherited: bool = False) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH if not inherited else ConfidenceLevel.MEDIUM,
        score=Decimal("1") if not inherited else Decimal("0.9"),
        reasons=[reason],
        requires_confirmation=False,
    )


def _inherited(item):
    if getattr(item, "origin", None) == FieldOrigin.INHERITED_CONVERSATION:
        return item
    return item.model_copy(update={"origin": FieldOrigin.INHERITED_CONVERSATION})


def _json(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json(item) for item in value]
    return value


def _unique(items: list, key: str) -> list:
    result = []
    seen: set[str] = set()
    for item in items:
        identity = str(getattr(item, key))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(item)
    return result


class ContextResolutionEngine:
    """Pure, deterministic resolver. Persistence remains owned by ConversationStateService."""

    _RESET = (
        "nova analise", "novo assunto", "limpe o contexto", "zerar contexto",
        "recomecar", "comece de novo", "reiniciar analise",
    )
    _BACKTRACK = (
        "volte para a analise anterior", "voltar para a analise anterior",
        "retome a analise anterior", "continue do ponto anterior",
    )
    _CORRECTION = ("na verdade", "corrigindo", "quis dizer", "correcao")
    _REMOVAL = (
        "sem ", "remova ", "retire ", "exclua ", "exceto ",
        "nao considere ", "nao quero ", "nao compare", "nao use ",
        "mantenha somente ",
    )
    _COMPARISON = (
        "compare", "comparar", "comparacao", "versus", " vs ",
        "os dois meses", "esses dois meses", "ambos os meses",
    )
    _ROLL_UP = ("resuma", "consolide", "sem detalhar", "total geral", "agrupe tudo")
    _SALES_METRICS = {
        "faturamento_comercial", "ticket_medio", "desconto_total", "desconto_medio",
        "saida_rb", "devolucao", "ranking_vendedores", "ranking_clientes",
    }

    def resolve(
        self,
        *,
        current_intent: QueryIntentV2,
        current_question: str,
        persisted_state: ConversationStateV2,
        context: ContextResolutionContext,
    ) -> ContextResolutionResult:
        self._validate_inputs(current_intent, current_question, persisted_state, context)
        normalized = _normalize(current_question)
        state_before = compute_state_checksum(persisted_state)
        current_intent = self._with_explicit_filters(current_intent, normalized)
        relationship = self._relationship(current_intent, persisted_state, context, normalized)
        rules = [f"CTX.RELATIONSHIP.{relationship.value}"]
        if relationship == ContextRelationship.CLARIFICATION_ANSWER:
            current_intent = self._with_pending_clarification_answer(
                current_intent,
                normalized,
                persisted_state.pending_clarification_request,
            )

        if relationship == ContextRelationship.RESET:
            return self._reset_result(
                current_intent=current_intent,
                persisted_state=persisted_state,
                context=context,
                state_before=state_before,
                rules=rules,
            )
        if relationship == ContextRelationship.OUT_OF_SCOPE:
            return self._preserve_out_of_scope_result(
                current_intent=current_intent,
                persisted_state=persisted_state,
                context=context,
                state_before=state_before,
                rules=rules,
                question=current_question,
            )

        explicit_metrics = list(current_intent.metric_refs)
        explicit_dimensions = list(current_intent.dimension_refs)
        explicit_filters = list(current_intent.filters)
        conflicts = self._filter_conflicts(explicit_filters)
        if conflicts:
            explicit_filters = []
            rules.append("CTX.FILTER.CONFLICT_BLOCKED")
        constrained_fields = {item.field_id for item in explicit_filters}
        explicit_dimensions = [
            item for item in explicit_dimensions
            if item.dimension_id not in constrained_fields
            or f"por {item.dimension_id}" in normalized
        ]
        explicit_windows = list(current_intent.time_windows)
        explicit_visualizations = [
            item for item in current_intent.requested_visualizations
            if item.origin == FieldOrigin.EXPLICIT_USER
        ]
        if relationship == ContextRelationship.REMOVAL and explicit_metrics:
            explicit_metrics = []

        allow_inheritance = relationship not in {
            ContextRelationship.NEW_TOPIC,
            ContextRelationship.OUT_OF_SCOPE,
            ContextRelationship.RESET,
        }
        metrics = explicit_metrics or (
            [_inherited(item) for item in persisted_state.active_metric_refs]
            if allow_inheritance else []
        )
        dimensions = self._resolve_dimensions(
            explicit_dimensions, persisted_state, relationship, allow_inheritance, normalized,
        )
        filters = self._resolve_filters(
            explicit_filters, persisted_state, relationship, allow_inheritance, normalized,
        )
        if relationship == ContextRelationship.REMOVAL and explicit_windows:
            removed_ranges = {(item.start, item.end) for item in explicit_windows}
            windows = [
                _inherited(item) for item in persisted_state.active_time_windows
                if (item.start, item.end) not in removed_ranges
            ]
        else:
            windows = explicit_windows or (
                [_inherited(item) for item in persisted_state.active_time_windows]
                if allow_inheritance else []
            )
        if relationship == ContextRelationship.REMOVAL and any(
            term in normalized for term in ("grafico", "tabela", "visualizacao")
        ):
            visualizations = []
        else:
            visualizations = explicit_visualizations or (
                [_inherited(item) for item in persisted_state.active_visualizations]
                if allow_inheritance else list(current_intent.requested_visualizations)
            )
        recent_windows = self._recent_windows(
            persisted_state.recent_time_windows,
            persisted_state.active_time_windows,
            explicit_windows,
        )

        comparison = current_intent.comparison
        if relationship == ContextRelationship.COMPARISON_EXTENSION and comparison is None:
            comparison = self._build_temporal_comparison(metrics, recent_windows)
            if comparison:
                windows = [window for operand in comparison.operands for window in operand.time_windows]
                rules.append("CTX.COMPARISON.RECENT_TWO_WINDOWS")
        elif (
            comparison is None
            and allow_inheritance
            and relationship in {
                ContextRelationship.DRILL_DOWN,
                ContextRelationship.ROLL_UP,
                ContextRelationship.FOLLOW_UP,
                ContextRelationship.BRANCH_CONTINUATION,
                ContextRelationship.BACKTRACK,
            }
        ):
            comparison = persisted_state.active_comparison
            if comparison:
                windows = list(persisted_state.active_time_windows)
                rules.append("CTX.COMPARISON.PRESERVE_ON_SHAPE_CHANGE")
        elif explicit_windows and relationship != ContextRelationship.COMPARISON_EXTENSION:
            comparison = None
        if relationship == ContextRelationship.REMOVAL and "compare" in normalized:
            comparison = None

        intent_kind = self._resolved_intent_kind(
            current_intent, persisted_state, relationship, comparison, dimensions,
        )
        clarification = (
            self._conflict_clarification(conflicts)
            if conflicts else self._resolve_clarification(
                current_intent, persisted_state, metrics, relationship,
            )
        )
        if (
            relationship == ContextRelationship.COMPARISON_EXTENSION
            and comparison is None
        ):
            clarification = ClarificationRequest(
                question="Quais sao os dois periodos que devem ser comparados?",
                missing_fields=["time_windows"],
                candidate_options=[],
                reason="A comparacao precisa de dois periodos distintos no contexto.",
                confidence=_confidence("Comparacao incompleta detectada deterministicamente."),
            )
        readiness = self._readiness(
            current_intent, metrics, comparison, clarification, relationship,
        )
        if readiness == ExecutionReadiness.READY:
            clarification = None

        resolved_intent = QueryIntentV2.model_validate({
            **current_intent.model_dump(mode="python"),
            "contract": current_intent.contract.model_copy(
                update={"created_at": context.reference_datetime}
            ),
            "intent_kind": intent_kind,
            "readiness": readiness,
            "metric_refs": metrics,
            "dimension_refs": dimensions,
            "filters": filters,
            "time_windows": windows,
            "comparison": comparison,
            "requested_visualizations": visualizations,
            "clarification": clarification,
            "field_origins": self._field_origins(
                current_intent, explicit_metrics, explicit_dimensions, explicit_filters,
                explicit_windows, explicit_visualizations,
            ),
        })
        subject = self._subject_signature(resolved_intent)
        subject_changed = bool(
            persisted_state.active_subject
            and persisted_state.active_subject != subject.domain
        )
        if subject_changed:
            rules.append("CTX.SUBJECT.CHANGED")

        decisions = self._field_decisions(
            persisted_state=persisted_state,
            resolved_intent=resolved_intent,
            explicit_fields={
                "active_metric_refs": bool(explicit_metrics),
                "active_dimension_refs": bool(explicit_dimensions),
                "active_filters": bool(explicit_filters),
                "active_time_windows": bool(explicit_windows),
                "active_visualizations": bool(explicit_visualizations),
            },
            relationship=relationship,
            source_node_id=context.current_node_id,
        )
        provisional_state = ConversationStateV2.model_validate({
            **persisted_state.model_dump(mode="python"),
            "active_metric_refs": metrics,
            "active_dimension_refs": dimensions,
            "active_filters": filters,
            "active_time_windows": windows,
            "active_comparison": comparison,
            "active_visualizations": visualizations,
            "active_subject": subject.domain,
            "recent_time_windows": recent_windows,
            "last_intent_kind": intent_kind,
            "last_readiness": readiness,
            "pending_clarification": clarification is not None,
            "pending_clarification_request": clarification,
            "last_context_relationship": relationship.value,
            "field_origins": resolved_intent.field_origins,
            "updated_at": context.reference_datetime,
        })
        operations = self._operations(
            persisted_state, provisional_state, decisions, subject, comparison,
            clarification, context,
        )
        patch = self._patch(
            operations=operations,
            question=current_question,
            persisted_state=persisted_state,
            provisional_state=provisional_state,
            context=context,
        )
        resolved_state = provisional_state.model_copy(
            update={"last_context_patch_fingerprint": patch.idempotency_fingerprint}
        )
        state_after = compute_state_checksum(resolved_state)
        summary = self._public_summary(
            resolved_intent, decisions, relationship, clarification,
        )
        inherited_count = sum(
            1
            for values in (metrics, dimensions, filters, windows, visualizations)
            for item in values
            if getattr(item, "origin", None) == FieldOrigin.INHERITED_CONVERSATION
        )
        warnings = []
        if inherited_count > context.maximum_inherited_fields:
            raise ContextResolutionError(
                "CONTEXT_INHERITANCE_LIMIT",
                "The inherited context exceeds the governed field limit.",
            )

        return ContextResolutionResult(
            resolved_intent=resolved_intent,
            resolved_state=resolved_state,
            patch=patch,
            readiness=readiness,
            confidence=resolved_intent.confidence,
            relationship=relationship,
            field_decisions=decisions,
            conflicts=conflicts,
            clarification=clarification,
            warnings=warnings,
            public_context_summary=summary,
            rule_ids=rules,
            state_checksum_before=state_before,
            state_checksum_after=state_after,
            expected_context_version=persisted_state.context_version,
            base_node_id=context.parent_node_id,
        )

    def _validate_inputs(
        self,
        intent: QueryIntentV2,
        question: str,
        state: ConversationStateV2,
        context: ContextResolutionContext,
    ) -> None:
        if not question.strip() or len(question) > 1000:
            raise ContextResolutionError("INVALID_QUESTION", "Question is empty or too long.")
        if state.context_epoch != context.context_epoch:
            raise ContextResolutionError("CONTEXT_EPOCH_CONFLICT", "Context epoch is stale.")
        if state.context_version != context.context_version:
            raise ContextResolutionError("CONTEXT_VERSION_CONFLICT", "Context version is stale.")
        if context.expected_context_version not in {None, state.context_version}:
            raise ContextResolutionError("CONTEXT_VERSION_CONFLICT", "Expected context version is stale.")
        if intent.contract.schema_version != "2.0":
            raise ContextResolutionError("UNSUPPORTED_INTENT_VERSION", "Intent version is unsupported.")

    def _relationship(
        self,
        intent: QueryIntentV2,
        state: ConversationStateV2,
        context: ContextResolutionContext,
        text: str,
    ) -> ContextRelationship:
        if any(marker in text for marker in self._RESET):
            return ContextRelationship.RESET
        if intent.readiness == ExecutionReadiness.OUT_OF_SCOPE:
            return ContextRelationship.OUT_OF_SCOPE
        if any(marker in text for marker in self._BACKTRACK):
            return ContextRelationship.BACKTRACK
        if any(marker in text for marker in self._REMOVAL):
            return ContextRelationship.REMOVAL
        if any(marker in text for marker in self._CORRECTION):
            return ContextRelationship.CORRECTION
        if any(marker in f" {text} " for marker in self._COMPARISON):
            return ContextRelationship.COMPARISON_EXTENSION
        if state.pending_clarification:
            return ContextRelationship.CLARIFICATION_ANSWER
        if context.parent_node_id and context.active_head_node_id and (
            context.parent_node_id != context.active_head_node_id
        ):
            return ContextRelationship.BRANCH_CONTINUATION
        if not state.active_metric_refs and not state.active_subject:
            return ContextRelationship.NEW_TOPIC
        if self._is_new_domain(text, intent, state):
            return ContextRelationship.NEW_TOPIC
        if any(marker in text for marker in self._ROLL_UP):
            return ContextRelationship.ROLL_UP
        if intent.dimension_refs:
            return ContextRelationship.DRILL_DOWN
        if intent.time_windows or intent.filters or intent.metric_refs:
            return ContextRelationship.REFINEMENT
        return ContextRelationship.FOLLOW_UP

    def _is_new_domain(
        self, text: str, intent: QueryIntentV2, state: ConversationStateV2,
    ) -> bool:
        if any(term in text for term in ("estoque", "compras", "financeiro", "contas a pagar")):
            return state.active_subject not in {None, self._domain_from_text(text)}
        if not intent.metric_refs or not state.active_metric_refs:
            return False
        old_domain = self._domain_for_metrics(state.active_metric_refs)
        new_domain = self._domain_for_metrics(intent.metric_refs)
        return old_domain != new_domain

    def _resolve_dimensions(
        self,
        explicit: list[DimensionReference],
        state: ConversationStateV2,
        relationship: ContextRelationship,
        allow_inheritance: bool,
        text: str,
    ) -> list[DimensionReference]:
        inherited = [_inherited(item) for item in state.active_dimension_refs]
        if relationship == ContextRelationship.REMOVAL:
            if "agrupamento" in text or "sem detalhar" in text:
                return []
            return [
                item for item in inherited
                if _normalize(item.dimension_id) not in text
            ]
        if explicit and relationship == ContextRelationship.DRILL_DOWN:
            return _unique([*inherited, *explicit], "dimension_id")
        if explicit:
            return explicit
        if relationship == ContextRelationship.ROLL_UP:
            return []
        return inherited if allow_inheritance else []

    def _resolve_filters(
        self,
        explicit: list[FilterSpecification],
        state: ConversationStateV2,
        relationship: ContextRelationship,
        allow_inheritance: bool,
        text: str,
    ) -> list[FilterSpecification]:
        inherited = [_inherited(item) for item in state.active_filters]
        if relationship == ContextRelationship.REMOVAL:
            return [
                item for item in inherited
                if _normalize(str(item.value or "")) not in text
                and _normalize(item.field_id) not in text
            ]
        if not explicit:
            return inherited if allow_inheritance else []
        explicit_fields = {item.field_id for item in explicit}
        return [
            *[item for item in inherited if item.field_id not in explicit_fields],
            *explicit,
        ]

    def _recent_windows(
        self,
        recent: list[TimeWindow],
        active: list[TimeWindow],
        current: list[TimeWindow],
    ) -> list[TimeWindow]:
        ordered = [*recent, *active, *current]
        deduped: dict[tuple[date, date], TimeWindow] = {}
        for window in ordered:
            key = (window.start, window.end)
            deduped.pop(key, None)
            deduped[key] = window
        return list(deduped.values())[-12:]

    def _build_temporal_comparison(
        self,
        metrics: list[MetricReference],
        recent_windows: list[TimeWindow],
    ) -> ComparisonSpecification | None:
        if not metrics or len(recent_windows) < 2:
            return None
        selected = [
            window.model_copy(update={
                "window_id": (
                    f"context_period_{index}_"
                    f"{window.start:%Y%m%d}_{window.end:%Y%m%d}"
                ),
            })
            for index, window in enumerate(recent_windows[-2:], start=1)
        ]
        operands = [
            ComparisonOperand(
                operand_id=f"period_{index}",
                label=window.label,
                metric_refs=[_inherited(metric) for metric in metrics],
                time_windows=[_inherited(window)],
                filters=[],
                entity_refs=[],
                origin=FieldOrigin.INHERITED_CONVERSATION,
            )
            for index, window in enumerate(selected, start=1)
        ]
        return ComparisonSpecification(
            comparison_id="conversation_period_comparison",
            kind=ComparisonKind.PERIOD_VS_PERIOD,
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
            origin=FieldOrigin.INHERITED_CONVERSATION,
            confidence=_confidence("Comparacao pedida sobre os dois periodos recentes.", inherited=True),
        )

    def _resolved_intent_kind(
        self,
        current: QueryIntentV2,
        state: ConversationStateV2,
        relationship: ContextRelationship,
        comparison: ComparisonSpecification | None,
        dimensions: list[DimensionReference],
    ) -> IntentKind:
        if comparison is not None:
            return IntentKind.COMPARISON
        if relationship == ContextRelationship.OUT_OF_SCOPE:
            return IntentKind.OUT_OF_SCOPE
        if relationship == ContextRelationship.DRILL_DOWN:
            return IntentKind.BREAKDOWN
        if current.intent_kind not in {IntentKind.CLARIFICATION, IntentKind.FOLLOW_UP}:
            return current.intent_kind
        if state.last_intent_kind not in {None, IntentKind.CLARIFICATION, IntentKind.OUT_OF_SCOPE}:
            if state.last_intent_kind == IntentKind.COMPARISON:
                return IntentKind.BREAKDOWN if dimensions else IntentKind.METRIC
            return state.last_intent_kind
        return IntentKind.BREAKDOWN if dimensions else IntentKind.METRIC

    def _resolve_clarification(
        self,
        current: QueryIntentV2,
        state: ConversationStateV2,
        metrics: list[MetricReference],
        relationship: ContextRelationship,
    ) -> ClarificationRequest | None:
        if relationship == ContextRelationship.CLARIFICATION_ANSWER:
            pending = state.pending_clarification_request
            if pending is None:
                return ClarificationRequest(
                    question="Qual informacao deve completar a analise anterior?",
                    missing_fields=["pending_clarification"],
                    candidate_options=[],
                    reason="O estado legado registra uma clarificacao sem detalhes estruturados.",
                    confidence=_confidence(
                        "Clarificacao legada incompleta preservada por seguranca.",
                        inherited=True,
                    ),
                )
            if not self._clarification_is_answered(current, pending):
                return pending
            return None
        if metrics:
            return None
        return current.clarification

    def _clarification_is_answered(
        self,
        current: QueryIntentV2,
        pending: ClarificationRequest,
    ) -> bool:
        if not pending.missing_fields:
            return current.readiness == ExecutionReadiness.READY
        available = {
            "metric": bool(current.metric_refs),
            "dimension": bool(current.dimension_refs),
            "filter": bool(current.filters),
            "time_window": bool(current.time_windows),
            "period": bool(current.time_windows),
            "visualization": bool(current.requested_visualizations),
            "comparison": current.comparison is not None,
            "ordering": False,
            "limit": False,
        }
        for missing in pending.missing_fields:
            field = _normalize(missing).removeprefix("active_")
            filter_field = field.rsplit(".", 1)[-1]
            if any(item.field_id == filter_field for item in current.filters):
                continue
            singular = field.rstrip("s")
            if not any(
                is_available
                for key, is_available in available.items()
                if key in field or key == singular
            ):
                return False
        return True

    def _with_pending_clarification_answer(
        self,
        intent: QueryIntentV2,
        text: str,
        pending: ClarificationRequest | None,
    ) -> QueryIntentV2:
        if pending is None or intent.filters or not pending.candidate_options:
            return intent
        selected = next(
            (
                option for option in pending.candidate_options
                if _normalize(option) == text
            ),
            None,
        )
        filter_field = None
        for missing_field in pending.missing_fields:
            normalized_field = _normalize(missing_field).removeprefix("active_")
            if normalized_field in {"filial", "produto", "vendedor", "cliente"}:
                filter_field = normalized_field
                break
            if normalized_field.startswith(("filter.", "filters.")):
                filter_field = normalized_field.rsplit(".", 1)[-1]
                break
        if selected is None or filter_field is None:
            return intent
        if filter_field == "filter":
            return intent
        query_filter = FilterSpecification(
            filter_id=f"clarification_{stable_fingerprint([filter_field, selected])[:16]}",
            field_id=filter_field,
            operator=FilterOperator.EQ,
            value=selected,
            values=[],
            origin=FieldOrigin.EXPLICIT_USER,
            confidence=_confidence("Opcao de filtro escolhida explicitamente pelo usuario."),
            is_explicit=True,
        )
        return QueryIntentV2.model_validate({
            **intent.model_dump(mode="python"),
            "filters": [query_filter],
        })

    def _readiness(
        self,
        current: QueryIntentV2,
        metrics: list[MetricReference],
        comparison: ComparisonSpecification | None,
        clarification: ClarificationRequest | None,
        relationship: ContextRelationship,
    ) -> ExecutionReadiness:
        if current.readiness == ExecutionReadiness.OUT_OF_SCOPE:
            return ExecutionReadiness.OUT_OF_SCOPE
        if comparison is None and (
            current.intent_kind == IntentKind.COMPARISON
            or relationship == ContextRelationship.COMPARISON_EXTENSION
        ):
            return ExecutionReadiness.CLARIFICATION_REQUIRED
        if not metrics or clarification is not None:
            return ExecutionReadiness.CLARIFICATION_REQUIRED
        return ExecutionReadiness.READY

    def _with_explicit_filters(self, intent: QueryIntentV2, text: str) -> QueryIntentV2:
        filters = list(intent.filters)
        known_fields = {item.field_id for item in filters}
        filial_matches = list(re.finditer(
            r"\b(?:filial|loja|unidade)\s+(?:da\s+|de\s+)?([a-z0-9][a-z0-9 _.-]{0,60}?)(?=$|[?,.;]|\s+(?:em|no|na|por|com|e)\b)",
            text,
        ))
        if filial_matches and "filial" not in known_fields:
            for index, filial_match in enumerate(filial_matches, start=1):
                value = filial_match.group(1).strip()
                filters.append(FilterSpecification(
                    filter_id=f"filter_filial_{index}",
                    field_id="filial",
                    operator=FilterOperator.EQ,
                    value=value,
                    values=[],
                    origin=FieldOrigin.EXPLICIT_USER,
                    confidence=_confidence("Filial informada explicitamente pelo usuario."),
                    is_explicit=True,
                ))
        if filters == intent.filters:
            return intent
        return QueryIntentV2.model_validate({
            **intent.model_dump(mode="python"),
            "filters": filters,
        })

    def _filter_conflicts(
        self, filters: list[FilterSpecification],
    ) -> list[ContextConflict]:
        by_field: dict[str, list[FilterSpecification]] = {}
        for query_filter in filters:
            by_field.setdefault(query_filter.field_id, []).append(query_filter)
        conflicts = []
        for field, candidates in by_field.items():
            values = {
                stable_fingerprint([candidate.operator.value, candidate.value, candidate.values])
                for candidate in candidates
            }
            if len(values) <= 1:
                continue
            options = [
                str(candidate.value if candidate.value is not None else candidate.values)
                for candidate in candidates
            ]
            conflicts.append(ContextConflict(
                conflict_id=stable_fingerprint([field, options])[:32],
                field_path=f"active_filters.{field}",
                previous_candidates=[],
                current_candidates=[_json(candidate) for candidate in candidates],
                severity=ConflictSeverity.ERROR,
                reason="Dois valores explicitos incompativeis foram informados para o mesmo filtro.",
                candidate_options=options,
                blocks_execution=True,
                requires_clarification=True,
            ))
        return conflicts

    def _conflict_clarification(
        self, conflicts: list[ContextConflict],
    ) -> ClarificationRequest:
        fields = [
            conflict.field_path.rsplit(".", 1)[-1]
            for conflict in conflicts
        ]
        options = [
            option
            for conflict in conflicts
            for option in conflict.candidate_options
        ]
        return ClarificationRequest(
            question="Qual valor deve ser usado para o filtro informado?",
            missing_fields=fields,
            candidate_options=options,
            reason="A pergunta contem valores explicitos conflitantes.",
            confidence=_confidence("Conflito material detectado deterministicamente."),
        )

    def _field_origins(
        self,
        intent: QueryIntentV2,
        metrics: list,
        dimensions: list,
        filters: list,
        windows: list,
        visualizations: list,
    ) -> dict[str, FieldOrigin]:
        origins = dict(intent.field_origins)
        for field, explicit in (
            ("metric_refs", metrics),
            ("dimension_refs", dimensions),
            ("filters", filters),
            ("time_windows", windows),
            ("requested_visualizations", visualizations),
        ):
            origins[field] = (
                FieldOrigin.EXPLICIT_USER
                if explicit else FieldOrigin.INHERITED_CONVERSATION
            )
        return origins

    def _subject_signature(self, intent: QueryIntentV2) -> ContextSubjectSignature:
        metric_ids = [item.metric_id for item in intent.metric_refs]
        dimension_ids = [item.dimension_id for item in intent.dimension_refs]
        domain = self._domain_for_metrics(intent.metric_refs)
        payload = {
            "domain": domain,
            "metric_ids": metric_ids,
            "entity_types": [],
            "dimension_ids": dimension_ids,
            "comparison_kind": intent.comparison.kind.value if intent.comparison else None,
            "intent_kind": intent.intent_kind.value,
        }
        return ContextSubjectSignature(**payload, fingerprint=stable_fingerprint(payload))

    def _domain_for_metrics(self, metrics: list[MetricReference]) -> str:
        ids = {item.metric_id for item in metrics}
        if ids & self._SALES_METRICS:
            return "sales"
        return sorted(ids)[0].split(".", 1)[0] if ids else "unresolved"

    def _domain_from_text(self, text: str) -> str:
        if "estoque" in text:
            return "inventory"
        if "compra" in text:
            return "purchasing"
        if "financeiro" in text or "contas a pagar" in text:
            return "finance"
        return "sales"

    def _field_decisions(
        self,
        *,
        persisted_state: ConversationStateV2,
        resolved_intent: QueryIntentV2,
        explicit_fields: dict[str, bool],
        relationship: ContextRelationship,
        source_node_id: UUID,
    ) -> list[ContextFieldDecision]:
        mapping = {
            "active_metric_refs": (persisted_state.active_metric_refs, resolved_intent.metric_refs),
            "active_dimension_refs": (persisted_state.active_dimension_refs, resolved_intent.dimension_refs),
            "active_filters": (persisted_state.active_filters, resolved_intent.filters),
            "active_time_windows": (persisted_state.active_time_windows, resolved_intent.time_windows),
            "active_visualizations": (
                persisted_state.active_visualizations, resolved_intent.requested_visualizations,
            ),
        }
        result = []
        for field, (previous, resolved) in mapping.items():
            explicit = explicit_fields[field]
            if _json(previous) == _json(resolved):
                action = FieldDecisionAction.KEEP
            elif not resolved:
                action = FieldDecisionAction.CLEAR
            elif explicit and previous:
                action = (
                    FieldDecisionAction.APPEND
                    if relationship == ContextRelationship.DRILL_DOWN and field == "active_dimension_refs"
                    else FieldDecisionAction.REPLACE
                )
            elif explicit:
                action = FieldDecisionAction.SET
            else:
                action = FieldDecisionAction.INHERIT
            result.append(ContextFieldDecision(
                field_path=field,
                action=action,
                previous_value=_json(previous),
                current_value=_json(resolved if explicit else []),
                resolved_value=_json(resolved),
                previous_origin=persisted_state.field_origins.get(field.removeprefix("active_")),
                current_origin=FieldOrigin.EXPLICIT_USER if explicit else None,
                resolved_origin=(
                    FieldOrigin.EXPLICIT_USER if explicit
                    else FieldOrigin.INHERITED_CONVERSATION if resolved else None
                ),
                source_node_id=source_node_id,
                rule_id=f"CTX.FIELD.{field.upper()}.{action.value}",
                confidence=_confidence(
                    "Campo explicito prevaleceu." if explicit else "Contexto valido herdado.",
                    inherited=not explicit,
                ),
                inherited=not explicit and bool(resolved),
                overridden=explicit and bool(previous),
                removed=not resolved and bool(previous),
                conflict=False,
            ))
        return result

    def _operations(
        self,
        previous: ConversationStateV2,
        current: ConversationStateV2,
        decisions: list[ContextFieldDecision],
        subject: ContextSubjectSignature,
        comparison: ComparisonSpecification | None,
        clarification: ClarificationRequest | None,
        context: ContextResolutionContext,
    ) -> list:
        operations = []
        sequence = 0

        def common(field: str, reason: str, value: object):
            nonlocal sequence
            sequence += 1
            fingerprint = stable_fingerprint(value)
            return {
                "operation_id": stable_fingerprint(
                    [context.current_node_id, sequence, field, reason, fingerprint]
                )[:32],
                "field_path": field,
                "origin": FieldOrigin.SYSTEM_GENERATED,
                "source_node_id": context.current_node_id,
                "reason_code": reason,
                "confidence": _confidence("Operacao deterministica do motor de contexto."),
                "value_fingerprint": fingerprint,
            }

        values = {
            "active_metric_refs": current.active_metric_refs,
            "active_dimension_refs": current.active_dimension_refs,
            "active_filters": current.active_filters,
            "active_time_windows": current.active_time_windows,
            "active_visualizations": current.active_visualizations,
        }
        for decision in decisions:
            if decision.action == FieldDecisionAction.KEEP:
                continue
            value = values[decision.field_path]
            if not value:
                operations.append(ClearFieldOperation(
                    **common(decision.field_path, "FIELD_CLEARED", decision.field_path),
                ))
                continue
            operations.append(ClearFieldOperation(
                **common(decision.field_path, "FIELD_REPLACEMENT_START", decision.field_path),
            ))
            for item in value:
                operations.append(AppendFieldOperation(
                    **common(decision.field_path, "FIELD_VALUE_APPENDED", item),
                    value=item,
                ))
        operations.append(SetActiveSubjectOperation(
            **common("active_subject", "SUBJECT_RESOLVED", subject),
            subject=subject,
        ))
        if comparison is not None:
            operations.append(SetActiveComparisonOperation(
                **common("active_comparison", "COMPARISON_RESOLVED", comparison),
                comparison=comparison,
            ))
        elif previous.active_comparison is not None:
            operations.append(ClearActiveComparisonOperation(
                **common("active_comparison", "COMPARISON_CLEARED", "active_comparison"),
            ))
        if clarification is not None:
            operations.append(SetPendingClarificationOperation(
                **common("pending_clarification", "CLARIFICATION_PENDING", clarification),
                clarification=clarification,
            ))
        elif previous.pending_clarification_request is not None:
            operations.append(ResolvePendingClarificationOperation(
                **common("pending_clarification", "CLARIFICATION_RESOLVED", "resolved"),
            ))
        operations.append(SetActiveHeadReferenceOperation(
            **common("active_head_node_id", "HEAD_ADVANCED", context.current_node_id),
            head_node_id=context.current_node_id,
        ))
        return operations

    def _patch(
        self,
        *,
        operations: list,
        question: str,
        persisted_state: ConversationStateV2,
        provisional_state: ConversationStateV2,
        context: ContextResolutionContext,
    ) -> ContextPatchV2:
        identity = stable_fingerprint({
            "epoch": persisted_state.context_epoch,
            "version": persisted_state.context_version,
            "node": str(context.current_node_id),
            "question": _normalize(question),
            "state": compute_state_checksum(provisional_state),
        })
        payload = [_json(operation) for operation in operations]
        return ContextPatchV2(
            patch_id=identity[:32],
            base_context_epoch=persisted_state.context_epoch,
            base_context_version=persisted_state.context_version,
            base_node_id=context.parent_node_id,
            operations=operations,
            resolved_at=context.reference_datetime,
            checksum=stable_fingerprint(payload),
            idempotency_fingerprint=identity,
        )

    def _public_summary(
        self,
        intent: QueryIntentV2,
        decisions: list[ContextFieldDecision],
        relationship: ContextRelationship,
        clarification: ClarificationRequest | None,
    ) -> PublicContextSummary:
        return PublicContextSummary(
            active_metrics=[item.display_name for item in intent.metric_refs],
            active_periods=[item.label for item in intent.time_windows],
            inherited_filters=[
                f"{item.field_id}: {item.value}"
                for item in intent.filters
                if item.origin == FieldOrigin.INHERITED_CONVERSATION
            ],
            active_dimensions=[item.display_name for item in intent.dimension_refs],
            active_comparison=intent.comparison.kind.value if intent.comparison else None,
            replaced_fields=[
                item.field_path for item in decisions if item.overridden
            ],
            removed_fields=[
                item.field_path for item in decisions if item.removed
            ],
            reset=relationship == ContextRelationship.RESET,
            clarification_required=clarification is not None,
        )

    def _reset_result(
        self,
        *,
        current_intent: QueryIntentV2,
        persisted_state: ConversationStateV2,
        context: ContextResolutionContext,
        state_before: str,
        rules: list[str],
    ) -> ContextResolutionResult:
        cleared = ConversationStateV2(
            context_epoch=persisted_state.context_epoch,
            context_version=persisted_state.context_version,
            updated_at=context.reference_datetime,
        )
        fingerprint = stable_fingerprint(["reset", context.current_node_id, state_before])
        operation = ResetContextOperation(
            operation_id=fingerprint[:32],
            field_path="context",
            origin=FieldOrigin.EXPLICIT_USER,
            source_node_id=context.current_node_id,
            reason_code="EXPLICIT_TOTAL_RESET",
            confidence=_confidence("Reset solicitado explicitamente pelo usuario."),
            value_fingerprint=stable_fingerprint("TOTAL"),
            reset_scope="TOTAL",
        )
        patch = ContextPatchV2(
            patch_id=fingerprint[:32],
            base_context_epoch=persisted_state.context_epoch,
            base_context_version=persisted_state.context_version,
            base_node_id=context.parent_node_id,
            operations=[operation],
            resolved_at=context.reference_datetime,
            checksum=stable_fingerprint([operation]),
            idempotency_fingerprint=fingerprint,
        )
        resolved_state = cleared.model_copy(
            update={"last_context_patch_fingerprint": fingerprint}
        )
        return ContextResolutionResult(
            resolved_intent=current_intent,
            resolved_state=resolved_state,
            patch=patch,
            readiness=current_intent.readiness,
            confidence=current_intent.confidence,
            relationship=ContextRelationship.RESET,
            field_decisions=[],
            conflicts=[],
            clarification=None,
            warnings=[],
            public_context_summary=PublicContextSummary(
                reset=True,
                clarification_required=False,
            ),
            rule_ids=[*rules, "CTX.RESET.TOTAL"],
            state_checksum_before=state_before,
            state_checksum_after=compute_state_checksum(resolved_state),
            expected_context_version=persisted_state.context_version,
            base_node_id=context.parent_node_id,
        )

    def _preserve_out_of_scope_result(
        self,
        *,
        current_intent: QueryIntentV2,
        persisted_state: ConversationStateV2,
        context: ContextResolutionContext,
        state_before: str,
        rules: list[str],
        question: str,
    ) -> ContextResolutionResult:
        state = persisted_state.model_copy(update={
            "last_intent_kind": IntentKind.OUT_OF_SCOPE,
            "last_readiness": ExecutionReadiness.OUT_OF_SCOPE,
            "last_context_relationship": ContextRelationship.OUT_OF_SCOPE.value,
            "updated_at": context.reference_datetime,
        })
        patch = self._patch(
            operations=[],
            question=question,
            persisted_state=persisted_state,
            provisional_state=state,
            context=context,
        )
        state = state.model_copy(
            update={"last_context_patch_fingerprint": patch.idempotency_fingerprint}
        )
        return ContextResolutionResult(
            resolved_intent=current_intent,
            resolved_state=state,
            patch=patch,
            readiness=ExecutionReadiness.OUT_OF_SCOPE,
            confidence=current_intent.confidence,
            relationship=ContextRelationship.OUT_OF_SCOPE,
            field_decisions=[],
            conflicts=[],
            clarification=None,
            warnings=["O assunto ativo foi preservado porque a pergunta esta fora do escopo."],
            public_context_summary=PublicContextSummary(
                active_metrics=[
                    item.display_name for item in persisted_state.active_metric_refs
                ],
                active_periods=[
                    item.label for item in persisted_state.active_time_windows
                ],
                inherited_filters=[
                    f"{item.field_id}: {item.value}"
                    for item in persisted_state.active_filters
                ],
                active_dimensions=[
                    item.display_name for item in persisted_state.active_dimension_refs
                ],
                active_comparison=(
                    persisted_state.active_comparison.kind.value
                    if persisted_state.active_comparison else None
                ),
            ),
            rule_ids=[*rules, "CTX.OUT_OF_SCOPE.PRESERVE_ACTIVE_CONTEXT"],
            state_checksum_before=state_before,
            state_checksum_after=compute_state_checksum(state),
            expected_context_version=persisted_state.context_version,
            base_node_id=context.parent_node_id,
        )
