"""
LuminaAI — Smart Cache Audit Service
lumina.smart-cache-materialization/1.0
"""
import logging
from typing import Dict, Optional
from pydantic import JsonValue
from .repository import SmartCacheRepository

logger = logging.getLogger(__name__)


class SmartCacheAuditService:
    def __init__(self, repository: SmartCacheRepository):
        self.repository = repository

    async def log_event(
        self,
        tenant_id: str,
        event_type: str,
        reason_code: str,
        cache_key_checksum: Optional[str] = None,
        user_id: Optional[str] = None,
        decision: Optional[str] = None,
        details: Optional[Dict[str, JsonValue]] = None,
    ):
        await self.repository.log_event(
            tenant_id=tenant_id,
            event_type=event_type,
            reason_code=reason_code,
            cache_key_checksum=cache_key_checksum,
            user_id=user_id,
            decision=decision,
            details=details,
        )
