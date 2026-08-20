"""Governed materialization build orchestration.

This service delegates every numerical operation to Safe Analytical PostgreSQL
and every certification decision to Validation & Provenance. It never compiles
SQL, reads Oracle, or publishes a snapshot automatically.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Protocol

from contracts.safe_analytical_postgresql_v2 import (
    AnalyticalExecutionResultV2,
    AnalyticalQuerySpecV2,
)
from contracts.smart_cache_materialization_v2 import (
    CertificationStatus,
    FreshnessStatus,
    MaterializationBuildStatus,
    MaterializationBuildV2,
    MaterializationSnapshotV2,
)
from contracts.validation_provenance_v2 import (
    CertificationEnvelopeV2,
    ValidationContextV2,
    ValidationRequestV2,
    ValidationStatus,
)
from services.safe_analytical_postgresql import SafeAnalyticalPostgreSQLService
from services.validation_provenance import GovernedValidationPipeline

from .repository import MaterializationRepository


logger = logging.getLogger(__name__)


class AnalyticalExecutor(Protocol):
    async def execute_query(
        self, spec: AnalyticalQuerySpecV2, tenant_id: str, user_id: str = "system"
    ) -> AnalyticalExecutionResultV2: ...


class ValidationExecutor(Protocol):
    async def execute(self, request: ValidationRequestV2) -> CertificationEnvelopeV2: ...


class GovernedMaterializationBuildService:
    def __init__(
        self,
        repository: MaterializationRepository,
        analytical_executor: AnalyticalExecutor | None = None,
        validation_executor: ValidationExecutor | None = None,
    ):
        self.repository = repository
        self.analytical_executor = analytical_executor or SafeAnalyticalPostgreSQLService()
        self.validation_executor = validation_executor or GovernedValidationPipeline()

    async def build_snapshot(
        self,
        *,
        tenant_id: str,
        user_id: str,
        definition_id: str,
        expected_lock_version: int,
        permissions: list[str],
        request_id: str,
        incremental: bool = False,
    ) -> tuple[MaterializationBuildV2, MaterializationSnapshotV2]:
        started = time.perf_counter()
        build_id = f"build_{uuid.uuid4().hex}"
        definition = await self.repository.get_definition(tenant_id, definition_id)
        if definition is None:
            raise ValueError("materialization definition not found for trusted tenant")
        if definition.lifecycle not in {"APPROVED", "PUBLISHED", "STALE"}:
            raise ValueError("definition is not eligible for a governed build")
        if "materialization:build" not in permissions:
            raise PermissionError("materialization:build permission is required")
        if incremental:
            watermark = str(definition.source_json.get("watermark", ""))
            if not watermark or watermark.lower() in {"unknown", "unverified"}:
                raise ValueError("incremental build requires a verified watermark")

        query_spec = AnalyticalQuerySpecV2.model_validate(definition.query_json)
        building = await self.repository.transition_definition(
            tenant_id,
            definition_id,
            definition.version,
            expected_lock_version=expected_lock_version,
            expected_lifecycle=definition.lifecycle,
            new_lifecycle="BUILDING",
        )
        try:
            analytical_result = await self.analytical_executor.execute_query(
                query_spec, tenant_id, user_id
            )
            if analytical_result.error is not None:
                raise RuntimeError("safe analytical execution returned an error")
            if not analytical_result.validation.tenant_isolation_verified:
                raise RuntimeError("safe analytical tenant proof is invalid")
            if analytical_result.statistics.truncated:
                raise RuntimeError("truncated analytical results cannot be materialized")

            validating = await self.repository.transition_definition(
                tenant_id,
                definition_id,
                definition.version,
                expected_lock_version=building.lock_version,
                expected_lifecycle="BUILDING",
                new_lifecycle="VALIDATING",
            )
            result_payload = analytical_result.model_dump(mode="json")
            result_payload["query_fingerprint"] = definition.query_fingerprint
            tenant_proof = {
                "tenant_id": tenant_id,
                "verified": True,
                "strategy": str(definition.source_json.get("tenant_strategy", "")),
            }
            envelope = await self.validation_executor.execute(
                ValidationRequestV2(
                    context=ValidationContextV2(
                        tenant_id=uuid.UUID(tenant_id),
                        user_id=uuid.UUID(user_id),
                        roles=["ADMIN"],
                        permissions=permissions,
                        request_id=request_id,
                    ),
                    result_payload=result_payload,
                    proposed_facts=[],
                    proposed_claims=[],
                    tenant_proof=tenant_proof,
                )
            )
            if envelope.overall_status is not ValidationStatus.VALID:
                raise RuntimeError("validation and provenance did not certify the snapshot as VALID")

            payload_serialized = json.dumps(
                result_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            )
            payload_checksum = hashlib.sha256(payload_serialized.encode("utf-8")).hexdigest()
            snapshot_id = f"snap_{uuid.uuid4().hex}"
            watermark = str(definition.source_json.get("watermark", ""))
            source_sync_version = str(definition.source_json.get("source_sync_version", ""))
            snapshot_material = {
                "snapshot_id": snapshot_id,
                "definition_id": definition_id,
                "tenant_id": tenant_id,
                "version": definition.version,
                "payload_checksum": payload_checksum,
                "certification_id": str(envelope.certification_id),
                "tenant_proof_id": envelope.result_certification.tenant_proof_checksum,
                "watermark": watermark,
            }
            checksum = hashlib.sha256(
                json.dumps(snapshot_material, sort_keys=True).encode("utf-8")
            ).hexdigest()
            snapshot_model = await self.repository.save_snapshot(
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                definition_id=definition_id,
                definition_version=definition.version,
                row_count=analytical_result.statistics.row_count,
                fact_count=len(envelope.facts),
                payload_size_bytes=len(payload_serialized.encode("utf-8")),
                certification_id=str(envelope.certification_id),
                certification_status=CertificationStatus.VALID.value,
                tenant_proof_id=envelope.result_certification.tenant_proof_checksum,
                watermark=watermark,
                source_sync_version=source_sync_version,
                payload_json=result_payload,
                payload_checksum=payload_checksum,
                checksum=checksum,
            )
            ready = await self.repository.transition_definition(
                tenant_id,
                definition_id,
                definition.version,
                expected_lock_version=validating.lock_version,
                expected_lifecycle="VALIDATING",
                new_lifecycle="READY",
            )
            duration = (time.perf_counter() - started) * 1000
            await self.repository.save_build(
                tenant_id=tenant_id,
                build_id=build_id,
                definition_id=definition_id,
                definition_version=definition.version,
                status=MaterializationBuildStatus.READY.value,
                snapshot_id=snapshot_id,
                duration_ms=duration,
            )
            build = MaterializationBuildV2(
                build_id=build_id,
                definition_id=definition_id,
                tenant_id=tenant_id,
                version=definition.version,
                status=MaterializationBuildStatus.READY,
                build_duration_ms=duration,
                snapshot_id=snapshot_id,
                started_at=snapshot_model.built_at.isoformat(),
                completed_at=snapshot_model.built_at.isoformat(),
            )
            snapshot = MaterializationSnapshotV2(
                snapshot_id=snapshot_id,
                definition_id=definition_id,
                tenant_id=tenant_id,
                version=definition.version,
                row_count=snapshot_model.row_count,
                fact_count=snapshot_model.fact_count,
                payload_size_bytes=snapshot_model.payload_size_bytes,
                certification_id=snapshot_model.certification_id,
                certification_status=CertificationStatus.VALID,
                tenant_proof_id=snapshot_model.tenant_proof_id,
                watermark=snapshot_model.watermark,
                source_sync_version=snapshot_model.source_sync_version,
                payload_checksum=snapshot_model.payload_checksum,
                freshness=FreshnessStatus.FRESH,
                built_at=snapshot_model.built_at.isoformat(),
                checksum=snapshot_model.checksum,
            )
            return build, snapshot
        except asyncio.CancelledError:
            await self._record_failure(
                tenant_id, build_id, definition_id, definition.version, "CANCELLED"
            )
            raise
        except Exception as exc:
            logger.exception("Governed materialization build failed")
            await self._record_failure(
                tenant_id, build_id, definition_id, definition.version, type(exc).__name__
            )
            raise

    async def _record_failure(
        self,
        tenant_id: str,
        build_id: str,
        definition_id: str,
        definition_version: int,
        error_code: str,
    ) -> None:
        await self.repository.mark_definition_failed(
            tenant_id, definition_id, definition_version
        )
        await self.repository.save_build(
            tenant_id=tenant_id,
            build_id=build_id,
            definition_id=definition_id,
            definition_version=definition_version,
            status=(
                MaterializationBuildStatus.CANCELLED.value
                if error_code == "CANCELLED"
                else MaterializationBuildStatus.FAILED.value
            ),
            error_code=error_code[:128],
        )
