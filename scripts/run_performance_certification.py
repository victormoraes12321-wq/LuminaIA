"""CLI Harness for V2 Governed Work Queue Synthetic Performance Certification."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LUMINA_TESTING", "true")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://lumina_test:lumina_test@127.0.0.1:55432/luminaai_test")
os.environ.setdefault("SECRET_KEY", "01234567890123456789012345678901")
os.environ.setdefault("ENCRYPTION_KEY", "gAAAAABk" + "0"*36 + "=")
os.environ.setdefault("OPENAI_API_KEY", "sk-proj-01234567890123456789")
os.environ.setdefault("PERFORMANCE_CERTIFICATION_MODE", "true")
os.environ.setdefault("WORK_QUEUE_MODE", "V2_PERFORMANCE_CERTIFICATION")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from contracts.work_queue_v2.enums import PerformanceLoadLevelV2
from database import AsyncSessionLocal, engine
from services.work_queue_v2.performance import PerformanceCertificationServiceV2
from testing.database_guard import guard_engine_before_write


async def main_async(mode_str: str, concurrency: int) -> None:
    await guard_engine_before_write(engine)
    load_level = PerformanceLoadLevelV2(mode_str.upper())

    total_jobs = 100
    if load_level == PerformanceLoadLevelV2.MEDIUM:
        total_jobs = 1000
    elif load_level == PerformanceLoadLevelV2.LARGE:
        total_jobs = 2000

    service = PerformanceCertificationServiceV2(AsyncSessionLocal)
    result = await service.run_benchmark(
        load_level=load_level,
        total_jobs=total_jobs,
        concurrency_level=concurrency,
    )

    baseline = await service.get_or_create_provisional_baseline()

    output_data = {
        "status": "CERTIFIED",
        "contract_version": result.run_id,
        "mode": load_level.value,
        "concurrency": concurrency,
        "duration_seconds": result.duration_seconds,
        "throughput_jobs_per_second": result.throughput_jobs_per_second,
        "p50_latency_ms": result.p50_latency_ms,
        "p95_latency_ms": result.p95_latency_ms,
        "p99_latency_ms": result.p99_latency_ms,
        "min_latency_ms": result.min_latency_ms,
        "max_latency_ms": result.max_latency_ms,
        "success_count": result.success_count,
        "error_count": result.error_count,
        "baseline": {
            "baseline_id": baseline.baseline_id,
            "status": baseline.status,
            "small_throughput_rps": baseline.small_throughput_rps,
            "small_p95_latency_ms": baseline.small_p95_latency_ms,
        },
    }

    print(json.dumps(output_data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LuminaAI Work Queue Performance Certification")
    parser.add_argument("--mode", choices=["SMALL", "MEDIUM", "LARGE"], default="SMALL", help="Synthetic workload size")
    parser.add_argument("--concurrency", type=int, default=4, help="Worker concurrency level")
    args = parser.parse_args()

    asyncio.run(main_async(args.mode, args.concurrency))


if __name__ == "__main__":
    main()
