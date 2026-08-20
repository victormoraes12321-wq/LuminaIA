from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

from contracts.semantic_retrieval_v2 import (
    SemanticClarificationOptionV2,
    SemanticClarificationV2,
    SemanticSearchCandidateV2,
)
from models.semantic_retrieval import SemanticClarification
from models.user import User
from services.semantic_retrieval.checksums import checksum_for
from services.semantic_retrieval.errors import semantic_error
from services.semantic_retrieval.repository import SemanticRetrievalRepository


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class SemanticClarificationService:
    def __init__(
        self,
        repository: SemanticRetrievalRepository,
        *,
        signing_secret: str,
        ttl_seconds: int = 600,
    ) -> None:
        if len(signing_secret) < 16:
            raise ValueError("clarification signing secret is too short")
        self.repository = repository
        self.secret = signing_secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds

    def _token(self, payload: dict[str, str]) -> str:
        encoded = _b64(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signature = _b64(
            hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        )
        return f"{encoded}.{signature}"

    async def create(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        mention_id: uuid.UUID,
        candidates: tuple[SemanticSearchCandidateV2, ...],
    ) -> SemanticClarificationV2:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        clarification_id = uuid.uuid4()
        stored_options: list[dict[str, str]] = []
        public_options: list[SemanticClarificationOptionV2] = []
        for candidate in candidates[:10]:
            payload = {
                "clarification_id": str(clarification_id),
                "tenant_id": str(user.tenant_id),
                "user_id": str(user.id),
                "session_id": str(session_id),
                "document_id": str(candidate.document_id),
                "expires_at": expires_at.isoformat(),
            }
            token = self._token(payload)
            stored_options.append(
                {
                    "token": token,
                    "document_id": str(candidate.document_id),
                    "canonical_id": candidate.canonical_reference.canonical_id,
                }
            )
            public_options.append(
                SemanticClarificationOptionV2(
                    option_token=token,
                    public_label=candidate.public_label,
                    entity_type=candidate.entity_type,
                    domain=candidate.domain,
                    provenance_summary="Referencia empresarial publicada.",
                )
            )
        checksum = checksum_for(stored_options)
        await self.repository.create_clarification(
            tenant_id=user.tenant_id,
            row=SemanticClarification(
                id=clarification_id,
                tenant_id=user.tenant_id,
                user_id=user.id,
                session_id=session_id,
                mention_id=mention_id,
                options=stored_options,
                options_checksum=checksum,
                expires_at=expires_at,
            ),
        )
        return SemanticClarificationV2(
            clarification_id=clarification_id,
            tenant_id=user.tenant_id,
            user_id=user.id,
            session_id=session_id,
            mention_id=mention_id,
            question="Qual destas opcoes representa o que voce quis dizer?",
            options=tuple(public_options),
            expires_at=expires_at,
        )

    async def resolve(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        clarification_id: uuid.UUID,
        option_token: str,
    ) -> uuid.UUID:
        row = await self.repository.get_clarification(
            tenant_id=user.tenant_id,
            user_id=user.id,
            clarification_id=clarification_id,
        )
        now = datetime.now(timezone.utc)
        if (
            row is None
            or row.session_id != session_id
            or row.status != "PENDING"
            or row.expires_at <= now
        ):
            raise semantic_error(
                "ENTITY_CLARIFICATION_EXPIRED",
                "A opcao de esclarecimento expirou ou nao pertence a esta conversa.",
            )
        match = next(
            (item for item in row.options if item.get("token") == option_token),
            None,
        )
        if match is None:
            raise semantic_error(
                "ENTITY_CLARIFICATION_INVALID_OPTION",
                "A opcao selecionada nao pertence a este esclarecimento.",
            )
        encoded, separator, signature = option_token.partition(".")
        expected = _b64(
            hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        )
        if not separator or not hmac.compare_digest(signature, expected):
            raise semantic_error(
                "ENTITY_CLARIFICATION_INVALID_OPTION",
                "A assinatura da opcao de esclarecimento e invalida.",
            )
        document_id = uuid.UUID(match["document_id"])
        resolved = await self.repository.resolve_clarification(
            tenant_id=user.tenant_id,
            user_id=user.id,
            session_id=session_id,
            clarification_id=clarification_id,
            resolved_document_id=document_id,
            now=now,
        )
        if not resolved:
            raise semantic_error(
                "ENTITY_CLARIFICATION_EXPIRED",
                "O esclarecimento foi alterado ou expirou.",
            )
        return document_id
