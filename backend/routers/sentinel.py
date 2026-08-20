"""
LuminaAI — Router do Sentinela de Anomalias (IA Autônoma)
---------------------------------------------------------
Fornece inteligência proativa sobre riscos de churn, ruptura de estoque e desempenho de filiais.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from routers.dependencies import get_current_user
from models.user import User
from services.sentinel_anomaly_service import (
    run_sentinel_anomalies_scan,
    get_anomaly_investigation_detail,
)

router = APIRouter(prefix="/api/v1/sentinel", tags=["Sentinel Anomaly Detection"])


@router.get("/anomalies")
async def get_sentinel_anomalies(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna a lista de anomalias detectadas autonomamente pelo Sentinela LuminaAI.
    """
    anomalies = await run_sentinel_anomalies_scan()
    return {
        "success": True,
        "total_anomalias": len(anomalies),
        "data": anomalies,
    }


@router.get("/investigate")
async def get_sentinel_investigation_detail(
    categoria: str = Query(..., description="Categoria da anomalia (ex: CLIENTE_VIP_CHURN, ESTOQUE_RUPTURA)"),
    codigo: str = Query(..., description="Código da entidade investigada (ex: codcli, codprod, filial)"),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna o dossiê detalhado e aprofundado para investigação de uma anomalia.
    """
    detail = await get_anomaly_investigation_detail(categoria=categoria, codigo=codigo)
    return {
        "success": True,
        "data": detail,
    }

