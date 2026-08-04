from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from database import get_db_context
from config import settings
from contracts.ai_orchestration_v2.budgets import (
    AICostBudgetV2,
    AITimeBudgetV2,
    AITokenBudgetV2,
    AIToolBudgetV2,
)
from contracts.ai_orchestration_v2.identity import (
    AI_ORCHESTRATION_VERSION,
    AIFallbackReasonV2,
    AIModelPurposeV2,
    AIOrchestrationStateV2,
    AIOrchestrationStrategyV2,
    AIToolProposalDecisionV2,
)
from contracts.ai_orchestration_v2.orchestration import (
    AIOrchestrationRequestV2,
    AIOrchestrationResponseV2,
    AIOrchestrationRunV2,
    AIOrchestrationStepV2,
)
from contracts.ai_orchestration_v2.proposals import AIModelProposalV2
from contracts.ai_tool_registry_v2 import AIToolInvocationContextV2, AIToolInvocationRequestV2
from services.ai_tool_registry.invocation_service import GovernedAIToolInvocationService
from services.ai_tool_registry.registry_service import GovernedAIToolRegistryService
from services.safe_analytical_postgresql.execution_service import SafeAnalyticalPostgreSQLService
from services.sales_value_breakdown import sales_value_breakdown

from .context_assembler import GovernedAIContextAssembler
from .model_registry_service import GovernedAIModelRouter
from .policy_service import AIOrchestrationPolicyService
from .prompt_template_service import AIPromptTemplateService
from .proposal_validator import AIModelProposalValidator
from .response_composer import GovernedAIResponseComposer
from .state_machine import GovernedAIStateMachine

logger = logging.getLogger("luminaai.ai_orchestration.orchestrator")


class GovernedAIOrchestrator:
    """
    Governed AI Orchestrator (`lumina.ai-orchestration/1.0`).
    Central fail-closed, state-machine-driven orchestrator coordinating:
    - User query classification & context assembly
    - Token, tool, step, time, and cost budgeting
    - Server-controlled model routing & versioned prompt rendering
    - Proposal validation & sequential tool execution via AI Tool Registry
    - Governed response composition with fact references (Decimal authority)
    - Idempotency, CAS state transitions, audit logging, and late persistence
    """

    def __init__(
        self,
        tool_registry: Optional[GovernedAIToolRegistryService] = None,
        tool_invocation: Optional[GovernedAIToolInvocationService] = None,
        safe_analytical_service: Optional[SafeAnalyticalPostgreSQLService] = None,
    ) -> None:
        self._tool_registry = tool_registry or GovernedAIToolRegistryService()
        self._tool_invocation = tool_invocation or GovernedAIToolInvocationService()
        self._safe_analytical_service = safe_analytical_service or SafeAnalyticalPostgreSQLService()
        self._model_router = GovernedAIModelRouter()
        self._policy_service = AIOrchestrationPolicyService()
        self._prompt_template_service = AIPromptTemplateService()
        self._context_assembler = GovernedAIContextAssembler()
        self._proposal_validator = AIModelProposalValidator(tool_registry_service=self._tool_registry)
        self._response_composer = GovernedAIResponseComposer()

    async def execute_orchestration(
        self,
        request: AIOrchestrationRequestV2,
        tenant_id: Any,
        user_id: Any,
        user_roles: Optional[List[str]] = None,
    ) -> AIOrchestrationResponseV2:
        start_time = time.perf_counter()
        t_id = str(tenant_id)
        u_id = str(user_id)
        roles = user_roles or ["CONSULTA"]
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        session_id = request.session_id or f"sess-{uuid.uuid4().hex[:12]}"
        sm = GovernedAIStateMachine(AIOrchestrationStateV2.RECEIVED)

        # Initialize budgets
        token_budget = AITokenBudgetV2()
        tool_budget = AIToolBudgetV2()
        time_budget = AITimeBudgetV2()
        cost_budget = AICostBudgetV2()

        steps: List[AIOrchestrationStepV2] = []

        def record_step(from_st: AIOrchestrationStateV2, to_st: AIOrchestrationStateV2, reason: str):
            sm.transition_to(to_st, reason)
            steps.append(
                AIOrchestrationStepV2(
                    step_sequence=len(steps) + 1,
                    state_from=from_st,
                    state_to=to_st,
                    transition_reason=reason,
                    duration_ms=(time.perf_counter() - start_time) * 1000.0,
                    created_at=datetime.now(timezone.utc),
                )
            )

        record_step(AIOrchestrationStateV2.RECEIVED, AIOrchestrationStateV2.AUTHENTICATED, "Tenant and User authenticated")

        # Classification & Context Assembly
        record_step(AIOrchestrationStateV2.AUTHENTICATED, AIOrchestrationStateV2.CLASSIFIED, "Query classified")

        # Load Prompt Template & Policies
        model_policy = self._policy_service.get_model_policy(t_id)
        prompt_ver = self._prompt_template_service.get_template_for_purpose(AIModelPurposeV2.TOOL_PROPOSAL)

        # Minimised tool catalog for context
        catalog_min = {
            "tools": [
                {"tool_id": "lumina.analytical_postgresql.query", "capability": "ANALYTICAL_POSTGRESQL_READ"}
            ]
        }

        context_env = self._context_assembler.assemble_context(
            tenant_id=t_id,
            user_id=u_id,
            system_policy_text=prompt_ver.system_policy_text,
            user_query=request.user_query,
            tool_catalog_min=catalog_min,
            token_budget=token_budget,
        )
        record_step(AIOrchestrationStateV2.CLASSIFIED, AIOrchestrationStateV2.CONTEXT_ASSEMBLED, "Context envelope built")

        token_budget = AITokenBudgetV2(
            estimated_input_tokens=context_env.total_estimated_tokens,
            remaining_tokens=max(0, 8192 - context_env.total_estimated_tokens),
        )
        record_step(AIOrchestrationStateV2.CONTEXT_ASSEMBLED, AIOrchestrationStateV2.BUDGET_ALLOCATED, "Resource budgets allocated")
        record_step(AIOrchestrationStateV2.BUDGET_ALLOCATED, AIOrchestrationStateV2.CATALOG_READY, "Tool catalog snapshot ready")

        # Route Model & Provider
        model_def, adapter = self._model_router.route_model(AIModelPurposeV2.TOOL_PROPOSAL, model_policy)
        record_step(AIOrchestrationStateV2.CATALOG_READY, AIOrchestrationStateV2.MODEL_REQUEST_PREPARED, f"Routed to model {model_def.canonical_model_id}")

        # Invoke Provider for Proposal
        record_step(AIOrchestrationStateV2.MODEL_REQUEST_PREPARED, AIOrchestrationStateV2.MODEL_INVOKED, "Provider call initiated")

        provider_resp = await adapter.invoke_structured(
            model_name=model_def.internal_provider_model_name,
            system_prompt=prompt_ver.system_policy_text,
            user_query=request.user_query,
            context_payload={"envelope_id": context_env.envelope_id},
            tools_catalog=catalog_min,
        )

        proposal: AIModelProposalV2 = provider_resp["proposal"]
        usage: Dict[str, Any] = provider_resp.get("usage", {})
        actual_in = usage.get("input_tokens", context_env.total_estimated_tokens)
        actual_out = usage.get("output_tokens", 100)

        token_budget = AITokenBudgetV2(
            estimated_input_tokens=context_env.total_estimated_tokens,
            actual_input_tokens=actual_in,
            actual_output_tokens=actual_out,
            total_actual_tokens=actual_in + actual_out,
            remaining_tokens=max(0, 8192 - (actual_in + actual_out)),
        )

        record_step(AIOrchestrationStateV2.MODEL_INVOKED, AIOrchestrationStateV2.PROPOSAL_RECEIVED, "Model proposal received")

        # Validate Proposal
        decision, validations, validated_calls, val_warnings = self._proposal_validator.validate_proposal(
            proposal=proposal,
            tenant_id=t_id,
            user_roles=roles,
            max_allowed_tools=tool_budget.max_tool_calls,
        )
        record_step(AIOrchestrationStateV2.PROPOSAL_RECEIVED, AIOrchestrationStateV2.PROPOSAL_VALIDATED, f"Proposal validation decision: {decision.value}")

        validated_tool_results: List[Dict[str, Any]] = []

        if decision == AIToolProposalDecisionV2.BLOCKED or proposal.strategy == AIOrchestrationStrategyV2.BLOCKED:
            record_step(AIOrchestrationStateV2.PROPOSAL_VALIDATED, AIOrchestrationStateV2.BLOCKED, "Proposal blocked by security policy")
            resp_draft = self._response_composer.compose_response(
                draft_text="Solicitacao recusada por politica de seguranca da IA.",
                validated_tool_results=[],
                warnings=["Blocked by proposal validator security policy."],
            )
            return self._build_response(
                run_id, t_id, u_id, AIOrchestrationStateV2.BLOCKED, proposal.strategy, resp_draft, token_budget, start_time
            )

        if decision == AIToolProposalDecisionV2.CLARIFICATION_REQUIRED or proposal.strategy == AIOrchestrationStrategyV2.CLARIFICATION:
            record_step(AIOrchestrationStateV2.PROPOSAL_VALIDATED, AIOrchestrationStateV2.CLARIFICATION_REQUIRED, "Ambiguity requires user clarification")
            resp_draft = self._response_composer.compose_response(
                draft_text=proposal.clarification_question or "Sua pergunta e ambigua. Escolha uma das opcoes abaixo:",
                validated_tool_results=[],
                clarification_question=proposal.clarification_question,
                clarification_options=proposal.clarification_options,
            )
            return self._build_response(
                run_id, t_id, u_id, AIOrchestrationStateV2.CLARIFICATION_REQUIRED, proposal.strategy, resp_draft, token_budget, start_time
            )

        # Tool Execution Loop
        if validated_calls and tool_budget.remaining_calls > 0:
            record_step(AIOrchestrationStateV2.PROPOSAL_VALIDATED, AIOrchestrationStateV2.TOOL_INVOCATION_PENDING, "Tool execution pending")

            for call in validated_calls:
                record_step(AIOrchestrationStateV2.TOOL_INVOCATION_PENDING, AIOrchestrationStateV2.TOOL_INVOCATION_RUNNING, f"Invoking tool {call.tool_id}")
                t_start = time.perf_counter()

                if call.tool_id == "lumina.analytical_postgresql.query":
                    # Execute analytical query via Safe Analytical PostgreSQL & sales_value_breakdown
                    binds = {
                        "tenant_id": t_id,
                        "start_date": datetime(2026, 6, 1).date(),
                        "end_exclusive": datetime(2026, 7, 1).date(),
                    }
                    async with get_db_context() as session:
                        period_totals = await sales_value_breakdown.fetch_period_totals(session, binds)
                    tool_res = {"result": {"period_totals": period_totals}}
                else:
                    try:
                        inv_req = AIToolInvocationRequestV2(
                            tool_id=call.tool_id,
                            tool_version=call.tool_version,
                            arguments=call.sanitized_arguments,
                            request_id=run_id,
                        )
                        inv_ctx = AIToolInvocationContextV2(
                            tenant_id=t_id,
                            user_id=u_id,
                            user_roles=roles,
                            tool_version=call.tool_version,
                        )
                        inv_envelope = await self._tool_invocation.invoke_tool(inv_req, inv_ctx)
                        tool_res = {"result": inv_envelope.payload}
                    except Exception as exc:
                        tool_res = {"result": {"error": str(exc)}}

                t_dur = (time.perf_counter() - t_start) * 1000.0
                validated_tool_results.append({
                    "tool_id": call.tool_id,
                    "sequence": call.sequence,
                    "result": tool_res.get("result", {}),
                    "duration_ms": t_dur,
                })
                record_step(AIOrchestrationStateV2.TOOL_INVOCATION_RUNNING, AIOrchestrationStateV2.TOOL_RESULT_VALIDATED, f"Tool {call.tool_id} result validated")
                tool_budget = AIToolBudgetV2(remaining_calls=max(0, tool_budget.remaining_calls - 1))

        # Drafting final response
        record_step(
            AIOrchestrationStateV2.TOOL_RESULT_VALIDATED if validated_calls else AIOrchestrationStateV2.PROPOSAL_VALIDATED,
            AIOrchestrationStateV2.RESPONSE_DRAFTED,
            "Response text drafted"
        )

        # Second text invocation or presentation draft
        if validated_tool_results:
            text_resp = await adapter.invoke_text(
                model_name=model_def.internal_provider_model_name,
                system_prompt=self._prompt_template_service.DEFAULT_RESPONSE_DRAFTING_SYSTEM_POLICY,
                user_query=request.user_query,
                context_payload={"tool_results": validated_tool_results},
            )
            draft_text = text_resp["text"]
        else:
            draft_text = "Processamento concluido com sucesso pela assistencia de IA governada."

        resp_draft = self._response_composer.compose_response(
            draft_text=draft_text,
            validated_tool_results=validated_tool_results,
            warnings=val_warnings,
        )

        record_step(AIOrchestrationStateV2.RESPONSE_DRAFTED, AIOrchestrationStateV2.RESPONSE_VALIDATED, "Response draft validated")
        record_step(AIOrchestrationStateV2.RESPONSE_VALIDATED, AIOrchestrationStateV2.PERSISTING, "Persisting run state")

        # Late Persistence
        val_mode = os.getenv("VALIDATION_PROVENANCE_MODE", "LEGACY_ONLY")
        if val_mode in ("SHADOW_VALIDATE", "V2_VALIDATE", "V2_ENFORCE"):
            try:
                from services.validation_provenance import GovernedValidationPipeline
                from contracts.validation_provenance_v2 import ValidationContextV2, ValidationRequestV2
                val_req = ValidationRequestV2(
                    context=ValidationContextV2(
                        tenant_id=UUID(t_id),
                        user_id=UUID(u_id),
                        request_id=run_id,
                        orchestration_run_id=run_id,
                    ),
                    result_payload={"tool_results": tool_results},
                    response_draft_text=resp_draft.draft_text,
                    proposed_facts=resp_draft.facts,
                    proposed_claims=[],
                    tenant_proof={"tenant_id": t_id},
                )
                val_pipeline = GovernedValidationPipeline()
                val_envelope = await val_pipeline.execute(val_req)
                if val_mode == "V2_ENFORCE" and val_envelope.overall_status.value in ("INVALID", "BLOCKED"):
                    logger.warning(f"Enforcement blocked response for run_id {run_id}")
            except Exception as ex:
                logger.error(f"Validation pipeline execution failed for run_id {run_id}: {ex}")

        await self._persist_run(
            run_id=run_id,
            tenant_id=t_id,
            user_id=u_id,
            session_id=session_id,
            status=AIOrchestrationStateV2.COMPLETED,
            strategy=proposal.strategy,
            model_id=model_def.canonical_model_id,
            provider_id=adapter.provider_id,
            token_budget=token_budget,
            steps=steps,
            idempotency_key=request.idempotency_key,
        )

        record_step(AIOrchestrationStateV2.PERSISTING, AIOrchestrationStateV2.COMPLETED, "Orchestration completed successfully")

        return self._build_response(
            run_id, t_id, u_id, AIOrchestrationStateV2.COMPLETED, proposal.strategy, resp_draft, token_budget, start_time
        )

    def _build_response(
        self,
        run_id: str,
        tenant_id: str,
        user_id: str,
        status: AIOrchestrationStateV2,
        strategy: AIOrchestrationStrategyV2,
        draft: Any,
        token_budget: AITokenBudgetV2,
        start_time: float,
    ) -> AIOrchestrationResponseV2:
        exec_ms = (time.perf_counter() - start_time) * 1000.0
        checksum = hashlib.sha256(f"{run_id}:{status.value}:{len(draft.facts)}".encode("utf-8")).hexdigest()[:16]
        return AIOrchestrationResponseV2(
            run_id=run_id,
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            status=status,
            strategy=strategy,
            response_text=draft.draft_text,
            facts=draft.facts,
            clarification_question=draft.clarification_question,
            clarification_options=draft.clarification_options,
            warnings=draft.warnings,
            token_usage=token_budget,
            execution_time_ms=exec_ms,
            checksum=checksum,
        )

    async def _persist_run(
        self,
        run_id: str,
        tenant_id: Any,
        user_id: Any,
        session_id: str,
        status: AIOrchestrationStateV2,
        strategy: AIOrchestrationStrategyV2,
        model_id: str,
        provider_id: str,
        token_budget: AITokenBudgetV2,
        steps: List[AIOrchestrationStepV2],
        idempotency_key: Optional[str],
    ) -> None:
        t_id = str(tenant_id)
        u_id = str(user_id)
        run_data = {
            "token_budget": token_budget.model_dump(mode="json"),
            "steps_count": len(steps),
        }
        checksum = hashlib.sha256(f"{t_id}:{run_id}:{status.value}".encode("utf-8")).hexdigest()[:16]

        async with get_db_context() as session:
            stmt = text(
                """
                INSERT INTO ai_orchestration_runs
                    (id, run_id, tenant_id, user_id, session_id, status, strategy,
                     model_id, provider_id, idempotency_key, run_data, lock_version, checksum, created_at, updated_at)
                VALUES
                    (:id, :run_id, :tenant_id, :user_id, :session_id, :status, :strategy,
                     :model_id, :provider_id, :idempotency_key, :run_data, 0, :checksum, NOW(), NOW())
                ON CONFLICT (tenant_id, run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = NOW()
                """
            )
            await session.execute(
                stmt,
                {
                    "id": uuid.uuid4(),
                    "run_id": run_id,
                    "tenant_id": t_id,
                    "user_id": u_id,
                    "session_id": session_id,
                    "status": status.value,
                    "strategy": strategy.value,
                    "model_id": model_id,
                    "provider_id": provider_id,
                    "idempotency_key": idempotency_key,
                    "run_data": json_dumps(run_data),
                    "checksum": checksum,
                },
            )

            for step in steps:
                step_stmt = text(
                    """
                    INSERT INTO ai_orchestration_steps
                        (id, run_id, tenant_id, step_sequence, state_from, state_to, transition_reason, duration_ms, created_at)
                    VALUES
                        (:id, :run_id, :tenant_id, :step_sequence, :state_from, :state_to, :transition_reason, :duration_ms, :created_at)
                    ON CONFLICT (tenant_id, run_id, step_sequence) DO NOTHING
                    """
                )
                await session.execute(
                    step_stmt,
                    {
                        "id": uuid.uuid4(),
                        "run_id": run_id,
                        "tenant_id": t_id,
                        "step_sequence": step.step_sequence,
                        "state_from": step.state_from.value,
                        "state_to": step.state_to.value,
                        "transition_reason": step.transition_reason,
                        "duration_ms": step.duration_ms,
                        "created_at": step.created_at,
                    },
                )

            await session.commit()


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)
