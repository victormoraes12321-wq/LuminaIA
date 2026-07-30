from __future__ import annotations

import hashlib
import json
from datetime import timezone
from decimal import Decimal

from contracts.analytical_v2 import (
    ConfidenceAssessment,
    ConfidenceLevel,
    FieldOrigin,
    FilterOperator,
    FilterSpecification,
    VisualizationKind,
    VisualizationSpecification,
)
from contracts.conversation_state_v2 import ConversationStateV2
from contracts.user_analytical_profile_v2 import (
    AnalyticalDefaultPreferenceV2,
    ConsentStatus,
    PreferenceApplicationContext,
    PreferenceApplicationDecisionV2,
    PreferenceApplicationResultV2,
    PreferenceConflictV2,
    PreferenceDecision,
    PreferenceOrigin,
    PreferenceRisk,
    PreferenceStatus,
    PresentationPreferenceV2,
    PublicAppliedPreferenceItemV2,
    PublicAppliedPreferenceSummaryV2,
    UserAnalyticalProfileV2,
    UserPreferenceItemV2,
    UserPreferenceType,
    UserProfileRolloutMode,
)
from services.context_resolution import ContextResolutionResult

from .policies import policy_for_item


def stable_fingerprint(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        level=ConfidenceLevel.HIGH,
        score=Decimal("1"),
        reasons=["Preferência explícita e governada do usuário."],
        requires_confirmation=False,
    )


def _consent_status(item: UserPreferenceItemV2) -> ConsentStatus:
    if item.risk == PreferenceRisk.SAFE_PRESENTATION:
        return ConsentStatus.NOT_REQUIRED
    if item.consent is None:
        return ConsentStatus.MISSING
    return item.consent.status


class UserPreferenceApplicationEngine:
    """Pure profile resolver. It never persists, queries a database or calculates values."""

    def apply(
        self,
        *,
        current_intent,
        current_question: str,
        conversation_state: ConversationStateV2,
        context_resolution: ContextResolutionResult,
        profile: UserAnalyticalProfileV2,
        context: PreferenceApplicationContext,
    ) -> PreferenceApplicationResultV2:
        if profile.tenant_id != context.tenant_id or profile.user_id != context.user_id:
            raise ValueError("profile identity does not match authenticated application context")
        if current_intent != context_resolution.resolved_intent:
            raise ValueError("preferences must run after context resolution")
        if current_question != context.current_question:
            raise ValueError("application question does not match context")

        intent = current_intent
        decisions: list[PreferenceApplicationDecisionV2] = []
        conflicts: list[PreferenceConflictV2] = []
        public_items: list[PublicAppliedPreferenceItemV2] = []
        ignored: list[str] = []
        consent_required: list[str] = []
        applied_ids = []

        for item in sorted(profile.preferences, key=lambda value: (value.preference_key, str(value.preference_id))):
            decision, intent, conflict, public_item = self._apply_item(
                item=item,
                intent=intent,
                profile=profile,
                conversation_state=conversation_state,
                context=context,
            )
            decisions.append(decision)
            if conflict:
                conflicts.append(conflict)
                ignored.append(conflict.public_message)
            if public_item:
                public_items.append(public_item)
            if decision.decision == PreferenceDecision.CONSENT_REQUIRED:
                consent_required.append(item.preference_key)
            if decision.decision == PreferenceDecision.APPLIED:
                applied_ids.append(item.preference_id)

        shadow = context.rollout_mode in {
            UserProfileRolloutMode.LEGACY_ONLY,
            UserProfileRolloutMode.SHADOW,
        }
        final_intent = current_intent if shadow else intent
        summary = PublicAppliedPreferenceSummaryV2(
            applied=[] if shadow else public_items,
            ignored=ignored,
            consent_required=consent_required,
            has_visible_analytical_default=any(
                item.preference_type == UserPreferenceType.ANALYTICAL_DEFAULT
                for item in public_items
            ) if not shadow else False,
        )
        payload = {
            "intent": final_intent.model_dump(mode="json"),
            "decisions": [decision.model_dump(mode="json") for decision in decisions],
            "profile_version": profile.profile_version,
            "shadow": shadow,
        }
        return PreferenceApplicationResultV2(
            resolved_intent=final_intent,
            readiness=context_resolution.readiness,
            decisions=decisions,
            conflicts=conflicts,
            public_summary=summary,
            applied_preference_ids=[] if shadow else applied_ids,
            profile_version=profile.profile_version,
            deterministic_fingerprint=stable_fingerprint(payload),
            shadow_only=shadow,
        )

    def _apply_item(
        self,
        *,
        item: UserPreferenceItemV2,
        intent,
        profile: UserAnalyticalProfileV2,
        conversation_state: ConversationStateV2,
        context: PreferenceApplicationContext,
    ):
        field_path = self._field_path(item)
        consent_status = _consent_status(item)

        def decision(kind: PreferenceDecision, reason: str, *, visible: bool = False):
            return PreferenceApplicationDecisionV2(
                preference_id=item.preference_id,
                preference_key=item.preference_key,
                field_path=field_path,
                decision=kind,
                reason_code=reason,
                risk=item.risk,
                origin=item.origin.kind,
                consent_status=consent_status,
                visible_to_user=visible,
            )

        if profile.status.value != "ACTIVE":
            return decision(PreferenceDecision.SKIPPED, "PROFILE_NOT_ACTIVE"), intent, None, None
        if item.status != PreferenceStatus.ACTIVE:
            return decision(PreferenceDecision.SKIPPED, f"PREFERENCE_{item.status.value}"), intent, None, None
        now = context.reference_datetime.astimezone(timezone.utc)
        if item.expires_at and item.expires_at.astimezone(timezone.utc) <= now:
            return decision(PreferenceDecision.SKIPPED, "PREFERENCE_EXPIRED"), intent, None, None
        if item.effective_from and item.effective_from.astimezone(timezone.utc) > now:
            return decision(PreferenceDecision.SKIPPED, "PREFERENCE_NOT_EFFECTIVE"), intent, None, None
        if item.effective_to and item.effective_to.astimezone(timezone.utc) <= now:
            return decision(PreferenceDecision.SKIPPED, "PREFERENCE_NO_LONGER_EFFECTIVE"), intent, None, None
        policy = policy_for_item(item)
        if policy is None or item.risk == PreferenceRisk.FORBIDDEN:
            return decision(PreferenceDecision.BLOCKED, "FIELD_POLICY_FORBIDS_APPLICATION"), intent, None, None
        if item.origin.kind not in policy.allowed_origins:
            return decision(PreferenceDecision.SKIPPED, "ORIGIN_NOT_AUTO_APPLICABLE"), intent, None, None
        if policy.consent_required and consent_status != ConsentStatus.GRANTED:
            return decision(PreferenceDecision.CONSENT_REQUIRED, "ACTIVE_CONSENT_REQUIRED", visible=True), intent, None, None
        if item.risk == PreferenceRisk.REFERENCE_ONLY:
            return decision(PreferenceDecision.SKIPPED, "REFERENCE_ONLY"), intent, None, None
        if context.pending_clarification and item.risk != PreferenceRisk.SAFE_PRESENTATION:
            return decision(PreferenceDecision.SKIPPED, "PENDING_CLARIFICATION"), intent, None, None
        if context.reset_explicit and item.risk != PreferenceRisk.SAFE_PRESENTATION:
            return decision(PreferenceDecision.SKIPPED, "RESET_BLOCKS_DEFAULTS_THIS_TURN", visible=True), intent, None, None
        if field_path in context.removal_fields and item.risk != PreferenceRisk.SAFE_PRESENTATION:
            conflict = PreferenceConflictV2(
                preference_id=item.preference_id,
                field_path=field_path,
                reason_code="EXPLICIT_REMOVAL_WINS",
                public_message=f"{item.preference_key} não foi aplicado porque você removeu esse filtro neste turno.",
                blocks_application=True,
            )
            return decision(PreferenceDecision.CONFLICT, "EXPLICIT_REMOVAL_WINS", visible=True), intent, conflict, None

        if isinstance(item.content, PresentationPreferenceV2):
            return self._presentation(item, intent, decision)
        if isinstance(item.content, AnalyticalDefaultPreferenceV2):
            return self._analytical_default(
                item, intent, conversation_state, context, decision,
            )

        extensions = dict(intent.contract.extensions)
        extensions.setdefault("user_profile", {})
        profile_extension = dict(extensions["user_profile"])
        profile_extension[item.preference_type.value.lower()] = item.content.model_dump(
            mode="json", exclude={"kind"}
        )
        extensions["user_profile"] = profile_extension
        updated = intent.model_copy(
            update={"contract": intent.contract.model_copy(update={"extensions": extensions})}
        )
        public = self._public(item, item.preference_key)
        return decision(PreferenceDecision.APPLIED, "SAFE_PRESENTATION_APPLIED"), updated, None, public

    def _presentation(self, item, intent, decision):
        content: PresentationPreferenceV2 = item.content
        existing = list(intent.requested_visualizations)
        requested_explicitly = any(
            visual.origin == FieldOrigin.EXPLICIT_USER for visual in existing
        )
        visual_name = content.preferred_visualization
        if requested_explicitly or visual_name == "AUTO":
            selected = existing
            reason = "EXPLICIT_VISUALIZATION_WINS" if requested_explicitly else "PRESENTATION_OPTIONS_APPLIED"
        else:
            kind = VisualizationKind(visual_name)
            selected = [
                VisualizationSpecification(
                    visualization_id=f"profile.{item.preference_id.hex[:16]}",
                    kind=kind,
                    title="Visualização preferida",
                    metric_ids=[metric.metric_id for metric in intent.metric_refs],
                    dimension_ids=[dimension.dimension_id for dimension in intent.dimension_refs],
                    data_reference="profile.presentation",
                    priority=100,
                    is_primary=True,
                    origin=FieldOrigin.USER_PREFERENCE,
                    options={
                        "table_density": content.table_density,
                        "page_size": content.page_size,
                        "decimal_places": content.decimal_places,
                        "chart_granularity": content.chart_granularity,
                    },
                )
            ]
            reason = "SAFE_PRESENTATION_APPLIED"
        extensions = dict(intent.contract.extensions)
        extensions["user_profile_presentation"] = {
            "table_density": content.table_density,
            "page_size": content.page_size,
            "decimal_places": content.decimal_places,
            "theme": content.theme,
        }
        updated = intent.model_copy(
            update={
                "requested_visualizations": selected,
                "contract": intent.contract.model_copy(update={"extensions": extensions}),
            }
        )
        return decision(PreferenceDecision.APPLIED, reason), updated, None, self._public(
            item, content.preferred_visualization
        )

    def _analytical_default(self, item, intent, conversation_state, context, decision):
        content: AnalyticalDefaultPreferenceV2 = item.content
        target = content.target_field
        occupied = {
            "metric": bool(intent.metric_refs),
            "dimension": bool(intent.dimension_refs),
            "filter": bool(intent.filters),
            "period": bool(intent.time_windows),
            "entity": bool(
                intent.comparison
                and any(operand.entity_refs for operand in intent.comparison.operands)
            ),
            "ordering": False,
            "limit": False,
        }[target]
        if occupied:
            conflict = PreferenceConflictV2(
                preference_id=item.preference_id,
                field_path=self._field_path(item),
                reason_code="CURRENT_REQUEST_OR_CONTEXT_WINS",
                public_message=f"{item.preference_key} não foi aplicado porque o pedido ou o contexto atual já definiu esse campo.",
                blocks_application=False,
            )
            return decision(PreferenceDecision.SKIPPED, "CURRENT_REQUEST_OR_CONTEXT_WINS", visible=True), intent, conflict, None

        updated = intent
        if target == "metric":
            ref = next(
                (value for value in context.governed_metric_refs if value.metric_id == content.canonical_id),
                None,
            )
            if ref is None:
                return decision(PreferenceDecision.BLOCKED, "KNOWLEDGE_REFERENCE_INVALID", visible=True), intent, None, None
            updated = intent.model_copy(update={
                "metric_refs": [ref.model_copy(update={"origin": FieldOrigin.USER_PREFERENCE})],
                "field_origins": {**intent.field_origins, "metric_refs": FieldOrigin.USER_PREFERENCE},
            })
        elif target == "dimension":
            ref = next(
                (value for value in context.governed_dimension_refs if value.dimension_id == content.canonical_id),
                None,
            )
            if ref is None:
                return decision(PreferenceDecision.BLOCKED, "KNOWLEDGE_REFERENCE_INVALID", visible=True), intent, None, None
            updated = intent.model_copy(update={
                "dimension_refs": [ref.model_copy(update={"origin": FieldOrigin.USER_PREFERENCE})],
                "field_origins": {**intent.field_origins, "dimension_refs": FieldOrigin.USER_PREFERENCE},
            })
        elif target == "filter":
            if (
                content.filter_field_id not in context.allowed_filter_fields
                or content.canonical_id not in context.allowed_canonical_ids
            ):
                return decision(PreferenceDecision.BLOCKED, "KNOWLEDGE_REFERENCE_INVALID", visible=True), intent, None, None
            operator = FilterOperator(content.filter_operator)
            values = list(content.filter_values)
            spec = FilterSpecification(
                filter_id=f"profile.{item.preference_id.hex[:16]}",
                field_id=content.filter_field_id,
                operator=operator,
                value=values[0] if operator == FilterOperator.EQ else None,
                values=values if operator == FilterOperator.IN else [],
                origin=FieldOrigin.USER_PREFERENCE,
                confidence=_confidence(),
                is_explicit=False,
            )
            updated = intent.model_copy(update={
                "filters": [spec],
                "field_origins": {**intent.field_origins, "filters": FieldOrigin.USER_PREFERENCE},
            })
        elif target == "period":
            ref = next(
                (value for value in context.governed_time_windows if value.window_id == content.period_key),
                None,
            )
            if ref is None:
                return decision(PreferenceDecision.BLOCKED, "TEMPORAL_REFERENCE_INVALID", visible=True), intent, None, None
            updated = intent.model_copy(update={
                "time_windows": [ref.model_copy(update={"origin": FieldOrigin.USER_PREFERENCE})],
                "field_origins": {**intent.field_origins, "time_windows": FieldOrigin.USER_PREFERENCE},
            })
        elif target == "entity":
            return decision(PreferenceDecision.SKIPPED, "ENTITY_DEFAULT_REQUIRES_PLANNER_ADAPTER", visible=True), intent, None, None
        else:
            extensions = dict(intent.contract.extensions)
            profile_plan = dict(extensions.get("user_profile_plan_defaults", {}))
            profile_plan[target] = content.limit if target == "limit" else content.canonical_id
            extensions["user_profile_plan_defaults"] = profile_plan
            updated = intent.model_copy(
                update={"contract": intent.contract.model_copy(update={"extensions": extensions})}
            )

        return decision(PreferenceDecision.APPLIED, "CONSENTED_DEFAULT_FILLED_GAP", visible=True), updated, None, self._public(
            item, content.display_label
        )

    @staticmethod
    def _field_path(item: UserPreferenceItemV2) -> str:
        if isinstance(item.content, AnalyticalDefaultPreferenceV2):
            return {
                "metric": "metrics",
                "dimension": "dimensions",
                "entity": "entities",
                "filter": "filters",
                "period": "default_period",
                "ordering": "ordering",
                "limit": "limit",
            }[item.content.target_field]
        return item.preference_type.value.lower()

    @staticmethod
    def _public(item: UserPreferenceItemV2, value: str) -> PublicAppliedPreferenceItemV2:
        return PublicAppliedPreferenceItemV2(
            preference_type=item.preference_type,
            label=item.preference_key,
            value_label=str(value),
            origin_label={
                PreferenceOrigin.USER_EXPLICIT: "Definido por você",
                PreferenceOrigin.SYSTEM_DEFAULT: "Padrão do sistema",
                PreferenceOrigin.ADMIN_POLICY: "Política permitida",
                PreferenceOrigin.LEGACY_IMPORT: "Importado do sistema anterior",
                PreferenceOrigin.MIGRATED: "Migrado",
                PreferenceOrigin.FEEDBACK_CANDIDATE: "Sugestão não confirmada",
                PreferenceOrigin.INFERRED_UNCONFIRMED: "Inferência não confirmada",
            }[item.origin.kind],
            expires_at=item.expires_at,
        )
