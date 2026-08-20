"""
LuminaAI Governed Provenance Graph Service
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from contracts.validation_provenance_v2 import (
    AnalyticalClaimV2,
    AnalyticalFactV2,
    InternalProvenanceSummaryV2,
    ProvenanceEdgeType,
    ProvenanceEdgeV2,
    ProvenanceGraphV2,
    ProvenanceManifestV2,
    ProvenanceNodeType,
    ProvenanceNodeV2,
)


class ProvenanceGraphService:
    @staticmethod
    def build_graph(
        tenant_id: UUID,
        request_id: str,
        facts: List[AnalyticalFactV2],
        claims: List[AnalyticalClaimV2],
        query_fingerprint: Optional[str] = None,
        tenant_proof_checksum: Optional[str] = None,
    ) -> ProvenanceGraphV2:
        graph_id = uuid4()
        nodes: List[ProvenanceNodeV2] = []
        edges: List[ProvenanceEdgeV2] = []
        seen_nodes: Set[str] = set()

        # Add Request Node
        req_node_id = f"NODE-REQ-{request_id[:8]}"
        req_ck = hashlib.sha256(f"{tenant_id}:{req_node_id}".encode("utf-8")).hexdigest()
        nodes.append(
            ProvenanceNodeV2(
                node_id=req_node_id,
                tenant_id=tenant_id,
                node_type=ProvenanceNodeType.USER_REQUEST,
                label=f"User Request {request_id}",
                reference_id=request_id,
                checksum=req_ck,
            )
        )
        seen_nodes.add(req_node_id)

        # Add Query Execution Node if present
        exec_node_id = None
        if query_fingerprint:
            exec_node_id = f"NODE-EXEC-{query_fingerprint[:8]}"
            exec_ck = hashlib.sha256(f"{tenant_id}:{exec_node_id}".encode("utf-8")).hexdigest()
            nodes.append(
                ProvenanceNodeV2(
                    node_id=exec_node_id,
                    tenant_id=tenant_id,
                    node_type=ProvenanceNodeType.COMPILED_QUERY,
                    label="Safe Analytical PostgreSQL Execution",
                    reference_id=query_fingerprint,
                    checksum=exec_ck,
                )
            )
            seen_nodes.add(exec_node_id)

            e_ck = hashlib.sha256(f"{tenant_id}:{req_node_id}:{exec_node_id}".encode("utf-8")).hexdigest()
            edges.append(
                ProvenanceEdgeV2(
                    edge_id=f"EDGE-1",
                    tenant_id=tenant_id,
                    source_node_id=req_node_id,
                    target_node_id=exec_node_id,
                    edge_type=ProvenanceEdgeType.EXECUTED_BY,
                    checksum=e_ck,
                )
            )

        # Add Fact Nodes & Edges
        fact_node_map: Dict[str, str] = {}
        for f in facts:
            f_node_id = f"NODE-FACT-{f.fact_id}"
            f_ck = hashlib.sha256(f"{tenant_id}:{f_node_id}:{f.checksum}".encode("utf-8")).hexdigest()
            nodes.append(
                ProvenanceNodeV2(
                    node_id=f_node_id,
                    tenant_id=tenant_id,
                    node_type=ProvenanceNodeType.ANALYTICAL_FACT,
                    label=f"Fact {f.fact_id} ({f.fact_type})",
                    reference_id=f.checksum,
                    checksum=f_ck,
                )
            )
            seen_nodes.add(f_node_id)
            fact_node_map[f.fact_id] = f_node_id

            parent_node = exec_node_id or req_node_id
            edge_ck = hashlib.sha256(f"{tenant_id}:{parent_node}:{f_node_id}".encode("utf-8")).hexdigest()
            edges.append(
                ProvenanceEdgeV2(
                    edge_id=f"EDGE-F-{f.fact_id}",
                    tenant_id=tenant_id,
                    source_node_id=parent_node,
                    target_node_id=f_node_id,
                    edge_type=ProvenanceEdgeType.PRODUCED,
                    checksum=edge_ck,
                )
            )

        # Add Claim Nodes & Edges
        for c in claims:
            c_node_id = f"NODE-CLAIM-{c.claim_id}"
            c_ck = hashlib.sha256(f"{tenant_id}:{c_node_id}:{c.checksum}".encode("utf-8")).hexdigest()
            nodes.append(
                ProvenanceNodeV2(
                    node_id=c_node_id,
                    tenant_id=tenant_id,
                    node_type=ProvenanceNodeType.ANALYTICAL_CLAIM,
                    label=f"Claim {c.claim_id} ({c.claim_type})",
                    reference_id=c.checksum,
                    checksum=c_ck,
                )
            )
            seen_nodes.add(c_node_id)

            for fref in c.fact_references:
                if fref in fact_node_map:
                    f_parent = fact_node_map[fref]
                    edge_ck = hashlib.sha256(f"{tenant_id}:{f_parent}:{c_node_id}".encode("utf-8")).hexdigest()
                    edges.append(
                        ProvenanceEdgeV2(
                            edge_id=f"EDGE-C-{c.claim_id}-{fref}",
                            tenant_id=tenant_id,
                            source_node_id=f_parent,
                            target_node_id=c_node_id,
                            edge_type=ProvenanceEdgeType.SUPPORTS,
                            checksum=edge_ck,
                        )
                    )

        # Check DAG cycle detection
        has_cycles = False
        adj: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
        for e in edges:
            if e.source_node_id in adj and e.target_node_id in adj:
                adj[e.source_node_id].append(e.target_node_id)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(n: str) -> bool:
            visited.add(n)
            rec_stack.add(n)
            for neighbor in adj.get(n, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(n)
            return False

        for n in adj:
            if n not in visited:
                if dfs(n):
                    has_cycles = True
                    break

        graph_ck = hashlib.sha256(
            json.dumps([n.checksum for n in nodes] + [e.checksum for e in edges], sort_keys=True).encode("utf-8")
        ).hexdigest()

        return ProvenanceGraphV2(
            graph_id=graph_id,
            tenant_id=tenant_id,
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            orphan_node_ids=[],
            checksum=graph_ck,
        )
