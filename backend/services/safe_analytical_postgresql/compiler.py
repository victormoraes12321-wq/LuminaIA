from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Tuple

from contracts.safe_analytical_postgresql_v2.catalog import (
    AnalyticalCatalogSnapshotV2,
    AnalyticalDatasetDefinitionV2,
    AnalyticalRelationDefinitionV2,
)
from contracts.safe_analytical_postgresql_v2.compilation import (
    AnalyticalBindParameterV2,
    AnalyticalCompiledQueryV2,
    AnalyticalIsolationProofV2,
)
from contracts.safe_analytical_postgresql_v2.identity import (
    SAFE_ANALYTICAL_POSTGRESQL_VERSION,
    AnalyticalTenantStrategyV2,
)
from contracts.safe_analytical_postgresql_v2.query_spec import (
    AnalyticalFilterOperatorV2,
    AnalyticalQueryBudgetV2,
    AnalyticalQuerySpecV2,
)
from services.safe_analytical_postgresql.exceptions import (
    AnalyticalBudgetExceededError,
    AnalyticalCompilationError,
    AnalyticalSecurityViolationError,
)

FORBIDDEN_SQL_PATTERNS = [
    r";",
    r"--",
    r"/\*",
    r"\*/",
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bUNION\b",
    r"\bINFORMATION_SCHEMA\b",
    r"\bPG_",
]


class GovernedAnalyticalSQLCompiler:
    """
    Compiles canonical AnalyticalQuerySpecV2 into parameterized SQL with mandatory tenant isolation proofs.
    """

    def __init__(self, catalog_snapshot: AnalyticalCatalogSnapshotV2):
        self.catalog_snapshot = catalog_snapshot

    def compile(
        self,
        spec: AnalyticalQuerySpecV2,
        tenant_id: str,
        budget: AnalyticalQueryBudgetV2 = AnalyticalQueryBudgetV2(),
    ) -> AnalyticalCompiledQueryV2:

        # 1. Budget & Complexity check
        self._check_budget(spec, budget)

        # 2. Get Dataset Definition
        dataset = self._get_dataset(spec.dataset_id)

        # 3. Find primary relation (vw_vendas_lm)
        relation_name, relation = self._get_relation(dataset)

        # 4. Enforce tenant isolation proof
        proof = self._create_isolation_proof(dataset, relation_name, relation, tenant_id)

        # 5. Build SELECT clause, GROUP BY clause, and binds
        select_exprs, group_by_exprs, binds = self._build_select_and_group(spec, dataset, relation)

        # 6. Build WHERE clause (tenant predicate + user filters)
        where_clauses, binds = self._build_where_clause(spec, dataset, relation, tenant_id, binds)

        # 7. Build ORDER BY clause
        order_by_clause = self._build_order_by(spec, dataset, relation)

        # 8. Build LIMIT & OFFSET
        limit_val = spec.pagination.limit
        offset_val = spec.pagination.offset
        binds.append(AnalyticalBindParameterV2(name="bind_limit", value=limit_val, value_type="INTEGER"))
        binds.append(AnalyticalBindParameterV2(name="bind_offset", value=offset_val, value_type="INTEGER"))

        # Assemble SQL
        select_str = ", ".join(select_exprs)
        where_str = " AND ".join(where_clauses)
        group_str = f" GROUP BY {', '.join(group_by_exprs)}" if group_by_exprs else ""
        order_str = f" ORDER BY {order_by_clause}" if order_by_clause else ""

        sql_template = (
            f"SELECT {select_str} FROM {relation.physical_name} "
            f"WHERE {where_str}"
            f"{group_str}"
            f"{order_str} "
            f"LIMIT :bind_limit OFFSET :bind_offset"
        )

        # 9. Perform SQL Security Check
        self._assert_sql_security(sql_template)

        # 10. Generate fingerprint
        fingerprint = self._calc_fingerprint(sql_template, spec)

        compiled_id = f"cmp_{fingerprint[:16]}"

        return AnalyticalCompiledQueryV2(
            compiled_query_id=compiled_id,
            contract_version=SAFE_ANALYTICAL_POSTGRESQL_VERSION,
            sql_template=sql_template,
            bind_parameters=binds,
            isolation_proof=proof,
            query_fingerprint=fingerprint,
            target_database="POSTGRESQL_ANALYTICAL",
            statement_timeout_seconds=budget.maximum_timeout_seconds,
            lock_timeout_seconds=3.0,
        )

    def _check_budget(self, spec: AnalyticalQuerySpecV2, budget: AnalyticalQueryBudgetV2) -> None:
        if len(spec.metrics) > budget.maximum_metrics:
            raise AnalyticalBudgetExceededError(
                f"Requested metrics ({len(spec.metrics)}) exceed budget limit ({budget.maximum_metrics})."
            )
        if len(spec.dimensions) > budget.maximum_dimensions:
            raise AnalyticalBudgetExceededError(
                f"Requested dimensions ({len(spec.dimensions)}) exceed budget limit ({budget.maximum_dimensions})."
            )

    def _get_dataset(self, dataset_id: str) -> AnalyticalDatasetDefinitionV2:
        if dataset_id in self.catalog_snapshot.datasets:
            return self.catalog_snapshot.datasets[dataset_id]
        for ds in self.catalog_snapshot.datasets.values():
            if ds.canonical_dataset_id == dataset_id or ds.domain == dataset_id:
                return ds
        raise AnalyticalCompilationError(f"Dataset '{dataset_id}' not found in published catalog snapshot.")

    def _get_relation(self, dataset: AnalyticalDatasetDefinitionV2) -> Tuple[str, AnalyticalRelationDefinitionV2]:
        if not dataset.relations:
            raise AnalyticalCompilationError(f"Dataset '{dataset.canonical_dataset_id}' has no relations.")
        first_key = list(dataset.relations.keys())[0]
        return first_key, dataset.relations[first_key]

    def _create_isolation_proof(
        self,
        dataset: AnalyticalDatasetDefinitionV2,
        relation_name: str,
        relation: AnalyticalRelationDefinitionV2,
        tenant_id: str,
    ) -> AnalyticalIsolationProofV2:

        if not tenant_id or not tenant_id.strip():
            raise AnalyticalSecurityViolationError("Tenant ID is required for analytical query compilation.")

        tenant_col = relation.tenant_column or "tenant_id"
        if tenant_col not in relation.columns:
            raise AnalyticalSecurityViolationError(
                f"Relation '{relation.physical_name}' missing tenant column '{tenant_col}'."
            )

        proof_data = {
            "tenant_id": tenant_id,
            "dataset_id": dataset.canonical_dataset_id,
            "relation": relation.physical_name,
            "tenant_col": tenant_col,
            "strategy": dataset.tenant_strategy.value,
        }
        proof_checksum = hashlib.sha256(json.dumps(proof_data, sort_keys=True).encode("utf-8")).hexdigest()

        return AnalyticalIsolationProofV2(
            tenant_strategy=dataset.tenant_strategy,
            tenant_id=tenant_id,
            tenant_predicate_applied=True,
            tenant_column=tenant_col,
            dataset_id=dataset.canonical_dataset_id,
            relation_id=relation_name,
            connection_scope="READ_ONLY_POSTGRESQL",
            proof_checksum=proof_checksum,
            validation_status="VALIDATED",
        )

    def _build_select_and_group(
        self,
        spec: AnalyticalQuerySpecV2,
        dataset: AnalyticalDatasetDefinitionV2,
        relation: AnalyticalRelationDefinitionV2,
    ) -> Tuple[List[str], List[str], List[AnalyticalBindParameterV2]]:
        select_exprs = []
        group_by_exprs = []
        binds: List[AnalyticalBindParameterV2] = []

        # 1. Selected Dimensions
        for dim_sel in spec.dimensions:
            dim_key = dim_sel.dimension_id
            if dim_key in dataset.dimension_bindings:
                dim_binding = dataset.dimension_bindings[dim_key]
                col_name = dim_binding.column_name
            elif dim_key in relation.columns:
                col_name = dim_key
            else:
                raise AnalyticalCompilationError(f"Dimension '{dim_key}' not defined in dataset catalog.")

            phys_col = relation.columns[col_name].physical_name
            alias = dim_sel.alias or phys_col
            select_exprs.append(f"{phys_col} AS {alias}")
            group_by_exprs.append(phys_col)

        # 2. Selected Metrics
        for met_sel in spec.metrics:
            met_key = met_sel.metric_id
            if met_key not in dataset.metric_bindings:
                raise AnalyticalCompilationError(f"Metric '{met_key}' not defined in dataset catalog.")
            met_binding = dataset.metric_bindings[met_key]
            alias = met_sel.alias or met_key

            # Pure aggregate expression from binding
            expr = met_binding.formula_expression
            select_exprs.append(f"{expr} AS {alias}")

        if not select_exprs:
            # Default fallback: COUNT(*) AS row_count
            select_exprs.append("COUNT(*) AS row_count")

        return select_exprs, group_by_exprs, binds

    def _build_where_clause(
        self,
        spec: AnalyticalQuerySpecV2,
        dataset: AnalyticalDatasetDefinitionV2,
        relation: AnalyticalRelationDefinitionV2,
        tenant_id: str,
        binds: List[AnalyticalBindParameterV2],
    ) -> Tuple[List[str], List[AnalyticalBindParameterV2]]:

        tenant_col = relation.tenant_column or "tenant_id"
        where_clauses = [f"{tenant_col} = :bind_tenant_id"]
        binds.append(AnalyticalBindParameterV2(name="bind_tenant_id", value=tenant_id, value_type="STRING"))

        bind_idx = 0

        # User filters
        if spec.filter_group and spec.filter_group.expressions:
            for expr in spec.filter_group.expressions:
                dim_key = expr.dimension_id
                if dim_key in dataset.dimension_bindings:
                    col_name = dataset.dimension_bindings[dim_key].column_name
                elif dim_key in relation.columns:
                    col_name = dim_key
                else:
                    raise AnalyticalCompilationError(f"Filter dimension '{dim_key}' not found in catalog.")

                phys_col = relation.columns[col_name].physical_name

                if expr.operator == AnalyticalFilterOperatorV2.EQ:
                    bind_name = f"bind_filter_{bind_idx}"
                    bind_idx += 1
                    val = expr.values[0] if expr.values else ""
                    where_clauses.append(f"{phys_col} = :{bind_name}")
                    binds.append(AnalyticalBindParameterV2(name=bind_name, value=val, value_type="STRING"))

                elif expr.operator == AnalyticalFilterOperatorV2.IN:
                    bind_name = f"bind_filter_{bind_idx}"
                    bind_idx += 1
                    vals = expr.values
                    where_clauses.append(f"{phys_col} = ANY(:{bind_name})")
                    binds.append(AnalyticalBindParameterV2(name=bind_name, value=vals, value_type="LIST"))

                elif expr.operator in (AnalyticalFilterOperatorV2.BETWEEN, AnalyticalFilterOperatorV2.DATE_RANGE):
                    bind_name1 = f"bind_filter_{bind_idx}_start"
                    bind_name2 = f"bind_filter_{bind_idx}_end"
                    bind_idx += 1
                    val1 = expr.values[0] if len(expr.values) > 0 else ""
                    val2 = expr.values[1] if len(expr.values) > 1 else val1
                    where_clauses.append(f"{phys_col} BETWEEN :{bind_name1} AND :{bind_name2}")
                    binds.append(AnalyticalBindParameterV2(name=bind_name1, value=val1, value_type="STRING"))
                    binds.append(AnalyticalBindParameterV2(name=bind_name2, value=val2, value_type="STRING"))

                elif expr.operator == AnalyticalFilterOperatorV2.IS_NULL:
                    where_clauses.append(f"{phys_col} IS NULL")

                elif expr.operator == AnalyticalFilterOperatorV2.IS_NOT_NULL:
                    where_clauses.append(f"{phys_col} IS NOT NULL")

        return where_clauses, binds

    def _build_order_by(
        self,
        spec: AnalyticalQuerySpecV2,
        dataset: AnalyticalDatasetDefinitionV2,
        relation: AnalyticalRelationDefinitionV2,
    ) -> str:
        if not spec.order_by:
            return ""
        order_parts = []
        for ob in spec.order_by:
            field = ob.field
            direction = ob.direction.upper()
            if direction not in ("ASC", "DESC"):
                direction = "ASC"

            if field in dataset.metric_bindings:
                phys_field = field
            elif field in dataset.dimension_bindings:
                phys_field = dataset.dimension_bindings[field].column_name
            elif field in relation.columns:
                phys_field = relation.columns[field].physical_name
            else:
                phys_field = field

            order_parts.append(f"{phys_field} {direction}")
        return ", ".join(order_parts)

    def _assert_sql_security(self, sql_string: str) -> None:
        upper_sql = sql_string.upper()
        for pat in FORBIDDEN_SQL_PATTERNS:
            if re.search(pat, upper_sql, re.IGNORECASE):
                raise AnalyticalSecurityViolationError(
                    f"FORBIDDEN: SQL template contains illegal pattern '{pat}'."
                )

    def _calc_fingerprint(self, sql: str, spec: AnalyticalQuerySpecV2) -> str:
        data = {
            "sql": sql,
            "dataset": spec.dataset_id,
            "metrics": [m.metric_id for m in spec.metrics],
            "dimensions": [d.dimension_id for d in spec.dimensions],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()
