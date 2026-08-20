"""
LuminaAI — Event Engine
-----------------------
Orquestrador central de pub/sub assíncrono para eventos em tempo real
no Live Dashboard Runtime. Garante isolamento estrito de Multi-Tenant.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Set

logger = logging.getLogger("luminaai.data_platform.event_engine")


class EventEngine:
    """
    Motor de Eventos responsável por notificar dinamicamente as conexões
    ativas sobre modificações na Data Platform ou nos pacotes analíticos.
    """

    def __init__(self):
        # Mapeia tenant_id -> conjunto de filas de escuta ativas
        self._listeners: Dict[uuid.UUID, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._event_history: list[Dict[str, Any]] = [] # Audit trail básico de eventos

    async def subscribe(self, tenant_id: uuid.UUID) -> asyncio.Queue:
        """
        Inscreve um cliente para escutar eventos em tempo real de um Tenant específico.
        """
        async with self._lock:
            if tenant_id not in self._listeners:
                self._listeners[tenant_id] = set()
            q = asyncio.Queue(maxsize=200)
            self._listeners[tenant_id].add(q)
            logger.info(
                "[EventEngine] Novo ouvinte registrado | tenant=%s | total_ouvintes=%d",
                tenant_id,
                len(self._listeners[tenant_id]),
            )
            return q

    async def unsubscribe(self, tenant_id: uuid.UUID, queue: asyncio.Queue) -> None:
        """
        Remove a inscrição do cliente da escuta de eventos do Tenant.
        """
        async with self._lock:
            if tenant_id in self._listeners:
                self._listeners[tenant_id].discard(queue)
                if not self._listeners[tenant_id]:
                    del self._listeners[tenant_id]
                logger.info("[EventEngine] Ouvinte removido | tenant=%s", tenant_id)

    async def publish(self, tenant_id: uuid.UUID, event_type: str, data: Dict[str, Any]) -> int:
        """
        Publica um evento analítico para todos os clientes inscritos do Tenant correspondente.
        Garante isolamento Multi-Tenant estrito.
        """
        async with self._lock:
            # Tipos de eventos oficiais permitidos
            valid_events = {
                "SYNC_FINISHED",
                "DATASET_UPDATED",
                "RUNTIME_UPDATED",
                "DASHBOARD_UPDATED",
                "PACKAGE_UPDATED",
                "TEMPLATE_CHANGED",
                "VERSION_CREATED",
            }
            if event_type not in valid_events:
                logger.warning("[EventEngine] Tentativa de publicar tipo de evento inválido: %s", event_type)
                return 0

            listeners = self._listeners.get(tenant_id, set())
            
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "tenant_id": str(tenant_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": data,
            }

            # Registra no audit trail em memória
            self._event_history.append(event)
            if len(self._event_history) > 1000:
                self._event_history.pop(0) # Mantém tamanho sob controle de memória

            if not listeners:
                logger.debug("[EventEngine] Nenhum ouvinte ativo para tenant=%s", tenant_id)
                return 0

            delivered = 0
            for queue in list(listeners):
                try:
                    if queue.full():
                        queue.get_nowait() # Descarta evento mais antigo se a fila encher
                    queue.put_nowait(event)
                    delivered += 1
                except Exception as e:
                    logger.error("[EventEngine] Falha ao repassar evento para ouvinte: %s", e)

            logger.info(
                "[EventEngine] Evento publicado | tipo=%s | tenant=%s | entregue_a=%d_clientes",
                event_type,
                tenant_id,
                delivered,
            )
            return delivered

    def get_event_history(self, tenant_id: uuid.UUID | None = None) -> list[Dict[str, Any]]:
        """
        Retorna o histórico de eventos auditáveis, opcionalmente filtrados por Tenant.
        """
        if tenant_id:
            tenant_str = str(tenant_id)
            return [e for e in self._event_history if e["tenant_id"] == tenant_str]
        return list(self._event_history)


# Export singleton
event_engine = EventEngine()
