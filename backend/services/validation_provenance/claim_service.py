"""
LuminaAI Governed Analytical Claim Service
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from contracts.validation_provenance_v2 import (
    AnalyticalClaimBindingV2,
    AnalyticalClaimV2,
    AnalyticalClaimValidationV2,
    AnalyticalFactSetV2,
    AnalyticalFactV2,
    ClaimType,
    ValidationStatus,
)


class AnalyticalClaimValidationService:
    @staticmethod
    def validate_claims(
        tenant_id: UUID,
        proposed_claims: List[Dict],
        fact_set: AnalyticalFactSetV2,
    ) -> AnalyticalClaimValidationV2:
        validated_claims: List[AnalyticalClaimV2] = []
        bindings: List[AnalyticalClaimBindingV2] = []
        all_bound = True
        fact_map = {f.fact_id: f for f in fact_set.facts}

        for idx, pc in enumerate(proposed_claims):
            claim_id = pc.get("claim_id", f"CLAIM-{idx+1:03d}")
            claim_type_str = pc.get("claim_type", "NUMERIC")
            try:
                claim_type = ClaimType(claim_type_str)
            except Exception:
                claim_type = ClaimType.NUMERIC

            text = pc.get("text", "")
            fact_refs = pc.get("fact_references", [])
            claim_ck = hashlib.sha256(f"{tenant_id}:{claim_id}:{text}:{json.dumps(fact_refs)}".encode("utf-8")).hexdigest()

            claim = AnalyticalClaimV2(
                claim_id=claim_id,
                claim_type=claim_type,
                text=text,
                fact_references=fact_refs,
                metric_references=pc.get("metric_references", []),
                period_references=pc.get("period_references", []),
                comparison_references=pc.get("comparison_references", []),
                qualifiers=pc.get("qualifiers", []),
                origin=pc.get("origin", "MODEL_PROPOSED"),
                checksum=claim_ck,
            )
            validated_claims.append(claim)

            # Perform binding
            if claim_type in (ClaimType.NUMERIC, ClaimType.COMPARATIVE, ClaimType.RANKING, ClaimType.TEMPORAL, ClaimType.COMPLETENESS):
                if not fact_refs:
                    all_bound = False
                    binding = AnalyticalClaimBindingV2(
                        claim_id=claim_id,
                        fact_ids=[],
                        validation_status=ValidationStatus.INVALID,
                        canonical_value_checksum=hashlib.sha256(b"UNBOUND").hexdigest(),
                        mismatch_reason="Numeric/Comparative claim missing supporting fact references",
                    )
                else:
                    valid_bound_facts = [fref for fref in fact_refs if fref in fact_map]
                    if len(valid_bound_facts) != len(fact_refs):
                        all_bound = False
                        binding = AnalyticalClaimBindingV2(
                            claim_id=claim_id,
                            fact_ids=valid_bound_facts,
                            validation_status=ValidationStatus.INVALID,
                            canonical_value_checksum=hashlib.sha256(b"INVALID_REF").hexdigest(),
                            mismatch_reason="Claim references one or more non-existent facts",
                        )
                    else:
                        canonical_vals = [fact_map[fid].value.model_dump_json() for fid in valid_bound_facts]
                        c_ck = hashlib.sha256(json.dumps(canonical_vals, sort_keys=True).encode("utf-8")).hexdigest()
                        binding = AnalyticalClaimBindingV2(
                            claim_id=claim_id,
                            fact_ids=valid_bound_facts,
                            validation_status=ValidationStatus.VALID,
                            public_display_value=text,
                            canonical_value_checksum=c_ck,
                        )
                bindings.append(binding)

        status = ValidationStatus.VALID if all_bound else ValidationStatus.INVALID

        return AnalyticalClaimValidationV2(
            claims=validated_claims,
            bindings=bindings,
            all_numeric_claims_bound=all_bound,
            validation_status=status,
        )
