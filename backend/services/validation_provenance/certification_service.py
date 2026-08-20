"""
LuminaAI Governed Certification Service
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from contracts.validation_provenance_v2 import (
    AnalyticalClaimValidationV2,
    AnalyticalFactV2,
    CertificationEnvelopeV2,
    PublicProvenanceSummaryV2,
    ResponseCertificationV2,
    ResultCertificationV2,
    ValidationStatus,
)


class CertificationService:
    @staticmethod
    def certify(
        tenant_id: UUID,
        user_id: UUID,
        request_id: str,
        result_payload: Dict,
        response_draft_text: Optional[str],
        claim_validation: AnalyticalClaimValidationV2,
        facts: List[AnalyticalFactV2],
        public_summary: PublicProvenanceSummaryV2,
        overall_status: ValidationStatus,
        warnings: List[str],
        critical_issues: List[str],
        orchestration_run_id: Optional[str] = None,
        query_fingerprint: Optional[str] = None,
        tenant_proof_checksum: str = "",
    ) -> CertificationEnvelopeV2:
        cert_id = uuid4()
        now_iso = datetime.now(timezone.utc).isoformat()
        result_checksum = hashlib.sha256(json.dumps(result_payload, sort_keys=True).encode("utf-8")).hexdigest()

        # Build ResultCertificationV2
        res_cert_content = f"{tenant_id}:{request_id}:{result_checksum}:{query_fingerprint}:{tenant_proof_checksum}:{overall_status}"
        res_cert_ck = hashlib.sha256(res_cert_content.encode("utf-8")).hexdigest()
        result_cert = ResultCertificationV2(
            certification_id=cert_id,
            tenant_id=tenant_id,
            request_id=request_id,
            result_checksum=result_checksum,
            query_fingerprint=query_fingerprint,
            tenant_proof_checksum=tenant_proof_checksum,
            status=overall_status,
            certified_at=now_iso,
            checksum=res_cert_ck,
        )

        # Build ResponseCertificationV2
        draft_ck = hashlib.sha256((response_draft_text or "").encode("utf-8")).hexdigest()
        resp_cert_content = f"{cert_id}:{tenant_id}:{request_id}:{draft_ck}:{claim_validation.validation_status}"
        resp_cert_ck = hashlib.sha256(resp_cert_content.encode("utf-8")).hexdigest()
        response_cert = ResponseCertificationV2(
            certification_id=cert_id,
            result_certification_id=cert_id,
            tenant_id=tenant_id,
            request_id=request_id,
            response_draft_checksum=draft_ck,
            claim_validation=claim_validation,
            status=claim_validation.validation_status if overall_status == ValidationStatus.VALID else overall_status,
            certified_at=now_iso,
            checksum=resp_cert_ck,
        )

        # Build Envelope Checksum
        env_content = f"{cert_id}:{tenant_id}:{request_id}:{res_cert_ck}:{resp_cert_ck}:{overall_status}"
        env_ck = hashlib.sha256(env_content.encode("utf-8")).hexdigest()

        return CertificationEnvelopeV2(
            contract_version="lumina.validation-provenance/1.0",
            certification_id=cert_id,
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            orchestration_run_id=orchestration_run_id,
            result_certification=result_cert,
            response_certification=response_cert,
            facts=facts,
            public_summary=public_summary,
            overall_status=overall_status,
            warnings=warnings,
            critical_issues=critical_issues,
            policy_version="1.0.0",
            validator_versions={"pipeline": "1.0.0"},
            superseded_by_id=None,
            created_at=now_iso,
            checksum=env_ck,
        )
