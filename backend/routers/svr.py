from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.svr import SVRCompatibilityMatrix, SVRAuditLog, SVRVersion
from routers.dependencies import get_current_user, enforce_password_change, check_admin_role
from services.svr_service import svr_service
from services.svr_migration import svr_migration

logger = logging.getLogger("luminaai.routers.svr")

router = APIRouter(
    prefix="/svr",
    tags=["⚙️ Semantic Version Registry"],
    dependencies=[Depends(enforce_password_change), Depends(check_admin_role)],
)

# ── Schemas Pydantic ──────────────────────────────────────────────────

class ConceptRegisterRequest(BaseModel):
    concept_id: str = Field(..., description="ID corporativo do conceito (ex: MET_001)")
    concept_type: str = Field(..., description="Tipo do conceito (METRIC, KPI, DIMENSION, BLUEPRINT, DASHBOARD, etc.)")
    semantic_version: str = Field(..., description="Versão semântica (ex: 2.0)")
    mapping_version: str = Field(..., description="Versão de mapeamento físico (ex: 2)")
    blueprint_version: str | None = Field(default=None, description="Versão do blueprint se aplicável")
    snapshot: dict[str, Any] = Field(..., description="Snapshot JSON com os dados completos do conceito")
    motivo: str | None = Field(default=None, description="Motivo da alteração/evolução")
    impacto: str | None = Field(default=None, description="Impacto previsto para o negócio")


class ConceptDeprecateRequest(BaseModel):
    concept_id: str = Field(...)
    semantic_version: str = Field(...)
    mapping_version: str = Field(...)
    status: str = Field(..., description="ACTIVE | LEGACY | DEPRECATED | OBSOLETE")
    motivo: str | None = Field(default=None)


class MigrationEvaluateRequest(BaseModel):
    concept_id: str = Field(...)
    new_semantic_version: str = Field(...)
    new_mapping_version: str = Field(...)

# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/", status_code=status.HTTP_200_OK)
async def get_version_center(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Retorna o panorama geral e estatísticas de governança do Version Center do Tenant.
    """
    summary = await svr_service.get_version_center_summary(db, current_user.tenant_id)
    return summary


@router.get("/concepts/{concept_id}/history", status_code=status.HTTP_200_OK)
async def get_concept_history(
    concept_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Retorna o histórico detalhado e logs de auditoria de um conceito específico.
    """
    try:
        # Busca todas as versões do conceito
        stmt_v = select(SVRVersion).where(
            and_(
                SVRVersion.tenant_id == current_user.tenant_id,
                SVRVersion.concept_id == concept_id
            )
        ).order_by(SVRVersion.criado_em.desc())
        res_v = await db.execute(stmt_v)
        versions = res_v.scalars().all()

        # Busca a matriz de compatibilidade vigente
        stmt_m = select(SVRCompatibilityMatrix).where(
            and_(
                SVRCompatibilityMatrix.tenant_id == current_user.tenant_id,
                SVRCompatibilityMatrix.concept_id == concept_id
            )
        ).order_by(SVRCompatibilityMatrix.data_vigencia.desc())
        res_m = await db.execute(stmt_m)
        matrix = res_m.scalars().all()

        # Busca histórico de auditorias
        stmt_a = select(SVRAuditLog).where(
            and_(
                SVRAuditLog.tenant_id == current_user.tenant_id,
                SVRAuditLog.concept_id == concept_id
            )
        ).order_by(SVRAuditLog.criado_em.desc())
        res_a = await db.execute(stmt_a)
        audits = res_a.scalars().all()

        return {
            "concept_id": concept_id,
            "versions": [
                {
                    "id": str(v.id),
                    "semantic_version": v.semantic_version,
                    "mapping_version": v.mapping_version,
                    "blueprint_version": v.blueprint_version,
                    "autor": v.autor,
                    "motivo": v.motivo,
                    "criado_em": v.criado_em.isoformat(),
                    "snapshot": v.snapshot
                } for v in versions
            ],
            "compatibility": [
                {
                    "semantic_version": m.semantic_version,
                    "mapping_version": m.mapping_version,
                    "blueprint_version": m.blueprint_version,
                    "status": m.status,
                    "data_vigencia": m.data_vigencia.isoformat(),
                    "data_expiracao": m.data_expiracao.isoformat() if m.data_expiracao else None,
                    "motivo": m.motivo_alteracao,
                    "impacto": m.impacto
                } for m in matrix
            ],
            "audits": [
                {
                    "id": str(a.id),
                    "action": a.action_type,
                    "user": a.usuario,
                    "time": a.criado_em.isoformat(),
                    "version_before": a.versao_anterior,
                    "version_after": a.versao_nova,
                    "reason": a.motivo,
                    "details": a.detalhes
                } for a in audits
            ]
        }
    except Exception as exc:
        logger.error("[SVR Router] Erro ao buscar histórico: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recuperar histórico do SVR: {exc}"
        )


@router.post("/concepts/register", status_code=status.HTTP_201_CREATED)
async def register_concept(
    payload: ConceptRegisterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Registra uma nova versão de conceito semântico/físico no SVR.
    """
    try:
        version_rec = await svr_service.register_concept_version(
            db=db,
            tenant_id=current_user.tenant_id,
            concept_id=payload.concept_id,
            concept_type=payload.concept_type,
            semantic_version=payload.semantic_version,
            mapping_version=payload.mapping_version,
            snapshot=payload.snapshot,
            autor=current_user.email,
            motivo=payload.motivo,
            impacto=payload.impacto,
            blueprint_version=payload.blueprint_version
        )
        return {
            "success": True,
            "version_id": str(version_rec.id),
            "concept_id": payload.concept_id,
            "semantic_version": payload.semantic_version,
            "mapping_version": payload.mapping_version
        }
    except Exception as exc:
        logger.error("[SVR Router] Erro ao registrar conceito: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar nova versão no SVR: {exc}"
        )


@router.post("/concepts/deprecate", status_code=status.HTTP_200_OK)
async def deprecate_concept_version(
    payload: ConceptDeprecateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Altera o status de depreciação de uma versão na matriz de compatibilidade.
    """
    success = await svr_service.set_version_status(
        db=db,
        tenant_id=current_user.tenant_id,
        concept_id=payload.concept_id,
        semantic_version=payload.semantic_version,
        mapping_version=payload.mapping_version,
        status=payload.status,
        autor=current_user.email,
        motivo=payload.motivo
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível alterar o status da versão. Verifique se o conceito e versão existem."
        )
    return {"success": True, "concept_id": payload.concept_id, "status": payload.status}


@router.post("/migration/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_migration(
    payload: MigrationEvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Simula e avalia o impacto de migração para uma nova versão de conceito corporativo.
    Retorna o relatório de impacto detalhado.
    """
    report = await svr_migration.evaluate_migration_impact(
        db=db,
        tenant_id=current_user.tenant_id,
        concept_id=payload.concept_id,
        new_semantic_version=payload.new_semantic_version,
        new_mapping_version=payload.new_mapping_version
    )
    if "error" in report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=report["error"]
        )
    return report
