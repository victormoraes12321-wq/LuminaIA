"""
LuminaAI Governed Validation & Provenance V2 Repository
Version: lumina.validation-provenance/1.0
"""

import uuid
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.validation_provenance import (
    AnalyticalClaimBindingModel,
    AnalyticalClaimModel,
    AnalyticalFactModel,
    ProvenanceManifestModel,
    ResponseCertificationModel,
    ResultCertificationModel,
    ValidationEventModel,
    ValidationPolicyModel,
    ValidationRunModel,
)


class ValidationProvenanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_policy(self, tenant_id: UUID) -> Optional[ValidationPolicyModel]:
        stmt = (
            select(ValidationPolicyModel)
            .where(
                ValidationPolicyModel.tenant_id == tenant_id,
                ValidationPolicyModel.is_active == True,
            )
            .order_by(ValidationPolicyModel.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def save_policy(self, policy: ValidationPolicyModel) -> ValidationPolicyModel:
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def save_validation_run(self, run: ValidationRunModel) -> ValidationRunModel:
        self.session.add(run)
        await self.session.flush()
        return run

    async def save_facts(self, facts: List[AnalyticalFactModel]) -> List[AnalyticalFactModel]:
        for fact in facts:
            self.session.add(fact)
        await self.session.flush()
        return facts

    async def save_claims(self, claims: List[AnalyticalClaimModel]) -> List[AnalyticalClaimModel]:
        for claim in claims:
            self.session.add(claim)
        await self.session.flush()
        return claims

    async def save_claim_bindings(self, bindings: List[AnalyticalClaimBindingModel]) -> List[AnalyticalClaimBindingModel]:
        for binding in bindings:
            self.session.add(binding)
        await self.session.flush()
        return bindings

    async def save_provenance_manifest(self, manifest: ProvenanceManifestModel) -> ProvenanceManifestModel:
        self.session.add(manifest)
        await self.session.flush()
        return manifest

    async def save_result_certification(self, result_cert: ResultCertificationModel) -> ResultCertificationModel:
        self.session.add(result_cert)
        await self.session.flush()
        return result_cert

    async def save_response_certification(self, response_cert: ResponseCertificationModel) -> ResponseCertificationModel:
        self.session.add(response_cert)
        await self.session.flush()
        return response_cert

    async def update_response_certification_cas(
        self,
        cert_id: UUID,
        tenant_id: UUID,
        expected_lock_version: int,
        superseded_by_id: UUID,
    ) -> bool:
        stmt = (
            update(ResponseCertificationModel)
            .where(
                ResponseCertificationModel.id == cert_id,
                ResponseCertificationModel.tenant_id == tenant_id,
                ResponseCertificationModel.lock_version == expected_lock_version,
            )
            .values(
                superseded_by_id=superseded_by_id,
                lock_version=expected_lock_version + 1,
            )
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount == 1

    async def save_event(self, event: ValidationEventModel) -> ValidationEventModel:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_certification_by_checksum(self, tenant_id: UUID, checksum: str) -> Optional[ResultCertificationModel]:
        stmt = select(ResultCertificationModel).where(
            ResultCertificationModel.tenant_id == tenant_id,
            ResultCertificationModel.checksum == checksum,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
