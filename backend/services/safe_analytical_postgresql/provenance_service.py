from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from contracts.safe_analytical_postgresql_v2.compilation import AnalyticalCompiledQueryV2
from contracts.safe_analytical_postgresql_v2.execution import AnalyticalExecutionResultV2
from contracts.safe_analytical_postgresql_v2.identity import SAFE_ANALYTICAL_POSTGRESQL_VERSION
from contracts.safe_analytical_postgresql_v2.provenance import AnalyticalQueryProvenanceV2


class AnalyticalProvenanceService:
    """
    Constructs deterministic provenance records for analytical queries.
    """

    def generate_provenance(
        self,
        compiled_query: AnalyticalCompiledQueryV2,
        result: AnalyticalExecutionResultV2,
    ) -> AnalyticalQueryProvenanceV2:
        prov_id = f"prv_{compiled_query.compiled_query_id}"

        return AnalyticalQueryProvenanceV2(
            provenance_id=prov_id,
            contract_version=SAFE_ANALYTICAL_POSTGRESQL_VERSION,
            catalog_version="1.0.0",
            dataset_id=compiled_query.isolation_proof.dataset_id,
            tenant_strategy=compiled_query.isolation_proof.tenant_strategy,
            isolation_proof_checksum=compiled_query.isolation_proof.proof_checksum,
            query_fingerprint=compiled_query.query_fingerprint,
            row_count=result.statistics.row_count,
            truncated=result.statistics.truncated,
            validation_status="VALIDATED" if result.validation.is_valid else "INVALID",
            execution_time_ms=result.statistics.execution_time_ms,
            executed_at=datetime.now(timezone.utc).isoformat(),
        )
