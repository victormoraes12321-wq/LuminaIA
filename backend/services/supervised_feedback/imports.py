from __future__ import annotations

import json
import uuid

from pydantic import ValidationError

from contracts.supervised_feedback_v2 import (
    ApprovedTrainingExampleV2,
    EvaluationCaseV2,
    GovernedImportDryRunRequestV2,
    GovernedImportDryRunResultV2,
)
from services.supervised_feedback.checksums import checksum, content_sha256


_FORBIDDEN_KEYS = frozenset(
    {
        "sql",
        "binds",
        "password",
        "secret",
        "token",
        "authorization",
        "cookie",
        "chain_of_thought",
        "raw_dataset",
    }
)


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in _FORBIDDEN_KEYS or _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


class GovernedImportDryRunValidator:
    """Strict offline validation. It does not persist, publish or execute records."""

    MAX_PAYLOAD_BYTES = 20 * 1024 * 1024

    def validate(
        self,
        *,
        request: GovernedImportDryRunRequestV2,
        authenticated_tenant_id: uuid.UUID,
    ) -> GovernedImportDryRunResultV2:
        content = ("\n".join(request.lines) + ("\n" if request.lines else "")).encode(
            "utf-8"
        )
        if len(content) > self.MAX_PAYLOAD_BYTES:
            return self._result(
                request=request,
                valid=0,
                rejected=len(request.lines),
                issues=["PAYLOAD_TOO_LARGE"],
            )
        if content_sha256(content) != request.content_checksum:
            return self._result(
                request=request,
                valid=0,
                rejected=len(request.lines),
                issues=["CONTENT_CHECKSUM_MISMATCH"],
            )

        model = {
            "GOVERNED_DATASET_EXPORT": ApprovedTrainingExampleV2,
            "VERSIONED_EVALUATION_CASE": EvaluationCaseV2,
            "SYNTHETIC_FIXTURE": EvaluationCaseV2,
        }[request.source_kind]
        valid = 0
        issues: list[str] = []
        for index, line in enumerate(request.lines):
            try:
                payload = json.loads(line)
                if _contains_forbidden_key(payload):
                    raise ValueError("FORBIDDEN_FIELD")
                record = model.model_validate_json(line)
                tenant_scope = getattr(record, "tenant_scope", authenticated_tenant_id)
                if tenant_scope not in {None, authenticated_tenant_id}:
                    raise ValueError("CROSS_TENANT_RECORD")
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                code = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                issues.append(f"LINE_{index + 1}:{code[:80]}")
            else:
                valid += 1
        return self._result(
            request=request,
            valid=valid,
            rejected=len(request.lines) - valid,
            issues=issues[:100],
        )

    @staticmethod
    def _result(
        *,
        request: GovernedImportDryRunRequestV2,
        valid: int,
        rejected: int,
        issues: list[str],
    ) -> GovernedImportDryRunResultV2:
        payload = {
            "source_kind": request.source_kind,
            "record_count": len(request.lines),
            "valid_count": valid,
            "rejected_count": rejected,
            "issues": issues,
            "dry_run": True,
            "persisted": False,
            "published": False,
            "content_checksum": request.content_checksum,
        }
        return GovernedImportDryRunResultV2(
            **payload,
            result_checksum=checksum(payload),
        )
