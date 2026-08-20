"""
LuminaAI — Router do Sentinela de Anomalias (IA Autônoma)
---------------------------------------------------------
Fornece inteligência proativa sobre riscos de churn, ruptura de estoque e desempenho de filiais.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from routers.dependencies import get_current_user
from models.user import User
from services.sentinel_anomaly_service import run_sentinel_anomalies_scan

router = APIRouter(prefix="/api/v1/sentinel", tags=["Sentinel Anomaly Detection"])


@router.get("/anomalies")
async def get_sentinel_anomalies(
    current_user: User = Depends(get_current_user),
):
    """
    Retorna a lista de anomalias detectadas autonomamente pelo Sentinela LuminaAI.
    """
    anomalies = await run_sentinel_anomalies_scan(tenant_id=str(current_user.tenant_id))
    return {
        "success": True,
        "total_anomalias": len(anomalies),
        "data": anomalies,
    }
