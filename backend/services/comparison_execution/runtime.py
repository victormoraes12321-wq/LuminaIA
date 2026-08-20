from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from database import get_db_context
from models.tenant import Tenant
from services.connection_credentials import decrypt_connection_details
from services.postgresql_clone_service import (
    get_clone_db_connection,
    release_clone_db_connection,
)

from .catalog import default_comparison_execution_catalog
from .executor import UniversalComparisonExecutor
from .models import ComparisonExecutionContext
from .query_runner import AsyncpgComparisonQueryRunner


class ComparisonRuntimeUnavailable(RuntimeError):
    pass


def build_execution_context_from_plan(plan) -> ComparisonExecutionContext:
    if plan.scope is None:
        raise ComparisonRuntimeUnavailable("Comparison plan has no trusted scope")
    source_catalog = default_comparison_execution_catalog()
    source_ids = tuple(item.source_id for item in plan.source_refs)
    source = next(
        (
            source_catalog.source(source_id, plan.scope.tenant_id)
            for source_id in source_ids
            if source_catalog.source(source_id, plan.scope.tenant_id) is not None
        ),
        None,
    )
    if source is None:
        raise ComparisonRuntimeUnavailable("No governed comparison source is available")
    return ComparisonExecutionContext(
        tenant_id=plan.scope.tenant_id,
        user_id=plan.scope.user_id,
        user_role=plan.scope.user_role,
        session_id=plan.scope.session_id,
        permission_fingerprint=plan.scope.permission_fingerprint,
        allowed_source_ids=source_ids,
        allowed_metric_ids=tuple(item.metric_id for item in plan.metric_refs),
        allowed_dimension_ids=tuple(item.dimension_id for item in plan.dimension_refs)
        or tuple(source.dimensions),
        query_timeout_seconds=Decimal("10"),
        total_timeout_seconds=Decimal("30"),
        source_version=source.source_version,
        feature_flags={},
    )


async def execute_plan_on_tenant_clone(plan):
    context = build_execution_context_from_plan(plan)
    async with get_db_context() as session:
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == context.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            raise ComparisonRuntimeUnavailable("Authenticated tenant was not found")
        details = decrypt_connection_details(tenant.clone_db_conn)

    async def acquire():
        return await get_clone_db_connection(details, tenant_id=context.tenant_id)

    async def release(connection):
        await release_clone_db_connection(connection, tenant_id=context.tenant_id)

    runner = AsyncpgComparisonQueryRunner(acquire, release)
    return await UniversalComparisonExecutor(runner).execute(plan, context)
