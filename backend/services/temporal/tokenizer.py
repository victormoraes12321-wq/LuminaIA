from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_MOJIBAKE_MARKERS = ("Ãƒ", "Ã‚", "Ã¢â‚¬")


@dataclass(frozen=True)
class TemporalToken:
    value: str
    start: int
    end: int


def normalize_temporal_text(value: str) -> str:
    text = str(value or "").lower()
    for _ in range(2):
        if not any(marker in text for marker in _MOJIBAKE_MARKERS):
            break
        try:
            repaired = text.encode("cp1252").decode("utf-8")
        except UnicodeError:
            break
        if repaired == text:
            break
        text = repaired
    text = text.replace("º", "o").replace("ª", "a")
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"mar\?+o", "marco", normalized)
    normalized = re.sub(r"m\?+s", "mes", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize_temporal_text(value: str) -> tuple[TemporalToken, ...]:
    normalized = normalize_temporal_text(value)
    return tuple(
        TemporalToken(match.group(0), match.start(), match.end())
        for match in re.finditer(r"\d+|[a-z]+|[/:-]", normalized)
    )
