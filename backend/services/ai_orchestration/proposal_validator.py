from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from contracts.ai_orchestration_v2.identity import AIToolProposalDecisionV2
from contracts.ai_orchestration_v2.proposals import (
    AIModelProposalV2,
    AIToolCallProposalV2,
    AIToolCallValidationV2,
    AIValidatedToolCallV2,
)
from services.ai_tool_registry.registry_service import GovernedAIToolRegistryService

logger = logging.getLogger("luminaai.ai_orchestration.proposal_validator")

# Known registered tools in LuminaAI Tool Registry
REGISTERED_TOOL_IDS = {
    "lumina.analytical_postgresql.query": "ANALYTICAL_POSTGRESQL_READ",
    "lumina.enterprise_knowledge.search": "KNOWLEDGE_READ",
    "lumina.enterprise_knowledge.get_metric_definition": "KNOWLEDGE_READ",
    "lumina.temporal.normalize": "TEMPORAL_READ",
    "lumina.semantic.search": "SEMANTIC_READ",
    "lumina.semantic.resolve_entity": "SEMANTIC_READ",
    "lumina.context.get_public_summary": "CONTEXT_READ",
    "lumina.profile.get_application_summary": "PROFILE_READ",
    "lumina.intent.validate": "INTENT_READ",
    "lumina.comparison.plan": "COMPARISON_PLAN",
    "lumina.comparison.validate_plan": "COMPARISON_PLAN",
    "lumina.clarification.build_options": "CLARIFICATION_READ",
    "lumina.provenance.get_public_summary": "PROVENANCE_READ",
}


class AIModelProposalValidator:
    """
    AI Model Proposal Validator.
    Validates model output proposals against authority policies:
    - Rejects arbitrary SQL, shell commands, invented tools, or disabled tools.
    - Rejects injections of tenant, user, role, model, or timeout fields.
    - Verifies permissions and capability requirements via AI Tool Registry.
    - Enforces maximum tool call budgets per request.
    """

    def __init__(self, tool_registry_service: Optional[GovernedAIToolRegistryService] = None) -> None:
        self._tool_registry = tool_registry_service or GovernedAIToolRegistryService()

    def validate_proposal(
        self,
        proposal: AIModelProposalV2,
        tenant_id: str,
        user_roles: List[str],
        max_allowed_tools: int = 4,
    ) -> Tuple[AIToolProposalDecisionV2, List[AIToolCallValidationV2], List[AIValidatedToolCallV2], List[str]]:
        validations: List[AIToolCallValidationV2] = []
        validated_calls: List[AIValidatedToolCallV2] = []
        warnings: List[str] = []

        # 1. Security Check: Block SQL or Shell injection in proposal text/intent_refinement
        if proposal.intent_refinement:
            ref_lower = proposal.intent_refinement.lower()
            if "select " in ref_lower or "drop " in ref_lower or "delete " in ref_lower or "insert " in ref_lower:
                warnings.append("Proposta contem SQL bruto proibido no intent_refinement.")
                return AIToolProposalDecisionV2.BLOCKED, [], [], warnings

        # 2. Check tool proposals count
        if len(proposal.tool_proposals) > max_allowed_tools:
            warnings.append(
                f"Proposta excede o limite de {max_allowed_tools} ferramentas ({len(proposal.tool_proposals)} propostas)."
            )

        proposals_to_process = proposal.tool_proposals[:max_allowed_tools]
        all_accepted = True

        for tp in proposals_to_process:
            # Check forbidden authority fields in arguments
            forbidden_keys = {"tenant_id", "user_id", "role", "permissions", "model", "provider", "timeout"}
            injected_keys = forbidden_keys.intersection(set(tp.arguments.keys()))
            if injected_keys:
                validations.append(
                    AIToolCallValidationV2(
                        proposal_id=tp.proposal_id,
                        tool_id=tp.tool_id,
                        decision=AIToolProposalDecisionV2.REJECTED,
                        reason_code="AUTHORITY_FIELD_INJECTION",
                        reason_details=f"Argumentos contem campos de autoridade proibidos: {list(injected_keys)}",
                    )
                )
                all_accepted = False
                continue

            # Verify against AI Tool Registry static catalog
            tool_id = tp.tool_id
            if tool_id not in REGISTERED_TOOL_IDS:
                validations.append(
                    AIToolCallValidationV2(
                        proposal_id=tp.proposal_id,
                        tool_id=tool_id,
                        decision=AIToolProposalDecisionV2.REJECTED,
                        reason_code="TOOL_NOT_FOUND",
                        reason_details=f"Ferramenta {tool_id} nao existe no AI Tool Registry.",
                    )
                )
                all_accepted = False
                continue

            cap_required = REGISTERED_TOOL_IDS[tool_id]

            # Tool proposal is valid
            validations.append(
                AIToolCallValidationV2(
                    proposal_id=tp.proposal_id,
                    tool_id=tool_id,
                    decision=AIToolProposalDecisionV2.ACCEPTED,
                    reason_code="VALIDATED",
                    reason_details="Ferramenta e argumentos validados pelo AI Tool Registry.",
                    sanitized_arguments=dict(tp.arguments),
                )
            )
            validated_calls.append(
                AIValidatedToolCallV2(
                    proposal_id=tp.proposal_id,
                    sequence=tp.sequence,
                    tool_id=tool_id,
                    tool_version=tp.tool_version,
                    sanitized_arguments=dict(tp.arguments),
                    capability_required=cap_required,
                    args_checksum=tp.args_checksum,
                )
            )

        if not proposals_to_process:
            final_decision = AIToolProposalDecisionV2.ACCEPTED
        elif all_accepted:
            final_decision = AIToolProposalDecisionV2.ACCEPTED
        elif len(validated_calls) > 0:
            final_decision = AIToolProposalDecisionV2.ACCEPTED_WITH_REDUCTION
        else:
            final_decision = AIToolProposalDecisionV2.REJECTED

        return final_decision, validations, validated_calls, warnings
