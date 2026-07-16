"""
LuminaAI - Metadata Catalog API
-------------------------------
Read-only governance endpoints for the Data Platform Metadata Catalog.
All access is tenant-scoped and routed through CatalogAPI.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from models.user import User
from routers.dependencies import enforce_password_change
from schemas.metadata_catalog import (
    MetadataCatalogResponse,
    MetadataCatalogVersionResponse,
)
from services.data_platform.catalog_api import catalog_api

logger = logging.getLogger("luminaai.routers.metadata_catalog")

router = APIRouter(
    prefix="/metadata-catalog",
    tags=["Metadata Catalog"],
    dependencies=[Depends(enforce_password_change)],
)


def _normalize_tags(tags: list[str] | None) -> list[str] | None:
    if not tags:
        return None

    normalized: list[str] = []
    for item in tags:
        normalized.extend(tag.strip() for tag in item.split(",") if tag.strip())
    return normalized or None


@router.get(
    "/summary",
    summary="Resumo executivo do Metadata Catalog",
)
async def get_metadata_summary(
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> dict[str, Any]:
    """Return tenant-scoped catalog totals, health and cache summary."""
    return await catalog_api.summary(current_user.tenant_id)


@router.get(
    "/health",
    summary="Relatorio de saude do Metadata Catalog",
)
async def get_metadata_health(
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> dict[str, Any]:
    """Return aggregated health scores and active alerts for the tenant."""
    return await catalog_api.get_health_report(current_user.tenant_id)


@router.get(
    "/",
    response_model=list[MetadataCatalogResponse],
    summary="Pesquisar estruturas no Metadata Catalog",
)
async def search_metadata_catalog(
    current_user: Annotated[User, Depends(enforce_password_change)],
    q: str | None = Query(default=None, description="Texto para busca por nome, id ou owner."),
    tipo: str | None = Query(default=None, description="Tipo da estrutura: VIEW, DATASET, BLUEPRINT, DASHBOARD, KPI."),
    tags: list[str] | None = Query(default=None, description="Tags, repetidas ou separadas por virgula."),
    categoria: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MetadataCatalogResponse]:
    """Search tenant structures without exposing direct database access."""
    results = await catalog_api.query(
        tenant_id=current_user.tenant_id,
        search_query=q,
        tipo=tipo,
        tags=_normalize_tags(tags),
        categoria=categoria,
        limit=limit,
    )
    return [MetadataCatalogResponse.model_validate(item) for item in results]


@router.get(
    "/{estrutura_id}",
    response_model=MetadataCatalogResponse,
    summary="Obter metadados de uma estrutura",
)
async def get_metadata_entity(
    estrutura_id: str,
    current_user: Annotated[User, Depends(enforce_password_change)],
    tipo: str | None = Query(default=None),
) -> MetadataCatalogResponse:
    """Return one tenant-scoped structure by id, optionally constrained by type."""
    entity = (
        await catalog_api.get(current_user.tenant_id, tipo, estrutura_id)
        if tipo
        else await catalog_api.get_any(current_user.tenant_id, estrutura_id)
    )
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrutura nao encontrada no Metadata Catalog deste tenant.",
        )
    return MetadataCatalogResponse.model_validate(entity)


@router.get(
    "/{estrutura_id}/lineage",
    summary="Obter Data Lineage de uma estrutura",
)
async def get_metadata_lineage(
    estrutura_id: str,
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> list[dict[str, Any]]:
    """Return the ERP -> table -> view -> dataset -> blueprint -> dashboard chain."""
    return await catalog_api.get_lineage(current_user.tenant_id, estrutura_id)


@router.get(
    "/{estrutura_id}/dependency-graph",
    summary="Obter grafo de dependencias de uma estrutura",
)
async def get_metadata_dependency_graph(
    estrutura_id: str,
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> dict[str, Any]:
    """Return direct upstream and downstream dependencies for a structure."""
    return await catalog_api.get_dependency_graph(current_user.tenant_id, estrutura_id)


@router.get(
    "/{estrutura_id}/impact",
    summary="Obter impacto de alteracao de uma estrutura",
)
async def get_metadata_impact(
    estrutura_id: str,
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> dict[str, Any]:
    """Return direct and transitive downstream impact for a structure."""
    return await catalog_api.get_impact(current_user.tenant_id, estrutura_id)


@router.get(
    "/{estrutura_id}/versions",
    response_model=list[MetadataCatalogVersionResponse],
    summary="Obter historico de versoes de uma estrutura",
)
async def get_metadata_versions(
    estrutura_id: str,
    current_user: Annotated[User, Depends(enforce_password_change)],
) -> list[MetadataCatalogVersionResponse]:
    """Return immutable version snapshots for the selected structure."""
    versions = await catalog_api.get_version_history(current_user.tenant_id, estrutura_id)
    return [MetadataCatalogVersionResponse.model_validate(item) for item in versions]
