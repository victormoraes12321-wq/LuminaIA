from __future__ import annotations

import re
from dataclasses import dataclass

from contracts.semantic_retrieval_v2 import SemanticDataClassification


_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?55\s*)?\(?\d{2}\)?\s*9?\d{4}[-\s]?\d{4}(?!\d)")),
    ("CPF", re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")),
    ("CREDENTIAL_URL", re.compile(r"\b(?:postgres(?:ql)?|oracle|mysql)://\S+:\S+@", re.I)),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("TOKEN", re.compile(r"\b(?:sk|pk|token|bearer)[-_ ][A-Za-z0-9._-]{20,}\b", re.I)),
    (
        "PROMPT_INJECTION",
        re.compile(
            r"\b(?:ignore|desconsidere|revele|mostre)\b.{0,40}"
            r"\b(?:instrucoes|instructions|system prompt|prompt interno)\b",
            re.I,
        ),
    ),
    (
        "EXECUTABLE_INSTRUCTION",
        re.compile(r"\b(?:execute|drop|truncate|delete from|alter table)\b", re.I),
    ),
)


@dataclass(frozen=True)
class SemanticContentInspection:
    allowed: bool
    reason_codes: tuple[str, ...]
    classification: SemanticDataClassification


def inspect_semantic_content(
    values: tuple[str, ...],
    *,
    classification: SemanticDataClassification,
) -> SemanticContentInspection:
    reasons: list[str] = []
    for value in values:
        if len(value) > 4000:
            reasons.append("OVERSIZED_CONTENT")
        if "\x00" in value:
            reasons.append("NULL_BYTE")
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            reasons.append("CONTROL_CHARACTER")
        for code, pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(value):
                reasons.append(code)
    if classification in {
        SemanticDataClassification.SENSITIVE_PERSONAL_DATA,
        SemanticDataClassification.FORBIDDEN,
    }:
        reasons.append("CLASSIFICATION_FORBIDDEN")
    unique = tuple(sorted(set(reasons)))
    return SemanticContentInspection(
        allowed=not unique,
        reason_codes=unique,
        classification=classification,
    )
