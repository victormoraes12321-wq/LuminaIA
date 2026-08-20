"""Static Governed Job Registry for V2 Work Queue."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from contracts.work_queue_v2.enums import (
    ConcurrencyClassV2,
    WorkQueueErrorClassV2,
    WorkQueueJobPriorityV2,
    WorkQueueJobTypeV2,
)

JobHandlerCallable = Callable[[str, dict[str, str]], Awaitable[dict[str, str]]]


@dataclass(frozen=True)
class JobTypeSpecV2:
    job_type: WorkQueueJobTypeV2
    default_priority: WorkQueueJobPriorityV2
    max_attempts: int
    timeout_seconds: float
    lease_duration_seconds: int
    heartbeat_interval_seconds: int
    concurrency_class: ConcurrencyClassV2
    retryable_errors: tuple[WorkQueueErrorClassV2, ...]
    cancellation_supported: bool
    description: str


DEFAULT_RETRYABLE = (
    WorkQueueErrorClassV2.DATABASE_TRANSIENT,
    WorkQueueErrorClassV2.TEMPORARY_RESOURCE_EXHAUSTION,
    WorkQueueErrorClassV2.LEASE_LOST,
    WorkQueueErrorClassV2.DEPENDENCY_TEMPORARILY_UNAVAILABLE,
    WorkQueueErrorClassV2.TIMEOUT_RETRYABLE,
)


class GovernedJobRegistryV2:
    _specs: dict[WorkQueueJobTypeV2, JobTypeSpecV2] = {
        WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.POST_SYNC_INSIGHT_RUN,
            default_priority=WorkQueueJobPriorityV2.HIGH,
            max_attempts=3,
            timeout_seconds=120.0,
            lease_duration_seconds=60,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.CPU_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Executa o pipeline determinístico de Post-Sync Insights",
        ),
        WorkQueueJobTypeV2.MATERIALIZATION_BUILD: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.MATERIALIZATION_BUILD,
            default_priority=WorkQueueJobPriorityV2.NORMAL,
            max_attempts=3,
            timeout_seconds=300.0,
            lease_duration_seconds=120,
            heartbeat_interval_seconds=30,
            concurrency_class=ConcurrencyClassV2.MATERIALIZATION_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Constrói materialização de catálogo/cubo analítico",
        ),
        WorkQueueJobTypeV2.MATERIALIZATION_REFRESH: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.MATERIALIZATION_REFRESH,
            default_priority=WorkQueueJobPriorityV2.NORMAL,
            max_attempts=3,
            timeout_seconds=180.0,
            lease_duration_seconds=60,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.MATERIALIZATION_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Atualiza incrementalmente materialização analítica",
        ),
        WorkQueueJobTypeV2.CACHE_REFRESH: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.CACHE_REFRESH,
            default_priority=WorkQueueJobPriorityV2.LOW,
            max_attempts=2,
            timeout_seconds=60.0,
            lease_duration_seconds=30,
            heartbeat_interval_seconds=10,
            concurrency_class=ConcurrencyClassV2.DB_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Pré-aquece entrada de Smart Cache",
        ),
        WorkQueueJobTypeV2.EVALUATION_RUN: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.EVALUATION_RUN,
            default_priority=WorkQueueJobPriorityV2.BACKGROUND,
            max_attempts=2,
            timeout_seconds=180.0,
            lease_duration_seconds=60,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.CPU_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Executa suíte de avaliação de regressão",
        ),
        WorkQueueJobTypeV2.DASHBOARD_BACKGROUND_REFRESH: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.DASHBOARD_BACKGROUND_REFRESH,
            default_priority=WorkQueueJobPriorityV2.LOW,
            max_attempts=2,
            timeout_seconds=90.0,
            lease_duration_seconds=45,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.BACKGROUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Atualiza widgets de dashboard em background",
        ),
        WorkQueueJobTypeV2.ANALYTICAL_BACKGROUND_QUERY: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.ANALYTICAL_BACKGROUND_QUERY,
            default_priority=WorkQueueJobPriorityV2.NORMAL,
            max_attempts=3,
            timeout_seconds=120.0,
            lease_duration_seconds=60,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.DB_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Executa consulta analítica longa em background",
        ),
        WorkQueueJobTypeV2.SYNC_POST_PROCESSING: JobTypeSpecV2(
            job_type=WorkQueueJobTypeV2.SYNC_POST_PROCESSING,
            default_priority=WorkQueueJobPriorityV2.HIGH,
            max_attempts=3,
            timeout_seconds=180.0,
            lease_duration_seconds=60,
            heartbeat_interval_seconds=15,
            concurrency_class=ConcurrencyClassV2.CPU_BOUND,
            retryable_errors=DEFAULT_RETRYABLE,
            cancellation_supported=True,
            description="Processamento pós-sincronização de catálogo",
        ),
    }

    _handlers: dict[WorkQueueJobTypeV2, JobHandlerCallable] = {}

    @classmethod
    def get_spec(cls, job_type: WorkQueueJobTypeV2) -> JobTypeSpecV2:
        if job_type not in cls._specs:
            raise KeyError(f"Unregistered job type: {job_type}")
        return cls._specs[job_type]

    @classmethod
    def register_handler(cls, job_type: WorkQueueJobTypeV2, handler: JobHandlerCallable) -> None:
        if job_type not in cls._specs:
            raise KeyError(f"Cannot register handler for unknown job type: {job_type}")
        cls._handlers[job_type] = handler

    @classmethod
    def get_handler(cls, job_type: WorkQueueJobTypeV2) -> JobHandlerCallable | None:
        return cls._handlers.get(job_type)

    @classmethod
    def list_specs(cls) -> list[JobTypeSpecV2]:
        return list(cls._specs.values())
