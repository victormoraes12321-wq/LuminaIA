from __future__ import annotations

import logging
from dataclasses import dataclass, field

from contracts.enterprise_knowledge_v2 import CONTRACT_VERSION, KnowledgeRolloutMode

logger = logging.getLogger("luminaai.enterprise_knowledge.observability")


@dataclass
class KnowledgeCounters:
    mode: KnowledgeRolloutMode
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def snapshot(self) -> dict[str, str | int]:
        return {
            "contract_version": CONTRACT_VERSION,
            "mode": self.mode.value,
            **self.counters,
        }

    def log_snapshot(self) -> None:
        logger.info("enterprise_knowledge_metrics %s", self.snapshot())
