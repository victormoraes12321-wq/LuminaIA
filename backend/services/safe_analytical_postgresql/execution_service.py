from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from contracts.safe_analytical_postgresql_v2.catalog import AnalyticalCatalogSnapshotV2
from contracts.safe_analytical_postgresql_v2.compilation import AnalyticalCompiledQueryV2
from contracts.safe_analytical_postgresql_v2.execution import AnalyticalExecutionResultV2
from contracts.safe_analytical_postgresql_v2.identity import AnalyticalRolloutModeV2
from contracts.safe_analytical_postgresql_v2.provenance import AnalyticalQueryProvenanceV2
from contracts.safe_analytical_postgresql_v2.query_spec import AnalyticalQueryBudgetV2, AnalyticalQuerySpecV2
from database import get_db_context
from services.safe_analytical_postgresql.catalog_service import AnalyticalCatalogService
from services.safe_analytical_postgresql.compiler import GovernedAnalyticalSQLCompiler
from services.safe_analytical_postgresql.connection_guard import AnalyticalConnectionGuard
from services.safe_analytical_postgresql.exceptions import (
    AnalyticalExecutionError,
    AnalyticalSecurityViolationError,
)
from services.safe_analytical_postgresql.provenance_service import AnalyticalProvenanceService
from services.safe_analytical_postgresql.result_validator import AnalyticalResultValidator


class SafeAnalyticalPostgreSQLService:
    """
    Main authority and execution engine for Governed Analytical PostgreSQL queries.
    """

    def __init__(self, catalog_service: Optional[AnalyticalCatalogService] = None):
        self.catalog_service = catalog_service or AnalyticalCatalogService()
        self.result_validator = AnalyticalResultValidator()
        self.provenance_service = AnalyticalProvenanceService()

    def get_rollout_mode(self) -> AnalyticalRolloutModeV2:
        val = os.getenv("SAFE_ANALYTICAL_POSTGRESQL_MODE", "LEGACY_ONLY").upper()
        try:
            return AnalyticalRolloutModeV2(val)
        except ValueError:
            return AnalyticalRolloutModeV2.LEGACY_ONLY

    def get_catalog_snapshot(self) -> AnalyticalCatalogSnapshotV2:
        return self.catalog_service.get_default_catalog_snapshot()

    def compile_query(
        self,
        spec: AnalyticalQuerySpecV2,
        tenant_id: str,
        budget: AnalyticalQueryBudgetV2 = AnalyticalQueryBudgetV2(),
    ) -> AnalyticalCompiledQueryV2:
        snapshot = self.get_catalog_snapshot()
        compiler = GovernedAnalyticalSQLCompiler(snapshot)
        return compiler.compile(spec=spec, tenant_id=tenant_id, budget=budget)

    async def execute_query(
        self,
        spec: AnalyticalQuerySpecV2,
        tenant_id: str,
        user_id: str = "system",
        budget: AnalyticalQueryBudgetV2 = AnalyticalQueryBudgetV2(),
    ) -> AnalyticalExecutionResultV2:

        # 1. Connection Guard Assertions
        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/lumina_analytical")
        AnalyticalConnectionGuard.assert_safe_target(
            db_url=db_url,
            target_name="POSTGRESQL_ANALYTICAL",
            tenant_id=tenant_id,
            is_read_only=True,
        )

        # 2. Compile Query
        compiled_query = self.compile_query(spec=spec, tenant_id=tenant_id, budget=budget)

        # 3. Prepare parameters
        bind_map: Dict[str, Any] = {}
        for param in compiled_query.bind_parameters:
            bind_map[param.name] = param.value

        start_time = time.perf_counter()

        # 4. Execute on Analytical PostgreSQL Connection
        try:
            async with get_db_context() as session:
                # Set statement timeout for read-only query
                timeout_ms = int(compiled_query.statement_timeout_seconds * 1000)
                await session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms};"))

                stmt = text(compiled_query.sql_template)
                res = await session.execute(stmt, bind_map)

                # Fetch dictionary rows
                mappings = res.mappings().all()
                raw_rows = [dict(m) for m in mappings]

        except Exception as e:
            raise AnalyticalExecutionError(f"Database execution failed: {str(e)}")

        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        # 5. Format & Validate Result
        exec_result = self.result_validator.validate_and_format(
            raw_rows=raw_rows,
            compiled_query=compiled_query,
            execution_time_ms=execution_time_ms,
            max_rows=budget.maximum_rows,
            max_bytes=budget.maximum_result_bytes,
        )

        # 6. Generate Provenance
        _provenance = self.provenance_service.generate_provenance(compiled_query, exec_result)

        return exec_result
