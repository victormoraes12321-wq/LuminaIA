"""
LuminaAI - Business Knowledge API Router
----------------------------------------
REST endpoints for Business Knowledge Engine consultation, governance and rollback.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from routers.dependencies import enforce_password_change
from services.business.business_knowledge_engine import business_knowledge_engine

logger = logging.getLogger("luminaai.routers.business_knowledge")

router = APIRouter(
    prefix="/api/v1/business-knowledge",
    tags=["Business Knowledge Engine"],
)


class ConceptResponse(BaseModel):
    id: str
    nome: str
    descricao: str
    categoria: str
    area: str
    departamento: str
    definicao_oficial: str
    unidade: str
    tipo: str
    origem: str
    owner: str
    versao: int
    sinonimos: list[str]
    status: str

    model_config = {"from_attributes": True}


class KPIResponse(BaseModel):
    id: str
    nome: str
    descricao: str
    categoria: str
    area: str
    objetivo: str
    formula_oficial: str
    periodicidade: str
    formato: str
    precisao: int
    unidade: str
    limites: dict
    faixas: dict
    benchmark: dict
    responsavel: str
    status: str
    versao: int
    tags: list[str]

    model_config = {"from_attributes": True}


class FormulaResponse(BaseModel):
    id: str
    nome: str
    formula: str
    entradas: list[dict]
    saidas: list[dict]
    pre_requisitos: list[str]
    dependencias: list[str]
    validacoes: list[str]
    status: str
    versao: int

    model_config = {"from_attributes": True}


class ObservabilityResponse(BaseModel):
    concepts_active_count: int
    kpis_active_count: int
    formulas_active_count: int
    relationships_count: int
    governance_logs_count: int
    contexts_available: int


class ImpactResponse(BaseModel):
    alvo: str
    total_impactos: int
    kpis_impactados: list[str]
    formulas_impactadas: list[str]
    packages_impactados: list[dict]
    blueprints_impactados: list[dict]
    grau_severidade: str


class RollbackRequest(BaseModel):
    estrutura_tipo: str = Field(..., description="Tipo do elemento: CONCEPT, KPI ou FORMULA")
    estrutura_nome: str = Field(..., description="Nome oficial do elemento a reverter")
    target_version: int = Field(..., description="Versao para a qual deseja restaurar")


class RollbackResponse(BaseModel):
    success: bool
    estrutura_tipo: str
    estrutura_nome: str
    versao_anterior: int
    versao_atual: int
    revertido_para_versao: int
    autor: str


class RegisterConceptRequest(BaseModel):
    nome: str
    descricao: str
    categoria: str = "Geral"
    area: str = "Geral"
    departamento: str = "Geral"
    definicao_oficial: str | None = None
    unidade: str = ""
    tipo: str = "Metrica"
    origem: str = "Manual"
    owner: str = "Negocio"
    sinonimos: list[str] = Field(default_factory=list)
    abreviacoes: list[str] = Field(default_factory=list)
    exemplos: list[str] = Field(default_factory=list)
    observacoes: str | None = None


class RegisterKPIRequest(BaseModel):
    nome: str
    descricao: str
    categoria: str = "Geral"
    area: str = "Geral"
    objetivo: str
    formula_oficial: str
    periodicidade: str = "Mensal"
    formato: str = "number"
    precisao: int = 2
    unidade: str = ""
    limites: dict = Field(default_factory=dict)
    faixas: dict = Field(default_factory=dict)
    benchmark: dict = Field(default_factory=dict)
    responsavel: str = "Gestor"
    tags: list[str] = Field(default_factory=list)


@router.get(
    "/dictionary",
    response_model=list[ConceptResponse],
    summary="Listar conceitos do dicionario",
)
async def list_dictionary_concepts(
    current_user: Annotated[User, Depends(enforce_password_change)],
    categoria: str | None = Query(None),
    area: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[ConceptResponse]:
    """Return active concepts for the authenticated tenant."""
    concepts = await business_knowledge_engine.dictionary.list_concepts(
        tenant_id=current_user.tenant_id,
        db=db,
        categoria=categoria,
        area=area,
    )
    return [ConceptResponse.model_validate(c) for c in concepts]


@router.post(
    "/dictionary",
    response_model=ConceptResponse,
    summary="Registrar/Atualizar conceito de negocio",
)
async def register_concept(
    body: RegisterConceptRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> ConceptResponse:
    """Register or update a governed business concept."""
    concept = await business_knowledge_engine.dictionary.register_concept(
        tenant_id=current_user.tenant_id,
        concept_data=body.model_dump(),
        autor=current_user.email,
        db=db,
    )
    return ConceptResponse.model_validate(concept)


@router.get(
    "/kpis",
    response_model=list[KPIResponse],
    summary="Listar KPIs registrados",
)
async def list_registered_kpis(
    current_user: Annotated[User, Depends(enforce_password_change)],
    categoria: str | None = Query(None),
    area: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[KPIResponse]:
    """Return official KPIs for the authenticated tenant."""
    kpis = await business_knowledge_engine.kpi_registry.list_kpis(
        tenant_id=current_user.tenant_id,
        db=db,
        categoria=categoria,
        area=area,
    )
    return [KPIResponse.model_validate(k) for k in kpis]


@router.post(
    "/kpis",
    response_model=KPIResponse,
    summary="Registrar/Atualizar KPI oficial",
)
async def register_kpi(
    body: RegisterKPIRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> KPIResponse:
    """Register or update an official KPI."""
    kpi = await business_knowledge_engine.kpi_registry.register_kpi(
        tenant_id=current_user.tenant_id,
        kpi_data=body.model_dump(),
        autor=current_user.email,
        db=db,
    )
    return KPIResponse.model_validate(kpi)


@router.get(
    "/formulas",
    response_model=list[FormulaResponse],
    summary="Listar formulas de BI",
)
async def list_formulas(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> list[FormulaResponse]:
    """Return active BI formulas."""
    formulas = await business_knowledge_engine.formula_engine.list_formulas(
        current_user.tenant_id,
        db,
    )
    return [FormulaResponse.model_validate(f) for f in formulas]


@router.get(
    "/observability",
    response_model=ObservabilityResponse,
    summary="Metricas de observabilidade do BKE",
)
async def get_observability(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> ObservabilityResponse:
    """Return counts for rules, KPIs, dependencies and audit logs."""
    obs = await business_knowledge_engine.get_observability_metrics(
        current_user.tenant_id,
        db,
    )
    return ObservabilityResponse(**obs)


@router.get(
    "/impact",
    response_model=ImpactResponse,
    summary="Analise de impacto de dependencia",
)
async def get_impact_analysis(
    current_user: Annotated[User, Depends(enforce_password_change)],
    target: str = Query(..., description="Nome do indicador ou formula a ser analisado"),
    db: AsyncSession = Depends(get_db),
) -> ImpactResponse:
    """Identify side effects if a rule or KPI changes."""
    impact = await business_knowledge_engine.dependency_engine.get_impact_analysis(
        tenant_id=current_user.tenant_id,
        element_name=target,
        db=db,
    )
    return ImpactResponse(**impact)


@router.post(
    "/rollback",
    response_model=RollbackResponse,
    summary="Executar rollback de versao",
)
async def execute_rollback(
    body: RollbackRequest,
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> RollbackResponse:
    """Atomically restore a governed element to a previous version."""
    try:
        res = await business_knowledge_engine.governance.rollback(
            tenant_id=current_user.tenant_id,
            estrutura_tipo=body.estrutura_tipo,
            estrutura_nome=body.estrutura_nome,
            target_version=body.target_version,
            autor=current_user.email,
            db=db,
        )
        return RollbackResponse(**res)
    except Exception as e:
        logger.error("[BKE Router] Erro no rollback: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/seed",
    response_model=dict,
    summary="Semear formulas e relacoes de BI padrao",
)
async def seed_bke(
    current_user: Annotated[User, Depends(enforce_password_change)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seed the default BI formulas and cause/effect relationships."""
    f_count = await business_knowledge_engine.formula_engine.seed_formulas(
        current_user.tenant_id,
        db,
    )
    r_count = await business_knowledge_engine.relationship_engine.seed_relationships(
        current_user.tenant_id,
        db,
    )

    from services.semantic_layer import sync_from_semantic_catalog

    await sync_from_semantic_catalog(str(current_user.tenant_id))

    return {
        "success": True,
        "formulas_seeded": f_count,
        "relationships_seeded": r_count,
    }
