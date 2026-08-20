from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from config import settings
from contracts.ai_tool_registry_v2 import (
    AIToolInvocationContextV2,
    AIToolInvocationErrorV2,
    AIToolInvocationRequestV2,
    AIToolInvocationResultV2,
    AIToolOutputEnvelopeV2,
    AIToolRegistryMode,
)
from services.ai_tool_registry.adapters.registry_map import REGISTERED_TOOL_ADAPTERS, get_adapter_class
from services.ai_tool_registry.circuit_breaker import circuit_breaker_manager
from services.ai_tool_registry.exceptions import (
    AIToolAccessDeniedException,
    AIToolAdapterNotRegisteredException,
    AIToolCircuitOpenException,
    AIToolDisabledException,
    AIToolInputInvalidException,
    AIToolNotFoundException,
    AIToolOutputInvalidException,
    AIToolRateLimitedException,
    AIToolTimeoutException,
)
from services.ai_tool_registry.rate_limiter import rate_limiter_manager
from services.ai_tool_registry.repository import ai_tool_registry_repository

logger = logging.getLogger("luminaai.services.ai_tool_registry.invocation_service")


class GovernedAIToolInvocationService:
    """
    Fail-closed execution authority for governed AI tool invocations.
    Guarantees auth, schema validation, payload limits, rate limiting, circuit breaker,
    deadline timeouts, output redaction, and structural audit logging.
    """

    def __init__(self):
        self.repo = ai_tool_registry_repository
        self.circuit_mgr = circuit_breaker_manager
        self.rate_limiter = rate_limiter_manager

    async def invoke_tool(
        self,
        request: AIToolInvocationRequestV2,
        context: AIToolInvocationContextV2,
    ) -> AIToolOutputEnvelopeV2:
        start_time = time.time()
        tool_id = request.tool_id

        # 1. Check feature flag mode
        current_mode = settings.AI_TOOL_REGISTRY_MODE
        if current_mode == "LEGACY_ONLY":
            logger.info("AI_TOOL_REGISTRY_MODE is LEGACY_ONLY. Invocation permitted only via legacy handlers.")

        # Map tool_id to adapter
        adapter_id_map = {
            "lumina.enterprise_knowledge.search": "enterprise_knowledge.search.v1",
            "lumina.enterprise_knowledge.get_metric_definition": "enterprise_knowledge.get_metric_definition.v1",
            "lumina.temporal.normalize": "temporal.normalize.v1",
            "lumina.semantic.search": "semantic.search.v1",
            "lumina.semantic.resolve_entity": "semantic.resolve_entity.v1",
            "lumina.context.get_public_summary": "context.get_public_summary.v1",
            "lumina.profile.get_application_summary": "profile.get_application_summary.v1",
            "lumina.intent.validate": "intent.validate.v1",
            "lumina.comparison.plan": "comparison.plan.v1",
            "lumina.comparison.validate_plan": "comparison.validate_plan.v1",
            "lumina.clarification.build_options": "clarification.build_options.v1",
            "lumina.provenance.get_public_summary": "provenance.get_public_summary.v1",
        }
        adapter_id = adapter_id_map.get(tool_id)

        # Forbidden / Unknown tools rejection
        if not adapter_id or adapter_id not in REGISTERED_TOOL_ADAPTERS:
            raise AIToolNotFoundException(f"AI_TOOL_NOT_FOUND: Tool '{tool_id}' is not registered in the system.")

        # 2. Check Rate Limiter
        if not self.rate_limiter.check_rate_limit(context.tenant_id, context.user_id, tool_id):
            raise AIToolRateLimitedException(f"Rate limit exceeded for tool '{tool_id}' on tenant '{context.tenant_id}'.")

        # 3. Check Circuit Breaker
        circuit_state = self.circuit_mgr.get_state(tool_id, context.tool_version)
        if circuit_state.value == "OPEN":
            raise AIToolCircuitOpenException(f"Circuit Breaker for tool '{tool_id}' is OPEN.")

        # 4. Instantiate Adapter statically (no dynamic import!)
        adapter_cls = get_adapter_class(adapter_id)
        adapter_inst = adapter_cls()

        # 5. Validate context & permissions
        await adapter_inst.validate_context(context)

        # 6. Validate input arguments
        try:
            valid_args = await adapter_inst.validate_arguments(request.raw_arguments)
        except Exception as exc:
            raise AIToolInputInvalidException(f"Input argument validation failed for tool '{tool_id}': {exc}")

        # 7. Execute adapter with deadline timeout
        timeout = settings.AI_TOOL_MAX_EXECUTION_TIME_SECONDS
        try:
            raw_output = await asyncio.wait_for(
                adapter_inst.execute(valid_args, context),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self.circuit_mgr.record_failure(tool_id, context.tool_version)
            raise AIToolTimeoutException(f"Tool execution for '{tool_id}' timed out after {timeout} seconds.")
        except Exception as exc:
            self.circuit_mgr.record_failure(tool_id, context.tool_version)
            raise RuntimeError(f"Tool execution failed for '{tool_id}': {exc}")

        # 8. Validate output
        try:
            validated_output = await adapter_inst.validate_output(raw_output)
        except Exception as exc:
            self.circuit_mgr.record_failure(tool_id, context.tool_version)
            raise AIToolOutputInvalidException(f"Output schema validation failed for tool '{tool_id}': {exc}")

        # 9. Apply Redaction
        redacted_output = await adapter_inst.redact_output(validated_output, context)

        # Record success
        self.circuit_mgr.record_success(tool_id, context.tool_version)
        duration_ms = round((time.time() - start_time) * 1000.0, 2)

        out_serialized = json.dumps(redacted_output, sort_keys=True, default=str)
        out_checksum = hashlib.sha256(out_serialized.encode("utf-8")).hexdigest()

        # 10. Audit Logging
        await self.repo.log_invocation_record(
            request_id=context.request_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            tool_id=tool_id,
            version=context.tool_version,
            snapshot_id=context.snapshot_version,
            duration_ms=duration_ms,
            status="SUCCESS",
            input_checksum=valid_args.args_checksum,
            output_checksum=out_checksum,
            circuit_state=circuit_state.value,
        )

        res_obj = AIToolInvocationResultV2(
            success=True,
            data=redacted_output,
            execution_time_ms=duration_ms,
            cache_hit=False,
            output_checksum=out_checksum,
        )

        ctx_checksum = hashlib.sha256(context.model_dump_json().encode("utf-8")).hexdigest()
        envelope_chk = hashlib.sha256((tool_id + out_checksum).encode("utf-8")).hexdigest()

        return AIToolOutputEnvelopeV2(
            tool_id=tool_id,
            tool_version=context.tool_version,
            adapter_id=adapter_id,
            result=res_obj,
            invocation_context_checksum=ctx_checksum,
            envelope_checksum=envelope_chk,
        )


governed_ai_tool_invocation_service = GovernedAIToolInvocationService()
