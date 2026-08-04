"""
LuminaAI Governed Validation Pipeline
Version: lumina.validation-provenance/1.0
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from contracts.validation_provenance_v2 import (
    CertificationEnvelopeV2,
    ValidationCheckResultV2,
    ValidationContextV2,
    ValidationIssueV2,
    ValidationPolicyV2,
    ValidationRequestV2,
    ValidationRunV2,
    ValidationSeverity,
    ValidationStage,
    ValidationStageResultV2,
    ValidationStatus,
)
from .certification_service import CertificationService
from .claim_service import AnalyticalClaimValidationService
from .fact_service import AnalyticalFactService
from .policy_service import ValidationPolicyService
from .provenance_service import ProvenanceGraphService
from .public_provenance_service import PublicProvenanceService
from .validators.registry import get_validator


STAGE_ORDER: List[ValidationStage] = [
    ValidationStage.CONTRACT,
    ValidationStage.SECURITY,
    ValidationStage.TENANT_ISOLATION,
    ValidationStage.AUTHORIZATION,
    ValidationStage.AUTHORITY,
    ValidationStage.SEMANTIC,
    ValidationStage.TEMPORAL,
    ValidationStage.METRIC,
    ValidationStage.NUMERIC,
    ValidationStage.COMPARISON,
    ValidationStage.SHAPE,
    ValidationStage.COMPLETENESS,
    ValidationStage.FRESHNESS,
    ValidationStage.TOOL_RESULT,
    ValidationStage.ORCHESTRATION,
    ValidationStage.CLAIMS,
    ValidationStage.PROVENANCE,
    ValidationStage.PRESENTATION,
]


class GovernedValidationPipeline:
    def __init__(self, policy: Optional[ValidationPolicyV2] = None):
        self.policy = policy

    async def execute(self, request: ValidationRequestV2) -> CertificationEnvelopeV2:
        start_time = time.perf_counter()
        context = request.context
        tenant_id = context.tenant_id
        user_id = context.user_id
        request_id = context.request_id

        active_policy = self.policy or ValidationPolicyService.get_default_policy(tenant_id)
        stage_validator_map: Dict[ValidationStage, List] = {}
        for vdef in active_policy.validators:
            stage_validator_map.setdefault(vdef.stage, []).append(vdef)

        stage_results: List[ValidationStageResultV2] = []
        all_issues: List[ValidationIssueV2] = []
        critical_issues: List[str] = []
        warnings: List[str] = []
        pipeline_failed = False

        # Execute 18 stages in strict sequence
        for stage in STAGE_ORDER:
            if pipeline_failed and active_policy.fail_fast_on_critical:
                stage_results.append(
                    ValidationStageResultV2(
                        stage=stage,
                        status=ValidationStatus.SKIPPED_DEPENDENCY_FAILED,
                        checks=[],
                        issues=[],
                        execution_time_ms=0.0,
                    )
                )
                continue

            stage_start = time.perf_counter()
            stage_checks: List[ValidationCheckResultV2] = []
            stage_issues: List[ValidationIssueV2] = []
            stage_status = ValidationStatus.VALID

            # Execute all configured validators for this stage
            if stage in stage_validator_map:
                for vdef in stage_validator_map[stage]:
                    if vdef.enabled:
                        try:
                            validator_inst = get_validator(vdef.validator_id)
                            check_res = await validator_inst.validate(
                                context=context,
                                payload=request.result_payload,
                                proposed_facts=request.proposed_facts,
                                proposed_claims=request.proposed_claims,
                                tenant_proof=request.tenant_proof,
                            )
                            stage_checks.append(check_res)
                            stage_issues.extend(check_res.issues)
                            if check_res.status in (ValidationStatus.INVALID, ValidationStatus.BLOCKED):
                                stage_status = check_res.status
                            elif check_res.status == ValidationStatus.VALID_WITH_WARNINGS and stage_status == ValidationStatus.VALID:
                                stage_status = ValidationStatus.VALID_WITH_WARNINGS
                            elif check_res.status == ValidationStatus.PARTIAL and stage_status == ValidationStatus.VALID:
                                stage_status = ValidationStatus.PARTIAL
                        except KeyError:
                            pass

            stage_time_ms = (time.perf_counter() - stage_start) * 1000.0
            stage_results.append(
                ValidationStageResultV2(
                    stage=stage,
                    status=stage_status,
                    checks=stage_checks,
                    issues=stage_issues,
                    execution_time_ms=stage_time_ms,
                )
            )

            all_issues.extend(stage_issues)
            for iss in stage_issues:
                if iss.severity == ValidationSeverity.CRITICAL:
                    critical_issues.append(f"[{stage.value}] {iss.message}")
                    pipeline_failed = True
                elif iss.severity == ValidationSeverity.ERROR:
                    critical_issues.append(f"[{stage.value}] {iss.message}")
                elif iss.severity == ValidationSeverity.WARNING:
                    warnings.append(f"[{stage.value}] {iss.message}")

        # Materialize facts
        fact_set = AnalyticalFactService.extract_facts(
            tenant_id=tenant_id,
            result_payload=request.result_payload,
            proposed_facts=request.proposed_facts,
            tenant_proof=request.tenant_proof,
        )

        # Validate claims and bindings
        claim_validation = AnalyticalClaimValidationService.validate_claims(
            tenant_id=tenant_id,
            proposed_claims=request.proposed_claims,
            fact_set=fact_set,
        )

        # Build provenance DAG
        query_fp = request.result_payload.get("query_fingerprint")
        proof_ck = hashlib.sha256(
            json.dumps(request.tenant_proof or {"tenant_id": str(tenant_id)}, sort_keys=True).encode("utf-8")
        ).hexdigest()

        graph = ProvenanceGraphService.build_graph(
            tenant_id=tenant_id,
            request_id=request_id,
            facts=fact_set.facts,
            claims=claim_validation.claims,
            query_fingerprint=query_fp,
            tenant_proof_checksum=proof_ck,
        )

        # Determine overall status
        if critical_issues:
            overall_status = ValidationStatus.BLOCKED if any(i.severity == ValidationSeverity.CRITICAL for i in all_issues) else ValidationStatus.INVALID
        elif not claim_validation.all_numeric_claims_bound:
            overall_status = ValidationStatus.INVALID
        elif warnings:
            overall_status = ValidationStatus.VALID_WITH_WARNINGS
        else:
            overall_status = ValidationStatus.VALID

        # Build public summary
        public_summary = PublicProvenanceService.build_public_summary(
            facts=fact_set.facts,
            status=overall_status,
            warnings=warnings,
            certification_checksum="",
        )

        # Produce Certification Envelope
        envelope = CertificationService.certify(
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            result_payload=request.result_payload,
            response_draft_text=request.response_draft_text,
            claim_validation=claim_validation,
            facts=fact_set.facts,
            public_summary=public_summary,
            overall_status=overall_status,
            warnings=warnings,
            critical_issues=critical_issues,
            orchestration_run_id=context.orchestration_run_id,
            query_fingerprint=query_fp,
            tenant_proof_checksum=proof_ck,
        )

        public_summary.certification_checksum = envelope.checksum
        envelope.public_summary = public_summary

        return envelope
