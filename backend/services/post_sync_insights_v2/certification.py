"""Certification service for transforming validated candidates into certified post-sync insights v1.0."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from contracts.post_sync_insights_v2 import (
    POST_SYNC_INSIGHTS_CONTRACT_VERSION,
    PostSyncInsightCandidateV2,
    PostSyncInsightCertificationV2,
    PostSyncInsightLifecycleV2,
    PostSyncInsightV2,
)


class PostSyncInsightCertificationService:
    def certify_candidate(
        self,
        candidate: PostSyncInsightCandidateV2,
    ) -> PostSyncInsightV2:
        ins_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{candidate.tenant_id}:{candidate.fingerprint}")
        insight_id = f"insight-{ins_uuid}"
        cert_raw = f"{candidate.tenant_id}:{candidate.sync_run_id}:{candidate.fingerprint}:{candidate.evidence.checksum}"
        cert_checksum = hashlib.sha256(cert_raw.encode()).hexdigest()

        certification = PostSyncInsightCertificationV2(
            status="VALID",
            certified_at=datetime.now(timezone.utc),
            checksum=cert_checksum,
            verifier="ValidationProvenanceV2",
        )

        return PostSyncInsightV2(
            insight_id=insight_id,
            contract_version=POST_SYNC_INSIGHTS_CONTRACT_VERSION,
            tenant_id=candidate.tenant_id,
            sync_run_id=candidate.sync_run_id,
            insight_type=candidate.insight_type,
            category=candidate.category,
            severity=candidate.severity,
            lifecycle=PostSyncInsightLifecycleV2.PUBLISHED,
            summary=candidate.summary,
            evidence=candidate.evidence,
            provenance=candidate.provenance,
            certification=certification,
            score=candidate.score,
            warnings=(),
            published_at=datetime.now(timezone.utc),
            expires_at=None,
            fingerprint=candidate.fingerprint,
        )


certification_service = PostSyncInsightCertificationService()
