from __future__ import annotations

import logging
from typing import Optional

from services.safe_analytical_postgresql.exceptions import AnalyticalConnectionGuardError

logger = logging.getLogger("luminaai.safe_analytical_postgresql.connection_guard")


class AnalyticalConnectionGuard:
    """
    Verifies target database connection safety, read-only permissions, and blocks Oracle / unauthorized targets.
    """

    @staticmethod
    def assert_safe_target(
        db_url: str,
        target_name: str = "POSTGRESQL_ANALYTICAL",
        tenant_id: Optional[str] = None,
        is_read_only: bool = True,
    ) -> None:
        url_lower = db_url.lower()

        # 1. Oracle Block
        if any(token in url_lower for token in ["oracle", "cx_oracle", "oracledb", ":1521", "sid="]):
            raise AnalyticalConnectionGuardError(
                "FORBIDDEN: Analytical access to Oracle databases is strictly prohibited by LuminaAI architecture rules."
            )

        # 2. Must be PostgreSQL
        if not ("postgresql" in url_lower or "postgres" in url_lower):
            raise AnalyticalConnectionGuardError(
                f"FORBIDDEN: Target database '{target_name}' must be PostgreSQL."
            )

        # 3. Read-only assertion
        if not is_read_only:
            raise AnalyticalConnectionGuardError(
                "FORBIDDEN: Analytical execution requires a strictly read-only transaction."
            )

        # 4. Mandatory Tenant Proof
        if not tenant_id or not tenant_id.strip():
            raise AnalyticalConnectionGuardError(
                "FORBIDDEN: Cannot execute analytical query without valid authenticated tenant_id."
            )

        logger.debug(f"Connection guard verified target '{target_name}' for tenant '{tenant_id}'.")
