from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from contracts.semantic_retrieval_v2 import NORMALIZER_VERSION
from services.semantic_retrieval.checksums import checksum_for


_CONTROLLED_STOPWORDS = frozenset(
    {
        "a",
        "as",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "para",
        "por",
        "um",
        "uma",
    }
)
_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


@dataclass(frozen=True)
class NormalizedSemanticText:
    original: str
    normalized: str
    tokens: tuple[str, ...]
    significant_tokens: tuple[str, ...]
    character_ngrams: tuple[str, ...]
    possible_code: str | None
    locale: str
    version: str
    steps: tuple[str, ...]
    checksum: str


def _fold_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _character_ngrams(value: str, size: int = 3) -> tuple[str, ...]:
    compact = f"  {value}  "
    if len(compact) <= size:
        return (compact,)
    return tuple(sorted({compact[index : index + size] for index in range(len(compact) - size + 1)}))


def normalize_semantic_text(value: str, *, locale: str = "pt-BR") -> NormalizedSemanticText:
    original = str(value or "").strip()
    if not original:
        raise ValueError("semantic text cannot be empty")
    if len(original) > 500:
        raise ValueError("semantic text exceeds 500 characters")
    if "\x00" in original or any(
        ord(char) < 32 and char not in "\n\r\t" for char in original
    ):
        raise ValueError("semantic text contains forbidden controls")

    possible_code = (
        original
        if _CODE.fullmatch(original) and any(char.isdigit() for char in original)
        else None
    )
    normalized_unicode = unicodedata.normalize("NFKC", original)
    folded = _fold_diacritics(normalized_unicode.casefold())
    punctuation_spaced = re.sub(r"[\u2010-\u2015'\u2019`\u00b4]", " ", folded)
    if possible_code is None:
        punctuation_spaced = punctuation_spaced.replace("-", " ")
    lexical = re.sub(r"[^a-z0-9._/-]+", " ", punctuation_spaced)
    normalized = " ".join(lexical.split())
    tokens = tuple(token for token in normalized.split(" ") if token)
    significant = tuple(token for token in tokens if token not in _CONTROLLED_STOPWORDS)
    ngrams = _character_ngrams(normalized)
    steps = (
        "NFKC",
        "CASE_FOLD",
        "DIACRITIC_FOLD",
        "CONTROLLED_PUNCTUATION",
        "WHITESPACE_COLLAPSE",
        "CONTROLLED_STOPWORDS",
        "CHARACTER_TRIGRAMS",
    )
    payload = {
        "normalized": normalized,
        "tokens": tokens,
        "significant_tokens": significant,
        "possible_code": possible_code,
        "locale": locale,
        "version": NORMALIZER_VERSION,
    }
    return NormalizedSemanticText(
        original=original,
        normalized=normalized,
        tokens=tokens,
        significant_tokens=significant,
        character_ngrams=ngrams,
        possible_code=possible_code,
        locale=locale,
        version=NORMALIZER_VERSION,
        steps=steps,
        checksum=checksum_for(payload),
    )


def token_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def character_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
