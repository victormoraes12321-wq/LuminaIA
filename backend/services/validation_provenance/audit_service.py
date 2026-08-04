"""
LuminaAI Governed Validation Audit Service
Version: lumina.validation-provenance/1.0
"""

from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID, uuid4

from contracts.validation_provenance_v2 import (
    ValidationAuditEventV2,
    ValidationSeverity,
)


class ValidationAuditService:
    @staticmethod
    def create_audit_event(
        tenant_id: UUID,
        user_id: UUID,
        event_type: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.INFO,
        certification_id: Optional[UUID] = None,
        details: Optional[Dict[str, str]] = None,
    ) -> ValidationAuditEventV2:
        return ValidationAuditEventV2(
            event_id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            certification_id=certification_id,
            severity=severity,
            message=message,
            details=details or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
