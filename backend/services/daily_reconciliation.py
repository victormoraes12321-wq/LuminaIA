from __future__ import annotations

import inspect
import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from database import get_db_context
from models.tenant import Tenant
from services.data_platform.history_service import history_service
from services.erp_reconciliation import erp_reconciliation
from services.oracle_service import decrypt_connection_details, get_oracle_connection

logger = logging.getLogger("luminaai.daily_reconciliation")


class DailyReconciliationService:
    """Technical ERP reconciliation. Query/AI paths never call this service."""

    async def _close(self, resource: Any) -> None:
        close = getattr(resource, "close", None)
        if not close:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _periods(today: date) -> list[str]:
        yesterday = today - timedelta(days=1)
        previous_month_end = today.replace(day=1) - timedelta(days=1)
        return [previous_month_end.strftime("%Y-%m"), yesterday.isoformat()]

    async def run_for_tenant(self, tenant_id: uuid.UUID, *, force: bool = False) -> dict[str, Any]:
        today = date.today()
        oracle_connection = None
        async with get_db_context() as session:
            tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
            if tenant is None or not tenant.ativo:
                return {"status": "skipped", "reason": "tenant_inactive_or_missing"}

            sync_config = dict(tenant.sync_config or {})
            if not force and sync_config.get("last_reconciliation_date") == today.isoformat():
                return {"status": "skipped", "reason": "already_reconciled_today"}

            try:
                details = decrypt_connection_details(tenant.oracle_conn)
                oracle_connection = await get_oracle_connection(details, tenant_id=tenant.id)
                report = await erp_reconciliation.reconcile(
                    session,
                    periods=self._periods(today),
                    oracle_connection=oracle_connection,
                    include_oracle=True,
                )
            except Exception as exc:
                logger.exception("Daily reconciliation failed for tenant %s", tenant_id)
                report = {
                    "overall_status": "error",
                    "periods": [],
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
            finally:
                await self._close(oracle_connection)

            summary = {
                "status": report.get("overall_status"),
                "periods": [item.get("period") for item in report.get("periods", [])],
                "generated_at": report.get("generated_at"),
                "error": report.get("error"),
            }
            sync_config.update({
                "last_reconciliation_date": today.isoformat(),
                "last_reconciliation": summary,
            })
            tenant.sync_config = sync_config
            session.add(tenant)
            await session.commit()

        await history_service.log_change(
            tenant_id=tenant_id,
            estrutura_tipo="METADADOS",
            estrutura_id="ERP_RECONCILIATION",
            acao="UPDATE",
            detalhes=summary,
        )
        return summary


daily_reconciliation_service = DailyReconciliationService()
