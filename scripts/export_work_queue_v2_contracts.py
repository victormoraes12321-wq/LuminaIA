"""Export Work Queue V2 Contracts to docs/contracts/work_queue_v2/."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from contracts.work_queue_v2.enums import (
    ConcurrencyClassV2,
    WorkQueueAdmissionDecisionKindV2,
    WorkQueueBackpressureStateKindV2,
    WorkQueueErrorClassV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobStatusV2,
    WorkQueueJobTypeV2,
)
from services.work_queue_v2.registry import GovernedJobRegistryV2

DOCS_DIR = ROOT / "docs" / "contracts" / "work_queue_v2"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def export_contracts() -> None:
    manifest = {
        "contract_version": "lumina.scale-queues-performance/1.0",
        "job_types": [jt.value for jt in WorkQueueJobTypeV2],
        "priorities": [p.value for p in WorkQueueJobPriorityV2],
        "statuses": [s.value for s in WorkQueueJobStatusV2],
        "error_classes": [ec.value for ec in WorkQueueErrorClassV2],
        "concurrency_classes": [cc.value for cc in ConcurrencyClassV2],
        "backpressure_states": [bs.value for bs in WorkQueueBackpressureStateKindV2],
        "admission_decisions": [ad.value for ad in WorkQueueAdmissionDecisionKindV2],
        "registered_job_specs": [
            {
                "job_type": spec.job_type.value,
                "default_priority": spec.default_priority.value,
                "max_attempts": spec.max_attempts,
                "timeout_seconds": spec.timeout_seconds,
                "concurrency_class": spec.concurrency_class.value,
                "cancellation_supported": spec.cancellation_supported,
                "description": spec.description,
            }
            for spec in GovernedJobRegistryV2.list_specs()
        ],
    }

    output_path = DOCS_DIR / "work_queue_v2_manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Work Queue V2 contracts exported to {output_path}")


if __name__ == "__main__":
    export_contracts()
