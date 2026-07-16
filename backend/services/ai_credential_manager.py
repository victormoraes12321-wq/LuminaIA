from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Final, Literal

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.tenant import Tenant

logger = logging.getLogger("luminaai.services.ai_credential_manager")


ProviderId = Literal["openai", "anthropic", "google", "azure_openai", "openrouter", "ollama"]
CredentialSource = Literal["tenant", "global", "explicit"]

AUTHORIZED_OPENAI_MODEL: Final[str] = "gpt-4o-mini"

_INVALID_KEY_MARKERS: Final[tuple[str, ...]] = (
    "testkey",
    "test_key",
    "invalid",
    "example",
    "placeholder",
    "substitua",
    "replace",
    "your_",
    "sua_chave",
    "chave_openai",
    "openai_api_key",
)

_PROVIDER_ORDER: Final[tuple[ProviderId, ...]] = (
    "openai",
    "anthropic",
    "google",
    "azure_openai",
    "openrouter",
    "ollama",
)


class AICMError(Exception):
    """Base exception for controlled AI credential infrastructure failures."""

    user_message = (
        "Nao foi possivel utilizar os servicos de Inteligencia Artificial devido "
        "a uma falha de configuracao das credenciais. Consulte o administrador do sistema."
    )


class AICMCredentialUnavailableError(AICMError):
    """Raised when no valid credential can be resolved."""


class AICMProviderUnavailableError(AICMError):
    """Raised when the selected provider cannot complete the request."""


class AICMAuthenticationError(AICMError):
    """Raised when all credential/provider fallbacks failed due to authentication."""


@dataclass(slots=True)
class ProviderProfile:
    provider_id: ProviderId
    name: str
    version: str
    models_available: list[str]
    status: str = "UNKNOWN"
    latency_ms: float | None = None
    availability: float = 0.0
    rate_limits: dict[str, Any] = field(default_factory=dict)
    context_limits: dict[str, int] = field(default_factory=dict)
    estimated_cost: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class CredentialCandidate:
    provider_id: ProviderId
    credential_id: str
    source: CredentialSource
    api_key: str
    model: str
    tenant_id: uuid.UUID | None = None
    model_id: str | None = None
    label: str | None = None


@dataclass(slots=True)
class CredentialState:
    status: str = "UNKNOWN"
    last_validation_at: str | None = None
    last_used_at: str | None = None
    error_count: int = 0
    avg_response_ms: float = 0.0
    cooldown_until: float = 0.0
    fallback_active: bool = False
    last_error: str | None = None


@dataclass(slots=True)
class AIClientLease:
    provider_id: ProviderId
    credential_id: str
    credential_source: CredentialSource
    credential_hash: str
    model: str
    client: AsyncOpenAI
    tenant_id: uuid.UUID | None
    fallback_used: bool = False
    attempts: int = 1


class AICredentialManager:
    """
    Enterprise AI Credential Manager.

    This is the only backend component allowed to read AI provider credentials,
    instantiate provider clients, invalidate credentials and manage provider
    fallback/cooldown.
    """

    def __init__(self) -> None:
        self.cache_ttl_seconds = 300
        self.cooldown_seconds = 120
        self.max_attempts = 2
        self.allow_global_fallback = True
        self.allow_provider_fallback = False
        self.provider_priority: tuple[ProviderId, ...] = _PROVIDER_ORDER
        self._clients: dict[str, AsyncOpenAI] = {}
        self._states: dict[str, CredentialState] = {}
        self._incidents: list[dict[str, Any]] = []
        self._audit_events: list[dict[str, Any]] = []
        self._providers: dict[ProviderId, ProviderProfile] = self._build_provider_profiles()

    def _build_provider_profiles(self) -> dict[ProviderId, ProviderProfile]:
        return {
            "openai": ProviderProfile(
                provider_id="openai",
                name="OpenAI",
                version="v1",
                models_available=[AUTHORIZED_OPENAI_MODEL],
                status="CONFIGURED" if not self.is_probably_invalid_key(settings.OPENAI_API_KEY) else "MISSING",
                availability=100.0,
                context_limits={AUTHORIZED_OPENAI_MODEL: 128000},
                estimated_cost={AUTHORIZED_OPENAI_MODEL: 0.0},
            ),
            "anthropic": ProviderProfile("anthropic", "Anthropic", "prepared", [], "NOT_CONFIGURED"),
            "google": ProviderProfile("google", "Google Gemini", "prepared", [], "NOT_CONFIGURED"),
            "azure_openai": ProviderProfile("azure_openai", "Azure OpenAI", "prepared", [], "NOT_CONFIGURED"),
            "openrouter": ProviderProfile("openrouter", "OpenRouter", "prepared", [], "NOT_CONFIGURED"),
            "ollama": ProviderProfile("ollama", "Ollama", "prepared", [], "NOT_CONFIGURED"),
        }

    def safe_parse_json(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def is_probably_invalid_key(self, api_key: str | None, provider_id: ProviderId = "openai") -> bool:
        key = str(api_key or "").strip()
        if not key:
            return True
        lowered = key.lower()
        if any(marker in lowered for marker in _INVALID_KEY_MARKERS):
            return True
        if any(ch in key for ch in ("*", "•", "●")):
            return True
        if any(ord(ch) > 127 for ch in key):
            return True
        if provider_id == "openai" and not key.startswith("sk-"):
            return True
        return len(key) < 20

    def is_auth_error(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        message = str(exc).lower()
        return (
            status_code in {401, 403}
            or "invalid_api_key" in message
            or "incorrect api key" in message
            or "unauthorized" in message
            or "forbidden" in message
            or "token expired" in message
            or "credential revoked" in message
            or ("401" in message and "api key" in message)
            or ("403" in message and "api key" in message)
        )

    def validate_authorized_model(self, model: str | None, provider_id: ProviderId = "openai") -> str:
        if provider_id != "openai":
            raise AICMProviderUnavailableError(f"Provider ainda nao configurado: {provider_id}")
        target = model or settings.OPENAI_MODEL or AUTHORIZED_OPENAI_MODEL
        if target != AUTHORIZED_OPENAI_MODEL:
            logger.warning(
                "[AICM] Modelo IA incompatível (%s). Usando modelo autorizado: %s",
                target,
                AUTHORIZED_OPENAI_MODEL,
            )
            return AUTHORIZED_OPENAI_MODEL
        return target

    def credential_hash(self, api_key: str) -> str:
        return hashlib.sha256(str(api_key).encode("utf-8")).hexdigest()[:16]

    def mask_credential(self, api_key: str | None) -> str:
        key = str(api_key or "")
        if not key:
            return ""
        return f"****{key[-4:]}" if len(key) > 4 else "****"

    def _credential_id(self, provider_id: ProviderId, source: CredentialSource, api_key: str, tenant_id: uuid.UUID | None) -> str:
        tenant_part = str(tenant_id) if tenant_id else "global"
        return f"{provider_id}:{source}:{tenant_part}:{self.credential_hash(api_key)}"

    async def _load_tenant_config(self, db: AsyncSession | None, tenant_id: uuid.UUID | str | None) -> dict[str, Any]:
        if not db or not tenant_id:
            return {}
        try:
            stmt = select(Tenant.ia_config).where(Tenant.id == uuid.UUID(str(tenant_id)))
            result = await db.execute(stmt)
            return self.safe_parse_json(result.scalar_one_or_none())
        except Exception as exc:
            logger.warning("[AICM] Falha ao carregar ia_config do tenant %s: %s", tenant_id, exc)
            return {}

    def _candidate_from_key(
        self,
        provider_id: ProviderId,
        source: CredentialSource,
        api_key: str | None,
        model: str | None,
        tenant_id: uuid.UUID | None,
        model_id: str | None = None,
        label: str | None = None,
    ) -> CredentialCandidate | None:
        if self.is_probably_invalid_key(api_key, provider_id):
            return None
        key = str(api_key).strip()
        resolved_model = self.validate_authorized_model(model, provider_id)
        return CredentialCandidate(
            provider_id=provider_id,
            credential_id=self._credential_id(provider_id, source, key, tenant_id),
            source=source,
            api_key=key,
            model=resolved_model,
            tenant_id=tenant_id,
            model_id=model_id,
            label=label,
        )

    def _tenant_candidates(
        self,
        tenant_config: dict[str, Any],
        tenant_id: uuid.UUID | None,
        requested_model: str | None,
    ) -> list[CredentialCandidate]:
        candidates: list[CredentialCandidate] = []
        active_model_id = tenant_config.get("active_model_id")
        registered_models = tenant_config.get("registered_models", []) or []
        if isinstance(registered_models, list):
            active_model = next(
                (item for item in registered_models if isinstance(item, dict) and item.get("id") == active_model_id),
                None,
            )
            if active_model:
                provider = str(active_model.get("provider") or active_model.get("provider_id") or "openai").lower()
                if provider == "azure":
                    provider = "azure_openai"
                if provider in _PROVIDER_ORDER:
                    candidate = self._candidate_from_key(
                        provider_id=provider,  # type: ignore[arg-type]
                        source="tenant",
                        api_key=active_model.get("api_key"),
                        model=requested_model or active_model.get("model_base") or active_model.get("model"),
                        tenant_id=tenant_id,
                        model_id=active_model.get("id"),
                        label=active_model.get("name"),
                    )
                    if candidate:
                        candidates.append(candidate)

        provider = str(tenant_config.get("provider") or tenant_config.get("provider_id") or "openai").lower()
        if provider == "azure":
            provider = "azure_openai"
        if provider in _PROVIDER_ORDER:
            candidate = self._candidate_from_key(
                provider_id=provider,  # type: ignore[arg-type]
                source="tenant",
                api_key=tenant_config.get("api_key"),
                model=requested_model or tenant_config.get("model_base") or tenant_config.get("model"),
                tenant_id=tenant_id,
                label="tenant-default",
            )
            if candidate and candidate.credential_id not in {item.credential_id for item in candidates}:
                candidates.append(candidate)

        return candidates

    async def resolve_candidates(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        db: AsyncSession | None = None,
        tenant_config: dict[str, Any] | None = None,
        explicit_api_key: str | None = None,
        requested_model: str | None = None,
        provider_id: ProviderId = "openai",
        allow_global_fallback: bool | None = None,
    ) -> list[CredentialCandidate]:
        tenant_uuid = uuid.UUID(str(tenant_id)) if tenant_id else None
        config = tenant_config if tenant_config is not None else await self._load_tenant_config(db, tenant_uuid)
        config = self.safe_parse_json(config)

        candidates: list[CredentialCandidate] = []
        explicit = self._candidate_from_key(
            provider_id=provider_id,
            source="explicit",
            api_key=explicit_api_key,
            model=requested_model,
            tenant_id=tenant_uuid,
            label="explicit-request",
        )
        if explicit:
            candidates.append(explicit)

        candidates.extend(self._tenant_candidates(config, tenant_uuid, requested_model))

        global_allowed = self.allow_global_fallback if allow_global_fallback is None else allow_global_fallback
        if global_allowed:
            global_candidate = self._candidate_from_key(
                provider_id="openai",
                source="global",
                api_key=settings.OPENAI_API_KEY,
                model=requested_model or settings.OPENAI_MODEL,
                tenant_id=None,
                label="global-openai",
            )
            if global_candidate:
                candidates.append(global_candidate)

        deduped: list[CredentialCandidate] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.credential_id not in seen:
                deduped.append(candidate)
                seen.add(candidate.credential_id)
        return deduped

    def _state_for(self, credential_id: str) -> CredentialState:
        if credential_id not in self._states:
            self._states[credential_id] = CredentialState()
        return self._states[credential_id]

    def _is_in_cooldown(self, credential_id: str) -> bool:
        return self._state_for(credential_id).cooldown_until > time.time()

    def _record_audit(self, event: dict[str, Any]) -> None:
        safe_event = {
            **event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._audit_events.append(safe_event)
        self._audit_events = self._audit_events[-250:]

    def _record_incident(self, candidate: CredentialCandidate | None, exc: Exception, reason: str) -> None:
        incident = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": candidate.provider_id if candidate else None,
            "tenant_id": str(candidate.tenant_id) if candidate and candidate.tenant_id else None,
            "credential_id": candidate.credential_id if candidate else None,
            "credential_hash": self.credential_hash(candidate.api_key) if candidate else None,
            "source": candidate.source if candidate else None,
            "model": candidate.model if candidate else None,
            "reason": reason,
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
        }
        self._incidents.append(incident)
        self._incidents = self._incidents[-250:]
        logger.warning(
            "[AICM] Incidente IA | provider=%s source=%s credential=%s reason=%s error=%s",
            incident["provider"],
            incident["source"],
            incident["credential_hash"],
            reason,
            type(exc).__name__,
        )

    def _mark_failure(self, candidate: CredentialCandidate, exc: Exception, critical: bool = False) -> None:
        state = self._state_for(candidate.credential_id)
        state.status = "COOLDOWN" if critical else "DEGRADED"
        state.error_count += 1
        state.last_error = type(exc).__name__
        if critical:
            state.cooldown_until = time.time() + self.cooldown_seconds
            if candidate.credential_id in self._clients:
                self._clients.pop(candidate.credential_id, None)
        self._record_incident(candidate, exc, "AUTHENTICATION" if critical else "PROVIDER_FAILURE")

    def _mark_success(self, lease: AIClientLease, elapsed_ms: float, tokens: int = 0) -> None:
        state = self._state_for(lease.credential_id)
        state.status = "HEALTHY"
        state.last_used_at = datetime.now(timezone.utc).isoformat()
        state.last_error = None
        state.fallback_active = lease.fallback_used
        state.avg_response_ms = elapsed_ms if state.avg_response_ms == 0 else ((state.avg_response_ms * 0.8) + (elapsed_ms * 0.2))
        provider = self._providers.get(lease.provider_id)
        if provider:
            provider.status = "HEALTHY"
            provider.latency_ms = state.avg_response_ms
            provider.availability = 100.0
        self._record_audit(
            {
                "event": "ai_call_success",
                "provider": lease.provider_id,
                "model": lease.model,
                "credential_id": lease.credential_id,
                "credential_hash": lease.credential_hash,
                "tenant_id": str(lease.tenant_id) if lease.tenant_id else None,
                "source": lease.credential_source,
                "elapsed_ms": round(elapsed_ms, 2),
                "tokens": tokens,
                "fallback_used": lease.fallback_used,
                "attempts": lease.attempts,
            }
        )

    def _client_for_candidate(self, candidate: CredentialCandidate) -> AsyncOpenAI:
        if candidate.provider_id != "openai":
            raise AICMProviderUnavailableError(f"Provider sem adaptador ativo: {candidate.provider_id}")
        if candidate.credential_id not in self._clients:
            self._clients[candidate.credential_id] = AsyncOpenAI(
                api_key=candidate.api_key,
                timeout=float(settings.OPENAI_TIMEOUT),
                max_retries=2,
            )
        return self._clients[candidate.credential_id]

    async def resolve_client(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        db: AsyncSession | None = None,
        tenant_config: dict[str, Any] | None = None,
        explicit_api_key: str | None = None,
        requested_model: str | None = None,
        allow_global_fallback: bool | None = None,
        purpose: str = "generic",
    ) -> AIClientLease:
        candidates = await self.resolve_candidates(
            tenant_id=tenant_id,
            db=db,
            tenant_config=tenant_config,
            explicit_api_key=explicit_api_key,
            requested_model=requested_model,
            allow_global_fallback=allow_global_fallback,
        )
        if not candidates:
            exc = AICMCredentialUnavailableError("Nenhuma credencial de IA valida foi encontrada.")
            self._record_incident(None, exc, "NO_VALID_CREDENTIAL")
            raise exc

        for index, candidate in enumerate(candidates, start=1):
            if self._is_in_cooldown(candidate.credential_id):
                continue
            client = self._client_for_candidate(candidate)
            state = self._state_for(candidate.credential_id)
            state.last_validation_at = state.last_validation_at or datetime.now(timezone.utc).isoformat()
            state.status = "READY"
            return AIClientLease(
                provider_id=candidate.provider_id,
                credential_id=candidate.credential_id,
                credential_source=candidate.source,
                credential_hash=self.credential_hash(candidate.api_key),
                model=candidate.model,
                client=client,
                tenant_id=candidate.tenant_id,
                fallback_used=index > 1,
                attempts=index,
            )

        exc = AICMCredentialUnavailableError("Todas as credenciais de IA elegiveis estao em cooldown.")
        self._record_incident(None, exc, "ALL_CREDENTIALS_IN_COOLDOWN")
        raise exc

    async def execute_with_fallback(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        db: AsyncSession | None = None,
        tenant_config: dict[str, Any] | None = None,
        explicit_api_key: str | None = None,
        requested_model: str | None = None,
        purpose: str,
        operation: Callable[[AsyncOpenAI, str, AIClientLease], Awaitable[Any]],
    ) -> Any:
        candidates = await self.resolve_candidates(
            tenant_id=tenant_id,
            db=db,
            tenant_config=tenant_config,
            explicit_api_key=explicit_api_key,
            requested_model=requested_model,
        )
        if not candidates:
            exc = AICMCredentialUnavailableError("Nenhuma credencial de IA valida foi encontrada.")
            self._record_incident(None, exc, "NO_VALID_CREDENTIAL")
            raise exc

        last_exc: Exception | None = None
        for index, candidate in enumerate(candidates[: self.max_attempts + 1], start=1):
            if self._is_in_cooldown(candidate.credential_id):
                continue
            lease = AIClientLease(
                provider_id=candidate.provider_id,
                credential_id=candidate.credential_id,
                credential_source=candidate.source,
                credential_hash=self.credential_hash(candidate.api_key),
                model=candidate.model,
                client=self._client_for_candidate(candidate),
                tenant_id=candidate.tenant_id,
                fallback_used=index > 1,
                attempts=index,
            )
            start = time.perf_counter()
            try:
                result = await operation(lease.client, lease.model, lease)
                elapsed_ms = (time.perf_counter() - start) * 1000
                tokens = self._extract_tokens(result)
                self._mark_success(lease, elapsed_ms, tokens=tokens)
                return result
            except Exception as exc:
                last_exc = exc
                auth_failure = self.is_auth_error(exc)
                self._mark_failure(candidate, exc, critical=auth_failure)
                if auth_failure:
                    continue
                raise AICMProviderUnavailableError(str(exc)) from exc

        raise AICMAuthenticationError(str(last_exc or "Falha de autenticacao de IA.")) from last_exc

    def _extract_tokens(self, result: Any) -> int:
        if isinstance(result, tuple):
            for item in result:
                if isinstance(item, int):
                    return item
        usage = getattr(result, "usage", None)
        return int(getattr(usage, "total_tokens", 0) or 0)

    async def validate_connection(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        db: AsyncSession | None = None,
        tenant_config: dict[str, Any] | None = None,
        explicit_api_key: str | None = None,
        requested_model: str | None = None,
        allow_global_fallback: bool | None = None,
    ) -> dict[str, Any]:
        lease = await self.resolve_client(
            tenant_id=tenant_id,
            db=db,
            tenant_config=tenant_config,
            explicit_api_key=explicit_api_key,
            requested_model=requested_model,
            allow_global_fallback=allow_global_fallback,
            purpose="validation",
        )
        start = time.perf_counter()
        try:
            await lease.client.models.list()
            elapsed_ms = (time.perf_counter() - start) * 1000
            state = self._state_for(lease.credential_id)
            state.status = "HEALTHY"
            state.last_validation_at = datetime.now(timezone.utc).isoformat()
            state.avg_response_ms = elapsed_ms
            return {
                "success": True,
                "provider": lease.provider_id,
                "model": lease.model,
                "credential_id": lease.credential_id,
                "credential_hash": lease.credential_hash,
                "latency_ms": round(elapsed_ms, 2),
            }
        except Exception as exc:
            self._mark_failure(
                CredentialCandidate(
                    provider_id=lease.provider_id,
                    credential_id=lease.credential_id,
                    source=lease.credential_source,
                    api_key=lease.credential_hash,
                    model=lease.model,
                    tenant_id=lease.tenant_id,
                ),
                exc,
                critical=self.is_auth_error(exc),
            )
            raise

    async def startup_validate(self) -> dict[str, Any]:
        """Lightweight startup validation that never exposes secrets."""
        global_status = "READY" if not self.is_probably_invalid_key(settings.OPENAI_API_KEY) else "MISSING"
        provider = self._providers["openai"]
        provider.status = global_status
        report = {
            "status": "READY" if global_status == "READY" else "DEGRADED",
            "providers": self.get_provider_health(),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "network_validation": False,
        }
        self._record_audit({"event": "startup_validation", "status": report["status"]})
        return report

    async def invalidate_tenant(self, tenant_id: uuid.UUID | str) -> None:
        tenant_prefix = f":{tenant_id}:"
        to_remove = [key for key in self._clients if tenant_prefix in key]
        for key in to_remove:
            client = self._clients.pop(key, None)
            if client:
                try:
                    await client.close()
                except Exception:
                    pass
            self._states.pop(key, None)

    async def close_all(self) -> None:
        for client in list(self._clients.values()):
            try:
                await client.close()
            except Exception:
                pass
        self._clients.clear()

    def get_provider_health(self) -> list[dict[str, Any]]:
        return [
            {
                "provider_id": provider.provider_id,
                "name": provider.name,
                "version": provider.version,
                "models_available": provider.models_available,
                "status": provider.status,
                "latency_ms": provider.latency_ms,
                "availability": provider.availability,
                "rate_limits": provider.rate_limits,
                "context_limits": provider.context_limits,
                "estimated_cost": provider.estimated_cost,
            }
            for provider in self._providers.values()
        ]

    def get_status(self, tenant_id: uuid.UUID | str | None = None) -> dict[str, Any]:
        states = []
        for credential_id, state in self._states.items():
            if tenant_id and str(tenant_id) not in credential_id and ":global:" not in credential_id:
                continue
            states.append(
                {
                    "credential_id": credential_id,
                    "status": state.status,
                    "last_validation_at": state.last_validation_at,
                    "last_used_at": state.last_used_at,
                    "error_count": state.error_count,
                    "avg_response_ms": round(state.avg_response_ms, 2),
                    "cooldown_active": state.cooldown_until > time.time(),
                    "fallback_active": state.fallback_active,
                    "last_error": state.last_error,
                }
            )

        healthy = sum(1 for item in states if item["status"] in {"HEALTHY", "READY"})
        total = len(states) or 1
        health_score = round((healthy / total) * 100, 2)
        return {
            "status_geral": "HEALTHY" if health_score >= 80 else "DEGRADED",
            "provider_atual": "openai",
            "modelo_atual": AUTHORIZED_OPENAI_MODEL,
            "health_score": health_score,
            "authentication_score": health_score,
            "latency_score": self._latency_score(states),
            "availability_score": health_score,
            "success_rate": health_score,
            "providers": self.get_provider_health(),
            "credentials": states,
            "recent_incidents": self._incidents[-10:],
            "recent_audit_events": self._audit_events[-10:],
        }

    def _latency_score(self, states: list[dict[str, Any]]) -> float:
        latencies = [item["avg_response_ms"] for item in states if item.get("avg_response_ms")]
        if not latencies:
            return 100.0
        avg = sum(latencies) / len(latencies)
        return round(max(0.0, min(100.0, 100.0 - (avg / 100.0))), 2)


ai_credential_manager = AICredentialManager()
