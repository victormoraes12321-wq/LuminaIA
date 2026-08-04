from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional
from contracts.ai_tool_registry_v2 import AIToolCircuitState, AIToolCircuitBreakerStateV2

logger = logging.getLogger("luminaai.services.ai_tool_registry.circuit_breaker")


class CircuitBreakerManager:
    """
    Manages in-memory Circuit Breaker states per tool and version.
    Prevents cascading failures when a tool adapter experiences repeated crashes or timeouts.
    """

    def __init__(self, failure_threshold: int = 5, recovery_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_key(self, tool_id: str, version: str) -> str:
        return f"{tool_id}:{version}"

    def get_state(self, tool_id: str, version: str) -> AIToolCircuitState:
        key = self._get_key(tool_id, version)
        record = self._states.get(key)
        if not record:
            return AIToolCircuitState.CLOSED

        current_state = record["state"]
        if current_state == AIToolCircuitState.OPEN:
            # Check recovery window
            elapsed = time.time() - record["last_failure_time"]
            if elapsed >= self.recovery_seconds:
                record["state"] = AIToolCircuitState.HALF_OPEN
                logger.info("Circuit for %s transitioned OPEN -> HALF_OPEN after %.1fs", key, elapsed)
                return AIToolCircuitState.HALF_OPEN

        return current_state

    def record_success(self, tool_id: str, version: str) -> None:
        key = self._get_key(tool_id, version)
        record = self._states.get(key)
        if not record:
            return

        if record["state"] == AIToolCircuitState.HALF_OPEN:
            record["state"] = AIToolCircuitState.CLOSED
            record["failure_count"] = 0
            logger.info("Circuit for %s transitioned HALF_OPEN -> CLOSED (Success)", key)
        elif record["state"] == AIToolCircuitState.CLOSED:
            record["failure_count"] = max(0, record["failure_count"] - 1)

    def record_failure(self, tool_id: str, version: str) -> AIToolCircuitState:
        key = self._get_key(tool_id, version)
        now = time.time()
        record = self._states.setdefault(
            key,
            {
                "state": AIToolCircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": now,
            },
        )
        record["failure_count"] += 1
        record["last_failure_time"] = now

        if record["state"] in (AIToolCircuitState.CLOSED, AIToolCircuitState.HALF_OPEN):
            if record["failure_count"] >= self.failure_threshold or record["state"] == AIToolCircuitState.HALF_OPEN:
                record["state"] = AIToolCircuitState.OPEN
                logger.warning("Circuit for %s transitioned to OPEN (Failures: %d)", key, record["failure_count"])

        return record["state"]

    def export_state_contract(self, tool_id: str, version: str, adapter_id: str) -> AIToolCircuitBreakerStateV2:
        key = self._get_key(tool_id, version)
        record = self._states.get(key, {})
        state = record.get("state", AIToolCircuitState.CLOSED)
        return AIToolCircuitBreakerStateV2(
            tool_id=tool_id,
            adapter_id=adapter_id,
            state=state,
            failure_count=record.get("failure_count", 0),
            success_count=record.get("success_count", 0),
            last_failure_at=str(record.get("last_failure_time")) if record.get("last_failure_time") else None,
            last_state_change=str(time.time()),
        )


circuit_breaker_manager = CircuitBreakerManager()
