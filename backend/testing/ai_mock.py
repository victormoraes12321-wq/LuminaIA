from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


class DeterministicAIMockError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIMockCall:
    purpose: str
    model: str | None
    structured: bool


class _Completions:
    def __init__(self, provider: "DeterministicAIProvider", *, structured: bool) -> None:
        self._provider = provider
        self._structured = structured

    async def create(self, **kwargs: Any) -> Any:
        return await self._provider.respond(kwargs, structured=False)

    async def parse(self, **kwargs: Any) -> Any:
        return await self._provider.respond(kwargs, structured=True)


class DeterministicOpenAIClient:
    def __init__(self, provider: "DeterministicAIProvider") -> None:
        self.chat = SimpleNamespace(completions=_Completions(provider, structured=False))
        self.beta = SimpleNamespace(
            chat=SimpleNamespace(completions=_Completions(provider, structured=True))
        )

    async def close(self) -> None:
        return None


class DeterministicAIProvider:
    """Queue-driven OpenAI stand-in with no network implementation."""

    def __init__(self) -> None:
        self.calls: list[AIMockCall] = []
        self._structured_payloads: deque[Any] = deque()
        self._text_payloads: deque[str] = deque()
        self._failure: Exception | None = None
        self._timeout = False
        self.client = DeterministicOpenAIClient(self)

    def reset(self) -> None:
        self.calls.clear()
        self._structured_payloads.clear()
        self._text_payloads.clear()
        self._failure = None
        self._timeout = False

    def queue_structured(self, payload: Any) -> None:
        self._structured_payloads.append(payload)

    def queue_text(self, payload: str) -> None:
        self._text_payloads.append(payload)

    def fail_with(self, error: Exception) -> None:
        self._failure = error

    def timeout_next(self) -> None:
        self._timeout = True

    async def respond(self, kwargs: dict[str, Any], *, structured: bool) -> Any:
        self.calls.append(
            AIMockCall(
                purpose=str(kwargs.get("purpose") or "openai_mock"),
                model=kwargs.get("model"),
                structured=structured,
            )
        )
        if self._timeout:
            self._timeout = False
            raise TimeoutError("Timeout simulado do provedor de IA.")
        if self._failure is not None:
            error = self._failure
            self._failure = None
            raise error
        await asyncio.sleep(0)

        usage = SimpleNamespace(total_tokens=0)
        if structured:
            if not self._structured_payloads:
                raise DeterministicAIMockError(
                    "Resposta estruturada nao configurada no mock de IA."
                )
            payload = self._structured_payloads.popleft()
            response_format = kwargs.get("response_format")
            if response_format is not None and not isinstance(payload, response_format):
                payload = response_format.model_validate(payload)
            message = SimpleNamespace(parsed=payload, content=None)
        else:
            content = (
                self._text_payloads.popleft()
                if self._text_payloads
                else "Resposta simulada deterministica."
            )
            message = SimpleNamespace(content=content, parsed=None)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=usage,
        )


deterministic_ai_provider = DeterministicAIProvider()
