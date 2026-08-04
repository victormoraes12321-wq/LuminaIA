from __future__ import annotations

from typing import Any, Dict
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolInvocationContextV2,
    AIToolValidatedArgumentsV2,
)
from contracts.safe_analytical_postgresql_v2.query_spec import AnalyticalQuerySpecV2
from services.ai_tool_registry.adapters.base import GovernedToolAdapter
from services.safe_analytical_postgresql.execution_service import SafeAnalyticalPostgreSQLService


class AnalyticalPostgreSQLQueryToolAdapter(GovernedToolAdapter):
    """
    Governed AI Tool Adapter for executing read-only analytical PostgreSQL queries.
    Tool Name: lumina.analytical_postgresql.query
    Adapter ID: analytical_postgresql.query.v1
    Required Capability: ANALYTICAL_POSTGRESQL_READ
    """

    @property
    def adapter_id(self) -> str:
        return "analytical_postgresql.query.v1"

    @property
    def tool_id(self) -> str:
        return "lumina.analytical_postgresql.query"

    @property
    def tool_version(self) -> str:
        return "1.0.0"

    async def validate_registration(self) -> None:
        pass

    async def validate_context(self, context: AIToolInvocationContextV2) -> None:
        if not context.tenant_id:
            raise ValueError("Tenant ID is required for analytical query invocation")

    async def validate_arguments(self, raw_args: Dict[str, Any]) -> AIToolValidatedArgumentsV2:
        query_spec_dict = raw_args.get("query_spec", raw_args)
        spec = AnalyticalQuerySpecV2.model_validate(query_spec_dict)
        return AIToolValidatedArgumentsV2(
            raw_arguments=raw_args,
            parsed_arguments=spec.model_dump(mode="json"),
            validation_checksum="valid_analytical_spec",
        )

    def __init__(self):
        self.service = SafeAnalyticalPostgreSQLService()

    async def execute(self, params: Any, context: Any) -> Dict[str, Any]:
        # Handle dict or AIToolValidatedArgumentsV2/AIToolInvocationContextV2
        if isinstance(params, dict):
            raw_spec = params.get("query_spec", params)
            tenant_id = context.get("tenant_id", "system") if isinstance(context, dict) else context.tenant_id
            user_id = context.get("user_id", "system") if isinstance(context, dict) else context.user_id
        else:
            raw_spec = params.parsed_arguments
            tenant_id = context.tenant_id
            user_id = context.user_id

        spec = AnalyticalQuerySpecV2.model_validate(raw_spec)

        exec_result = await self.service.execute_query(
            spec=spec,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return exec_result.model_dump(mode="json")
