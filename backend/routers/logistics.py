"""
LuminaAI — Router de Logística, Filiais, Rebalanceamento e Análise Geográfica
----------------------------------------------------------------------------
Endpoints protegidos para apoio operacional e tomada de decisão logística.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from routers.dependencies import get_current_user
from models.user import User
from services.logistics_inventory_service import (
    get_inventory_branch_rebalancing,
    get_regional_sales_heatmap,
    get_cfop_movement_distribution,
)

router = APIRouter(prefix="/api/v1/logistics", tags=["Logistics & Operations"])


@router.get("/rebalancing")
async def list_branch_rebalancing(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna oportunidades de rebalanceamento de estoque entre filiais.
    """
    suggestions = await get_inventory_branch_rebalancing(limit=limit)
    return {
        "success": True,
        "total_oportunidades": len(suggestions),
        "data": suggestions,
    }


@router.get("/regional-heatmap")
async def get_regional_heatmap(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna o mapa de calor e ranking de faturamento por Município, UF e Praça.
    """
    heatmap = await get_regional_sales_heatmap(limit=limit)
    return {
        "success": True,
        "data": heatmap,
    }


@router.get("/cfop-distribution")
async def get_cfop_distribution(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna a segregação analítica dos movimentos por CFOP (vendas reais vs transferências).
    """
    distribution = await get_cfop_movement_distribution()
    return {
        "success": True,
        "data": distribution,
    }
