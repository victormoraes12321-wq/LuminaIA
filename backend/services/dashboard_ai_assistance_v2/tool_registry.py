from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardAiToolCapabilityV2:
    tool_id: str
    purpose: str
    maximum_calls: int


DASHBOARD_AI_TOOL_REGISTRY: tuple[DashboardAiToolCapabilityV2, ...] = (
    DashboardAiToolCapabilityV2("dashboard.metadata.lookup", "Metadados declarativos publicados", 4),
    DashboardAiToolCapabilityV2("dashboard.metric.resolve", "Resolver métrica canônica", 8),
    DashboardAiToolCapabilityV2("dashboard.dimension.resolve", "Resolver dimensão canônica", 8),
    DashboardAiToolCapabilityV2("dashboard.entity.resolve", "Resolver entidade canônica", 8),
    DashboardAiToolCapabilityV2("dashboard.period.normalize", "Normalizar período", 4),
    DashboardAiToolCapabilityV2("dashboard.knowledge.search", "Buscar conhecimento publicado", 4),
    DashboardAiToolCapabilityV2("dashboard.blueprint.validate", "Validar Blueprint V2", 2),
    DashboardAiToolCapabilityV2("dashboard.patch.validate", "Validar patch V2", 2),
)
_ALLOWED = frozenset(item.tool_id for item in DASHBOARD_AI_TOOL_REGISTRY)


class DashboardAiToolPolicyV2:
    @staticmethod
    def require(tool_id: str) -> None:
        if tool_id not in _ALLOWED:
            raise PermissionError("DASHBOARD_AI_TOOL_FORBIDDEN")

    @staticmethod
    def allowed_ids() -> tuple[str, ...]:
        return tuple(sorted(_ALLOWED))

