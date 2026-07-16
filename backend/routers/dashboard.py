"""
LuminaAI — Dashboard Router
----------------------------
Endpoints de controle e streaming de eventos (SSE) para o
Live Dashboard Runtime. Garante governança Multi-Tenant e auditoria.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User, UserRole
from routers.dependencies import get_current_user, enforce_password_change
from services.data_platform.event_engine import event_engine
from services.data_platform.live_dashboard_runtime import live_dashboard_runtime

logger = logging.getLogger("luminaai.routers.dashboard")

router = APIRouter(
    prefix="/dashboard",
    tags=["📊 Live Dashboard Runtime"],
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
    # ── 1. Controle de Permissões e Multi-Tenant ──
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
        # Inscreve a fila de eventos do cliente conectado no Event Engine
        queue = await event_engine.subscribe(tenant_id)
        
        # Envia evento de boas-vindas para validar a conexão aberta
        welcome_event = {
            "event_type": "CONNECTED",
            "timestamp": json.dumps(datetime.now().isoformat()) if hasattr(datetime, "now") else "",
            "message": "Conectado com sucesso ao Event Engine do LuminaAI."
        }
        yield f"data: {json.dumps(welcome_event)}\n\n"

        try:
            while True:
                # Aguarda reativamente novos eventos publicados
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            logger.info("[DashboardRouter] Conexão SSE cancelada para o usuário %s", current_user.id)
        finally:
            # Garante a desinscrição para evitar vazamento de memória
            await event_engine.unsubscribe(tenant_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no", # Previne buffering do Nginx
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
    # ── 1. Controle de Permissões e Multi-Tenant ──
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Tenant_id inconsistente com o usuário autenticado.",
        )

    try:
        # Dispara Smart Refresh reativo e recupera o patch de atualização
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
    # Se não for admin, força o tenant_id para o do próprio usuário
    target_tenant = tenant_id
    if current_user.role != UserRole.ADMIN:
        target_tenant = current_user.tenant_id
        
    return live_dashboard_runtime.get_telemetry_report(target_tenant)
