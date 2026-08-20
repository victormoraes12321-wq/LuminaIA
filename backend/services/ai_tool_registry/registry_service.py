from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from contracts.ai_tool_registry_v2 import (
    AIToolCapability,
    AIToolDefinitionV2,
    AIToolExecutionPolicyV2,
    AIToolIdentityV2,
    AIToolInputContractV2,
    AIToolLifecycle,
    AIToolOutputContractV2,
    AIToolRegistrationRequestV2,
    AIToolRegistryManifestV2,
    AIToolRegistrySnapshotV2,
    AIToolVersionV2,
)
from services.ai_tool_registry.adapters.registry_map import REGISTERED_TOOL_ADAPTERS, get_adapter_class
from services.ai_tool_registry.exceptions import (
    AIToolAccessDeniedException,
    AIToolAdapterNotRegisteredException,
    AIToolDependencyCycleException,
    AIToolNotFoundException,
    AIToolReservedCapabilityUnavailableException,
)
from services.ai_tool_registry.repository import ai_tool_registry_repository

logger = logging.getLogger("luminaai.services.ai_tool_registry.registry_service")


class GovernedAIToolRegistryService:
    """
    Core administrative & lifecycle management service for AI Tool Registry v2.
    """

    def __init__(self):
        self.repo = ai_tool_registry_repository

    async def register_tool_identity(
        self,
        tenant_id: str,
        user_id: str,
        user_permissions: List[str],
        request: AIToolRegistrationRequestV2,
    ) -> AIToolIdentityV2:
        # Check permissions
        if "ai_tool:create" not in user_permissions and "admin" not in [p.lower() for p in user_permissions]:
            raise AIToolAccessDeniedException("Permission 'ai_tool:create' required to register tool identities.")

        # Check adapter static allowlist
        if request.adapter_id not in REGISTERED_TOOL_ADAPTERS:
            raise AIToolAdapterNotRegisteredException(
                f"Adapter '{request.adapter_id}' is not present in the static allowlist."
            )

        # Check reserved capabilities (Prompt 15 analytical capabilities)
        reserved_caps = {
            AIToolCapability.ANALYTICAL_POSTGRESQL_READ,
            AIToolCapability.EXECUTE_GOVERNED_ANALYTICAL_PLAN,
        }
        for cap in request.capabilities:
            if cap in reserved_caps:
                raise AIToolReservedCapabilityUnavailableException(
                    f"Capability '{cap.value}' is reserved and disabled until Prompt 15."
                )

        identity = await self.repo.get_tool_identity_by_id(tenant_id, request.tool_id)
        if not identity:
            identity = await self.repo.create_tool_identity(
                tool_id=request.tool_id,
                canonical_name=request.canonical_name,
                display_name=request.display_name,
                description=request.description,
                capabilities=[c.value for c in request.capabilities],
                domain=request.domain,
                tool_type=request.tool_type.value,
                risk_class=request.risk_class.value,
                side_effect=request.side_effect.value,
                network_class=request.network_class.value,
                data_class=request.data_class.value,
                owner_id=user_id,
                tenant_id=tenant_id,
            )

        # Create version draft
        input_checksum = self.repo.compute_hash(request.input_schema)
        output_checksum = self.repo.compute_hash(request.output_schema)
        exec_pol = request.execution_policy.model_dump() if request.execution_policy else {}

        version_obj = await self.repo.create_tool_version(
            tool_identity_id=identity.id,
            tool_id=request.tool_id,
            version=request.version,
            adapter_id=request.adapter_id,
            input_contract={"json_schema": request.input_schema, "checksum": input_checksum},
            output_contract={"json_schema": request.output_schema, "checksum": output_checksum},
            execution_policy=exec_pol,
            author_id=user_id,
            tenant_id=tenant_id,
        )

        await self.repo.log_event(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="AI_TOOL_CREATED",
            tool_id=request.tool_id,
            version=request.version,
            payload={"adapter_id": request.adapter_id},
        )

        return AIToolIdentityV2(
            tool_id=identity.tool_id,
            canonical_name=identity.canonical_name,
            display_name=identity.display_name,
            description=identity.description,
            domain=identity.domain,
            tool_type=identity.tool_type,
            capabilities=[AIToolCapability(c) for c in identity.capabilities],
            risk_class=identity.risk_class,
            side_effect=identity.side_effect,
            network_class=identity.network_class,
            data_class=identity.data_class,
            owner=identity.owner_id,
            tenant_id=identity.tenant_id,
            scope=identity.scope,
            created_at=str(identity.created_at),
            checksum=identity.checksum,
        )

    async def submit_review(
        self,
        tenant_id: str,
        user_id: str,
        user_permissions: List[str],
        tool_id: str,
        version: str,
        approved: bool,
        review_notes: str = "",
    ) -> bool:
        if "ai_tool:review" not in user_permissions and "admin" not in [p.lower() for p in user_permissions]:
            raise AIToolAccessDeniedException("Permission 'ai_tool:review' required.")

        ver = await self.repo.get_tool_version(tool_id, version, tenant_id)
        if not ver:
            raise AIToolNotFoundException(f"Tool version '{tool_id}:{version}' not found.")

        # Self-approval check: Author cannot approve their own tool version!
        if ver.author_id == user_id and approved:
            raise AIToolAccessDeniedException("Author cannot approve their own tool version submission.")

        new_lifecycle = "APPROVED" if approved else "REJECTED"
        updated = await self.repo.update_tool_version_lifecycle(
            version_id=ver.id,
            expected_lock_version=ver.lock_version,
            new_lifecycle=new_lifecycle,
            reviewer_or_publisher_id=user_id,
        )
        if updated:
            await self.repo.add_review(
                tool_version_id=ver.id,
                reviewer_id=user_id,
                tenant_id=tenant_id,
                approved=approved,
                review_notes=review_notes,
            )
            await self.repo.log_event(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="AI_TOOL_REVIEW_APPROVED" if approved else "AI_TOOL_REVIEW_REJECTED",
                tool_id=tool_id,
                version=version,
            )
        return updated

    async def publish_tool_version(
        self,
        tenant_id: str,
        user_id: str,
        user_permissions: List[str],
        tool_id: str,
        version: str,
    ) -> bool:
        if "ai_tool:publish" not in user_permissions and "admin" not in [p.lower() for p in user_permissions]:
            raise AIToolAccessDeniedException("Permission 'ai_tool:publish' required.")

        ver = await self.repo.get_tool_version(tool_id, version, tenant_id)
        if not ver:
            raise AIToolNotFoundException(f"Tool version '{tool_id}:{version}' not found.")

        if ver.lifecycle not in ("APPROVED", "ACTIVE"):
            raise ValueError(f"Cannot publish tool version in lifecycle state '{ver.lifecycle}'. Must be APPROVED.")

        updated = await self.repo.update_tool_version_lifecycle(
            version_id=ver.id,
            expected_lock_version=ver.lock_version,
            new_lifecycle="ACTIVE",
            reviewer_or_publisher_id=user_id,
        )
        if updated:
            await self.repo.log_event(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="AI_TOOL_VERSION_ACTIVATED",
                tool_id=tool_id,
                version=version,
            )
        return updated

    async def disable_tool_version(
        self,
        tenant_id: str,
        user_id: str,
        user_permissions: List[str],
        tool_id: str,
        version: str,
        reason: str = "",
    ) -> bool:
        if "ai_tool:disable" not in user_permissions and "admin" not in [p.lower() for p in user_permissions]:
            raise AIToolAccessDeniedException("Permission 'ai_tool:disable' required.")

        ver = await self.repo.get_tool_version(tool_id, version, tenant_id)
        if not ver:
            raise AIToolNotFoundException(f"Tool version '{tool_id}:{version}' not found.")

        updated = await self.repo.update_tool_version_lifecycle(
            version_id=ver.id,
            expected_lock_version=ver.lock_version,
            new_lifecycle="DISABLED",
            reviewer_or_publisher_id=user_id,
        )
        if updated:
            await self.repo.log_event(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="AI_TOOL_VERSION_DISABLED",
                tool_id=tool_id,
                version=version,
                payload={"reason": reason},
            )
        return updated

    async def publish_snapshot(
        self,
        tenant_id: str,
        user_id: str,
        user_permissions: List[str],
        snapshot_id: str,
        version: str,
        active_tool_versions: Dict[str, str],
        disabled_tool_ids: Optional[List[str]] = None,
    ) -> AIToolRegistrySnapshotV2:
        if "ai_tool:publish" not in user_permissions and "admin" not in [p.lower() for p in user_permissions]:
            raise AIToolAccessDeniedException("Permission 'ai_tool:publish' required.")

        # Check dependency cycles
        self.detect_dependency_cycles(active_tool_versions)

        curr_active = await self.repo.get_active_snapshot()
        prev_id = curr_active.snapshot_id if curr_active else None

        snap = await self.repo.create_snapshot(
            snapshot_id=snapshot_id,
            version=version,
            active_tool_versions=active_tool_versions,
            created_by=user_id,
            disabled_tool_ids=disabled_tool_ids,
            previous_snapshot_id=prev_id,
        )

        await self.repo.log_event(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="AI_TOOL_REGISTRY_SNAPSHOT_PUBLISHED",
            tool_id="system_registry",
            version=version,
            payload={"snapshot_id": snapshot_id},
        )

        return AIToolRegistrySnapshotV2(
            snapshot_id=snap.snapshot_id,
            version=snap.version,
            status=snap.status,
            active_tool_versions=snap.active_tool_versions,
            disabled_tool_ids=snap.disabled_tool_ids,
            dependency_graph_checksum=snap.dependency_graph_checksum,
            created_by=snap.created_by,
            published_by=snap.published_by,
            created_at=str(snap.created_at),
            published_at=str(snap.published_at) if snap.published_at else None,
            previous_snapshot_id=snap.previous_snapshot_id,
            checksum=snap.checksum,
        )

    def detect_dependency_cycles(self, active_tool_versions: Dict[str, str]) -> None:
        # Static cycle validation placeholder
        pass

    async def get_active_manifest(self, tenant_id: str) -> AIToolRegistryManifestV2:
        snapshot = await self.repo.get_active_snapshot()
        if not snapshot:
            # Return synthetic default initial snapshot if DB unseeded
            snapshot_obj = AIToolRegistrySnapshotV2(
                snapshot_id="snap_initial_v1",
                version="1.0.0",
                status="PUBLISHED",
                active_tool_versions={
                    "lumina.enterprise_knowledge.search": "1.0.0",
                    "lumina.enterprise_knowledge.get_metric_definition": "1.0.0",
                    "lumina.temporal.normalize": "1.0.0",
                    "lumina.semantic.search": "1.0.0",
                    "lumina.semantic.resolve_entity": "1.0.0",
                    "lumina.context.get_public_summary": "1.0.0",
                    "lumina.profile.get_application_summary": "1.0.0",
                    "lumina.intent.validate": "1.0.0",
                    "lumina.comparison.plan": "1.0.0",
                    "lumina.comparison.validate_plan": "1.0.0",
                    "lumina.clarification.build_options": "1.0.0",
                    "lumina.provenance.get_public_summary": "1.0.0",
                },
                disabled_tool_ids=[],
                dependency_graph_checksum="initial_checksum",
                created_by="system",
                created_at="2026-07-30T00:00:00Z",
                checksum="initial_snapshot_checksum",
            )
        else:
            snapshot_obj = AIToolRegistrySnapshotV2(
                snapshot_id=snapshot.snapshot_id,
                version=snapshot.version,
                status=snapshot.status,
                active_tool_versions=snapshot.active_tool_versions,
                disabled_tool_ids=snapshot.disabled_tool_ids,
                dependency_graph_checksum=snapshot.dependency_graph_checksum,
                created_by=snapshot.created_by,
                published_by=snapshot.published_by,
                created_at=str(snapshot.created_at),
                published_at=str(snapshot.published_at) if snapshot.published_at else None,
                previous_snapshot_id=snapshot.previous_snapshot_id,
                checksum=snapshot.checksum,
            )

        # Build list of active tool definitions
        tool_defs: List[AIToolDefinitionV2] = []
        for tool_id, ver_str in snapshot_obj.active_tool_versions.items():
            if tool_id in snapshot_obj.disabled_tool_ids:
                continue

            adapter_id_map = {
                "lumina.enterprise_knowledge.search": "enterprise_knowledge.search.v1",
                "lumina.enterprise_knowledge.get_metric_definition": "enterprise_knowledge.get_metric_definition.v1",
                "lumina.temporal.normalize": "temporal.normalize.v1",
                "lumina.semantic.search": "semantic.search.v1",
                "lumina.semantic.resolve_entity": "semantic.resolve_entity.v1",
                "lumina.context.get_public_summary": "context.get_public_summary.v1",
                "lumina.profile.get_application_summary": "profile.get_application_summary.v1",
                "lumina.intent.validate": "intent.validate.v1",
                "lumina.comparison.plan": "comparison.plan.v1",
                "lumina.comparison.validate_plan": "comparison.validate_plan.v1",
                "lumina.clarification.build_options": "clarification.build_options.v1",
                "lumina.provenance.get_public_summary": "provenance.get_public_summary.v1",
            }
            adapter_id = adapter_id_map.get(tool_id, f"{tool_id.split('.')[-1]}.v1")

            identity = AIToolIdentityV2(
                tool_id=tool_id,
                canonical_name=tool_id,
                display_name=tool_id.replace(".", " ").title(),
                description=f"Governed AI tool capability for {tool_id}",
                capabilities=[AIToolCapability.READ_ENTERPRISE_KNOWLEDGE],
                owner="system",
                tenant_id=str(tenant_id),
                created_at="2026-07-30T00:00:00Z",
                checksum="ident_checksum",
            )
            active_ver = AIToolVersionV2(
                tool_id=tool_id,
                version=ver_str,
                adapter_id=adapter_id,
                input_contract=AIToolInputContractV2(json_schema={"type": "object"}, checksum="in_chk"),
                output_contract=AIToolOutputContractV2(json_schema={"type": "object"}, checksum="out_chk"),
                execution_policy=AIToolExecutionPolicyV2(),
                lifecycle=AIToolLifecycle.ACTIVE,
                author_id="system",
                checksum="ver_chk",
                created_at="2026-07-30T00:00:00Z",
            )
            tool_defs.append(AIToolDefinitionV2(identity=identity, active_version=active_ver))

        manifest_chk = self.repo.compute_hash({"snapshot_id": snapshot_obj.snapshot_id, "count": len(tool_defs)})
        return AIToolRegistryManifestV2(
            snapshot=snapshot_obj,
            tool_definitions=tool_defs,
            total_tools_count=len(tool_defs),
            manifest_checksum=manifest_chk,
        )


governed_ai_tool_registry_service = GovernedAIToolRegistryService()
