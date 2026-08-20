"""Reviewed synthetic goldens for Prompt 22; contains no business data."""
from __future__ import annotations

from copy import deepcopy


def golden_cases() -> dict[str, dict[str, object]]:
    cases: dict[str, dict[str, object]] = {
        "creation_request": {"operation": "CREATE_DASHBOARD", "instruction": "Painel executivo sintético"},
        "intent": {"objective": "Painel executivo sintético", "metrics": ["metric.revenue.total"]},
        "clarification": {"kind": "METRIC", "status": "NEEDS_CLARIFICATION", "options": ["metric.revenue.gross", "metric.revenue.net"]},
        "design_spec": {"template": "EXECUTIVE_OVERVIEW", "metrics": ["metric.revenue.total"], "period": "period.last.closed.month"},
        "executive_proposal": {"template": "EXECUTIVE_OVERVIEW", "status": "READY_FOR_REVIEW", "lifecycle": "DRAFT"},
        "sales_proposal": {"template": "SALES_PERFORMANCE", "status": "READY_FOR_REVIEW", "lifecycle": "DRAFT"},
        "financial_proposal": {"template": "FINANCIAL_OVERVIEW", "status": "READY_FOR_REVIEW", "lifecycle": "DRAFT"},
        "ranking_proposal": {"template": "PRODUCT_RANKING", "status": "READY_FOR_REVIEW", "lifecycle": "DRAFT"},
        "comparison_proposal": {"template": "COMPARATIVE_ANALYSIS", "status": "READY_FOR_REVIEW", "lifecycle": "DRAFT"},
        "unknown_metric_blocked": {"code": "DASHBOARD_AI_UNKNOWN_METRIC", "status": "BLOCKED"},
        "ambiguity": {"code": "DASHBOARD_AI_METRIC_AMBIGUOUS", "status": "NEEDS_CLARIFICATION"},
        "semantic_patch_proposal": {"kind": "SEMANTIC", "status": "READY_FOR_REVIEW", "application": "NEW_DRAFT_REVISION"},
        "visual_proposal": {"kind": "VISUAL", "status": "READY_FOR_REVIEW", "semantic_change": False},
        "accepted_proposal": {"status": "ACCEPTED", "applied": False},
        "rejected_proposal": {"status": "REJECTED", "applied": False},
        "applied_draft": {"status": "APPLIED", "dashboard_lifecycle": "DRAFT", "published": False},
        "injection_blocked": {"code": "DASHBOARD_AI_PROMPT_INJECTION_BLOCKED", "status": "BLOCKED"},
        "publish_blocked": {"code": "DASHBOARD_AI_OPERATION_FORBIDDEN", "status": "BLOCKED"},
        "evidence_summary": {"authority": "MetricRegistry", "canonical_reference": "metric.revenue.total"},
        "public_rationale": {"summary": "Seleção baseada em referências canônicas.", "chain_of_thought": False},
        "feedback_reference": {"workflow": "lumina.supervised-feedback/1.0", "automatic_learning": False},
        "legacy_only": {"mode": "LEGACY_ONLY", "new_paths": 0, "new_requests": 0},
        "shadow": {"mode": "SHADOW_ANALYZE", "persisted_proposal": False, "applied": False},
    }
    return deepcopy(cases)
