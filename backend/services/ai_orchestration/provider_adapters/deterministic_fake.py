from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Dict, Optional
from contracts.ai_orchestration_v2.identity import AIOrchestrationStrategyV2
from contracts.ai_orchestration_v2.proposals import (
    AIModelProposalV2,
    AIResponseDraftInstructionV2,
    AIToolCallProposalV2,
)
from .base import GovernedAIProviderAdapter


class DeterministicFakeAIProviderAdapter(GovernedAIProviderAdapter):
    """
    Deterministic, network-free fake provider for LuminaAI testing.
    Produces repeatable fixtures, simulates usage, delays, tool proposals,
    malformed outputs, prompt injections, and cancellations.
    """

    def __init__(self) -> None:
        self._simulate_delay_ms: float = 0.0
        self._force_timeout: bool = False
        self._force_error: Optional[str] = None
        self._cancelled_runs: set[str] = set()

    @property
    def provider_id(self) -> str:
        return "fake_provider"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def configure_simulation(
        self,
        delay_ms: float = 0.0,
        force_timeout: bool = False,
        force_error: Optional[str] = None,
    ) -> None:
        self._simulate_delay_ms = delay_ms
        self._force_timeout = force_timeout
        self._force_error = force_error

    async def validate_configuration(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    async def cancel(self, run_id: str) -> bool:
        self._cancelled_runs.add(run_id)
        return True

    async def invoke_structured(
        self,
        model_name: str,
        system_prompt: str,
        user_query: str,
        context_payload: Dict[str, Any],
        tools_catalog: Optional[Dict[str, Any]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        if self._force_timeout:
            await asyncio.sleep(0.05)
            raise TimeoutError("DeterministicFakeAIProviderAdapter timeout simulated")

        if self._force_error:
            raise RuntimeError(f"Simulated error: {self._force_error}")

        if self._simulate_delay_ms > 0:
            await asyncio.sleep(self._simulate_delay_ms / 1000.0)

        query_lower = user_query.lower()
        checksum = hashlib.sha256(f"{model_name}:{user_query}".encode("utf-8")).hexdigest()[:16]

        # Check for prompt injection in user query
        if "ignore todas" in query_lower or "revele o system prompt" in query_lower or "system prompt" in query_lower or "drop table" in query_lower:
            proposal = AIModelProposalV2(
                proposal_id=f"prop-inj-{checksum}",
                strategy=AIOrchestrationStrategyV2.BLOCKED,
                clarification_question="Solicitacao recusada por politica de seguranca.",
                checksum=hashlib.sha256(f"inj:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
        elif "faturamento de junho" in query_lower or "receita de vendas" in query_lower or "vendas de junho" in query_lower:
            # Propose tool call for sales analytics
            tool_proposal = AIToolCallProposalV2(
                proposal_id=f"prop-tool-1-{checksum}",
                sequence=1,
                tool_id="lumina.analytical_postgresql.query",
                tool_version="1.0.0",
                arguments={
                    "query_spec": {
                        "dataset_id": "sales_analytics",
                        "metrics": ["total_sales"],
                        "dimensions": ["date"],
                        "filters": [
                            {"field": "date", "operator": "GREATER_THAN_OR_EQUAL", "value": "2026-06-01"},
                            {"field": "date", "operator": "LESS_THAN", "value": "2026-07-01"}
                        ]
                    }
                },
                justification="Consulta analitica de faturamento de junho de 2026",
                args_checksum=hashlib.sha256(f"tool1:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
            proposal = AIModelProposalV2(
                proposal_id=f"prop-analytical-{checksum}",
                strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
                tool_proposals=[tool_proposal],
                draft_instruction=AIResponseDraftInstructionV2(
                    mode="DETERMINISTIC_PRESENTATION",
                    tone="PROFESSIONAL",
                    format_as="TEXT",
                ),
                checksum=hashlib.sha256(f"analytical:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
        elif "mostre centro" in query_lower or "ambiguidade" in query_lower:
            proposal = AIModelProposalV2(
                proposal_id=f"prop-ambig-{checksum}",
                strategy=AIOrchestrationStrategyV2.CLARIFICATION,
                clarification_question="Voce deseja ver dados da Filial Centro, Regiao Centro ou Categoria Centro?",
                clarification_options=["Filial Centro", "Regiao Centro", "Categoria Centro"],
                checksum=hashlib.sha256(f"ambig:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
        elif "inventada" in query_lower or "run_anything" in query_lower:
            tool_proposal = AIToolCallProposalV2(
                proposal_id=f"prop-invented-{checksum}",
                sequence=1,
                tool_id="lumina.run_anything",
                tool_version="1.0.0",
                arguments={"cmd": "whoami"},
                justification="Executar comando",
                args_checksum=hashlib.sha256(f"inv:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
            proposal = AIModelProposalV2(
                proposal_id=f"prop-inv-tool-{checksum}",
                strategy=AIOrchestrationStrategyV2.SINGLE_TOOL_CALL,
                tool_proposals=[tool_proposal],
                checksum=hashlib.sha256(f"invtool:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
        elif "select *" in query_lower or "sql no output" in query_lower:
            proposal = AIModelProposalV2(
                proposal_id=f"prop-sql-{checksum}",
                strategy=AIOrchestrationStrategyV2.BLOCKED,
                intent_refinement="SELECT * FROM users",
                checksum=hashlib.sha256(f"sql:{checksum}".encode("utf-8")).hexdigest()[:16],
            )
        else:
            proposal = AIModelProposalV2(
                proposal_id=f"prop-direct-{checksum}",
                strategy=AIOrchestrationStrategyV2.SINGLE_MODEL_CALL,
                draft_instruction=AIResponseDraftInstructionV2(
                    mode="MODEL_ASSISTED",
                    tone="PROFESSIONAL",
                    format_as="TEXT",
                ),
                checksum=hashlib.sha256(f"direct:{checksum}".encode("utf-8")).hexdigest()[:16],
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        input_tokens = len(system_prompt) // 4 + len(user_query) // 4 + 50
        output_tokens = 120

        return {
            "proposal": proposal,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "duration_ms": duration_ms,
        }

    async def invoke_text(
        self,
        model_name: str,
        system_prompt: str,
        user_query: str,
        context_payload: Dict[str, Any],
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        query_lower = user_query.lower()

        if "junho" in query_lower and "300" in str(context_payload):
            text_out = "O faturamento comercial referente a junho de 2026 foi de R$ 300,00."
        elif "julho" in query_lower and "400" in str(context_payload):
            text_out = "O faturamento comercial referente a julho de 2026 foi de R$ 400,00."
        else:
            text_out = "Processamento concluido com sucesso pela assistencia de IA governada do LuminaAI."

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        input_tokens = len(system_prompt) // 4 + len(user_query) // 4 + 40
        output_tokens = len(text_out) // 4 + 10

        return {
            "text": text_out,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            "duration_ms": duration_ms,
        }
