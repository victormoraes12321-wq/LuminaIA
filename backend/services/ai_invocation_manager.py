from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Final, Literal

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_credential_manager import AIClientLease, AICMError, ai_credential_manager

logger = logging.getLogger("luminaai.services.ai_invocation_manager")


InvocationStrategy = Literal[
    "FULL_AI",
    "PARTIAL_AI",
    "BLUEPRINT_ONLY",
    "CACHE_ONLY",
    "HYBRID",
    "REPROCESS",
    "EXPLAIN_ONLY",
    "REFRESH_ONLY",
]
RiskLevel = Literal["BAIXO", "MEDIO", "ALTO", "CRITICO"]

_AI_REQUIRED_STRATEGIES: Final[set[InvocationStrategy]] = {
    "FULL_AI",
    "PARTIAL_AI",
    "HYBRID",
    "REPROCESS",
    "EXPLAIN_ONLY",
    "REFRESH_ONLY",
}
_CACHE_SAFE_PURPOSES: Final[set[str]] = {
    "iar_semantic_fallback",
}
_HIGH_RISK_TERMS: Final[tuple[str, ...]] = (
    "financeiro",
    "faturamento",
    "lucro",
    "margem",
    "meta",
    "estoque critico",
    "anomalia",
    "queda",
    "prejuizo",
    "rentabilidade",
)


@dataclass(slots=True)
class AIMDecisionScores:
    semantic_similarity_score: float = 0.0
    blueprint_compatibility_score: float = 0.0
    cache_reliability_score: float = 0.0
    context_change_score: float = 0.0
    freshness_requirement_score: float = 0.0
    business_risk_score: float = 0.0
    complexity_score: float = 0.0
    estimated_token_cost: float = 0.0
    estimated_latency: float = 0.0
    expected_confidence: float = 0.0


@dataclass(slots=True)
class AIMDecision:
    decision_id: str
    purpose: str
    strategy: InvocationStrategy
    should_invoke_ai: bool
    reason: str
    risk_level: RiskLevel
    scores: AIMDecisionScores
    estimated_tokens: int
    estimated_cost: float
    estimated_latency_ms: float
    cache_key: str | None = None
    blueprint_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(slots=True)
class AIMInvocationResult:
    result: Any
    decision: AIMDecision
    elapsed_ms: float
    tokens_estimated: int
    tokens_consumed: int
    cost_estimated: float
    cost_real: float
    token_savings: int
    cache_hit: bool
    provider: str | None = None
    model: str | None = None


class AIMPolicyViolationError(Exception):
    """Raised when AIM blocks unsafe reuse and no AI invocation is possible."""


class AIInvocationManager:
    """
    Enterprise AI Invocation Manager.

    AIM governs every model invocation decision. It never interprets language,
    selects business metrics, queries databases or owns credentials. Credential
    resolution remains exclusively inside AICM.
    """

    def __init__(self) -> None:
        self.semantic_similarity_threshold = 82.0
        self.blueprint_compatibility_threshold = 85.0
        self.cache_reliability_threshold = 92.0
        self.confidence_threshold = 80.0
        self.cache_ttl_seconds = 300
        self.estimated_cost_per_1k_tokens = 0.00015
        self._response_cache: dict[str, dict[str, Any]] = {}
        self._decisions: list[dict[str, Any]] = []
        self._invocations: list[dict[str, Any]] = []
        self._learning_events: list[dict[str, Any]] = []
        self._dashboard = {
            "total_decisions": 0,
            "ai_calls": 0,
            "ai_calls_avoided": 0,
            "cache_hits": 0,
            "blueprint_reuses": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "tokens_estimated": 0,
            "tokens_consumed": 0,
            "tokens_saved": 0,
            "estimated_cost": 0.0,
            "real_cost": 0.0,
            "latency_total_ms": 0.0,
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _clamp_score(self, value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except Exception:
            number = default
        if number <= 1.0 and number > 0.0:
            number *= 100.0
        return round(max(0.0, min(100.0, number)), 2)

    def _normalize_query(self, value: str | None) -> str:
        text = (value or "").lower().strip()
        return re.sub(r"\s+", " ", text)

    def _fingerprint(self, *, tenant_id: uuid.UUID | str | None, purpose: str, context: dict[str, Any]) -> str:
        safe_parts = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "purpose": purpose,
            "query": self._normalize_query(str(context.get("query") or context.get("pergunta") or "")),
            "semantic_version": context.get("semantic_version"),
            "blueprint_version": context.get("blueprint_version"),
            "business_rules_version": context.get("business_rules_version"),
            "metadata_version": context.get("metadata_version"),
            "svr_version": context.get("svr_version"),
            "filters": context.get("filters"),
            "metrics": context.get("metrics"),
            "dimensions": context.get("dimensions"),
            "period": context.get("period"),
        }
        raw = repr(sorted(safe_parts.items()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _estimate_tokens(self, context: dict[str, Any]) -> int:
        text_parts = [
            str(context.get("query") or context.get("pergunta") or ""),
            str(context.get("prompt") or ""),
            str(context.get("messages") or ""),
            str(context.get("data_shape") or ""),
        ]
        chars = sum(len(part) for part in text_parts)
        explicit = context.get("estimated_tokens")
        if explicit is not None:
            try:
                return max(1, int(explicit))
            except Exception:
                pass
        return max(64, int(chars / 4) + 250)

    def _risk_score(self, context: dict[str, Any]) -> float:
        explicit = context.get("business_risk_score")
        if explicit is not None:
            return self._clamp_score(explicit)
        query = self._normalize_query(str(context.get("query") or context.get("pergunta") or ""))
        score = 20.0
        if any(term in query for term in _HIGH_RISK_TERMS):
            score += 55.0
        if context.get("critical") or context.get("requires_precision"):
            score += 35.0
        return self._clamp_score(score)

    def _risk_level(self, score: float) -> RiskLevel:
        if score >= 90:
            return "CRITICO"
        if score >= 70:
            return "ALTO"
        if score >= 40:
            return "MEDIO"
        return "BAIXO"

    def _complexity_score(self, context: dict[str, Any]) -> float:
        explicit = context.get("complexity_score")
        if explicit is not None:
            return self._clamp_score(explicit)
        query = str(context.get("query") or context.get("pergunta") or "")
        metrics = context.get("metrics") or []
        dimensions = context.get("dimensions") or []
        filters = context.get("filters") or {}
        score = min(35.0, len(query) / 5.0)
        score += min(25.0, len(metrics) * 8.0 if isinstance(metrics, list) else 0.0)
        score += min(20.0, len(dimensions) * 6.0 if isinstance(dimensions, list) else 0.0)
        score += min(20.0, len(filters) * 5.0 if isinstance(filters, dict) else 0.0)
        return self._clamp_score(score)

    def _cache_reliability(self, cache_key: str, context: dict[str, Any]) -> float:
        if context.get("cache_invalidated"):
            return 0.0
        cached = self._response_cache.get(cache_key)
        if not cached:
            return self._clamp_score(context.get("cache_reliability_score"), default=0.0)
        age = time.time() - float(cached.get("created_at_epoch") or 0)
        if age > self.cache_ttl_seconds:
            return 0.0
        if any(
            context.get(flag)
            for flag in (
                "context_changed",
                "version_changed",
                "metrics_changed",
                "dimensions_changed",
                "period_changed",
                "business_rules_changed",
                "svr_changed",
                "metadata_changed",
            )
        ):
            return 0.0
        return max(0.0, 100.0 - (age / self.cache_ttl_seconds) * 10.0)

    def decide(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        purpose: str,
        context: dict[str, Any] | None = None,
        force_ai: bool = False,
        allow_response_reuse: bool | None = None,
    ) -> AIMDecision:
        context = dict(context or {})
        cache_key = self._fingerprint(tenant_id=tenant_id, purpose=purpose, context=context)
        estimated_tokens = self._estimate_tokens(context)
        risk_score = self._risk_score(context)
        complexity_score = self._complexity_score(context)
        cache_score = self._cache_reliability(cache_key, context)

        scores = AIMDecisionScores(
            semantic_similarity_score=self._clamp_score(context.get("semantic_similarity_score"), default=0.0),
            blueprint_compatibility_score=self._clamp_score(context.get("blueprint_compatibility_score"), default=0.0),
            cache_reliability_score=self._clamp_score(cache_score),
            context_change_score=self._clamp_score(100.0 if context.get("context_changed") else context.get("context_change_score"), default=0.0),
            freshness_requirement_score=self._clamp_score(
                100.0 if context.get("fresh_data_required", True) else context.get("freshness_requirement_score"),
                default=75.0,
            ),
            business_risk_score=risk_score,
            complexity_score=complexity_score,
            estimated_token_cost=self._clamp_score((estimated_tokens / 4000.0) * 100.0),
            estimated_latency=self._clamp_score(context.get("estimated_latency_score"), default=min(100.0, 25.0 + estimated_tokens / 80.0)),
            expected_confidence=self._clamp_score(context.get("expected_confidence"), default=85.0),
        )
        risk_level = self._risk_level(risk_score)
        should_reuse_response = bool(allow_response_reuse)
        if allow_response_reuse is None:
            should_reuse_response = purpose in _CACHE_SAFE_PURPOSES

        reason = "Precisao priorizada: chamada de IA requerida."
        strategy: InvocationStrategy = "FULL_AI"
        should_invoke_ai = True

        if purpose == "data_insights":
            strategy = "EXPLAIN_ONLY"
            reason = "Geracao textual explicativa sobre evidencias ja calculadas pelo backend."
        elif purpose == "iar_semantic_fallback":
            strategy = "PARTIAL_AI"
            reason = "Fallback semantico pontual e de baixo custo."
        elif purpose == "csie_corporate_intent_plan":
            strategy = "HYBRID"
            reason = "CSIE local/memoria nao resolveu; IA complementa sem substituir regras corporativas."

        unsafe_reuse = (
            force_ai
            or scores.context_change_score > 0
            or scores.freshness_requirement_score >= 80
            or scores.business_risk_score >= 70
            or scores.expected_confidence < self.confidence_threshold
            or context.get("metrics_changed")
            or context.get("dimensions_changed")
            or context.get("period_changed")
            or context.get("business_rules_changed")
            or context.get("svr_changed")
            or context.get("metadata_changed")
            or context.get("user_requested_reinterpretation")
        )

        if (
            should_reuse_response
            and not unsafe_reuse
            and scores.cache_reliability_score >= self.cache_reliability_threshold
            and cache_key in self._response_cache
        ):
            strategy = "CACHE_ONLY"
            should_invoke_ai = False
            reason = "Cache reutilizado com contexto, versoes e confianca preservados."
        elif (
            context.get("blueprint_valid")
            and context.get("blueprint_compatible")
            and not unsafe_reuse
            and scores.blueprint_compatibility_score >= self.blueprint_compatibility_threshold
            and context.get("reusable_payload") is not None
        ):
            strategy = "BLUEPRINT_ONLY"
            should_invoke_ai = False
            reason = "Blueprint reutilizado com compatibilidade integral validada."

        decision = AIMDecision(
            decision_id=f"aim_{uuid.uuid4().hex[:12]}",
            purpose=purpose,
            strategy=strategy,
            should_invoke_ai=should_invoke_ai,
            reason=reason,
            risk_level=risk_level,
            scores=scores,
            estimated_tokens=estimated_tokens,
            estimated_cost=self._estimate_cost(estimated_tokens),
            estimated_latency_ms=max(80.0, estimated_tokens * 0.55),
            cache_key=cache_key,
            blueprint_id=str(context.get("blueprint_id")) if context.get("blueprint_id") else None,
        )
        self._record_decision(decision, context)
        return decision

    def _estimate_cost(self, tokens: int) -> float:
        return round((max(0, tokens) / 1000.0) * self.estimated_cost_per_1k_tokens, 8)

    def _extract_tokens(self, result: Any) -> int:
        if isinstance(result, tuple):
            for item in result:
                if isinstance(item, int):
                    return max(0, item)
        usage = getattr(result, "usage", None)
        return int(getattr(usage, "total_tokens", 0) or 0)

    async def invoke(
        self,
        *,
        tenant_id: uuid.UUID | str | None,
        purpose: str,
        operation: Callable[[AsyncOpenAI, str, AIClientLease], Awaitable[Any]],
        db: AsyncSession | None = None,
        tenant_config: dict[str, Any] | None = None,
        explicit_api_key: str | None = None,
        requested_model: str | None = None,
        context: dict[str, Any] | None = None,
        force_ai: bool = False,
        allow_response_reuse: bool | None = None,
    ) -> Any:
        decision = self.decide(
            tenant_id=tenant_id,
            purpose=purpose,
            context=context,
            force_ai=force_ai,
            allow_response_reuse=allow_response_reuse,
        )

        if decision.strategy == "CACHE_ONLY":
            cached = self._response_cache.get(str(decision.cache_key))
            if cached:
                self._record_invocation(
                    decision=decision,
                    result=cached.get("result"),
                    elapsed_ms=0.0,
                    tokens_consumed=0,
                    cache_hit=True,
                    provider=None,
                    model=None,
                )
                return cached.get("result")
            raise AIMPolicyViolationError("AIM selecionou CACHE_ONLY, mas o cache nao estava disponivel.")

        if decision.strategy == "BLUEPRINT_ONLY":
            payload = (context or {}).get("reusable_payload")
            if payload is not None:
                self._record_invocation(
                    decision=decision,
                    result=payload,
                    elapsed_ms=0.0,
                    tokens_consumed=0,
                    cache_hit=False,
                    provider=None,
                    model=None,
                )
                return payload
            raise AIMPolicyViolationError("AIM selecionou BLUEPRINT_ONLY, mas nao recebeu payload reutilizavel.")

        start = time.perf_counter()
        lease_info: dict[str, str | None] = {"provider": None, "model": requested_model}

        async def _governed_operation(client: AsyncOpenAI, model: str, lease: AIClientLease) -> Any:
            lease_info["provider"] = lease.provider_id
            lease_info["model"] = model
            return await operation(client, model, lease)

        try:
            result = await ai_credential_manager.execute_with_fallback(
                tenant_id=tenant_id,
                db=db,
                tenant_config=tenant_config,
                explicit_api_key=explicit_api_key,
                requested_model=requested_model,
                purpose=purpose,
                operation=_governed_operation,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            tokens_consumed = self._extract_tokens(result)
            if allow_response_reuse or purpose in _CACHE_SAFE_PURPOSES:
                self._response_cache[str(decision.cache_key)] = {
                    "result": result,
                    "created_at": self._now(),
                    "created_at_epoch": time.time(),
                    "purpose": purpose,
                    "tokens_consumed": tokens_consumed,
                }
            self._record_invocation(
                decision=decision,
                result=result,
                elapsed_ms=elapsed_ms,
                tokens_consumed=tokens_consumed,
                cache_hit=False,
                provider=lease_info["provider"],
                model=lease_info["model"],
            )
            return result
        except AICMError:
            self._dashboard["failed_invocations"] += 1
            raise
        except Exception:
            self._dashboard["failed_invocations"] += 1
            raise

    def _record_decision(self, decision: AIMDecision, context: dict[str, Any]) -> None:
        self._dashboard["total_decisions"] += 1
        if not decision.should_invoke_ai:
            self._dashboard["ai_calls_avoided"] += 1
        event = {
            "timestamp": self._now(),
            "decision": asdict(decision),
            "query": str(context.get("query") or context.get("pergunta") or "")[:1000],
            "context_versions": {
                "semantic_version": context.get("semantic_version"),
                "blueprint_version": context.get("blueprint_version"),
                "business_rules_version": context.get("business_rules_version"),
                "metadata_version": context.get("metadata_version"),
                "svr_version": context.get("svr_version"),
            },
        }
        self._decisions.append(event)
        self._decisions = self._decisions[-500:]

    def _record_invocation(
        self,
        *,
        decision: AIMDecision,
        result: Any,
        elapsed_ms: float,
        tokens_consumed: int,
        cache_hit: bool,
        provider: str | None,
        model: str | None,
    ) -> None:
        token_savings = max(0, decision.estimated_tokens - tokens_consumed)
        cost_real = self._estimate_cost(tokens_consumed)
        if decision.should_invoke_ai:
            self._dashboard["ai_calls"] += 1
        if cache_hit:
            self._dashboard["cache_hits"] += 1
        if decision.strategy == "BLUEPRINT_ONLY":
            self._dashboard["blueprint_reuses"] += 1
        self._dashboard["successful_invocations"] += 1
        self._dashboard["tokens_estimated"] += decision.estimated_tokens
        self._dashboard["tokens_consumed"] += tokens_consumed
        self._dashboard["tokens_saved"] += token_savings
        self._dashboard["estimated_cost"] += decision.estimated_cost
        self._dashboard["real_cost"] += cost_real
        self._dashboard["latency_total_ms"] += elapsed_ms

        event = {
            "timestamp": self._now(),
            "decision_id": decision.decision_id,
            "purpose": decision.purpose,
            "strategy": decision.strategy,
            "reason": decision.reason,
            "scores": asdict(decision.scores),
            "risk_level": decision.risk_level,
            "provider": provider,
            "model": model,
            "tokens_estimated": decision.estimated_tokens,
            "tokens_consumed": tokens_consumed,
            "tokens_saved": token_savings,
            "estimated_cost": decision.estimated_cost,
            "real_cost": cost_real,
            "elapsed_ms": round(elapsed_ms, 2),
            "cache_hit": cache_hit,
            "result_type": type(result).__name__,
        }
        self._invocations.append(event)
        self._invocations = self._invocations[-500:]
        self._learning_events.append(
            {
                "timestamp": event["timestamp"],
                "decision_id": decision.decision_id,
                "strategy": decision.strategy,
                "elapsed_ms": event["elapsed_ms"],
                "tokens_delta": tokens_consumed - decision.estimated_tokens,
                "outcome": "SUCCESS",
            }
        )
        self._learning_events = self._learning_events[-500:]

    def register_feedback(self, decision_id: str, accepted: bool, correction: str | None = None) -> None:
        self._learning_events.append(
            {
                "timestamp": self._now(),
                "decision_id": decision_id,
                "accepted": bool(accepted),
                "correction": correction,
                "outcome": "USER_FEEDBACK",
            }
        )
        self._learning_events = self._learning_events[-500:]

    def get_status(self, tenant_id: uuid.UUID | str | None = None) -> dict[str, Any]:
        _ = tenant_id
        total = max(1, int(self._dashboard["total_decisions"]))
        successful = int(self._dashboard["successful_invocations"])
        failed = int(self._dashboard["failed_invocations"])
        invocations = max(1, successful + failed)
        ai_calls = int(self._dashboard["ai_calls"])
        avoided = int(self._dashboard["ai_calls_avoided"])
        avg_latency = self._dashboard["latency_total_ms"] / max(1, successful)
        return {
            "status": "HEALTHY" if failed == 0 else "DEGRADED",
            "total_decisions": total,
            "ai_calls": ai_calls,
            "ai_calls_avoided": avoided,
            "reuse_rate": round((avoided / total) * 100, 2),
            "cache_hit_rate": round((int(self._dashboard["cache_hits"]) / total) * 100, 2),
            "blueprint_reuse_rate": round((int(self._dashboard["blueprint_reuses"]) / total) * 100, 2),
            "invocation_success_rate": round((successful / invocations) * 100, 2),
            "tokens_estimated": int(self._dashboard["tokens_estimated"]),
            "tokens_consumed": int(self._dashboard["tokens_consumed"]),
            "tokens_saved": int(self._dashboard["tokens_saved"]),
            "estimated_cost": round(float(self._dashboard["estimated_cost"]), 8),
            "real_cost": round(float(self._dashboard["real_cost"]), 8),
            "estimated_savings": round(
                max(0.0, float(self._dashboard["estimated_cost"]) - float(self._dashboard["real_cost"])),
                8,
            ),
            "average_latency_ms": round(avg_latency, 2),
            "recent_decisions": self._decisions[-10:],
            "recent_invocations": self._invocations[-10:],
            "learning_events": self._learning_events[-10:],
            "policies": {
                "semantic_similarity_threshold": self.semantic_similarity_threshold,
                "blueprint_compatibility_threshold": self.blueprint_compatibility_threshold,
                "cache_reliability_threshold": self.cache_reliability_threshold,
                "confidence_threshold": self.confidence_threshold,
                "precision_over_cost": True,
            },
        }


ai_invocation_manager = AIInvocationManager()
