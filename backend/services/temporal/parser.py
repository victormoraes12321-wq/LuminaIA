from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from .lexicon_pt_br import (
    ACCUMULATED_ALIASES,
    CLOSED_MODIFIERS,
    COMPARISON_CONNECTORS,
    MONTHS,
)
from .models import TemporalRelation, TemporalSemanticType


@dataclass(frozen=True)
class ParsedTemporalExpression:
    start: int
    end: int
    source_text: str
    normalized_text: str
    semantic_type: TemporalSemanticType
    rule_id: str
    values: dict[str, Any]
    inferred: bool = False


@dataclass(frozen=True)
class TemporalParseResult:
    expressions: tuple[ParsedTemporalExpression, ...]
    relation: TemporalRelation
    unresolved: tuple[str, ...]


_MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
_ORDINAL_PATTERN = r"(?:primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|[1-4][oa]?)"


def parse_temporal_expressions(normalized: str) -> TemporalParseResult:
    expressions: list[ParsedTemporalExpression] = []
    occupied: list[tuple[int, int]] = []
    unresolved: list[str] = []

    def available(start: int, end: int) -> bool:
        return not any(start < current_end and end > current_start for current_start, current_end in occupied)

    def add(
        match: re.Match[str],
        semantic_type: TemporalSemanticType,
        rule_id: str,
        values: dict[str, Any],
        *,
        occupy: bool = True,
        inferred: bool = False,
    ) -> None:
        if not available(match.start(), match.end()):
            return
        expressions.append(
            ParsedTemporalExpression(
                start=match.start(),
                end=match.end(),
                source_text=match.group(0),
                normalized_text=match.group(0),
                semantic_type=semantic_type,
                rule_id=rule_id,
                values=values,
                inferred=inferred,
            )
        )
        if occupy:
            occupied.append(match.span())

    for range_match in re.finditer(
        rf"\bdo\s+({_ORDINAL_PATTERN})\s+ao\s+({_ORDINAL_PATTERN})\s+"
        r"trimestre(?:\s+de)?\s*(\d{4})\b",
        normalized,
    ):
        year = int(range_match.group(3))
        for group_index in (1, 2):
            start, end = range_match.span(group_index)
            expressions.append(
                ParsedTemporalExpression(
                    start=start,
                    end=end,
                    source_text=range_match.group(group_index),
                    normalized_text=range_match.group(group_index),
                    semantic_type=TemporalSemanticType.QUARTER,
                    rule_id="PTBR.CALENDAR.QUARTER",
                    values={
                        "quarter": _ordinal_number(range_match.group(group_index)),
                        "year": year,
                    },
                )
            )
        occupied.append(range_match.span())

    for list_match in re.finditer(
        r"\bmeses?\s+([0-9,\se]+?)\s+de\s+(\d{4})\b",
        normalized,
    ):
        year = int(list_match.group(2))
        number_region = list_match.group(1)
        region_start = list_match.start(1)
        for number_match in re.finditer(r"\d{1,2}", number_region):
            month = int(number_match.group(0))
            if not 1 <= month <= 12:
                continue
            start = region_start + number_match.start()
            end = region_start + number_match.end()
            expressions.append(
                ParsedTemporalExpression(
                    start=start,
                    end=end,
                    source_text=number_match.group(0),
                    normalized_text=number_match.group(0),
                    semantic_type=TemporalSemanticType.MONTH,
                    rule_id="PTBR.ABSOLUTE.MONTH",
                    values={"month": month, "year": year, "two_digit_year": False},
                )
            )
            occupied.append((start, end))
        occupied.append(list_match.span(2))

    # Fiscal rules precede civil quarter/year rules.
    fiscal_quarter_patterns = (
        re.compile(
            rf"\b(?:q|t)?([1-4])\s*(?:o\s+)?(?:trimestre\s+)?fiscal(?:\s+de)?\s*(\d{{4}})\b"
        ),
        re.compile(
            rf"\b({_ORDINAL_PATTERN})\s+trimestre\s+fiscal(?:\s+de)?\s*(\d{{4}})\b"
        ),
    )
    for pattern in fiscal_quarter_patterns:
        for match in pattern.finditer(normalized):
            raw_quarter = match.group(1)
            quarter = _ordinal_number(raw_quarter)
            add(
                match,
                TemporalSemanticType.FISCAL_PERIOD,
                "PTBR.FISCAL.QUARTER",
                {"quarter": quarter, "year": int(match.group(2)), "fiscal": True},
            )

    for match in re.finditer(r"\b(?:ano\s+fiscal(?:\s+de)?|exercicio\s+fiscal(?:\s+de)?|fy)\s*(\d{4})\b", normalized):
        add(
            match,
            TemporalSemanticType.FISCAL_PERIOD,
            "PTBR.FISCAL.YEAR",
            {"year": int(match.group(1)), "fiscal": True},
        )
    fiscal_relative_rules = (
        (r"\b(?:ano|exercicio)\s+fiscal\s+atual\b", "CURRENT_FISCAL_YEAR"),
        (r"\b(?:ano|exercicio)\s+fiscal\s+anterior\b", "PREVIOUS_FISCAL_YEAR"),
        (r"\btrimestre\s+fiscal\s+atual\b", "CURRENT_FISCAL_QUARTER"),
        (r"\btrimestre\s+fiscal\s+anterior\b", "PREVIOUS_FISCAL_QUARTER"),
    )
    for pattern, relative in fiscal_relative_rules:
        for match in re.finditer(pattern, normalized):
            add(
                match,
                TemporalSemanticType.FISCAL_PERIOD,
                "PTBR.FISCAL.QUARTER" if "QUARTER" in relative else "PTBR.FISCAL.YEAR",
                {"fiscal": True, "relative": relative},
            )

    # Accumulated aliases are closed lexical entries, not complete-question rules.
    for alias, canonical in sorted(ACCUMULATED_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        for match in re.finditer(rf"\b{re.escape(alias)}\b", normalized):
            add(
                match,
                TemporalSemanticType.ACCUMULATED_PERIOD,
                "PTBR.ACCUMULATED",
                {"accumulation": canonical},
            )

    # Rolling and closed windows.
    rolling_pattern = re.compile(
        r"\b(ultim[oa]s?|proxim[oa]s?)\s+(\d{1,3})\s+"
        r"(dia|dias|semana|semanas|mes|meses|ano|anos)"
        r"(?:\s+(fechad[oa]s?|complet[oa]s?|encerrad[oa]s?))?\b"
    )
    for match in rolling_pattern.finditer(normalized):
        modifier = match.group(1)
        closed = bool(match.group(4)) or any(
            word in match.group(0) for word in CLOSED_MODIFIERS
        )
        add(
            match,
            TemporalSemanticType.ROLLING_WINDOW,
            "PTBR.CLOSED.WINDOW" if closed else "PTBR.ROLLING.WINDOW",
            {
                "direction": "FUTURE" if modifier.startswith("proxim") else "PAST",
                "amount": int(match.group(2)),
                "unit": match.group(3),
                "closed": closed,
            },
        )
    for match in re.finditer(
        r"\b(?:contra|versus|vs)\s+(?:os\s+)?(\d{1,3})\s+dias\s+anteriores\b",
        normalized,
    ):
        add(
            match,
            TemporalSemanticType.ROLLING_WINDOW,
            "PTBR.ROLLING.WINDOW",
            {
                "direction": "PAST",
                "amount": int(match.group(1)),
                "unit": "dias",
                "closed": False,
                "previous_equivalent": True,
            },
        )

    # Explicit calendar dates.
    for match in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", normalized):
        add(
            match,
            TemporalSemanticType.ABSOLUTE_DATE,
            "PTBR.ABSOLUTE.DATE",
            {"year": int(match.group(1)), "month": int(match.group(2)), "day": int(match.group(3))},
        )
    for match in re.finditer(r"\b([0-3]?\d)[/-]([01]?\d)[/-](\d{4})\b", normalized):
        add(
            match,
            TemporalSemanticType.ABSOLUTE_DATE,
            "PTBR.ABSOLUTE.DATE",
            {"day": int(match.group(1)), "month": int(match.group(2)), "year": int(match.group(3))},
        )
    for match in re.finditer(
        rf"\b(?:dia\s+)?([0-3]?\d)\s+de\s+({_MONTH_PATTERN})\s+de\s+(\d{{4}})\b",
        normalized,
    ):
        add(
            match,
            TemporalSemanticType.ABSOLUTE_DATE,
            "PTBR.ABSOLUTE.DATE",
            {"day": int(match.group(1)), "month": MONTHS[match.group(2)], "year": int(match.group(3))},
        )

    # Fortnights precede generic month recognition because the month is part
    # of the richer expression.
    for match in re.finditer(
        rf"\b(primeira|segunda|1a|2a)\s+quinzena(?:\s+de)?\s+({_MONTH_PATTERN})(?:\s+de)?\s*(\d{{4}})?\b",
        normalized,
    ):
        add(
            match,
            TemporalSemanticType.FORTNIGHT,
            "PTBR.CALENDAR.FORTNIGHT",
            {
                "fortnight": 1 if match.group(1) in {"primeira", "1a"} else 2,
                "month": MONTHS[match.group(2)],
                "year": int(match.group(3)) if match.group(3) else None,
            },
        )
    for match in re.finditer(r"\b(primeira|segunda|1a|2a)\s+quinzena\b", normalized):
        add(
            match,
            TemporalSemanticType.FORTNIGHT,
            "PTBR.INFERENCE.YEAR",
            {
                "fortnight": 1 if match.group(1) in {"primeira", "1a"} else 2,
                "month": None,
                "year": None,
            },
            inferred=True,
        )

    # Explicit month/year forms, including configured two-digit policy at resolution.
    for match in re.finditer(r"\b(0?[1-9]|1[0-2])\s*/\s*(\d{2}|\d{4})\b", normalized):
        add(
            match,
            TemporalSemanticType.MONTH,
            "PTBR.ABSOLUTE.MONTH",
            {
                "month": int(match.group(1)),
                "year": int(match.group(2)),
                "two_digit_year": len(match.group(2)) == 2,
            },
        )
    for match in re.finditer(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", normalized):
        add(
            match,
            TemporalSemanticType.MONTH,
            "PTBR.ABSOLUTE.MONTH",
            {"month": int(match.group(2)), "year": int(match.group(1)), "two_digit_year": False},
        )
    for match in re.finditer(
        rf"\b(?:mes\s+)?({_MONTH_PATTERN})(?:\s+de|\s*/)?\s*(\d{{2}}|\d{{4}})\b",
        normalized,
    ):
        add(
            match,
            TemporalSemanticType.MONTH,
            "PTBR.ABSOLUTE.MONTH",
            {
                "month": MONTHS[match.group(1)],
                "year": int(match.group(2)),
                "two_digit_year": len(match.group(2)) == 2,
            },
        )
    for match in re.finditer(r"\bmes\s+(0?[1-9]|1[0-2])\s+de\s+(\d{4})\b", normalized):
        add(
            match,
            TemporalSemanticType.MONTH,
            "PTBR.ABSOLUTE.MONTH",
            {"month": int(match.group(1)), "year": int(match.group(2)), "two_digit_year": False},
        )

    # Civil quarter and semester.
    quarter_patterns = (
        re.compile(r"\b(?:t|q)([1-4])\s*/?\s*(?:de\s+)?(\d{4})\b"),
        re.compile(r"\b([1-4])t\s*(\d{4})\b"),
        re.compile(rf"\b({_ORDINAL_PATTERN})\s+trimestre(?:\s+de)?\s*(\d{{4}})\b"),
    )
    for pattern in quarter_patterns:
        for match in pattern.finditer(normalized):
            add(
                match,
                TemporalSemanticType.QUARTER,
                "PTBR.CALENDAR.QUARTER",
                {"quarter": _ordinal_number(match.group(1)), "year": int(match.group(2))},
            )
    for match in re.finditer(r"\b(?:t|q)([1-4])\b", normalized):
        add(
            match,
            TemporalSemanticType.QUARTER,
            "PTBR.INFERENCE.YEAR",
            {"quarter": int(match.group(1)), "year": None},
            inferred=True,
        )
    for match in re.finditer(rf"\b({_ORDINAL_PATTERN})\s+trimestre\b", normalized):
        add(
            match,
            TemporalSemanticType.QUARTER,
            "PTBR.INFERENCE.YEAR",
            {"quarter": _ordinal_number(match.group(1)), "year": None},
            inferred=True,
        )
    semester_patterns = (
        re.compile(r"\bs([12])\s*/?\s*(\d{4})\b"),
        re.compile(r"\b([12])s\s*(\d{4})\b"),
        re.compile(r"\b(primeir[oa]|segund[oa]|[12][oa]?)\s+semestre(?:\s+de)?\s*(\d{4})\b"),
    )
    for pattern in semester_patterns:
        for match in pattern.finditer(normalized):
            add(
                match,
                TemporalSemanticType.SEMESTER,
                "PTBR.CALENDAR.SEMESTER",
                {"semester": _ordinal_number(match.group(1)), "year": int(match.group(2))},
            )
    for match in re.finditer(r"\b(?:s([12])|([12])s)\b", normalized):
        add(
            match,
            TemporalSemanticType.SEMESTER,
            "PTBR.INFERENCE.YEAR",
            {"semester": int(match.group(1) or match.group(2)), "year": None},
            inferred=True,
        )

    for match in re.finditer(r"\bsemana(?:\s+iso)?\s+(\d{1,2})\s+de\s+(\d{4})\b", normalized):
        add(
            match,
            TemporalSemanticType.WEEK,
            "PTBR.CALENDAR.WEEK",
            {"iso_week": int(match.group(1)), "year": int(match.group(2))},
        )
    for match in re.finditer(
        rf"\b(primeira|segunda|1a|2a)\s+quinzena(?:\s+de)?\s+({_MONTH_PATTERN})(?:\s+de)?\s*(\d{{4}})?\b",
        normalized,
    ):
        add(
            match,
            TemporalSemanticType.FORTNIGHT,
            "PTBR.CALENDAR.FORTNIGHT",
            {
                "fortnight": 1 if match.group(1) in {"primeira", "1a"} else 2,
                "month": MONTHS[match.group(2)],
                "year": int(match.group(3)) if match.group(3) else None,
            },
        )

    # Relative named periods.
    relative_rules: tuple[tuple[str, str], ...] = (
        (r"\banteontem\b", "DAY_BEFORE_YESTERDAY"),
        (r"\bontem\b", "YESTERDAY"),
        (r"\bhoje\b", "TODAY"),
        (r"\bamanha\b", "TOMORROW"),
        (r"\b(?:esta|semana\s+atual)\s*semana\b|\bsemana\s+atual\b", "CURRENT_WEEK"),
        (r"\b(?:semana\s+passada|semana\s+anterior|ultima\s+semana)\b", "PREVIOUS_WEEK"),
        (r"\b(?:este|esse|mes\s+atual)\s*mes\b|\bmes\s+atual\b", "CURRENT_MONTH"),
        (r"\b(?:mes\s+passado|mes\s+anterior|ultimo\s+mes)\b", "PREVIOUS_MONTH"),
        (r"\b(?:trimestre\s+atual|este\s+trimestre)\b", "CURRENT_QUARTER"),
        (r"\b(?:trimestre\s+anterior|ultimo\s+trimestre)\b", "PREVIOUS_QUARTER"),
        (r"\b(?:semestre\s+atual|este\s+semestre)\b", "CURRENT_SEMESTER"),
        (r"\b(?:semestre\s+anterior|ultimo\s+semestre)\b", "PREVIOUS_SEMESTER"),
        (r"\b(?:ano\s+atual|este\s+ano)\b", "CURRENT_YEAR"),
        (r"\b(?:ano\s+passado|ano\s+anterior|ultimo\s+ano)\b", "PREVIOUS_YEAR"),
    )
    for pattern, relative in relative_rules:
        for match in re.finditer(pattern, normalized):
            add(
                match,
                TemporalSemanticType.RELATIVE_PERIOD,
                "PTBR.RELATIVE.DAY" if relative in {"TODAY", "YESTERDAY", "DAY_BEFORE_YESTERDAY", "TOMORROW"} else "PTBR.RELATIVE.PERIOD",
                {"relative": relative},
            )

    # Month names without years are retained and resolved by context policy.
    for match in re.finditer(rf"\b({_MONTH_PATTERN})\b", normalized):
        add(
            match,
            TemporalSemanticType.MONTH,
            "PTBR.INFERENCE.YEAR",
            {"month": MONTHS[match.group(1)], "year": None, "two_digit_year": False},
            inferred=True,
        )

    # Standalone civil years, excluding years already consumed by richer expressions.
    for match in re.finditer(r"\b(?:ano(?:\s+de)?\s+|em\s+)?(20\d{2})\b", normalized):
        add(
            match,
            TemporalSemanticType.YEAR,
            "PTBR.ABSOLUTE.YEAR",
            {"year": int(match.group(1))},
        )

    # Material ambiguities are never silently consumed.
    for match in re.finditer(r"\b([0-3]?\d)/([01]?\d)\b(?!/\d)", normalized):
        if available(match.start(), match.end()):
            unresolved.append(match.group(0))
    for match in re.finditer(r"\bdia\s+([0-3]?\d)\b", normalized):
        if available(match.start(), match.end()):
            unresolved.append(match.group(0))
    for phrase in ("ultimo periodo", "periodo anterior equivalente", "mesmo periodo anterior"):
        if phrase in normalized and not expressions:
            unresolved.append(phrase)
    if not expressions:
        generic_month = re.search(r"\b(?:do|no|neste|nesse)\s+mes\b", normalized)
        if generic_month:
            add(
                generic_month,
                TemporalSemanticType.RELATIVE_PERIOD,
                "PTBR.RELATIVE.PERIOD",
                {"relative": "CURRENT_MONTH"},
            )
    if not expressions:
        unknown_temporal = re.search(
            r"\b(?:mes|semana|trimestre|semestre|periodo)\s+"
            r"(?:lunar|sideral|desconhecido|indefinido)\b",
            normalized,
        )
        if unknown_temporal:
            unresolved.append(unknown_temporal.group(0))

    expressions.sort(key=lambda item: (item.start, item.end))
    expressions = _propagate_shared_year(expressions, normalized)
    relation = _detect_relation(normalized, expressions)
    return TemporalParseResult(
        expressions=tuple(expressions),
        relation=relation,
        unresolved=tuple(dict.fromkeys(unresolved)),
    )


def _ordinal_number(value: str) -> int:
    normalized = value.rstrip("oa")
    words = {
        "primeir": 1,
        "primeiro": 1,
        "primeira": 1,
        "segund": 2,
        "segundo": 2,
        "segunda": 2,
        "terceir": 3,
        "terceiro": 3,
        "terceira": 3,
        "quart": 4,
        "quarto": 4,
        "quarta": 4,
    }
    if normalized.isdigit():
        return int(normalized)
    return words.get(normalized, words.get(value, 1))


def _propagate_shared_year(
    expressions: list[ParsedTemporalExpression],
    normalized: str,
) -> list[ParsedTemporalExpression]:
    explicit_month_years = [
        expression
        for expression in expressions
        if expression.semantic_type
        in {
            TemporalSemanticType.MONTH,
            TemporalSemanticType.QUARTER,
            TemporalSemanticType.SEMESTER,
        }
        and expression.values.get("year") is not None
    ]
    if not explicit_month_years:
        return expressions
    propagated: list[ParsedTemporalExpression] = []
    for expression in expressions:
        if (
            expression.semantic_type
            not in {
                TemporalSemanticType.MONTH,
                TemporalSemanticType.QUARTER,
                TemporalSemanticType.SEMESTER,
            }
            or expression.values.get("year") is not None
        ):
            propagated.append(expression)
            continue
        compatible = [
            candidate
            for candidate in explicit_month_years
            if candidate.semantic_type == expression.semantic_type
        ]
        if not compatible:
            propagated.append(expression)
            continue
        nearest = min(
            compatible,
            key=lambda candidate: abs(candidate.start - expression.start),
        )
        between = normalized[min(expression.end, nearest.end) : max(expression.start, nearest.start)]
        if re.search(r"(?:,|\be\b|\ba\b|\bao\b|\bate\b|\bversus\b|\bvs\b|\bcontra\b)", between):
            values = dict(expression.values)
            values["year"] = nearest.values["year"]
            values["shared_year"] = True
            resolved_rule = {
                TemporalSemanticType.MONTH: "PTBR.ABSOLUTE.MONTH",
                TemporalSemanticType.QUARTER: "PTBR.CALENDAR.QUARTER",
                TemporalSemanticType.SEMESTER: "PTBR.CALENDAR.SEMESTER",
            }[expression.semantic_type]
            propagated.append(replace(expression, values=values, rule_id=resolved_rule))
        else:
            propagated.append(expression)
    return propagated


def _detect_relation(
    normalized: str,
    expressions: list[ParsedTemporalExpression],
) -> TemporalRelation:
    if not expressions:
        return TemporalRelation.NONE
    if any(connector.strip() in normalized for connector in COMPARISON_CONNECTORS):
        return TemporalRelation.COMPARISON
    if len(expressions) >= 2:
        first, last = expressions[0], expressions[-1]
        between = normalized[first.end : last.start]
        prefix = normalized[max(0, first.start - 10) : first.start]
        if re.search(r"\bentre\s*$", prefix) and re.search(r"\be\b", between):
            return TemporalRelation.RANGE
        if re.search(r"\bdesde\s*$", prefix) and re.search(r"\b(?:a|ate)\b", between):
            return TemporalRelation.RANGE
        if re.search(r"\b(?:de|do)\s*$", prefix) and re.search(r"\b(?:a|ao|ate)\b", between):
            return TemporalRelation.RANGE
        if re.search(r"\bate\b", between):
            return TemporalRelation.RANGE
        if (
            first.semantic_type == TemporalSemanticType.ABSOLUTE_DATE
            and last.semantic_type == TemporalSemanticType.ABSOLUTE_DATE
            and re.fullmatch(r"\s*(?:a|ate|to|->|--?)\s*", between)
        ):
            return TemporalRelation.RANGE
        if re.fullmatch(r"\s*-\s*", between):
            return TemporalRelation.RANGE
        return TemporalRelation.PERIOD_LIST
    return TemporalRelation.SINGLE
