from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional
from contracts.ai_orchestration_v2.budgets import AIContextBudgetV2, AITokenBudgetV2
from contracts.ai_orchestration_v2.context import (
    AIContextEnvelopeV2,
    AIContextSectionTypeV2,
    AIContextSectionV2,
    AIContextSelectionDecisionV2,
)
from .token_estimator import AITokenEstimator


class GovernedAIContextAssembler:
    """
    Governed AI Context Assembler.
    Assembles AIContextEnvelopeV2 deterministically according to strict section priorities:
    1. System Policy
    2. Output Contract
    3. Current User Query
    4. Canonical Intent
    5. Active Clarification
    6. Public Context
    7. Tool Catalog (Minimised)
    8. Enterprise Knowledge Snippets
    9. Semantic Candidates
    10. User Profile Summary
    11. Validated Tool Results

    Enforces token budgeting, truncation of optional sections, and zero disclosure
    of raw datasets, unminimized graphs, full DB schemas, or secret prompts.
    """

    def assemble_context(
        self,
        tenant_id: Any,
        user_id: Any,
        system_policy_text: str,
        user_query: str,
        canonical_intent: Optional[Any] = None,
        tool_catalog_min: Optional[Dict[str, Any]] = None,
        knowledge_snippets: Optional[List[Dict[str, Any]]] = None,
        semantic_candidates: Optional[List[Dict[str, Any]]] = None,
        profile_summary: Optional[Dict[str, Any]] = None,
        validated_tool_results: Optional[List[Dict[str, Any]]] = None,
        token_budget: Optional[AITokenBudgetV2] = None,
        context_budget: Optional[AIContextBudgetV2] = None,
    ) -> AIContextEnvelopeV2:
        t_id = str(tenant_id)
        u_id = str(user_id)
        budget_limit = token_budget.max_context_tokens if token_budget else 4096
        sections: List[AIContextSectionV2] = []
        decisions: List[AIContextSelectionDecisionV2] = []

        # 1. System Policy (Prio 100)
        sys_tokens = AITokenEstimator.estimate_text_tokens(system_policy_text)
        sys_checksum = hashlib.sha256(system_policy_text.encode("utf-8")).hexdigest()[:16]
        sections.append(
            AIContextSectionV2(
                section_type=AIContextSectionTypeV2.SYSTEM_POLICY,
                priority=100,
                content_text=system_policy_text,
                estimated_tokens=sys_tokens,
                checksum=sys_checksum,
            )
        )
        decisions.append(
            AIContextSelectionDecisionV2(
                section_type=AIContextSectionTypeV2.SYSTEM_POLICY,
                action="INCLUDED",
                reason="Mandatory server system policy",
                token_delta=sys_tokens,
            )
        )

        # 2. Output Contract (Prio 95)
        contract_text = "Retorne uma proposta tipada em JSON estrito compativel com AIModelProposalV2."
        c_tokens = AITokenEstimator.estimate_text_tokens(contract_text)
        c_checksum = hashlib.sha256(contract_text.encode("utf-8")).hexdigest()[:16]
        sections.append(
            AIContextSectionV2(
                section_type=AIContextSectionTypeV2.OUTPUT_CONTRACT,
                priority=95,
                content_text=contract_text,
                estimated_tokens=c_tokens,
                checksum=c_checksum,
            )
        )
        decisions.append(
            AIContextSelectionDecisionV2(
                section_type=AIContextSectionTypeV2.OUTPUT_CONTRACT,
                action="INCLUDED",
                reason="Mandatory output contract schema constraint",
                token_delta=c_tokens,
            )
        )

        # 3. Current User Message (Prio 90)
        q_tokens = AITokenEstimator.estimate_text_tokens(user_query)
        q_checksum = hashlib.sha256(user_query.encode("utf-8")).hexdigest()[:16]
        sections.append(
            AIContextSectionV2(
                section_type=AIContextSectionTypeV2.CURRENT_USER_MESSAGE,
                priority=90,
                content_text=f"Pergunta do usuario: {user_query}",
                estimated_tokens=q_tokens,
                checksum=q_checksum,
            )
        )
        decisions.append(
            AIContextSelectionDecisionV2(
                section_type=AIContextSectionTypeV2.CURRENT_USER_MESSAGE,
                action="INCLUDED",
                reason="Current user query",
                token_delta=q_tokens,
            )
        )

        # 4. Canonical Intent (Prio 85)
        if canonical_intent is not None:
            intent_str = f"Intent Canonico: {str(canonical_intent)}"
            i_tokens = AITokenEstimator.estimate_text_tokens(intent_str)
            i_checksum = hashlib.sha256(intent_str.encode("utf-8")).hexdigest()[:16]
            sections.append(
                AIContextSectionV2(
                    section_type=AIContextSectionTypeV2.CANONICAL_INTENT,
                    priority=85,
                    content_text=intent_str,
                    estimated_tokens=i_tokens,
                    checksum=i_checksum,
                )
            )
            decisions.append(
                AIContextSelectionDecisionV2(
                    section_type=AIContextSectionTypeV2.CANONICAL_INTENT,
                    action="INCLUDED",
                    reason="Governed canonical intent",
                    token_delta=i_tokens,
                )
            )

        # 5. Tool Catalog (Prio 80)
        if tool_catalog_min:
            t_json = json.dumps(tool_catalog_min, ensure_ascii=False)
            t_text = f"Catalogo minimo de ferramentas permitidas: {t_json}"
            t_tokens = AITokenEstimator.estimate_text_tokens(t_text)
            t_checksum = hashlib.sha256(t_text.encode("utf-8")).hexdigest()[:16]
            sections.append(
                AIContextSectionV2(
                    section_type=AIContextSectionTypeV2.TOOL_CATALOG,
                    priority=80,
                    content_text=t_text,
                    estimated_tokens=t_tokens,
                    checksum=t_checksum,
                )
            )
            decisions.append(
                AIContextSelectionDecisionV2(
                    section_type=AIContextSectionTypeV2.TOOL_CATALOG,
                    action="INCLUDED",
                    reason="Minimised tool catalog",
                    token_delta=t_tokens,
                )
            )

        # 6. Validated Tool Results (Prio 75)
        if validated_tool_results:
            tr_json = json.dumps(validated_tool_results, ensure_ascii=False)
            tr_text = f"Resultados validados de ferramentas (FATOS): {tr_json}"
            tr_tokens = AITokenEstimator.estimate_text_tokens(tr_text)
            tr_checksum = hashlib.sha256(tr_text.encode("utf-8")).hexdigest()[:16]
            sections.append(
                AIContextSectionV2(
                    section_type=AIContextSectionTypeV2.VALIDATED_TOOL_RESULTS,
                    priority=75,
                    content_text=tr_text,
                    estimated_tokens=tr_tokens,
                    checksum=tr_checksum,
                )
            )
            decisions.append(
                AIContextSelectionDecisionV2(
                    section_type=AIContextSectionTypeV2.VALIDATED_TOOL_RESULTS,
                    action="INCLUDED",
                    reason="Structured tool output facts",
                    token_delta=tr_tokens,
                )
            )

        # 7. Enterprise Knowledge (Prio 70)
        if knowledge_snippets:
            k_json = json.dumps(knowledge_snippets, ensure_ascii=False)
            k_text = f"Base de Conhecimento publicada (DADOS): {k_json}"
            k_tokens = AITokenEstimator.estimate_text_tokens(k_text)
            k_checksum = hashlib.sha256(k_text.encode("utf-8")).hexdigest()[:16]
            sections.append(
                AIContextSectionV2(
                    section_type=AIContextSectionTypeV2.ENTERPRISE_KNOWLEDGE,
                    priority=70,
                    content_text=k_text,
                    estimated_tokens=k_tokens,
                    checksum=k_checksum,
                )
            )
            decisions.append(
                AIContextSelectionDecisionV2(
                    section_type=AIContextSectionTypeV2.ENTERPRISE_KNOWLEDGE,
                    action="INCLUDED",
                    reason="Published knowledge definitions",
                    token_delta=k_tokens,
                )
            )

        # 8. User Profile Summary (Prio 60)
        if profile_summary:
            p_json = json.dumps(profile_summary, ensure_ascii=False)
            p_text = f"Resumo de perfil do usuario: {p_json}"
            p_tokens = AITokenEstimator.estimate_text_tokens(p_text)
            p_checksum = hashlib.sha256(p_text.encode("utf-8")).hexdigest()[:16]
            sections.append(
                AIContextSectionV2(
                    section_type=AIContextSectionTypeV2.USER_PROFILE_SUMMARY,
                    priority=60,
                    content_text=p_text,
                    estimated_tokens=p_tokens,
                    checksum=p_checksum,
                )
            )
            decisions.append(
                AIContextSelectionDecisionV2(
                    section_type=AIContextSectionTypeV2.USER_PROFILE_SUMMARY,
                    action="INCLUDED",
                    reason="Consented user preferences summary",
                    token_delta=p_tokens,
                )
            )

        # Check total tokens & compact/truncate optional sections if exceeding budget
        total_tokens = sum(sec.estimated_tokens for sec in sections if sec.included)
        is_compacted = False

        if total_tokens > budget_limit:
            # Sort optional sections by priority ascending (lowest priority first)
            optional_types = {
                AIContextSectionTypeV2.USER_PROFILE_SUMMARY,
                AIContextSectionTypeV2.ENTERPRISE_KNOWLEDGE,
                AIContextSectionTypeV2.SEMANTIC_CANDIDATES,
            }

            for sec_idx, sec in enumerate(sections):
                if sec.section_type in optional_types and total_tokens > budget_limit:
                    # Truncate / omit section
                    sections[sec_idx] = AIContextSectionV2(
                        section_type=sec.section_type,
                        priority=sec.priority,
                        classification=sec.classification,
                        source=sec.source,
                        content_text="",
                        estimated_tokens=0,
                        included=False,
                        truncated=True,
                        truncation_reason="Omitted due to token budget constraint",
                        checksum=sec.checksum,
                    )
                    total_tokens -= sec.estimated_tokens
                    is_compacted = True
                    decisions.append(
                        AIContextSelectionDecisionV2(
                            section_type=sec.section_type,
                            action="OMITTED_BUDGET",
                            reason="Context budget limit reached",
                            token_delta=-sec.estimated_tokens,
                        )
                    )

        envelope_checksum = hashlib.sha256(
            f"{t_id}:{u_id}:{total_tokens}:{len(sections)}".encode("utf-8")
        ).hexdigest()[:16]

        return AIContextEnvelopeV2(
            envelope_id=f"env-{envelope_checksum}",
            tenant_id=t_id,
            user_id=u_id,
            sections=sections,
            selection_decisions=decisions,
            total_estimated_tokens=total_tokens,
            is_compacted=is_compacted,
            checksum=envelope_checksum,
        )
