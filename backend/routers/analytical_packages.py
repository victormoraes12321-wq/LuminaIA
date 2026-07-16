"""
LuminaAI — Analytical Packages Router
---------------------------------------
Endpoints REST para gestão e consulta de Analytical Packages.

Rotas disponíveis:
  GET    /api/v1/analytical-packages          — Listar Packages do tenant
  GET    /api/v1/analytical-packages/stats    — Métricas globais de reuso
  GET    /api/v1/analytical-packages/{id}     — Detalhe de um Package
  GET    /api/v1/analytical-packages/{id}/instances — Histórico de execuções
  POST   /api/v1/analytical-packages/{id}/deprecate — Deprecar manualmente

Isolamento: Todos os endpoints são filtrados pelo tenant_id do usuário autenticado.
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.analytical_package import PackageStatus
from models.user import User
from routers.dependencies import enforce_password_change
from services.data_platform.analytical_package_service import analytical_package_service

logger = logging.getLogger("luminaai.routers.analytical_packages")

router = APIRouter(
    prefix="/api/v1/analytical-packages",
    tags=["Analytical Packages"],
)


# â”€â”€ Schemas de Resposta â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PackageSummaryResponse(BaseModel):
    id: str
    status: str
    version: int
    domain: str
    operation: str
    entity: str
    analysis_type: str
    view_names: list[str]
    blueprint_id: str | None
    quality_score: float
    health_score: float
    usage_count: int
    last_used_at: str | None
    avg_execution_time_ms: float
    created_by: str
    criado_em: str | None

    model_config = {"from_attributes": True}


class PackageDetailResponse(PackageSummaryResponse):
    intent_fingerprint: dict
    semantic_context: dict
    visual_strategy: dict
    interaction_strategy: dict
    analytical_structure: dict
    blueprint_snapshot: dict
    dependencies: dict
    compatible_fingerprints: list[str]
    atualizado_em: str | None


class PackageInstanceResponse(BaseModel):
    id: str
    package_id: str
    execution_time_ms: int
    was_package_reuse: bool
    compatibility_score: float
    query_params: dict
    criado_em: str | None
    data_freshness_at: str | None

    model_config = {"from_attributes": True}


class GlobalStatsResponse(BaseModel):
    packages_by_status: dict[str, int]
    total_packages: int
    total_executions: int
    total_reuses: int
    reuse_rate: float
    avg_quality_score: float
    avg_health_score: float
    cache_stats: dict[str, Any]


class DeprecateRequest(BaseModel):
    reason: str = "Deprecado manualmente pelo administrador."


# ── Dependency: usuário autenticado ──────────────────────────────────────────



# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get(
    "/stats",
    response_model=GlobalStatsResponse,
    summary="Métricas globais de Analytical Packages",
    description=(
        "Retorna métricas globais de reuso, scores médios e status de cache "
        "para todos os Analytical Packages do tenant autenticado."
    ),
)
async def get_package_stats(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> GlobalStatsResponse:
    """Métricas globais de Packages do tenant."""
    try:
        stats = await analytical_package_service.get_global_stats(
            tenant_id=current_user.tenant_id,
            db=db,
        )
        return GlobalStatsResponse(**stats)
    except Exception as e:
        logger.error("[AnalyticalPackages] Erro ao buscar stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao recuperar métricas de Packages.",
        )


@router.get(
    "",
    response_model=list[PackageSummaryResponse],
    summary="Listar Analytical Packages",
    description=(
        "Lista os Analytical Packages do tenant autenticado, "
        "ordenados por frequência de uso (mais usados primeiro)."
    ),
)
async def list_packages(
    current_user: Annotated[User, Depends(enforce_password_change)],
    pkg_status: str | None = Query(None, alias="status", description="Filtrar por status: ACTIVE, DEPRECATED, DRAFT, ARCHIVED"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[PackageSummaryResponse]:
    """Lista Packages do tenant com filtro opcional por status."""
    # Valida e converte status
    status_filter: PackageStatus | None = None
    if pkg_status:
        try:
            status_filter = PackageStatus(pkg_status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido: {pkg_status!r}. Válidos: ACTIVE, DEPRECATED, DRAFT, ARCHIVED",
            )

    packages = await analytical_package_service.list_packages(
        tenant_id=current_user.tenant_id,
        db=db,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return [_to_summary_response(pkg) for pkg in packages]


@router.get(
    "/{package_id}",
    response_model=PackageDetailResponse,
    summary="Detalhe de um Analytical Package",
    description="Retorna todos os campos de um Analytical Package específico.",
)
async def get_package(
    package_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> PackageDetailResponse:
    """Detalhe completo de um Package."""
    package = await analytical_package_service.get_package_by_id(
        package_id=package_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytical Package {package_id} não encontrado.",
        )

    return _to_detail_response(package)


@router.get(
    "/{package_id}/instances",
    response_model=list[PackageInstanceResponse],
    summary="Histórico de execuções de um Package",
    description=(
        "Lista as instâncias (snapshots de execução) de um Package, "
        "ordenadas da mais recente para a mais antiga."
    ),
)
async def list_package_instances(
    package_id: uuid.UUID,
    current_user: Annotated[User, Depends(enforce_password_change)],
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[PackageInstanceResponse]:
    """Histórico de execuções de um Package."""
    # Verifica se o Package existe
    package = await analytical_package_service.get_package_by_id(
        package_id=package_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytical Package {package_id} não encontrado.",
        )

    instances = await analytical_package_service.list_instances(
        package_id=package_id,
        tenant_id=current_user.tenant_id,
        db=db,
        limit=limit,
    )

    return [_to_instance_response(inst) for inst in instances]


@router.post(
    "/{package_id}/deprecate",
    response_model=dict,
    summary="Deprecar um Analytical Package manualmente",
    description=(
        "Marca um Package como DEPRECATED. "
        "O Package não será mais utilizado para reuso, mas permanece no banco para auditoria."
    ),
)
async def deprecate_package(
    package_id: uuid.UUID,
    body: DeprecateRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Depreca um Package manualmente."""
    package = await analytical_package_service.get_package_by_id(
        package_id=package_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )

    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analytical Package {package_id} não encontrado.",
        )

    if package.status == PackageStatus.DEPRECATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este Package já está deprecado.",
        )

    from models.analytical_package import PackageStatus as PS
    package.status = PS.DEPRECATED
    package.deprecation_reason = body.reason
    db.add(package)

    # Invalida cache L1
    from services.data_platform.package_cache import package_cache
    package_cache.l1_invalidate(current_user.tenant_id, package.intent_key)

    logger.info(
        "[AnalyticalPackages] Package DEPRECADO manualmente | id=%s motivo=%s",
        package_id, body.reason,
    )

    return {
        "success": True,
        "package_id": str(package_id),
        "status": "DEPRECATED",
        "reason": body.reason,
    }


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _to_summary_response(pkg: Any) -> PackageSummaryResponse:
    """Converte um AnalyticalPackage para PackageSummaryResponse."""
    fingerprint = pkg.intent_fingerprint or {}
    return PackageSummaryResponse(
        id=str(pkg.id),
        status=pkg.status.value,
        version=pkg.version,
        domain=fingerprint.get("domain", "GERAL"),
        operation=fingerprint.get("operation", "AGGREGATION"),
        entity=fingerprint.get("entity", "GERAL"),
        analysis_type=fingerprint.get("analysis_type", "AGGREGATION"),
        view_names=pkg.view_names or [],
        blueprint_id=pkg.blueprint_id,
        quality_score=pkg.quality_score or 0.0,
        health_score=pkg.health_score or 0.0,
        usage_count=pkg.usage_count or 0,
        last_used_at=pkg.last_used_at.isoformat() if pkg.last_used_at else None,
        avg_execution_time_ms=pkg.avg_execution_time_ms or 0.0,
        created_by=pkg.created_by or "AI_PIPELINE",
        criado_em=pkg.criado_em.isoformat() if pkg.criado_em else None,
    )


def _to_detail_response(pkg: Any) -> PackageDetailResponse:
    """Converte um AnalyticalPackage para PackageDetailResponse."""
    summary = _to_summary_response(pkg)
    return PackageDetailResponse(
        **summary.model_dump(),
        intent_fingerprint=pkg.intent_fingerprint or {},
        semantic_context=pkg.semantic_context or {},
        visual_strategy=pkg.visual_strategy or {},
        interaction_strategy=pkg.interaction_strategy or {},
        analytical_structure=pkg.analytical_structure or {},
        blueprint_snapshot=pkg.blueprint_snapshot or {},
        dependencies=pkg.dependencies or {},
        compatible_fingerprints=pkg.compatible_fingerprints or [],
        atualizado_em=pkg.atualizado_em.isoformat() if pkg.atualizado_em else None,
    )


def _to_instance_response(inst: Any) -> PackageInstanceResponse:
    """Converte uma PackageDashboardInstance para PackageInstanceResponse."""
    return PackageInstanceResponse(
        id=str(inst.id),
        package_id=str(inst.package_id),
        execution_time_ms=inst.execution_time_ms or 0,
        was_package_reuse=inst.was_package_reuse or False,
        compatibility_score=inst.compatibility_score or 1.0,
        query_params=inst.query_params or {},
        criado_em=inst.criado_em.isoformat() if inst.criado_em else None,
        data_freshness_at=inst.data_freshness_at.isoformat() if inst.data_freshness_at else None,
    )

