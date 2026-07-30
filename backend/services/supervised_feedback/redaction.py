from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from contracts.supervised_feedback_v2 import (
    FeedbackCorrectionV2,
    FeedbackRedactionManifestV2,
)
from contracts.supervised_feedback_v2.models import RedactedFieldV2
from services.supervised_feedback.checksums import checksum
from services.supervised_feedback.errors import FeedbackPayloadTooLargeError


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:bearer|basic)\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|password|passwd|secret|token|authorization|cookie)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|oracle|mysql)://[^\s]+"),
)
_PII_PATTERNS = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE = re.compile(r"\s+")
_CSV_FORMULA = re.compile(r"^[=+\-@]")


@dataclass(frozen=True)
class RedactionResult:
    explanation: str | None
    correction: FeedbackCorrectionV2 | None
    manifest: FeedbackRedactionManifestV2


class FeedbackRedactionEngine:
    POLICY_VERSION = "lumina.feedback-redaction/1.0"
    MAX_TEXT_BYTES = 8192

    @classmethod
    def sanitize_text(cls, value: str, *, csv_safe: bool = False) -> tuple[str, list[str]]:
        encoded = value.encode("utf-8")
        if len(encoded) > cls.MAX_TEXT_BYTES:
            raise FeedbackPayloadTooLargeError("Texto de feedback excede o limite permitido.")
        reasons: list[str] = []
        result = _CONTROL.sub(" ", value)
        if result != value:
            reasons.append("CONTROL_CHAR_REMOVED")
        for pattern in _SECRET_PATTERNS:
            result, count = pattern.subn("[REDACTED]", result)
            if count:
                reasons.append("SECRET_REDACTED")
        for pattern in _PII_PATTERNS:
            result, count = pattern.subn("[REDACTED]", result)
            if count:
                reasons.append("PII_REDACTED")
        result = _SPACE.sub(" ", result).strip()
        if csv_safe and _CSV_FORMULA.search(result):
            result = "'" + result
            reasons.append("CSV_FORMULA_NEUTRALIZED")
        return result[:2000], sorted(set(reasons))

    def redact(
        self,
        *,
        explanation: str | None,
        correction: FeedbackCorrectionV2 | None,
    ) -> RedactionResult:
        original_size = len((explanation or "").encode("utf-8"))
        fields: list[RedactedFieldV2] = []
        sanitized_explanation = None
        if explanation is not None:
            sanitized_explanation, reasons = self.sanitize_text(explanation)
            fields.extend(
                RedactedFieldV2(field_name="explanation", reason_code=reason)
                for reason in reasons
            )

        sanitized_correction = correction
        if correction is not None:
            items = []
            for index, item in enumerate(correction.items):
                payload = item.model_dump(mode="python")
                for field_name, value in tuple(payload.items()):
                    if isinstance(value, str):
                        clean, reasons = self.sanitize_text(value)
                        payload[field_name] = clean
                        fields.extend(
                            RedactedFieldV2(
                                field_name=f"correction.items[{index}].{field_name}",
                                reason_code=reason,
                            )
                            for reason in reasons
                        )
                items.append(payload)
            sanitized_correction = FeedbackCorrectionV2.model_validate({"items": items})

        redacted_size = len((sanitized_explanation or "").encode("utf-8"))
        manifest_payload = {
            "policy_version": self.POLICY_VERSION,
            "removed_fields": [],
            "transformed_fields": [item.model_dump(mode="json") for item in fields],
            "original_size_bytes": original_size,
            "redacted_size_bytes": redacted_size,
            "sensitive_content_detected": bool(fields),
        }
        manifest = FeedbackRedactionManifestV2(
            manifest_id=uuid.uuid4(),
            policy_version=self.POLICY_VERSION,
            removed_fields=[],
            transformed_fields=fields,
            original_size_bytes=original_size,
            redacted_size_bytes=redacted_size,
            sensitive_content_detected=bool(fields),
            checksum=checksum(manifest_payload),
        )
        return RedactionResult(
            explanation=sanitized_explanation,
            correction=sanitized_correction,
            manifest=manifest,
        )

    @classmethod
    def neutralize_csv(cls, value: str) -> str:
        return cls.sanitize_text(value, csv_safe=True)[0]
