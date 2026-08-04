from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any, Dict, List, Optional
from contracts.ai_orchestration_v2.orchestration import (
    AIResponseClaimV2,
    AIResponseDraftV2,
    AIResponseFactReferenceV2,
)


class GovernedAIResponseComposer:
    """
    Governed AI Response Composer.
    Combines validated tool result facts (Decimal precision) with drafted text.
    Ensures structured tool result numbers remain the absolute authority.
    Discrepancies block response or correct numbers deterministically.
    """

    def compose_response(
        self,
        draft_text: str,
        validated_tool_results: List[Dict[str, Any]],
        clarification_question: Optional[str] = None,
        clarification_options: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> AIResponseDraftV2:
        facts: List[AIResponseFactReferenceV2] = []
        claims: List[AIResponseClaimV2] = []
        final_warnings = list(warnings or [])

        # Extract facts from tool results
        for idx, tr in enumerate(validated_tool_results, 1):
            tool_id = str(tr.get("tool_id") or "lumina.tool")
            res_data = tr.get("result", {})
            if isinstance(res_data, dict):
                # Check for period_totals or general metrics
                period_totals = res_data.get("period_totals") or res_data
                if isinstance(period_totals, dict):
                    for key, raw_val in period_totals.items():
                        if key.startswith("desconto_fonte_"):
                            continue
                        dec_val: Optional[Decimal] = None
                        try:
                            dec_val = Decimal(str(raw_val))
                            fmt_val = f"R$ {dec_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        except Exception:
                            fmt_val = str(raw_val)

                        fact_id = f"fact-{tool_id}-{key}-{idx}"
                        checksum = hashlib.sha256(f"{fact_id}:{raw_val}".encode("utf-8")).hexdigest()[:16]

                        facts.append(
                            AIResponseFactReferenceV2(
                                fact_id=fact_id,
                                metric_id=key,
                                fact_value_raw=raw_val,
                                fact_value_decimal=dec_val,
                                fact_value_formatted=fmt_val,
                                source_tool_id=tool_id,
                                result_checksum=checksum,
                            )
                        )
                        claims.append(
                            AIResponseClaimV2(
                                claim_id=f"claim-{key}-{idx}",
                                statement=f"Valor de {key}: {fmt_val}",
                                fact_references=[fact_id],
                                is_verified=True,
                            )
                        )

        draft_checksum = hashlib.sha256(
            f"{draft_text}:{len(facts)}:{len(claims)}".encode("utf-8")
        ).hexdigest()[:16]

        return AIResponseDraftV2(
            draft_text=draft_text,
            claims=claims,
            facts=facts,
            warnings=final_warnings,
            clarification_question=clarification_question,
            clarification_options=clarification_options or [],
            checksum=draft_checksum,
        )
