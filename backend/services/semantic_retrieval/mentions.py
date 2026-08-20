from __future__ import annotations

import re
import uuid

from contracts.analytical_v2 import QueryIntentV2
from contracts.semantic_retrieval_v2 import EntityMentionV2, SemanticEntityType
from services.semantic_retrieval.normalization import normalize_semantic_text


_EXPLICIT_PATTERNS: tuple[tuple[SemanticEntityType, re.Pattern[str]], ...] = (
    (
        SemanticEntityType.BRANCH,
        re.compile(r"\b(?:filial|loja|unidade)\s+([A-Za-z0-9][\w .&/-]{0,80})", re.I),
    ),
    (
        SemanticEntityType.SELLER,
        re.compile(r"\b(?:vendedor(?:a)?|rca)\s+([A-Za-z][\w .'-]{1,80})", re.I),
    ),
    (
        SemanticEntityType.CUSTOMER,
        re.compile(r"\bcliente\s+([A-Za-z0-9][\w .&'/-]{1,100})", re.I),
    ),
    (
        SemanticEntityType.PRODUCT,
        re.compile(r"\b(?:produto|item)\s+([A-Za-z0-9][\w .&'/-]{0,100})", re.I),
    ),
)
_BOUNDARY_WORDS = re.compile(
    r"\b(?:no|na|nos|nas|em|de|do|da|dos|das|com|sem|por|entre|durante|"
    r"este|esta|esse|essa|mes|m[eê]s|ano|periodo|per[ií]odo)\b",
    re.I,
)


def _mention(
    *,
    text: str,
    start: int,
    end: int,
    entity_type: SemanticEntityType,
    source: str,
    candidate_field: str | None = None,
    confidence: float = 1.0,
) -> EntityMentionV2:
    normalized = normalize_semantic_text(text)
    return EntityMentionV2(
        mention_id=uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"lumina-semantic-mention:{start}:{end}:{entity_type.value}:{normalized.normalized}",
        ),
        text=text,
        normalized_text=normalized.normalized,
        start=start,
        end=end,
        expected_entity_type=entity_type,
        candidate_field=candidate_field,
        source=source,
        confidence=confidence,
    )


class SemanticMentionExtractor:
    """Deterministic adapter; temporal expressions remain outside this component."""

    def extract(self, intent: QueryIntentV2) -> tuple[EntityMentionV2, ...]:
        question = intent.raw_question
        mentions: list[EntityMentionV2] = []
        seen: set[tuple[str, SemanticEntityType]] = set()

        for reference in intent.metric_refs:
            key = (reference.display_name.casefold(), SemanticEntityType.METRIC)
            if key in seen:
                continue
            start = question.casefold().find(reference.display_name.casefold())
            start = max(0, start)
            end = min(len(question), start + len(reference.display_name))
            mentions.append(
                _mention(
                    text=reference.display_name,
                    start=start,
                    end=max(start + 1, end),
                    entity_type=SemanticEntityType.METRIC,
                    source="INTENT",
                    candidate_field="metric_refs",
                    confidence=float(reference.confidence.score),
                )
            )
            seen.add(key)

        for reference in intent.dimension_refs:
            key = (reference.display_name.casefold(), SemanticEntityType.DIMENSION)
            if key in seen:
                continue
            start = question.casefold().find(reference.display_name.casefold())
            start = max(0, start)
            end = min(len(question), start + len(reference.display_name))
            mentions.append(
                _mention(
                    text=reference.display_name,
                    start=start,
                    end=max(start + 1, end),
                    entity_type=SemanticEntityType.DIMENSION,
                    source="INTENT",
                    candidate_field="dimension_refs",
                    confidence=float(reference.confidence.score),
                )
            )
            seen.add(key)

        for query_filter in intent.filters:
            field_text = query_filter.field_id
            field_key = (field_text.casefold(), SemanticEntityType.DIMENSION)
            if field_key not in seen:
                mentions.append(
                    _mention(
                        text=field_text,
                        start=0,
                        end=max(1, min(len(question), len(field_text))),
                        entity_type=SemanticEntityType.DIMENSION,
                        source="FILTER_FIELD",
                        candidate_field=query_filter.filter_id,
                        confidence=float(query_filter.confidence.score),
                    )
                )
                seen.add(field_key)
            values = (
                query_filter.values
                if query_filter.values
                else ([query_filter.value] if query_filter.value is not None else [])
            )
            for value in values:
                if not isinstance(value, (str, int)):
                    continue
                value_text = str(value)
                value_key = (value_text.casefold(), SemanticEntityType.UNKNOWN)
                if value_key in seen:
                    continue
                start = question.casefold().find(value_text.casefold())
                start = max(0, start)
                mentions.append(
                    _mention(
                        text=value_text,
                        start=start,
                        end=max(start + 1, min(len(question), start + len(value_text))),
                        entity_type=SemanticEntityType.UNKNOWN,
                        source="FILTER_VALUE",
                        candidate_field=query_filter.field_id,
                        confidence=float(query_filter.confidence.score),
                    )
                )
                seen.add(value_key)

        for entity_type, pattern in _EXPLICIT_PATTERNS:
            for match in pattern.finditer(question):
                raw = _BOUNDARY_WORDS.split(match.group(1), maxsplit=1)[0].strip(" ,.;:?!")
                if not raw:
                    continue
                key = (raw.casefold(), entity_type)
                if key in seen:
                    continue
                raw_start = question.find(raw, match.start(1))
                mentions.append(
                    _mention(
                        text=raw,
                        start=raw_start,
                        end=raw_start + len(raw),
                        entity_type=entity_type,
                        source="EXPLICIT",
                    )
                )
                seen.add(key)

        return tuple(
            sorted(
                mentions,
                key=lambda item: (item.start, item.end, item.expected_entity_type.value, item.text),
            )
        )
