from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .enums import (
    ComparisonCalculation,
    ConfidenceLevel,
    FieldOrigin,
    TemporalGranularity,
    VisualizationKind,
)
from .models import ConfidenceAssessment, TimeWindow, VisualizationSpecification


MONTH_NAMES: dict[str, int] = {
    "janeiro": 1,
    "jan": 1,
    "fevereiro": 2,
    "fev": 2,
    "marco": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "maio": 5,
    "mai": 5,
    "junho": 6,
    "jun": 6,
    "julho": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "setembro": 9,
    "set": 9,
    "outubro": 10,
    "out": 10,
    "novembro": 11,
    "nov": 11,
    "dezembro": 12,
    "dez": 12,
}
MONTH_PATTERN = "|".join(sorted(MONTH_NAMES, key=len, reverse=True))
MONTH_LABELS = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Marco",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


@dataclass(frozen=True)
class _PeriodOccurrence:
    position: int
    month: int
    year: int
    raw: str


def normalize_analytical_text(value: str) -> str:
    text = str(value or "").lower()
    for _ in range(2):
        if not any(marker in text for marker in ("Ã", "Â", "â€")):
            break
        try:
            repaired = text.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
        if repaired == text:
            break
        text = repaired
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"mar\?+o", "marco", normalized)
    normalized = re.sub(r"m\?+s", "mes", normalized)
    normalized = re.sub(r"gr\?+fico", "grafico", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def extract_time_windows(
    text: str,
    *,
    timezone_name: str = "America/Sao_Paulo",
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER,
    temporal_context: object | None = None,
) -> list[TimeWindow]:
    from services.temporal import (
        TemporalContext,
        TemporalNormalizer,
        default_temporal_context,
    )

    context = temporal_context
    if context is None:
        context = default_temporal_context(
            timezone_name=timezone_name,
            origin=origin,
        )
    if not isinstance(context, TemporalContext):
        raise TypeError("temporal_context must be a TemporalContext")
    result = TemporalNormalizer().normalize(text, context)
    return [
        window.model_copy(update={"window_id": f"period_{index}"})
        for index, window in enumerate(result.windows, start=1)
    ]


def extract_visualizations(
    text: str,
    *,
    metric_ids: list[str] | None = None,
    dimension_ids: list[str] | None = None,
    data_reference: str = "primary_dataset",
    origin: FieldOrigin = FieldOrigin.EXPLICIT_USER,
) -> list[VisualizationSpecification]:
    normalized = normalize_analytical_text(text)
    patterns: tuple[tuple[VisualizationKind, re.Pattern[str]], ...] = (
        (VisualizationKind.DATA_TABLE, re.compile(r"\b(?:tabela|planilha|grade|listagem)\b")),
        (VisualizationKind.BAR_CHART, re.compile(r"\b(?:grafico\s+de\s+)?(?:barra|barras|coluna|colunas)\b")),
        (VisualizationKind.LINE_CHART, re.compile(r"\b(?:grafico\s+de\s+)?(?:linha|linhas|evolucao)\b")),
        (VisualizationKind.PIE_CHART, re.compile(r"\b(?:pizza|grafico\s+de\s+pizza)\b")),
        (VisualizationKind.DONUT_CHART, re.compile(r"\b(?:donut|rosca)\b")),
        (VisualizationKind.KPI_CARD, re.compile(r"\b(?:kpi|cartao|card)\b")),
        (VisualizationKind.AREA_CHART, re.compile(r"\b(?:grafico\s+de\s+)?area\b")),
        (VisualizationKind.SCATTER_CHART, re.compile(r"\b(?:scatter|dispersao)\b")),
        (VisualizationKind.HEATMAP, re.compile(r"\b(?:heatmap|mapa\s+de\s+calor)\b")),
        (VisualizationKind.TREEMAP, re.compile(r"\btreemap\b")),
        (VisualizationKind.FUNNEL, re.compile(r"\b(?:funil|funnel)\b")),
    )
    matches: list[tuple[int, VisualizationKind]] = []
    occupied_graph_spans: list[tuple[int, int]] = []
    for kind, pattern in patterns:
        for match in pattern.finditer(normalized):
            matches.append((match.start(), kind))
            if "grafico" in match.group(0):
                occupied_graph_spans.append(match.span())

    for match in re.finditer(r"\bgrafico\b", normalized):
        if not any(start <= match.start() < end for start, end in occupied_graph_spans):
            matches.append((match.start(), VisualizationKind.BAR_CHART))

    matches.sort(key=lambda item: item[0])
    ordered_kinds: list[VisualizationKind] = []
    for _, kind in matches:
        if kind not in ordered_kinds:
            ordered_kinds.append(kind)

    metric_values = list(metric_ids or [])
    dimension_values = list(dimension_ids or [])
    visualizations: list[VisualizationSpecification] = []
    for index, kind in enumerate(ordered_kinds, start=1):
        visualizations.append(
            VisualizationSpecification(
                visualization_id=f"visual_{index}",
                kind=kind,
                title=_visualization_title(kind),
                metric_ids=metric_values,
                dimension_ids=dimension_values,
                data_reference=data_reference,
                priority=100 - index,
                is_primary=index == 1,
                origin=origin,
                options={},
            )
        )
    return visualizations


def comparison_requested(text: str) -> bool:
    from services.temporal import (
        TemporalNormalizer,
        TemporalRelation,
        default_temporal_context,
    )

    result = TemporalNormalizer().normalize(text, default_temporal_context())
    return result.relation == TemporalRelation.COMPARISON


def default_comparison_calculations() -> list[ComparisonCalculation]:
    return [
        ComparisonCalculation.VALUE,
        ComparisonCalculation.ABSOLUTE_DIFFERENCE,
        ComparisonCalculation.PERCENTAGE_DIFFERENCE,
        ComparisonCalculation.DIRECTION,
    ]


def _visualization_title(kind: VisualizationKind) -> str:
    return {
        VisualizationKind.DATA_TABLE: "Tabela de dados",
        VisualizationKind.BAR_CHART: "Grafico de barras",
        VisualizationKind.LINE_CHART: "Grafico de linhas",
        VisualizationKind.PIE_CHART: "Grafico de pizza",
        VisualizationKind.DONUT_CHART: "Grafico de rosca",
        VisualizationKind.KPI_CARD: "Indicador principal",
        VisualizationKind.AREA_CHART: "Grafico de area",
        VisualizationKind.SCATTER_CHART: "Grafico de dispersao",
        VisualizationKind.HEATMAP: "Mapa de calor",
        VisualizationKind.TREEMAP: "Mapa hierarquico",
        VisualizationKind.FUNNEL: "Funil",
        VisualizationKind.SUMMARY_CARD: "Resumo",
        VisualizationKind.INSIGHTS_LIST: "Insights",
    }[kind]
