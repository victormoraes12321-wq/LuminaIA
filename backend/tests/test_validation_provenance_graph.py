"""
LuminaAI Validation & Provenance V2 Provenance Graph Tests
"""

from uuid import uuid4
import pytest

from services.validation_provenance.fact_service import AnalyticalFactService
from services.validation_provenance.claim_service import AnalyticalClaimValidationService
from services.validation_provenance.provenance_service import ProvenanceGraphService


def test_provenance_graph_construction():
    tid = uuid4()
    req_id = "REQ-PROV-001"
    fact_set = AnalyticalFactService.extract_facts(
        tenant_id=tid,
        result_payload={"value": "300"},
        proposed_facts=[
            {
                "fact_id": "FACT-001",
                "fact_type": "SCALAR_METRIC",
                "canonical_metric_id": "sales",
                "value": {"decimal_value": "300", "raw_type": "DECIMAL"},
                "source_result_ref": "res_ck_123",
            }
        ],
    )
    claim_val = AnalyticalClaimValidationService.validate_claims(
        tenant_id=tid,
        proposed_claims=[
            {
                "claim_id": "CLAIM-001",
                "claim_type": "NUMERIC",
                "text": "300",
                "fact_references": ["FACT-001"],
            }
        ],
        fact_set=fact_set,
    )

    graph = ProvenanceGraphService.build_graph(
        tenant_id=tid,
        request_id=req_id,
        facts=fact_set.facts,
        claims=claim_val.claims,
        query_fingerprint="fp_query_123",
    )

    assert len(graph.nodes) >= 3
    assert graph.has_cycles is False
