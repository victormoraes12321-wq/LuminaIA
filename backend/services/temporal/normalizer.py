from __future__ import annotations

import hashlib
import logging
import time
import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from contracts.analytical_v2 import (
    ClarificationRequest,
    ConfidenceAssessment,
    ConfidenceLevel,
    ExecutionReadiness,
    FieldOrigin,
    TimeWindow,
    TemporalGranularity,
)

from .models import (
    TEMPORAL_NORMALIZER_VERSION,
    ResolvedTemporalItem,
    TemporalComparisonGroup,
    TemporalContext,
    TemporalNormalizationResult,
    TemporalRelation,
    TemporalSemanticType,
    TemporalTextSpan,
)
from .clock import SystemTemporalClock, TemporalClock
from .parser import ParsedTemporalExpression, parse_temporal_expressions
from .resolver import (
    FutureTemporalPeriodError,
    TemporalAmbiguityError,
    TemporalResolutionError,
    resolve_expression,
)
from .tokenizer import normalize_temporal_text
from .timezone_support import InvalidTemporalTimezone, resolve_timezone


logger = logging.getLogger("luminaai.services.temporal")
MAX_TEMPORAL_INPUT_LENGTH = 4000
MAX_TEMPORAL_EXPRESSIONS = 32


class TemporalInputError(ValueError):
    pass


def default_temporal_context(
    *,
    reference_datetime: datetime | None = None,
    timezone_name: str = "America/Sao_Paulo",
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER,
    clock: TemporalClock | None = None,
) -> TemporalContext:
    reference = reference_datetime or (clock or SystemTemporalClock()).now()
    return TemporalContext(
        timezone=timezone_name,
        reference_datetime=reference,
        origin=origin,
    )


class TemporalNormalizer:
    """Pure, stateless and deterministic pt-BR temporal normalization service."""

    version = TEMPORAL_NORMALIZER_VERSION

    def normalize(
        self,
        text: str,
        context: TemporalContext,
    ) -> TemporalNormalizationResult:
        started = time.perf_counter()
        original = str(text or "")
        if len(original) > MAX_TEMPORAL_INPUT_LENGTH:
            raise TemporalInputError(
                f"Temporal input exceeds {MAX_TEMPORAL_INPUT_LENGTH} characters"
            )
        try:
            zone = resolve_timezone(context.timezone)
        except InvalidTemporalTimezone:
            return self._clarification_result(
                context=context,
                started=started,
                reason="Timezone IANA invalido ou nao autorizado.",
                question="Qual timezone configurado deve ser usado nesta consulta?",
                missing_fields=["timezone"],
                options=["America/Sao_Paulo", "UTC"],
                unresolved=(context.timezone,),
            )

        reference = context.reference_datetime.astimezone(zone)
        normalized = normalize_temporal_text(original)
        if _requests_equivalent_previous_period(normalized):
            if not context.base_time_windows:
                return self._clarification_result(
                    context=context,
                    started=started,
                    reason="O periodo equivalente anterior depende de um periodo base.",
                    question="Qual e o periodo base para calcular o periodo anterior equivalente?",
                    missing_fields=["base_time_windows"],
                    unresolved=(normalized[:256],),
                )
            return self._equivalent_previous_result(
                original=original,
                normalized=normalized,
                context=context,
                reference=reference,
                started=started,
            )
        parsed = parse_temporal_expressions(normalized)
        if len(parsed.expressions) > MAX_TEMPORAL_EXPRESSIONS:
            raise TemporalInputError(
                f"Temporal input contains more than {MAX_TEMPORAL_EXPRESSIONS} expressions"
            )

        items: list[ResolvedTemporalItem] = []
        spans: list[TemporalTextSpan] = []
        warnings: list[str] = []
        unresolved = list(parsed.unresolved)
        ambiguity_options: list[str] = []

        for index, expression in enumerate(parsed.expressions, start=1):
            confidence = self._confidence_for_expression(expression)
            try:
                start, end, label, granularity, partial, item_warnings = resolve_expression(
                    expression,
                    context,
                )
            except TemporalAmbiguityError as exc:
                unresolved.append(expression.source_text)
                ambiguity_options.extend(exc.candidates)
                warnings.append(str(exc))
                continue
            except (TemporalResolutionError, FutureTemporalPeriodError) as exc:
                unresolved.append(expression.source_text)
                warnings.append(str(exc))
                continue

            item_id = f"temporal_item_{index}"
            window = TimeWindow(
                window_id=f"temporal_window_{index}",
                label=label,
                start=start,
                end=end,
                end_inclusive=True,
                granularity=granularity,
                timezone=context.timezone,
                origin=context.origin,
                confidence=confidence,
                raw_expression=expression.source_text[:256],
            )
            item = ResolvedTemporalItem(
                item_id=item_id,
                window=window,
                semantic_type=expression.semantic_type,
                source_text=expression.source_text,
                rule_id=expression.rule_id,
                confidence=confidence,
                warnings=tuple(item_warnings),
                partial=partial,
                inferred=expression.inferred or bool(item_warnings),
                requires_confirmation=confidence.requires_confirmation,
            )
            items.append(item)
            warnings.extend(item_warnings)
            spans.append(
                TemporalTextSpan(
                    start=expression.start,
                    end=max(expression.end, expression.start + 1),
                    original=_safe_original_slice(original, expression),
                    normalized=expression.normalized_text,
                    rule_id=expression.rule_id,
                    confidence=confidence,
                )
            )

        items = _stable_deduplicate(items)
        relation = parsed.relation

        if relation == TemporalRelation.COMPARISON and len(items) < 2:
            unresolved.append("segundo operando temporal")
            return self._clarification_result(
                context=context,
                started=started,
                reason="A comparacao precisa de pelo menos dois periodos resolvidos.",
                question="Qual e o segundo periodo que deve ser comparado?",
                missing_fields=["time_windows"],
                options=ambiguity_options,
                unresolved=tuple(dict.fromkeys(unresolved)),
                warnings=tuple(dict.fromkeys(warnings)),
                items=tuple(items),
                spans=tuple(spans),
                relation=relation,
            )

        if unresolved:
            return self._clarification_result(
                context=context,
                started=started,
                reason="Uma expressao temporal possui mais de uma interpretacao valida ou nao foi resolvida.",
                question="Qual periodo exato deve ser usado nesta consulta?",
                missing_fields=["temporal_expression"],
                options=ambiguity_options,
                unresolved=tuple(dict.fromkeys(unresolved)),
                warnings=tuple(dict.fromkeys(warnings)),
                items=tuple(items),
                spans=tuple(spans),
                relation=relation,
            )

        range_item: ResolvedTemporalItem | None = None
        period_list: tuple[ResolvedTemporalItem, ...] = ()
        comparison_groups: tuple[TemporalComparisonGroup, ...] = ()
        windows: tuple[TimeWindow, ...]

        if relation == TemporalRelation.RANGE and len(items) >= 2:
            first, last = items[0], items[-1]
            if first.window.start > last.window.end:
                return self._clarification_result(
                    context=context,
                    started=started,
                    reason="O inicio do intervalo ocorre depois do fim.",
                    question="Quais anos devem ser usados nas duas extremidades do intervalo?",
                    missing_fields=["time_range"],
                    unresolved=(f"{first.source_text} -> {last.source_text}",),
                    warnings=("Intervalo temporal invertido nao foi auto-corrigido.",),
                    items=tuple(items),
                    spans=tuple(spans),
                    relation=relation,
                )
            range_confidence = _aggregate_confidence(items)
            range_window = TimeWindow(
                window_id="temporal_range_1",
                label=f"{first.window.label} ate {last.window.label}",
                start=first.window.start,
                end=last.window.end,
                end_inclusive=True,
                granularity=(
                    first.window.granularity
                    if first.window.granularity == last.window.granularity
                    else TemporalGranularity.CUSTOM
                ),
                timezone=context.timezone,
                origin=context.origin,
                confidence=range_confidence,
                raw_expression=normalized[:256],
            )
            range_item = ResolvedTemporalItem(
                item_id="temporal_range_item_1",
                window=range_window,
                semantic_type=TemporalSemanticType.DATE_RANGE,
                source_text=normalized[:256],
                rule_id="PTBR.RELATION.RANGE",
                confidence=range_confidence,
                warnings=tuple(dict.fromkeys(warnings)),
                partial=any(item.partial for item in items),
                inferred=any(item.inferred for item in items),
            )
            windows = (range_window,)
        elif relation == TemporalRelation.PERIOD_LIST:
            period_list = tuple(items)
            windows = tuple(item.window for item in items)
        elif relation == TemporalRelation.COMPARISON:
            comparison_groups = (
                TemporalComparisonGroup(
                    group_id="temporal_comparison_1",
                    operand_item_ids=tuple(item.item_id for item in items),
                ),
            )
            windows = tuple(item.window for item in items)
        else:
            windows = tuple(item.window for item in items)

        confidence = _aggregate_confidence(items)
        rule_ids = tuple(
            dict.fromkeys(
                [item.rule_id for item in items]
                + (
                    ["PTBR.RELATION.RANGE"]
                    if relation == TemporalRelation.RANGE
                    else ["PTBR.RELATION.LIST"]
                    if relation == TemporalRelation.PERIOD_LIST
                    else ["PTBR.RELATION.COMPARISON"]
                    if relation == TemporalRelation.COMPARISON
                    else []
                )
            )
        )
        result = TemporalNormalizationResult(
            windows=windows,
            range=range_item,
            period_list=period_list,
            comparison_groups=comparison_groups,
            items=tuple(items),
            relation=relation,
            consumed_spans=tuple(spans),
            unresolved_expressions=(),
            confidence=confidence,
            readiness=ExecutionReadiness.READY,
            warnings=tuple(dict.fromkeys(warnings)),
            rule_ids=rule_ids,
            reference_datetime=reference,
            timezone=context.timezone,
            calendar_kind=(
                "FISCAL"
                if any(item.semantic_type == TemporalSemanticType.FISCAL_PERIOD for item in items)
                else "CIVIL"
            ),
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        self._log_result(result, original)
        return result

    def _clarification_result(
        self,
        *,
        context: TemporalContext,
        started: float,
        reason: str,
        question: str,
        missing_fields: list[str],
        options: list[str] | tuple[str, ...] = (),
        unresolved: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
        items: tuple[ResolvedTemporalItem, ...] = (),
        spans: tuple[TemporalTextSpan, ...] = (),
        relation: TemporalRelation = TemporalRelation.NONE,
    ) -> TemporalNormalizationResult:
        confidence = _low_confidence(reason)
        clarification = ClarificationRequest(
            question=question,
            missing_fields=missing_fields,
            candidate_options=list(dict.fromkeys(options))[:20],
            reason=reason,
            confidence=confidence,
        )
        result = TemporalNormalizationResult(
            windows=tuple(item.window for item in items),
            items=items,
            relation=relation,
            consumed_spans=spans,
            unresolved_expressions=unresolved,
            confidence=confidence,
            readiness=ExecutionReadiness.CLARIFICATION_REQUIRED,
            clarification=clarification,
            warnings=warnings,
            rule_ids=tuple(dict.fromkeys([item.rule_id for item in items] + ["PTBR.AMBIGUOUS"])),
            reference_datetime=context.reference_datetime,
            timezone=context.timezone,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        self._log_result(result, "")
        return result

    def _equivalent_previous_result(
        self,
        *,
        original: str,
        normalized: str,
        context: TemporalContext,
        reference: datetime,
        started: float,
    ) -> TemporalNormalizationResult:
        confidence = ConfidenceAssessment(
            level=ConfidenceLevel.HIGH,
            score=Decimal("1"),
            reasons=["Periodo equivalente resolvido a partir do contexto estruturado."],
            requires_confirmation=False,
        )
        base = context.base_time_windows[0].model_copy(
            update={
                "window_id": "temporal_window_1",
                "origin": FieldOrigin.INHERITED_CONVERSATION,
            }
        )
        if "ano passado" in normalized or "ano anterior" in normalized:
            previous_start = _shift_year_clamped(base.start, -1)
            previous_end = _shift_year_clamped(base.end, -1)
        else:
            length = (base.end - base.start).days + 1
            previous_end = base.start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=length - 1)
        previous = base.model_copy(
            update={
                "window_id": "temporal_window_2",
                "label": f"Periodo anterior equivalente a {base.label}",
                "start": previous_start,
                "end": previous_end,
                "origin": context.origin,
                "confidence": confidence,
                "raw_expression": normalized[:256],
            }
        )
        items = (
            ResolvedTemporalItem(
                item_id="temporal_item_1",
                window=base,
                semantic_type=TemporalSemanticType.COMPARISON_TEMPORAL,
                source_text=base.label,
                rule_id="PTBR.RELATIVE.PERIOD",
                confidence=confidence,
                inferred=True,
            ),
            ResolvedTemporalItem(
                item_id="temporal_item_2",
                window=previous,
                semantic_type=TemporalSemanticType.COMPARISON_TEMPORAL,
                source_text=normalized[:256],
                rule_id="PTBR.RELATIVE.PERIOD",
                confidence=confidence,
            ),
        )
        result = TemporalNormalizationResult(
            windows=(base, previous),
            items=items,
            relation=TemporalRelation.COMPARISON,
            comparison_groups=(
                TemporalComparisonGroup(
                    group_id="temporal_comparison_1",
                    operand_item_ids=("temporal_item_1", "temporal_item_2"),
                ),
            ),
            consumed_spans=(
                TemporalTextSpan(
                    start=0,
                    end=max(len(normalized), 1),
                    original=original[:256] or normalized[:256],
                    normalized=normalized[:256],
                    rule_id="PTBR.RELATIVE.PERIOD",
                    confidence=confidence,
                ),
            ),
            confidence=confidence,
            readiness=ExecutionReadiness.READY,
            rule_ids=("PTBR.RELATIVE.PERIOD", "PTBR.RELATION.COMPARISON"),
            reference_datetime=reference,
            timezone=context.timezone,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        self._log_result(result, original)
        return result

    @staticmethod
    def _confidence_for_expression(
        expression: ParsedTemporalExpression,
    ) -> ConfidenceAssessment:
        if expression.inferred or expression.values.get("two_digit_year"):
            return ConfidenceAssessment(
                level=ConfidenceLevel.MEDIUM,
                score=Decimal("0.75"),
                reasons=["Expressao temporal resolvida por politica deterministica explicita."],
                requires_confirmation=False,
            )
        return ConfidenceAssessment(
            level=ConfidenceLevel.HIGH,
            score=Decimal("1"),
            reasons=["Expressao temporal completa reconhecida por regra deterministica."],
            requires_confirmation=False,
        )

    @staticmethod
    def _log_result(result: TemporalNormalizationResult, original: str) -> None:
        fingerprint = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16] if original else None
        logger.info(
            "temporal_normalization version=%s fingerprint=%s rules=%s expressions=%d "
            "windows=%d ambiguity=%s confidence=%s timezone=%s calendar=%s duration_ms=%.3f readiness=%s",
            result.normalizer_version,
            fingerprint,
            ",".join(result.rule_ids),
            len(result.items),
            len(result.windows),
            bool(result.unresolved_expressions),
            result.confidence.level.value,
            result.timezone,
            result.calendar_kind,
            result.duration_ms,
            result.readiness.value,
        )


def _safe_original_slice(
    original: str,
    expression: ParsedTemporalExpression,
) -> str:
    candidate = original[expression.start : expression.end]
    return candidate.strip() or expression.source_text


def _stable_deduplicate(
    items: list[ResolvedTemporalItem],
) -> list[ResolvedTemporalItem]:
    seen: set[tuple[object, ...]] = set()
    result: list[ResolvedTemporalItem] = []
    for item in items:
        key = (
            item.window.start,
            item.window.end,
            item.window.granularity,
            item.window.timezone,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return [
        item.model_copy(
            update={
                "item_id": f"temporal_item_{index}",
                "window": item.window.model_copy(update={"window_id": f"temporal_window_{index}"}),
            }
        )
        for index, item in enumerate(result, start=1)
    ]


def _aggregate_confidence(
    items: list[ResolvedTemporalItem],
) -> ConfidenceAssessment:
    if not items:
        return ConfidenceAssessment(
            level=ConfidenceLevel.UNKNOWN,
            score=Decimal("0"),
            reasons=["Nenhuma expressao temporal foi informada."],
            requires_confirmation=False,
        )
    levels = {item.confidence.level for item in items}
    if ConfidenceLevel.LOW in levels:
        return _low_confidence("Ha expressao temporal ambigua.")
    if ConfidenceLevel.MEDIUM in levels:
        return ConfidenceAssessment(
            level=ConfidenceLevel.MEDIUM,
            score=Decimal("0.75"),
            reasons=["Ao menos um periodo foi resolvido por politica deterministica."],
            requires_confirmation=False,
        )
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["Todos os periodos foram reconhecidos diretamente."],
        requires_confirmation=False,
    )


def _low_confidence(reason: str) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.LOW,
        score=Decimal("0.25"),
        reasons=[reason],
        requires_confirmation=True,
    )


def _requests_equivalent_previous_period(normalized: str) -> bool:
    return any(
        phrase in normalized
        for phrase in (
            "mesmo periodo do ano passado",
            "mesmo mes do ano anterior",
            "mesmo trimestre do ano passado",
            "periodo anterior equivalente",
            "mesmo periodo anterior",
        )
    )


def _shift_year_clamped(value: date, offset: int) -> date:
    year = value.year + offset
    return value.replace(day=min(value.day, calendar.monthrange(year, value.month)[1]), year=year)
