from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change, check_admin_or_gestor_role
from schemas.dashboard_studio import (
    DashboardDuplicateRequest,
    DashboardExportResponse,
    DashboardFavoriteRequest,
    DashboardImportRequest,
    DashboardInstanceCreate,
    DashboardInstanceResponse,
    DashboardInstanceUpdate,
    DashboardLayoutValidationRequest,
    DashboardLayoutValidationResponse,
    DashboardRollbackRequest,
    DashboardStudioVersionResponse,
    DashboardTemplateCreate,
    DashboardTemplateResponse,
    DashboardTemplateUpdate,
)
from services.dashboard_studio_service import dashboard_studio_service

router = APIRouter(
    prefix="/dashboard-studio",
    tags=["Dashboard Studio"],
    dependencies=[Depends(check_admin_or_gestor_role)],
)


@router.post(
    "/templates",
    response_model=DashboardTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: DashboardTemplateCreate,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.create_template(db, payload, current_user)


@router.get("/templates", response_model=list[DashboardTemplateResponse])
async def list_templates(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = Query(False),
):
    return await dashboard_studio_service.list_templates(db, current_user, include_archived)


@router.get("/templates/{template_id}", response_model=DashboardTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.get_template(db, template_id, current_user)


@router.patch("/templates/{template_id}", response_model=DashboardTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    payload: DashboardTemplateUpdate,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.update_template(db, template_id, payload, current_user)


@router.get("/templates/{template_id}/versions", response_model=list[DashboardStudioVersionResponse])
async def list_template_versions(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.list_template_versions(db, template_id, current_user)


@router.post("/templates/{template_id}/versions/{version}/rollback", response_model=DashboardTemplateResponse)
async def rollback_template(
    template_id: uuid.UUID,
    version: int,
    payload: DashboardRollbackRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.rollback_template(
        db,
        template_id,
        version,
        current_user,
        payload.description,
    )


@router.get("/templates/{template_id}/export", response_model=DashboardExportResponse)
async def export_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.export_template(db, template_id, current_user)


@router.post("/instances", response_model=DashboardInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: DashboardInstanceCreate,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.create_instance(db, payload, current_user)


@router.get("/instances", response_model=list[DashboardInstanceResponse])
async def list_instances(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: bool = Query(False),
    favorites_only: bool = Query(False),
):
    return await dashboard_studio_service.list_instances(
        db,
        current_user,
        include_archived,
        favorites_only,
    )


@router.get("/instances/{instance_id}", response_model=DashboardInstanceResponse)
async def get_instance(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.get_instance(db, instance_id, current_user)


@router.patch("/instances/{instance_id}", response_model=DashboardInstanceResponse)
async def update_instance(
    instance_id: uuid.UUID,
    payload: DashboardInstanceUpdate,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.update_instance(db, instance_id, payload, current_user)


@router.post("/instances/{instance_id}/duplicate", response_model=DashboardInstanceResponse)
async def duplicate_instance(
    instance_id: uuid.UUID,
    payload: DashboardDuplicateRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.duplicate_instance(db, instance_id, payload, current_user)


@router.post("/instances/{instance_id}/favorite", response_model=DashboardInstanceResponse)
async def set_favorite(
    instance_id: uuid.UUID,
    payload: DashboardFavoriteRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.set_favorite(db, instance_id, payload, current_user)


@router.get("/instances/{instance_id}/versions", response_model=list[DashboardStudioVersionResponse])
async def list_instance_versions(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.list_instance_versions(db, instance_id, current_user)


@router.post("/instances/{instance_id}/versions/{version}/rollback", response_model=DashboardInstanceResponse)
async def rollback_instance(
    instance_id: uuid.UUID,
    version: int,
    payload: DashboardRollbackRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.rollback_instance(
        db,
        instance_id,
        version,
        current_user,
        payload.description,
    )


@router.get("/instances/{instance_id}/export", response_model=DashboardExportResponse)
async def export_instance(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.export_instance(db, instance_id, current_user)


@router.post("/import", response_model=DashboardTemplateResponse | DashboardInstanceResponse, status_code=status.HTTP_201_CREATED)
async def import_layout(
    payload: DashboardImportRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await dashboard_studio_service.import_layout(db, payload, current_user)


@router.post("/validate-layout", response_model=DashboardLayoutValidationResponse)
async def validate_layout(
    payload: DashboardLayoutValidationRequest,
    _current_user: Annotated[User, Depends(enforce_password_change)],
):
    return dashboard_studio_service.validate_layout(payload.grid)
