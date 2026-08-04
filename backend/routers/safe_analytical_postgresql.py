from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from contracts.safe_analytical_postgresql_v2.compilation import AnalyticalCompiledQueryV2
from contracts.safe_analytical_postgresql_v2.execution import AnalyticalExecutionResultV2
from contracts.safe_analytical_postgresql_v2.query_spec import AnalyticalQuerySpecV2
from routers.auth import get_current_user
from services.safe_analytical_postgresql.exceptions import (
    AnalyticalError,
    AnalyticalSecurityViolationError,
)
from services.safe_analytical_postgresql.execution_service import SafeAnalyticalPostgreSQLService

logger = logging.getLogger("luminaai.routers.safe_analytical_postgresql")

router = APIRouter(prefix="/api/v2/analytical-postgresql", tags=["Safe Analytical PostgreSQL"])

service = SafeAnalyticalPostgreSQLService()


def _require_admin_or_gestor(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    role = current_user.get("role", "").upper()
    if role not in ("ADMIN", "GESTOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RBAC_DENIED: Access to safe analytical PostgreSQL administration requires ADMIN or GESTOR role.",
        )
    return current_user


class CompileRequest(BaseModel):
    query_spec: AnalyticalQuerySpecV2


class ExecuteRequest(BaseModel):
    query_spec: AnalyticalQuerySpecV2


@router.get("/catalog", response_model=Dict[str, Any])
async def get_analytical_catalog(
    current_user: Dict[str, Any] = Depends(_require_admin_or_gestor),
):
    """
    Returns published catalog snapshot for the authenticated tenant.
    """
    snapshot = service.get_catalog_snapshot()
    return snapshot.model_dump(mode="json")


@router.post("/compile", response_model=Dict[str, Any])
async def compile_analytical_query(
    request: CompileRequest,
    current_user: Dict[str, Any] = Depends(_require_admin_or_gestor),
):
    """
    Compiles canonical query spec into parameterized SQL with tenant isolation proof.
    """
    tenant_id = current_user.get("tenant_id", "system")
    try:
        compiled = service.compile_query(spec=request.query_spec, tenant_id=tenant_id)
        return compiled.model_dump(mode="json")
    except AnalyticalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.error_code, "message": e.message})
    except Exception as e:
        logger.error(f"Unexpected error compiling query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/execute", response_model=Dict[str, Any])
async def execute_analytical_query(
    request: ExecuteRequest,
    current_user: Dict[str, Any] = Depends(_require_admin_or_gestor),
):
    """
    Executes governed read-only PostgreSQL analytical query with isolation proof.
    """
    tenant_id = current_user.get("tenant_id", "system")
    user_id = str(current_user.get("id", "system"))

    try:
        res = await service.execute_query(
            spec=request.query_spec,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return res.model_dump(mode="json")
    except AnalyticalSecurityViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": e.error_code, "message": e.message})
    except AnalyticalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.error_code, "message": e.message})
    except Exception as e:
        logger.error(f"Unexpected error executing analytical query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
