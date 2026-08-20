"""
LuminaAI — Dashboard Router
----------------------------
Endpoints de controle e streaming de eventos (SSE) para o
Live Dashboard Runtime e métricas executivas em tempo real.
Garante governança Multi-Tenant e auditoria.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User, UserRole
from routers.dependencies import get_current_user, enforce_password_change
from services.data_platform.event_engine import event_engine
from services.data_platform.live_dashboard_runtime import live_dashboard_runtime
from services.executive_metrics_service import get_executive_metrics

logger = logging.getLogger("luminaai.routers.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["📊 Live Dashboard Runtime"],
)


@router.get(
    "/executive-metrics",
    summary="Métricas Executivas em Tempo Real (PostgreSQL Clone)",
    description="Retorna KPIs, evolução temporal, rankings e insights agregados diretamente da base analítica real.",
)
async def fetch_executive_metrics_endpoint(
    start_date: Optional[str] = Query(None, description="Data inicial no formato YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Data final no formato YYYY-MM-DD"),
    filial: Optional[str] = Query(None, description="Filial ou lista de filiais separadas por vírgula"),
    rca: Optional[str] = Query(None, description="Código ou nome do vendedor"),
    codprod: Optional[str] = Query(None, description="Código ou descrição do produto"),
    codcli: Optional[str] = Query(None, description="Código ou razão social do cliente"),
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Agregação analítica segura e em tempo real para a Dashboard Executiva.
    """
    try:
        data = await get_executive_metrics(
            tenant_id=str(current_user.tenant_id),
            start_date=start_date,
            end_date=end_date,
            filial=filial,
            rca=rca,
            codprod=codprod,
            codcli=codcli,
        )

        # ── Injeta o last_sync real do tenant para exibição consistente entre telas ──
        # A tela de Configurações lê de sync_config.last_sync; a Dashboard deve usar a mesma fonte.
        try:
            from sqlalchemy import select
            from models.tenant import Tenant
            from datetime import timezone
            import json as _json

            stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
            res = await db.execute(stmt)
            tenant_obj = res.scalar_one_or_none()
            if tenant_obj:
                sc = tenant_obj.sync_config or {}
                if isinstance(sc, str):
                    try:
                        sc = _json.loads(sc)
                    except Exception:
                        sc = {}
                last_sync_raw = sc.get("last_sync")
                if last_sync_raw:
                    from datetime import datetime, timezone, timedelta
                    try:
                        # Parse o ISO string e converte para horário de Brasília
                        dt = datetime.fromisoformat(last_sync_raw.replace("Z", "+00:00"))
                        brt = dt.astimezone(timezone(timedelta(hours=-3)))
                        freshness_str = brt.strftime("%d/%m/%Y, %H:%M") + " (PostgreSQL Clone)"
                    except Exception:
                        freshness_str = last_sync_raw + " (PostgreSQL Clone)"
                    # Injeta no metadata para que a dashboard exiba o horário correto
                    if "metadata" in data:
                        data["metadata"]["freshness"] = freshness_str
                        data["metadata"]["last_sync_iso"] = last_sync_raw
        except Exception as sync_exc:
            logger.debug("[DashboardRouter] Não foi possível injetar last_sync no freshness: %s", sync_exc)

        return {
            "success": True,
            "data": data,
        }
    except Exception as err:
        logger.exception("[DashboardRouter] Erro ao buscar métricas executivas: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar métricas analíticas: {err}",
        )


@router.get(
    "/events",
    summary="Assinatura Server-Sent Events (SSE) para Live Updates",
    description="Permite que o frontend assine e receba atualizações reativas parciais (Diff Rendering) do Dashboard Runtime.",
)
async def listen_dashboard_events(
    tenant_id: uuid.UUID = Query(..., description="ID da empresa (Tenant)"),
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
) -> StreamingResponse:
    """
    Estabelece canal de streaming SSE isolado logicamente por Tenant.
    """
    if current_user.tenant_id != tenant_id:
        logger.warning(
            "[DashboardRouter] Tentativa de escuta cross-tenant: user=%s | tenant=%s | target=%s",
            current_user.id,
            current_user.tenant_id,
            tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Você só pode receber atualizações do seu próprio Tenant.",
        )

    async def event_generator():
        queue = await event_engine.subscribe(tenant_id)
        welcome_event = {
            "event_type": "CONNECTED",
            "message": "Conectado com sucesso ao Event Engine do LuminaAI."
        }
        yield f"data: {json.dumps(welcome_event)}\n\n"

        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            logger.info("[DashboardRouter] Conexão SSE cancelada para o usuário %s", current_user.id)
        finally:
            await event_engine.unsubscribe(tenant_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post(
    "/refresh",
    summary="Forçar Smart Refresh de um Painel Analítico",
    description="Atualiza manualmente os datasets do pacote sem reconstruir a lógica de IA ou Blueprint.",
)
async def force_dashboard_refresh(
    package_id: uuid.UUID,
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Força re-execução do Smart Refresh reativo para o pacote informado.
    """
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Tenant_id inconsistente com o usuário autenticado.",
        )

    try:
        event_data = await live_dashboard_runtime.refresh_runtime(
            tenant_id=tenant_id,
            package_id=package_id,
            db=db
        )
        return {
            "status": "success",
            "message": "Smart Refresh finalizado e despachado com sucesso.",
            "data": event_data
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as err:
        logger.exception("[DashboardRouter] Erro no Smart Refresh manual: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao re-processar runtime do dashboard: {err}"
        )


@router.get(
    "/telemetry",
    summary="Relatório de Observabilidade de Renderização",
    description="Retorna dados agregados de performance de diff e quantidade de renderizações evitadas.",
)
async def get_dashboard_telemetry(
    tenant_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    _pwd_guard: User = Depends(enforce_password_change),
) -> list[Dict[str, Any]]:
    """
    Retorna logs históricos de performance da IA e do Live Runtime.
    Apenas administradores podem ler telemetria global.
    """
    target_tenant = tenant_id
    if current_user.role != UserRole.ADMIN:
        target_tenant = current_user.tenant_id
        
    return live_dashboard_runtime.get_telemetry_report(target_tenant)
