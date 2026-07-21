from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.dashboard_preference import DashboardPreference
from models.user import User
from routers.dependencies import enforce_password_change, get_current_user
from schemas.dashboard_preferences import DashboardPreferenceResponse, DashboardPreferenceUpdate


router = APIRouter(
    prefix="/dashboard-preferences",
    tags=["Dashboard Preferences"],
)

_SCOPE_RE = re.compile(r"^[a-zA-Z0-9_.:-]{1,80}$")


def _validate_scope(scope: str) -> str:
    clean = str(scope or "default").strip() or "default"
    if not _SCOPE_RE.fullmatch(clean):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Escopo de preferência inválido.",
        )
    return clean


def _response_from_model(pref: DashboardPreference | None, scope: str) -> DashboardPreferenceResponse:
    if pref is None:
        return DashboardPreferenceResponse(id=None, scope=scope, basis="liquido", format="tabela", instructions="")
    return DashboardPreferenceResponse(
        id=pref.id,
        scope=pref.scope,
        basis=pref.basis,  # type: ignore[arg-type]
        format=pref.format,  # type: ignore[arg-type]
        instructions=pref.instructions or "",
    )


@router.get(
    "/{scope}",
    response_model=DashboardPreferenceResponse,
    summary="Carregar preferência de dashboard do usuário",
)
async def get_dashboard_preference(
    scope: str = "default",
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> DashboardPreferenceResponse:
    clean_scope = _validate_scope(scope)
    stmt = select(DashboardPreference).where(
        DashboardPreference.tenant_id == current_user.tenant_id,
        DashboardPreference.user_id == current_user.id,
        DashboardPreference.scope == clean_scope,
    )
    result = await db.execute(stmt)
    return _response_from_model(result.scalar_one_or_none(), clean_scope)


@router.put(
    "/{scope}",
    response_model=DashboardPreferenceResponse,
    summary="Salvar preferência de dashboard do usuário",
)
async def put_dashboard_preference(
    payload: DashboardPreferenceUpdate,
    scope: str = "default",
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> DashboardPreferenceResponse:
    clean_scope = _validate_scope(scope)
    stmt = select(DashboardPreference).where(
        DashboardPreference.tenant_id == current_user.tenant_id,
        DashboardPreference.user_id == current_user.id,
        DashboardPreference.scope == clean_scope,
    )
    result = await db.execute(stmt)
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = DashboardPreference(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            scope=clean_scope,
        )
        db.add(pref)

    pref.basis = payload.basis
    pref.format = payload.format
    pref.instructions = payload.instructions
    await db.flush()
    return _response_from_model(pref, clean_scope)
