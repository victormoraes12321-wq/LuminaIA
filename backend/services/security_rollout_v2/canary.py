"""Deterministic server-side canary cohort calculation."""
from __future__ import annotations

import hashlib

from contracts.security_rollout_v2 import CanaryAssignmentV2, CanaryPolicyV2


class CanaryPolicyServiceV2:
    @staticmethod
    def assign(*, trusted_tenant_identifier: str, environment: str, policy: CanaryPolicyV2) -> CanaryAssignmentV2:
        digest = hashlib.sha256(f"{policy.policy_version}:{trusted_tenant_identifier}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % 10000
        if environment not in policy.allowed_environments:
            return CanaryAssignmentV2(policy_version=policy.policy_version, bucket=bucket, eligible=False, reason_code="ENVIRONMENT_DENIED")
        if trusted_tenant_identifier in policy.explicit_internal_tenants:
            return CanaryAssignmentV2(policy_version=policy.policy_version, bucket=bucket, eligible=True, reason_code="INTERNAL_ALLOWLIST")
        eligible = bucket < policy.percentage * 100
        return CanaryAssignmentV2(policy_version=policy.policy_version, bucket=bucket, eligible=eligible, reason_code="STABLE_BUCKET_ALLOW" if eligible else "STABLE_BUCKET_DENY")
