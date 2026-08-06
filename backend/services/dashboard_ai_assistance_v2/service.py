from __future__ import annotations

import uuid
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from contracts.dashboard_ai_assistance_v2 import (
    DashboardAiApplyRequestV2,
    DashboardAiApplyResultV2,
    DashboardAiAssistanceRequestV2,
    DashboardAiBlueprintProposalV2,
    DashboardAiClarificationQuestionV2,
    DashboardAiClarificationRequestV2,
    DashboardAiClarificationResponseV2,
    DashboardAiDesignIntentV2,
    DashboardAiOperationV2,
    DashboardAiRequestOriginV2,
    DashboardAiProposalDecisionV2,
    DashboardAiProposalStatusV2,
    DashboardAiProposalV2,
    DashboardAiProposalVersionV2,
    DashboardAiPublicRationaleV2,
    DashboardAiReviseRequestV2,
    DashboardAiRunBudgetV2,
    DashboardAiSemanticPatchProposalV2,
    DashboardAiVisualPatchProposalV2,
)
from contracts.dashboard_backend_v2 import DashboardCreateRequestV2, DashboardSemanticPatchRequestV2, DashboardVisualPatchRequestV2
from contracts.dashboard_blueprint_v2 import DashboardOriginV2
from services.dashboard_backend_v2 import (
    DashboardActorContextV2,
    DashboardAccessRepositoryV2,
    DashboardAuthoringServiceV2,
    DashboardPatchServiceV2,
    DashboardRepositoryV2,
    DashboardRevisionRepositoryV2,
    resolve_resource_capabilities,
)
from contracts.dashboard_backend_v2 import DashboardCapabilityBackendV2

from .errors import DashboardAiAssistanceError
from .integrity import checksum
from .intent import DashboardAiIntentExtractionServiceV2
from .lifecycle import DashboardAiProposalStateMachineV2
from .policy import DashboardAiCapabilityV2, DashboardAiPolicyV2
from .rationale import DashboardAiRationaleServiceV2
from .repositories import (
    DashboardAiAuditRepositoryV2,
    DashboardAiClarificationRepositoryV2,
    DashboardAiDecisionRepositoryV2,
    DashboardAiEvidenceRepositoryV2,
    DashboardAiProposalRepositoryV2,
    DashboardAiProposalVersionRepositoryV2,
    DashboardAiRunRepositoryV2,
)
from .resolution import DashboardDesignSpecServiceV2
from .semantic_compiler import DashboardAiSemanticPatchCompilerV2
from .synthesis import DashboardBlueprintSynthesisService
from .validation import DashboardAiProposalValidationServiceV2
from .visual_proposal import DashboardAiVisualProposalServiceV2
from services.dashboard_blueprint_v2.validation_service import DashboardPatchValidator
from contracts.dashboard_blueprint_v2 import DashboardBlueprintV2


class DashboardAiAssistanceServiceV2:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.proposals = DashboardAiProposalRepositoryV2(session)
        self.versions = DashboardAiProposalVersionRepositoryV2(session)
        self.clarifications = DashboardAiClarificationRepositoryV2(session)
        self.evidence = DashboardAiEvidenceRepositoryV2(session)
        self.decisions = DashboardAiDecisionRepositoryV2(session)
        self.runs = DashboardAiRunRepositoryV2(session)
        self.audit = DashboardAiAuditRepositoryV2(session)
        self.intent = DashboardAiIntentExtractionServiceV2()
        self.resolver = DashboardDesignSpecServiceV2()
        self.synthesis = DashboardBlueprintSynthesisService()
        self.validator = DashboardAiProposalValidationServiceV2()

    async def create(self, *, actor: DashboardActorContextV2, request: DashboardAiAssistanceRequestV2, idempotency_key: str) -> DashboardAiProposalV2:
        DashboardAiPolicyV2.require(actor.global_role, DashboardAiCapabilityV2.CREATE_PROPOSAL)
        DashboardAiPolicyV2.assert_operation(request.operation)
        self.intent.assert_model_operation(request.operation)
        if request.operation is not DashboardAiOperationV2.CREATE_DASHBOARD:
            return await self.create_edit(actor=actor, request=request, idempotency_key=idempotency_key)
        scope = checksum({"tenant": actor.tenant_id, "user": actor.user_id, "operation": request.operation.value, "key": idempotency_key})
        request_checksum = checksum(request)
        replay = await self.proposals.find_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None:
            return await self.contract(actor, replay)
        proposal_id = uuid.uuid4()
        design_intent = self.intent.extract_design(request.instruction)
        row = await self.proposals.create(
            id=proposal_id, tenant_id=uuid.UUID(actor.tenant_id), created_by_user_id=uuid.UUID(actor.user_id),
            operation=request.operation.value, origin=request.origin.value, status="RECEIVED", current_version=1, lock_version=1,
            target_dashboard_id=None, target_revision_id=None, applied_dashboard_id=None, applied_revision_id=None,
            intent_json=design_intent.model_dump(mode="json"), instruction_fingerprint=checksum(request.instruction),
            idempotency_scope=scope, request_checksum=request_checksum, expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        await self._audit(actor, row, "PROPOSAL_RECEIVED")
        budget = DashboardAiRunBudgetV2()
        run = await self.runs.append(
            id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, status="RUNNING", provider=self.intent.provider_id, model=self.intent.model_id,
            budget_json=budget.model_dump(mode="json"), input_fingerprint=row.instruction_fingerprint, usage_json={},
        )
        try:
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.ANALYZING)
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.RESOLVING)
            resolution = self.resolver.resolve(proposal_id=str(proposal_id), intent=design_intent)
            if resolution.blocking_code:
                row = await self._transition(actor, row, DashboardAiProposalStatusV2.BLOCKED)
                run.status = "BLOCKED"; run.completed_at = datetime.now(timezone.utc)
                await self._audit(actor, row, resolution.blocking_code, outcome="FAILED")
                return await self.contract(actor, row)
            if resolution.clarifications:
                row = await self._transition(actor, row, DashboardAiProposalStatusV2.NEEDS_CLARIFICATION)
                for question in resolution.clarifications:
                    await self.clarifications.create(
                        id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, proposal_version=row.current_version,
                        question_json=question.model_dump(mode="json"), response_json=None, status="OPEN", lock_version=1,
                        answered_by_user_id=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                    )
                run.status = "SUCCEEDED"; run.completed_at = datetime.now(timezone.utc)
                await self._audit(actor, row, "CLARIFICATION_REQUESTED")
                return await self.contract(actor, row)
            if resolution.design_spec is None:
                raise DashboardAiAssistanceError("DASHBOARD_AI_DESIGN_BLOCKED", "Não foi possível resolver o design.", 422)
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.SYNTHESIZING)
            blueprint = self.synthesis.synthesize(resolution.design_spec)
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.VALIDATING)
            blueprint_proposal, validation_evidence, warnings, risks = self.validator.validate_blueprint(blueprint, resolution.design_spec)
            now = datetime.now(timezone.utc)
            rationale = DashboardAiRationaleServiceV2.for_design(resolution.design_spec)
            content_basis = {"proposal": blueprint_proposal, "rationale": rationale, "evidence": resolution.evidence + validation_evidence, "warnings": warnings, "risks": risks}
            version = DashboardAiProposalVersionV2(
                proposal_id=str(row.id), version=row.current_version, status=DashboardAiProposalStatusV2.READY_FOR_REVIEW,
                blueprint_proposal=blueprint_proposal, rationale=rationale, evidence=resolution.evidence + validation_evidence,
                warnings=warnings, risks=risks, content_checksum=checksum(content_basis), created_at=now,
            )
            await self.versions.append(
                id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, version=row.current_version,
                status=version.status.value, content_json=version.model_dump(mode="json"), content_checksum=version.content_checksum,
                created_by_user_id=uuid.UUID(actor.user_id),
            )
            for item in version.evidence:
                await self.evidence.append(
                    id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id,
                    proposal_version=row.current_version, evidence_type=item.evidence_type, canonical_reference=item.canonical_reference,
                    public_label=item.public_label, authority_version=item.authority_version, evidence_checksum=item.checksum,
                )
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.READY_FOR_REVIEW)
            run.status = "SUCCEEDED"; run.completed_at = datetime.now(timezone.utc); run.usage_json = {"tool_calls": 3, "output_tokens": 0}
            await self._audit(actor, row, "PROPOSAL_READY_FOR_REVIEW")
            return await self.contract(actor, row)
        except DashboardAiAssistanceError:
            raise
        except (ValueError, TypeError) as exc:
            run.status = "FAILED"; run.completed_at = datetime.now(timezone.utc)
            if row.status not in {"BLOCKED", "FAILED", "CANCELLED"}:
                try: row = await self._transition(actor, row, DashboardAiProposalStatusV2.FAILED)
                except (ValueError, DashboardAiAssistanceError): pass
            await self._audit(actor, row, "PROPOSAL_FAILED", outcome="FAILED")
            raise DashboardAiAssistanceError("DASHBOARD_AI_PROPOSAL_FAILED", "A proposta não pôde ser produzida com segurança.", 422) from exc

    async def create_edit(self, *, actor: DashboardActorContextV2, request: DashboardAiAssistanceRequestV2, idempotency_key: str) -> DashboardAiProposalV2:
        if request.operation not in {DashboardAiOperationV2.PROPOSE_SEMANTIC_CHANGE, DashboardAiOperationV2.PROPOSE_VISUAL_CHANGE}:
            raise DashboardAiAssistanceError("DASHBOARD_AI_OPERATION_UNSUPPORTED", "Operação não cria uma nova proposta aplicável.", 422)
        dashboard_id, revision_id = request.context.target_dashboard_id, request.context.target_revision_id
        if not dashboard_id or not revision_id:
            raise DashboardAiAssistanceError("DASHBOARD_AI_TARGET_REQUIRED", "Dashboard e revisão alvo são obrigatórios.", 422)
        dashboard = await DashboardRepositoryV2(self.session).get(actor.tenant_id, dashboard_id)
        capabilities = await resolve_resource_capabilities(DashboardAccessRepositoryV2(self.session), actor=actor, dashboard=dashboard)
        required = DashboardCapabilityBackendV2.EDIT_SEMANTIC if request.operation is DashboardAiOperationV2.PROPOSE_SEMANTIC_CHANGE else DashboardCapabilityBackendV2.EDIT_VISUAL
        if required not in capabilities:
            raise DashboardAiAssistanceError("DASHBOARD_AI_ACCESS_DENIED", "O usuário não pode propor alterações neste dashboard.", 403)
        revision = await DashboardRevisionRepositoryV2(self.session).get(actor.tenant_id, dashboard_id, revision_id)
        base = DashboardBlueprintV2.model_validate_json(json.dumps(revision.blueprint_json, ensure_ascii=False))
        scope = checksum({"tenant": actor.tenant_id, "user": actor.user_id, "operation": request.operation.value, "resource": dashboard_id, "key": idempotency_key})
        request_checksum = checksum(request)
        replay = await self.proposals.find_replay(actor.tenant_id, scope, request_checksum)
        if replay is not None: return await self.contract(actor, replay)
        proposal_id = uuid.uuid4()
        if request.operation is DashboardAiOperationV2.PROPOSE_SEMANTIC_CHANGE:
            extracted = self.intent.extract_semantic(request.instruction, dashboard_id=dashboard_id, revision_id=revision_id)
            intent_json = extracted.model_dump(mode="json")
        else:
            extracted = None
            intent_json = {"objective": request.instruction, "target_dashboard_id": dashboard_id, "target_revision_id": revision_id}
        row = await self.proposals.create(
            id=proposal_id, tenant_id=uuid.UUID(actor.tenant_id), created_by_user_id=uuid.UUID(actor.user_id), operation=request.operation.value,
            origin=request.origin.value, status="RECEIVED", current_version=1, lock_version=1,
            target_dashboard_id=uuid.UUID(dashboard_id), target_revision_id=uuid.UUID(revision_id), applied_dashboard_id=None, applied_revision_id=None,
            intent_json=intent_json, instruction_fingerprint=checksum(request.instruction), idempotency_scope=scope, request_checksum=request_checksum,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        await self._audit(actor, row, "PROPOSAL_RECEIVED")
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.ANALYZING)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.RESOLVING)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.SYNTHESIZING)
        if extracted is not None:
            patch = DashboardAiSemanticPatchCompilerV2().compile(base=base, intent=extracted)
            if any(item.blocking for item in DashboardPatchValidator.validate_semantic(patch)):
                raise DashboardAiAssistanceError("DASHBOARD_AI_PATCH_BLOCKED", "Patch semântico fora da allowlist.", 422)
            payload = DashboardAiSemanticPatchProposalV2(intent=extracted, patch=patch, patch_checksum=checksum(patch))
            kwargs = {"semantic_proposal": payload}
            summary = "Proposta semântica compilada deterministicamente; a aplicação criará uma nova revisão DRAFT."
        else:
            patch = DashboardAiVisualProposalServiceV2().propose_title(base=base, title=request.instruction[:160])
            if any(item.blocking for item in DashboardPatchValidator.validate_visual(patch)):
                raise DashboardAiAssistanceError("DASHBOARD_AI_PATCH_BLOCKED", "Patch visual fora da allowlist.", 422)
            payload = DashboardAiVisualPatchProposalV2(objective=request.instruction, patch=patch, patch_checksum=checksum(patch))
            kwargs = {"visual_proposal": payload}
            summary = "Proposta visual compatível com o Prompt 21; nenhuma semântica foi alterada."
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.VALIDATING)
        rationale = DashboardAiPublicRationaleV2(summary=summary, decisions=("Revisão alvo validada", "Patch em allowlist"))
        version = DashboardAiProposalVersionV2(
            proposal_id=str(row.id), version=1, status=DashboardAiProposalStatusV2.READY_FOR_REVIEW,
            rationale=rationale, content_checksum=checksum({"payload": payload, "rationale": rationale}), created_at=datetime.now(timezone.utc), **kwargs,
        )
        await self.versions.append(id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, version=1, status=version.status.value, content_json=version.model_dump(mode="json"), content_checksum=version.content_checksum, created_by_user_id=uuid.UUID(actor.user_id))
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.READY_FOR_REVIEW)
        await self._audit(actor, row, "PROPOSAL_READY_FOR_REVIEW")
        return await self.contract(actor, row)

    async def revise(
        self,
        *,
        actor: DashboardActorContextV2,
        proposal_id: str,
        request: DashboardAiReviseRequestV2,
        idempotency_key: str,
    ) -> DashboardAiProposalV2:
        """Append an immutable proposal version; never mutate prior version content."""
        DashboardAiPolicyV2.require(actor.global_role, DashboardAiCapabilityV2.REVISE)
        row = await self.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
        instruction_fingerprint = checksum(request.instruction)
        if (
            row.current_version == request.expected_proposal_version + 1
            and row.instruction_fingerprint == instruction_fingerprint
        ):
            return await self.contract(actor, row)
        if row.status != "READY_FOR_REVIEW":
            raise DashboardAiAssistanceError(
                "DASHBOARD_AI_REVISION_NOT_ALLOWED",
                "Somente uma proposta pronta para revisÃ£o pode receber nova versÃ£o.",
                409,
            )

        latest_row = await self.versions.get(
            actor.tenant_id, proposal_id, request.expected_proposal_version
        )
        latest = DashboardAiProposalVersionV2.model_validate_json(
            json.dumps(latest_row.content_json, ensure_ascii=False)
        )
        new_version = request.expected_proposal_version + 1

        if latest.blueprint_proposal is not None:
            intent = self.intent.extract_design(request.instruction)
            resolution = self.resolver.resolve(proposal_id=proposal_id, intent=intent)
            if resolution.blocking_code or resolution.clarifications or resolution.design_spec is None:
                raise DashboardAiAssistanceError(
                    resolution.blocking_code or "DASHBOARD_AI_REVISION_CLARIFICATION_REQUIRED",
                    "A revisÃ£o precisa de uma instruÃ§Ã£o canÃ´nica sem ambiguidade.",
                    422,
                )
            blueprint = self.synthesis.synthesize(resolution.design_spec)
            proposal, validation_evidence, warnings, risks = self.validator.validate_blueprint(
                blueprint, resolution.design_spec
            )
            rationale = DashboardAiRationaleServiceV2.for_design(resolution.design_spec)
            evidence = resolution.evidence + validation_evidence
            payload_kwargs = {"blueprint_proposal": proposal}
            intent_json = intent.model_dump(mode="json")
        elif latest.semantic_proposal is not None:
            if not row.target_dashboard_id or not row.target_revision_id:
                raise DashboardAiAssistanceError("DASHBOARD_AI_TARGET_REQUIRED", "Dashboard e revisÃ£o alvo sÃ£o obrigatÃ³rios.", 422)
            base_row = await DashboardRevisionRepositoryV2(self.session).get(
                actor.tenant_id, str(row.target_dashboard_id), str(row.target_revision_id)
            )
            base = DashboardBlueprintV2.model_validate_json(json.dumps(base_row.blueprint_json, ensure_ascii=False))
            intent = self.intent.extract_semantic(
                request.instruction,
                dashboard_id=str(row.target_dashboard_id),
                revision_id=str(row.target_revision_id),
            )
            patch = DashboardAiSemanticPatchCompilerV2().compile(base=base, intent=intent)
            if any(item.blocking for item in DashboardPatchValidator.validate_semantic(patch)):
                raise DashboardAiAssistanceError("DASHBOARD_AI_PATCH_BLOCKED", "Patch semÃ¢ntico fora da allowlist.", 422)
            semantic = DashboardAiSemanticPatchProposalV2(intent=intent, patch=patch, patch_checksum=checksum(patch))
            payload_kwargs = {"semantic_proposal": semantic}
            intent_json = intent.model_dump(mode="json")
            evidence, warnings, risks = (), (), ()
            rationale = DashboardAiPublicRationaleV2(
                summary="Nova versÃ£o semÃ¢ntica compilada deterministicamente.",
                decisions=("RevisÃ£o alvo validada", "Patch em allowlist"),
            )
        elif latest.visual_proposal is not None:
            if not row.target_dashboard_id or not row.target_revision_id:
                raise DashboardAiAssistanceError("DASHBOARD_AI_TARGET_REQUIRED", "Dashboard e revisÃ£o alvo sÃ£o obrigatÃ³rios.", 422)
            base_row = await DashboardRevisionRepositoryV2(self.session).get(
                actor.tenant_id, str(row.target_dashboard_id), str(row.target_revision_id)
            )
            base = DashboardBlueprintV2.model_validate_json(json.dumps(base_row.blueprint_json, ensure_ascii=False))
            patch = DashboardAiVisualProposalServiceV2().propose_title(base=base, title=request.instruction[:160])
            if any(item.blocking for item in DashboardPatchValidator.validate_visual(patch)):
                raise DashboardAiAssistanceError("DASHBOARD_AI_PATCH_BLOCKED", "Patch visual fora da allowlist.", 422)
            visual = DashboardAiVisualPatchProposalV2(objective=request.instruction, patch=patch, patch_checksum=checksum(patch))
            payload_kwargs = {"visual_proposal": visual}
            intent_json = {"objective": request.instruction}
            evidence, warnings, risks = (), (), ()
            rationale = DashboardAiPublicRationaleV2(
                summary="Nova versÃ£o visual compatÃ­vel com o renderer governado.",
                decisions=("RevisÃ£o alvo validada", "Patch visual em allowlist"),
            )
        else:  # pragma: no cover - protected by the contract validator
            raise DashboardAiAssistanceError("DASHBOARD_AI_REVISION_PAYLOAD_INVALID", "ConteÃºdo revisÃ¡vel ausente.", 422)

        content_basis = {
            "payload": payload_kwargs,
            "rationale": rationale,
            "evidence": evidence,
            "warnings": warnings,
            "risks": risks,
        }
        version = DashboardAiProposalVersionV2(
            proposal_id=proposal_id,
            version=new_version,
            status=DashboardAiProposalStatusV2.READY_FOR_REVIEW,
            rationale=rationale,
            evidence=evidence,
            warnings=warnings,
            risks=risks,
            content_checksum=checksum(content_basis),
            created_at=datetime.now(timezone.utc),
            **payload_kwargs,
        )
        row = await self.proposals.begin_revision_cas(
            tenant_id=actor.tenant_id,
            proposal_id=proposal_id,
            expected_lock=request.expected_lock_version,
            expected_version=request.expected_proposal_version,
            instruction_fingerprint=instruction_fingerprint,
            intent_json=intent_json,
        )
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.RESOLVING)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.SYNTHESIZING)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.VALIDATING)
        await self.versions.append(
            id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id,
            version=new_version, status=version.status.value,
            content_json=version.model_dump(mode="json"),
            content_checksum=version.content_checksum,
            created_by_user_id=uuid.UUID(actor.user_id),
        )
        for item in evidence:
            await self.evidence.append(
                id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id,
                proposal_version=new_version, evidence_type=item.evidence_type,
                canonical_reference=item.canonical_reference,
                public_label=item.public_label, authority_version=item.authority_version,
                evidence_checksum=item.checksum,
            )
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.READY_FOR_REVIEW)
        await self._audit(actor, row, "DASHBOARD_AI_PROPOSAL_REVISED")
        return await self.contract(actor, row)

    async def contract(self, actor: DashboardActorContextV2, row) -> DashboardAiProposalV2:
        if str(row.tenant_id) != actor.tenant_id or str(row.created_by_user_id) != actor.user_id:
            raise DashboardAiAssistanceError("DASHBOARD_AI_PROPOSAL_NOT_FOUND", "Proposta não encontrada.", 404)
        latest_row = await self.versions.latest(actor.tenant_id, str(row.id))
        latest = DashboardAiProposalVersionV2.model_validate_json(json.dumps(latest_row.content_json, ensure_ascii=False)) if latest_row else None
        clarification = None
        open_rows = await self.clarifications.open_for(actor.tenant_id, str(row.id))
        if open_rows:
            questions = tuple(DashboardAiClarificationQuestionV2.model_validate_json(json.dumps(item.question_json, ensure_ascii=False)) for item in open_rows)
            clarification = DashboardAiClarificationRequestV2(
                proposal_id=str(row.id), proposal_version=row.current_version, questions=questions,
                expires_at=min(item.expires_at for item in open_rows), lock_version=max(item.lock_version for item in open_rows),
            )
        return DashboardAiProposalV2(
            proposal_id=str(row.id), operation=DashboardAiOperationV2(row.operation), origin=DashboardAiRequestOriginV2(row.origin), status=DashboardAiProposalStatusV2(row.status),
            current_version=row.current_version, lock_version=row.lock_version, latest=latest, clarification=clarification,
            target_dashboard_id=str(row.target_dashboard_id) if row.target_dashboard_id else None,
            target_revision_id=str(row.target_revision_id) if row.target_revision_id else None,
            applied_dashboard_id=str(row.applied_dashboard_id) if row.applied_dashboard_id else None,
            applied_revision_id=str(row.applied_revision_id) if row.applied_revision_id else None,
            created_at=row.created_at, updated_at=row.updated_at,
        )

    async def decide(self, *, actor: DashboardActorContextV2, proposal_id: str, version: int, decision: str, comment: str, expected_lock: int, idempotency_key: str) -> DashboardAiProposalDecisionV2:
        DashboardAiPolicyV2.require(actor.global_role, DashboardAiCapabilityV2.DECIDE)
        row = await self.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
        if row.status != "READY_FOR_REVIEW" or version != row.current_version:
            raise DashboardAiAssistanceError("DASHBOARD_AI_DECISION_STALE", "A versão não está pronta para decisão.", 409)
        existing = await self.decisions.for_version(actor.tenant_id, proposal_id, version)
        if existing:
            if existing.decision != decision: raise DashboardAiAssistanceError("DASHBOARD_AI_IDEMPOTENCY_CONFLICT", "A versão já recebeu outra decisão.", 409)
            return self._decision_contract(existing)
        scope = checksum({"tenant": actor.tenant_id, "proposal": proposal_id, "version": version, "key": idempotency_key})
        item = await self.decisions.append(
            id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, proposal_version=version, decision=decision,
            comment=comment, decided_by_user_id=uuid.UUID(actor.user_id), idempotency_scope=scope,
            request_checksum=checksum({"decision": decision, "comment": comment}),
        )
        target = DashboardAiProposalStatusV2.ACCEPTED if decision == "ACCEPT" else DashboardAiProposalStatusV2.REJECTED
        await self._transition(actor, row, target, expected_lock=expected_lock)
        await self._audit(actor, row, f"PROPOSAL_{target.value}")
        return self._decision_contract(item)

    async def answer_clarification(self, *, actor: DashboardActorContextV2, proposal_id: str, response: DashboardAiClarificationResponseV2) -> DashboardAiProposalV2:
        DashboardAiPolicyV2.require(actor.global_role, DashboardAiCapabilityV2.REVISE)
        row = await self.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
        if row.status != "NEEDS_CLARIFICATION":
            raise DashboardAiAssistanceError("DASHBOARD_AI_CLARIFICATION_NOT_OPEN", "A proposta não aguarda esclarecimento.", 409)
        open_rows = await self.clarifications.open_for(actor.tenant_id, proposal_id)
        selected_row = next((item for item in open_rows if item.question_json.get("question_id") == response.question_id), None)
        if selected_row is None:
            raise DashboardAiAssistanceError("DASHBOARD_AI_CLARIFICATION_NOT_FOUND", "Pergunta de esclarecimento não encontrada.", 404)
        question = DashboardAiClarificationQuestionV2.model_validate_json(json.dumps(selected_row.question_json, ensure_ascii=False))
        allowed = {item.option_id: item for item in question.options}
        if any(option_id not in allowed for option_id in response.selected_option_ids):
            raise DashboardAiAssistanceError("DASHBOARD_AI_CLARIFICATION_OPTION_INVALID", "Opção não pertence ao esclarecimento.", 422)
        chosen = tuple(allowed[item] for item in response.selected_option_ids)
        await self.clarifications.answer_cas(
            tenant_id=actor.tenant_id, proposal_id=proposal_id, clarification_id=str(selected_row.id),
            expected_lock=response.expected_lock_version, user_id=actor.user_id,
            response_json=response.model_dump(mode="json"),
        )
        remaining = await self.clarifications.open_for(actor.tenant_id, proposal_id)
        if remaining:
            return await self.contract(actor, row)
        intent = DashboardAiDesignIntentV2.model_validate_json(json.dumps(row.intent_json, ensure_ascii=False))
        references = tuple(item.canonical_reference for item in chosen if item.canonical_reference)
        if question.kind == "METRIC":
            labels = tuple(item.label for item in chosen)
            intent = intent.model_copy(update={"metric_mentions": labels})
        elif question.kind == "PERIOD":
            period_mentions = () if "period.last.closed.month" in references else ("mês atual",)
            intent = intent.model_copy(update={"period_mentions": period_mentions})
        row.intent_json = intent.model_dump(mode="json")
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.RESOLVING)
        resolution = self.resolver.resolve(proposal_id=proposal_id, intent=intent)
        if resolution.blocking_code or resolution.clarifications or resolution.design_spec is None:
            row = await self._transition(actor, row, DashboardAiProposalStatusV2.BLOCKED)
            return await self.contract(actor, row)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.SYNTHESIZING)
        blueprint = self.synthesis.synthesize(resolution.design_spec)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.VALIDATING)
        blueprint_proposal, validation_evidence, warnings, risks = self.validator.validate_blueprint(blueprint, resolution.design_spec)
        rationale = DashboardAiRationaleServiceV2.for_design(resolution.design_spec)
        evidence = resolution.evidence + validation_evidence
        version = DashboardAiProposalVersionV2(
            proposal_id=proposal_id, version=row.current_version, status=DashboardAiProposalStatusV2.READY_FOR_REVIEW,
            blueprint_proposal=blueprint_proposal, rationale=rationale, evidence=evidence, warnings=warnings, risks=risks,
            content_checksum=checksum({"proposal": blueprint_proposal, "rationale": rationale, "evidence": evidence}), created_at=datetime.now(timezone.utc),
        )
        await self.versions.append(id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, version=row.current_version, status=version.status.value, content_json=version.model_dump(mode="json"), content_checksum=version.content_checksum, created_by_user_id=uuid.UUID(actor.user_id))
        for item in evidence:
            await self.evidence.append(id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, proposal_version=row.current_version, evidence_type=item.evidence_type, canonical_reference=item.canonical_reference, public_label=item.public_label, authority_version=item.authority_version, evidence_checksum=item.checksum)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.READY_FOR_REVIEW)
        await self._audit(actor, row, "CLARIFICATION_RESOLVED")
        return await self.contract(actor, row)

    async def cancel(self, *, actor: DashboardActorContextV2, proposal_id: str, expected_lock: int) -> DashboardAiProposalV2:
        row = await self.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
        row = await self._transition(actor, row, DashboardAiProposalStatusV2.CANCELLED, expected_lock=expected_lock)
        await self._audit(actor, row, "PROPOSAL_CANCELLED")
        return await self.contract(actor, row)

    async def _transition(self, actor, row, target: DashboardAiProposalStatusV2, *, expected_lock: int | None = None, **extra):
        current = DashboardAiProposalStatusV2(row.status)
        DashboardAiProposalStateMachineV2.assert_transition(current, target)
        lock = row.lock_version if expected_lock is None else expected_lock
        return await self.proposals.transition_cas(tenant_id=actor.tenant_id, proposal_id=str(row.id), expected_lock=lock, current_status=current.value, target_status=target.value, **extra)

    async def _audit(self, actor, row, event_type: str, *, outcome: str = "SUCCESS") -> None:
        metadata = {"status": row.status, "version": row.current_version}
        await self.audit.append(id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id, actor_user_id=uuid.UUID(actor.user_id), event_type=event_type, outcome=outcome, metadata_json=metadata, metadata_checksum=checksum(metadata))

    @staticmethod
    def _decision_contract(row) -> DashboardAiProposalDecisionV2:
        return DashboardAiProposalDecisionV2(decision_id=str(row.id), proposal_id=str(row.proposal_id), proposal_version=row.proposal_version, decision=row.decision, comment=row.comment, decided_by_user_id=str(row.decided_by_user_id), decided_at=row.decided_at)


class DashboardAiProposalApplicationServiceV2:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.proposals = DashboardAiProposalRepositoryV2(session)
        self.versions = DashboardAiProposalVersionRepositoryV2(session)
        self.decisions = DashboardAiDecisionRepositoryV2(session)
        self.audit = DashboardAiAuditRepositoryV2(session)
        self.dashboard_repository = DashboardRepositoryV2(session)
        self.revision_repository = DashboardRevisionRepositoryV2(session)

    async def apply(self, *, actor: DashboardActorContextV2, proposal_id: str, request: DashboardAiApplyRequestV2, idempotency_key: str) -> DashboardAiApplyResultV2:
        row = await self.proposals.get(actor.tenant_id, proposal_id, user_id=actor.user_id)
        capability = DashboardAiCapabilityV2.APPLY_CREATE if row.operation == "CREATE_DASHBOARD" else DashboardAiCapabilityV2.APPLY_EDIT
        DashboardAiPolicyV2.require(actor.global_role, capability)
        if row.status == "APPLIED" and row.applied_dashboard_id and row.applied_revision_id:
            return DashboardAiApplyResultV2(proposal_id=proposal_id, proposal_version=request.proposal_version, status="APPLIED", dashboard_id=str(row.applied_dashboard_id), revision_id=str(row.applied_revision_id), replayed=True)
        if row.status != "ACCEPTED" or row.current_version != request.proposal_version:
            raise DashboardAiAssistanceError("DASHBOARD_AI_APPLY_NOT_ACCEPTED", "Somente a versão aceita pode ser aplicada.", 409)
        if await self.decisions.for_version(actor.tenant_id, proposal_id, request.proposal_version) is None:
            raise DashboardAiAssistanceError("DASHBOARD_AI_HUMAN_CONFIRMATION_REQUIRED", "A decisão humana é obrigatória.", 409)
        version_row = await self.versions.get(actor.tenant_id, proposal_id, request.proposal_version)
        version = DashboardAiProposalVersionV2.model_validate_json(json.dumps(version_row.content_json, ensure_ascii=False))
        if version.content_checksum != version_row.content_checksum:
            raise DashboardAiAssistanceError("DASHBOARD_AI_CHECKSUM_MISMATCH", "A versÃ£o persistida falhou na verificaÃ§Ã£o de integridade.", 409)
        if version.semantic_proposal and checksum(version.semantic_proposal.patch) != version.semantic_proposal.patch_checksum:
            raise DashboardAiAssistanceError("DASHBOARD_AI_CHECKSUM_MISMATCH", "O patch semÃ¢ntico falhou na verificaÃ§Ã£o de integridade.", 409)
        if version.visual_proposal and checksum(version.visual_proposal.patch) != version.visual_proposal.patch_checksum:
            raise DashboardAiAssistanceError("DASHBOARD_AI_CHECKSUM_MISMATCH", "O patch visual falhou na verificaÃ§Ã£o de integridade.", 409)
        row = await self.proposals.transition_cas(tenant_id=actor.tenant_id, proposal_id=proposal_id, expected_lock=request.expected_lock_version, current_status="ACCEPTED", target_status="APPLYING")
        if version.blueprint_proposal:
            item = version.blueprint_proposal
            created = await DashboardAuthoringServiceV2(self.session).create(
                actor=actor,
                request=DashboardCreateRequestV2(canonical_name=item.blueprint.identity.canonical_name, title=item.blueprint.identity.title, description=item.blueprint.identity.description, blueprint=item.blueprint, origin=DashboardOriginV2.AI_PROPOSED, reason="Aplicação humana de proposta assistida por IA."),
                idempotency_key=idempotency_key, idempotency_operation="APPLY_DASHBOARD_AI_PROPOSAL",
                idempotency_payload=request, idempotency_resource_id=proposal_id,
            )
            dashboard_id, revision_id, replayed = created.dashboard.identity.dashboard_id, created.revision.revision_id, created.replayed
        elif version.semantic_proposal and row.target_dashboard_id:
            dashboard = await self.dashboard_repository.get(actor.tenant_id, str(row.target_dashboard_id))
            base = await self.revision_repository.get(actor.tenant_id, str(row.target_dashboard_id), version.semantic_proposal.intent.target_revision_id)
            applied = await DashboardPatchServiceV2(self.session).apply_semantic(actor=actor, dashboard_id=str(row.target_dashboard_id), request=DashboardSemanticPatchRequestV2(patch=version.semantic_proposal.patch, expected_dashboard_lock_version=dashboard.lock_version, expected_revision_lock_version=base.lock_version, reason="Aplicação humana de proposta semântica assistida."), idempotency_key=idempotency_key)
            dashboard_id, revision_id, replayed = str(row.target_dashboard_id), applied.revision_id, False
        elif version.visual_proposal and row.target_dashboard_id:
            dashboard = await self.dashboard_repository.get(actor.tenant_id, str(row.target_dashboard_id))
            base = await self.revision_repository.get(actor.tenant_id, str(row.target_dashboard_id), str(row.target_revision_id))
            applied = await DashboardPatchServiceV2(self.session).apply_visual(actor=actor, dashboard_id=str(row.target_dashboard_id), request=DashboardVisualPatchRequestV2(patch=version.visual_proposal.patch, expected_dashboard_lock_version=dashboard.lock_version, expected_revision_lock_version=base.lock_version, reason="Aplicação humana de proposta visual assistida."), idempotency_key=idempotency_key)
            dashboard_id, revision_id, replayed = str(row.target_dashboard_id), applied.revision_id, False
        else:
            raise DashboardAiAssistanceError("DASHBOARD_AI_APPLY_PAYLOAD_INVALID", "Conteúdo aplicável ausente.", 422)
        row = await self.proposals.transition_cas(tenant_id=actor.tenant_id, proposal_id=proposal_id, expected_lock=row.lock_version, current_status="APPLYING", target_status="APPLIED", applied_dashboard_id=uuid.UUID(dashboard_id), applied_revision_id=uuid.UUID(revision_id))
        metadata = {"status": row.status, "version": row.current_version, "dashboard_id": dashboard_id, "revision_id": revision_id}
        await self.audit.append(
            id=uuid.uuid4(), proposal_id=row.id, tenant_id=row.tenant_id,
            actor_user_id=uuid.UUID(actor.user_id), event_type="DASHBOARD_AI_PROPOSAL_APPLIED",
            outcome="SUCCESS", metadata_json=metadata, metadata_checksum=checksum(metadata),
        )
        return DashboardAiApplyResultV2(proposal_id=proposal_id, proposal_version=request.proposal_version, status="APPLIED", dashboard_id=dashboard_id, revision_id=revision_id, replayed=replayed)
