from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken


_SENSITIVE = re.compile(
    r"(?i)(?:authorization\s*:|bearer\s+[a-z0-9._-]+|"
    r"(?:api[_-]?key|password|passwd|secret|token)\s*[:=])"
)
_EXECUTABLE_SQL = re.compile(
    r"(?is)^\s*(?:select|insert|update|delete|drop|alter|create|grant|revoke)\s+"
)


class ConversationContentError(ValueError):
    pass


@dataclass(frozen=True)
class ProtectedContent:
    ciphertext: bytes | None
    key_version: str | None
    fingerprint: str
    redacted: bool


class ConversationContentProtector:
    """Authenticated Fernet encryption with fail-closed key handling."""

    def __init__(
        self,
        *,
        key: str | bytes | None,
        key_version: str = "v1",
        persist_content: bool = True,
        max_content_bytes: int = 12000,
    ) -> None:
        self._persist_content = persist_content
        self._key_version = key_version
        self._max_content_bytes = max_content_bytes
        self._fernet: Fernet | None = None
        if key:
            try:
                self._fernet = Fernet(key.encode("ascii") if isinstance(key, str) else key)
            except (ValueError, TypeError) as exc:
                raise ConversationContentError("invalid conversation encryption key") from exc
        if persist_content and self._fernet is None:
            raise ConversationContentError(
                "conversation content persistence requires an authenticated encryption key"
            )

    @staticmethod
    def fingerprint(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def protect(self, content: str) -> ProtectedContent:
        encoded = content.encode("utf-8")
        if not encoded or len(encoded) > self._max_content_bytes:
            raise ConversationContentError("conversation content size is outside policy")
        fingerprint = self.fingerprint(content)
        unsafe = bool(_SENSITIVE.search(content) or _EXECUTABLE_SQL.search(content))
        if unsafe or not self._persist_content:
            return ProtectedContent(None, None, fingerprint, True)
        assert self._fernet is not None
        return ProtectedContent(
            self._fernet.encrypt(encoded),
            self._key_version,
            fingerprint,
            False,
        )

    def decrypt(self, ciphertext: bytes, *, key_version: str) -> str:
        if self._fernet is None or key_version != self._key_version:
            raise ConversationContentError("conversation content key is unavailable")
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as exc:
            raise ConversationContentError("conversation content authentication failed") from exc
