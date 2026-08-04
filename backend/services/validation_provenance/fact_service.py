"""
LuminaAI Governed Analytical Fact Service
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from contracts.validation_provenance_v2 import (
    AnalyticalFactSetV2,
    AnalyticalFactV2,
    AnalyticalFactValueV2,
    CompletenessStatus,
    FactType,
    ValidationStatus,
)


class AnalyticalFactService:
    @staticmethod
    def extract_facts(
        tenant_id: UUID,
        result_payload: Dict,
        proposed_facts: List[Dict],
        tenant_proof: Optional[Dict] = None,
    ) -> AnalyticalFactSetV2:
        extracted_facts: List[AnalyticalFactV2] = []
        proof_checksum = hashlib.sha256(
            json.dumps(tenant_proof or {"tenant_id": str(tenant_id)}, sort_keys=True).encode("utf-8")
        ).hexdigest()
        result_checksum = hashlib.sha256(
            json.dumps(result_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        # Build facts from proposed_facts or result_payload
        for idx, pf in enumerate(proposed_facts):
            fact_id = pf.get("fact_id", f"FACT-{idx+1:03d}")
            fact_type_str = pf.get("fact_type", "SCALAR_METRIC")
            try:
                fact_type = FactType(fact_type_str)
            except Exception:
                fact_type = FactType.SCALAR_METRIC

            val_dict = pf.get("value", {})
            if not isinstance(val_dict, dict):
                val_dict = {"string_value": str(val_dict), "raw_type": "STRING"}

            fact_val = AnalyticalFactValueV2(
                decimal_value=val_dict.get("decimal_value"),
                int_value=val_dict.get("int_value"),
                string_value=val_dict.get("string_value"),
                bool_value=val_dict.get("bool_value"),
                date_value=val_dict.get("date_value"),
                is_null=val_dict.get("is_null", False),
                raw_type=val_dict.get("raw_type", "STRING"),
            )

            fact_content = f"{tenant_id}:{fact_id}:{fact_type}:{fact_val.model_dump_json()}:{proof_checksum}"
            fact_ck = hashlib.sha256(fact_content.encode("utf-8")).hexdigest()

            fact = AnalyticalFactV2(
                fact_id=fact_id,
                tenant_id=tenant_id,
                fact_type=fact_type,
                canonical_metric_id=pf.get("canonical_metric_id"),
                canonical_dimension_ids=pf.get("canonical_dimension_ids", []),
                canonical_entity_refs=pf.get("canonical_entity_refs", []),
                period_start=pf.get("period_start"),
                period_end=pf.get("period_end"),
                value=fact_val,
                unit=pf.get("unit"),
                currency=pf.get("currency"),
                scale=pf.get("scale", 2),
                completeness=CompletenessStatus.COMPLETE,
                source_result_ref=pf.get("source_result_ref", result_checksum),
                metric_fingerprint=pf.get("metric_fingerprint"),
                tenant_proof_checksum=proof_checksum,
                validation_status=ValidationStatus.VALID,
                warnings=[],
                checksum=fact_ck,
            )
            extracted_facts.append(fact)

        # Fallback if no facts proposed but payload has scalar value
        if not extracted_facts and "value" in result_payload:
            raw_val = result_payload["value"]
            fact_val = AnalyticalFactValueV2(
                decimal_value=str(raw_val) if isinstance(raw_val, (int, float, str)) else None,
                string_value=str(raw_val),
                raw_type="DECIMAL" if isinstance(raw_val, (int, float)) else "STRING",
            )
            fact_id = "FACT-001"
            fact_content = f"{tenant_id}:{fact_id}:SCALAR_METRIC:{fact_val.model_dump_json()}:{proof_checksum}"
            fact_ck = hashlib.sha256(fact_content.encode("utf-8")).hexdigest()
            fact = AnalyticalFactV2(
                fact_id=fact_id,
                tenant_id=tenant_id,
                fact_type=FactType.SCALAR_METRIC,
                canonical_metric_id=result_payload.get("metric_id"),
                value=fact_val,
                unit=result_payload.get("unit"),
                currency=result_payload.get("currency"),
                source_result_ref=result_checksum,
                tenant_proof_checksum=proof_checksum,
                validation_status=ValidationStatus.VALID,
                checksum=fact_ck,
            )
            extracted_facts.append(fact)

        set_content = json.dumps([f.checksum for f in extracted_facts], sort_keys=True)
        set_checksum = hashlib.sha256(set_content.encode("utf-8")).hexdigest()

        return AnalyticalFactSetV2(
            tenant_id=tenant_id,
            facts=extracted_facts,
            fact_set_checksum=set_checksum,
        )
