from __future__ import annotations

from contracts.analytical_v2 import ComparisonKind, QueryPlanV2

from .fingerprints import stable_fingerprint
from .models import (
    ComparisonExecutionContext,
    ComparisonExecutionGraph,
    ComparisonExecutionNode,
    ComparisonExecutionStrategy,
    ExecutionNodeType,
)


def build_execution_graph(
    plan: QueryPlanV2,
    context: ComparisonExecutionContext,
    strategy: ComparisonExecutionStrategy,
) -> ComparisonExecutionGraph:
    comparison = plan.comparison
    if comparison is None:
        raise ValueError("Comparison specification is required")
    query_nodes = tuple(
        ComparisonExecutionNode(
            node_id=f"query:{operand.operand_id}",
            node_type=(
                ExecutionNodeType.TARGET_QUERY
                if comparison.kind == ComparisonKind.ACTUAL_VS_TARGET
                and operand.operand_id != comparison.baseline_operand_id
                else ExecutionNodeType.OPERAND_QUERY
            ),
            operand_id=operand.operand_id,
            timeout_seconds=context.query_timeout_seconds,
            failure_policy=context.failure_policy,
        )
        for operand in comparison.operands
    )
    query_ids = tuple(node.node_id for node in query_nodes)
    alignment = ComparisonExecutionNode(
        node_id="alignment:comparison",
        node_type=ExecutionNodeType.ALIGNMENT,
        dependencies=query_ids,
        timeout_seconds=context.total_timeout_seconds,
        failure_policy=context.failure_policy,
    )
    calculation = ComparisonExecutionNode(
        node_id="calculation:comparison",
        node_type=ExecutionNodeType.CALCULATION,
        dependencies=(alignment.node_id,),
        timeout_seconds=context.total_timeout_seconds,
        failure_policy=context.failure_policy,
    )
    validation = ComparisonExecutionNode(
        node_id="validation:comparison",
        node_type=ExecutionNodeType.VALIDATION,
        dependencies=(calculation.node_id,),
        timeout_seconds=context.total_timeout_seconds,
        failure_policy=context.failure_policy,
    )
    response = ComparisonExecutionNode(
        node_id="response:comparison",
        node_type=ExecutionNodeType.RESPONSE_ASSEMBLY,
        dependencies=(validation.node_id,),
        timeout_seconds=context.total_timeout_seconds,
        failure_policy=context.failure_policy,
    )
    nodes = (*query_nodes, alignment, calculation, validation, response)
    dependencies = {node.node_id: node.dependencies for node in nodes}
    execution_order = tuple(node.node_id for node in nodes)
    graph_shape = {
        "nodes": [
            {
                "id": node.node_id,
                "type": node.node_type.value,
                "dependencies": node.dependencies,
                "operand": node.operand_id,
            }
            for node in nodes
        ],
        "strategy": strategy.value,
        "maximum_concurrency": context.maximum_concurrency,
    }
    return ComparisonExecutionGraph(
        nodes=nodes,
        dependencies=dependencies,
        execution_order=execution_order,
        parallel_groups=(query_ids, (alignment.node_id,), (calculation.node_id,), (validation.node_id,), (response.node_id,)),
        maximum_concurrency=min(context.maximum_concurrency, len(query_nodes)),
        estimated_queries=len(query_nodes),
        estimated_rows=min(
            context.maximum_total_rows,
            len(query_nodes) * context.maximum_rows_per_operand,
        ),
        strategy=strategy,
        graph_fingerprint=stable_fingerprint(graph_shape),
    )
