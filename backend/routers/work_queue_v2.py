"""FastAPI router for V2 Governed Work Queue and Performance management."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User, UserRole
from models.work_queue_v2 import (
    WorkQueueAuditEventModelV2,
    WorkQueueDeadLetterModelV2,
    WorkQueueJobModelV2,
    WorkQueueWorkerModelV2,
    PerformanceBaselineModelV2,
    PerformanceRunModelV2,
)
from routers.auth import get_current_user
from schemas.work_queue_v2 import (
    PerformanceBaselineResponseV2,
    PerformanceRunRequestV2,
    PerformanceRunResponseV2,
    WorkQueueCancelRequestV2,
    WorkQueueDeadLetterListResponseV2,
    WorkQueueDeadLetterResponseV2,
    WorkQueueJobListResponseV2,
    WorkQueueJobResponseV2,
    WorkQueueReplayRequestV2,
    WorkQueueStatsResponseV2,
    WorkQueueWorkerListResponseV2,
    WorkQueueWorkerResponseV2,
)
from services.work_queue_v2.performance import PerformanceCertificationServiceV2
from services.work_queue_v2.queue_service import WorkQueueServiceV2
from services.observability_v2.redaction import ObservabilityRedactionService

router = APIRouter(prefix="/api/v2", tags=["Work Queue V2"])
_queue_service = WorkQueueServiceV2()


def _require_work_queue_enabled() -> None:
    if settings.WORK_QUEUE_MODE == "LEGACY_ONLY" and not settings.WORK_QUEUE_APIS_ENABLED and not settings.PERFORMANCE_CERTIFICATION_MODE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "WORK_QUEUE_NOT_AVAILABLE", "message": "Work Queue V2 is disabled in current mode."},
        )


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "WORK_QUEUE_ACCESS_DENIED", "message": "Work Queue administration requires ADMIN role."},
        )


def _require_gestor_or_admin(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.GESTOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "WORK_QUEUE_ACCESS_DENIED", "message": "Work Queue viewing requires ADMIN or GESTOR role."},
        )


@router.get("/work-queue/jobs", response_model=WorkQueueJobListResponseV2)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueJobListResponseV2:
    _require_work_queue_enabled()
    _require_gestor_or_admin(current_user)

    stmt = select(WorkQueueJobModelV2).where(WorkQueueJobModelV2.tenant_id == current_user.tenant_id).order_by(WorkQueueJobModelV2.created_at.desc()).offset(offset).limit(limit)
    jobs = (await session.execute(stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(WorkQueueJobModelV2).where(WorkQueueJobModelV2.tenant_id == current_user.tenant_id)
    total_count = (await session.execute(count_stmt)).scalar_one()

    items = [
        WorkQueueJobResponseV2(
            job_id=str(j.id),
            tenant_id=str(j.tenant_id),
            job_type=j.job_type,  # type: ignore
            priority=j.priority,  # type: ignore
            status=j.status,  # type: ignore
            attempts_count=j.attempts_count,
            max_attempts=j.max_attempts,
            assigned_worker_id=j.assigned_worker_id,
            available_at=j.available_at,
            created_at=j.created_at,
            claimed_at=j.claimed_at,
            completed_at=j.completed_at,
            last_error_class=j.last_error_class,  # type: ignore
            last_error_message=j.last_error_message,
        )
        for j in jobs
    ]
    return WorkQueueJobListResponseV2(jobs=tuple(items), total_count=total_count)


@router.get("/work-queue/jobs/{job_id}", response_model=WorkQueueJobResponseV2)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueJobResponseV2:
    _require_work_queue_enabled()
    _require_gestor_or_admin(current_user)

    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "WORK_QUEUE_INVALID_JOB_ID", "message": "Invalid job UUID format."})

    stmt = select(WorkQueueJobModelV2).where(and_(WorkQueueJobModelV2.id == j_uuid, WorkQueueJobModelV2.tenant_id == current_user.tenant_id))
    j = (await session.execute(stmt)).scalar_one_or_none()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "WORK_QUEUE_JOB_NOT_FOUND", "message": "Job not found."})

    return WorkQueueJobResponseV2(
        job_id=str(j.id),
        tenant_id=str(j.tenant_id),
        job_type=j.job_type,  # type: ignore
        priority=j.priority,  # type: ignore
        status=j.status,  # type: ignore
        attempts_count=j.attempts_count,
        max_attempts=j.max_attempts,
        assigned_worker_id=j.assigned_worker_id,
        available_at=j.available_at,
        created_at=j.created_at,
        claimed_at=j.claimed_at,
        completed_at=j.completed_at,
        last_error_class=j.last_error_class,  # type: ignore
        last_error_message=j.last_error_message,
    )


@router.post("/work-queue/jobs/{job_id}/cancel", response_model=WorkQueueJobResponseV2)
async def cancel_job(
    job_id: str,
    body: WorkQueueCancelRequestV2,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueJobResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)

    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "WORK_QUEUE_INVALID_JOB_ID", "message": "Invalid job UUID format."})

    stmt = select(WorkQueueJobModelV2).where(and_(WorkQueueJobModelV2.id == j_uuid, WorkQueueJobModelV2.tenant_id == current_user.tenant_id))
    j = (await session.execute(stmt)).scalar_one_or_none()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "WORK_QUEUE_JOB_NOT_FOUND", "message": "Job not found."})

    if j.status in ("SUCCEEDED", "CANCELLED", "EXPIRED", "DEAD_LETTER"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "WORK_QUEUE_ALREADY_TERMINAL", "message": f"Job is already terminal: {j.status}"})

    now = datetime.now(timezone.utc)
    j.status = "CANCELLED"
    j.completed_at = now
    j.updated_at = now
    j.last_error_message = ObservabilityRedactionService().redact_string(body.reason)[:512]

    audit = WorkQueueAuditEventModelV2(
        id=uuid.uuid4(),
        tenant_id=j.tenant_id,
        user_id=current_user.id,
        job_id=j.id,
        action="JOB_CANCELLED",
        details_checksum=uuid.uuid4().hex * 2,
        occurred_at=now,
    )
    session.add(audit)
    await session.commit()

    return WorkQueueJobResponseV2(
        job_id=str(j.id),
        tenant_id=str(j.tenant_id),
        job_type=j.job_type,  # type: ignore
        priority=j.priority,  # type: ignore
        status=j.status,  # type: ignore
        attempts_count=j.attempts_count,
        max_attempts=j.max_attempts,
        assigned_worker_id=j.assigned_worker_id,
        available_at=j.available_at,
        created_at=j.created_at,
        claimed_at=j.claimed_at,
        completed_at=j.completed_at,
        last_error_class=j.last_error_class,  # type: ignore
        last_error_message=j.last_error_message,
    )


@router.post("/work-queue/jobs/{job_id}/replay", response_model=WorkQueueJobResponseV2)
async def replay_job(
    job_id: str,
    body: WorkQueueReplayRequestV2,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueJobResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)

    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "WORK_QUEUE_INVALID_JOB_ID", "message": "Invalid job UUID format."})

    stmt = select(WorkQueueJobModelV2).where(and_(WorkQueueJobModelV2.id == j_uuid, WorkQueueJobModelV2.tenant_id == current_user.tenant_id))
    j = (await session.execute(stmt)).scalar_one_or_none()
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "WORK_QUEUE_JOB_NOT_FOUND", "message": "Job not found."})

    if j.status != "DEAD_LETTER":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "WORK_QUEUE_REPLAY_NOT_TERMINAL", "message": "Only dead-letter jobs may be replayed."})

    now = datetime.now(timezone.utc)
    j.status = "QUEUED"
    j.assigned_worker_id = None
    j.available_at = now
    j.updated_at = now
    j.lease_version += 1
    if body.override_priority:
        j.priority = body.override_priority.value

    audit = WorkQueueAuditEventModelV2(
        id=uuid.uuid4(),
        tenant_id=j.tenant_id,
        user_id=current_user.id,
        job_id=j.id,
        action="JOB_REPLAYED",
        details_checksum=uuid.uuid4().hex * 2,
        occurred_at=now,
    )
    session.add(audit)
    await session.commit()

    return WorkQueueJobResponseV2(
        job_id=str(j.id),
        tenant_id=str(j.tenant_id),
        job_type=j.job_type,  # type: ignore
        priority=j.priority,  # type: ignore
        status=j.status,  # type: ignore
        attempts_count=j.attempts_count,
        max_attempts=j.max_attempts,
        assigned_worker_id=j.assigned_worker_id,
        available_at=j.available_at,
        created_at=j.created_at,
        claimed_at=j.claimed_at,
        completed_at=j.completed_at,
        last_error_class=j.last_error_class,  # type: ignore
        last_error_message=j.last_error_message,
    )


@router.get("/work-queue/dead-letter", response_model=WorkQueueDeadLetterListResponseV2)
async def list_dead_letters(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueDeadLetterListResponseV2:
    _require_work_queue_enabled()
    _require_gestor_or_admin(current_user)

    stmt = select(WorkQueueDeadLetterModelV2).where(WorkQueueDeadLetterModelV2.tenant_id == current_user.tenant_id).order_by(WorkQueueDeadLetterModelV2.moved_to_dead_letter_at.desc()).offset(offset).limit(limit)
    dl_rows = (await session.execute(stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(WorkQueueDeadLetterModelV2).where(WorkQueueDeadLetterModelV2.tenant_id == current_user.tenant_id)
    total_count = (await session.execute(count_stmt)).scalar_one()

    items = [
        WorkQueueDeadLetterResponseV2(
            dead_letter_id=str(r.id),
            job_id=str(r.job_id),
            tenant_id=str(r.tenant_id),
            job_type=r.job_type,  # type: ignore
            total_attempts=r.total_attempts,
            last_error_class=r.last_error_class,  # type: ignore
            sanitized_error_message=r.sanitized_error_message,
            moved_to_dead_letter_at=r.moved_to_dead_letter_at,
        )
        for r in dl_rows
    ]
    return WorkQueueDeadLetterListResponseV2(dead_letters=tuple(items), total_count=total_count)


@router.get("/work-queue/workers", response_model=WorkQueueWorkerListResponseV2)
async def list_workers(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueWorkerListResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)

    stmt = select(WorkQueueWorkerModelV2).order_by(WorkQueueWorkerModelV2.started_at.desc())
    w_rows = (await session.execute(stmt)).scalars().all()

    items = [
        WorkQueueWorkerResponseV2(
            worker_id=w.worker_id,
            hostname=w.hostname,
            process_id=w.process_id,
            status=w.status,  # type: ignore
            active_jobs_count=w.active_jobs_count,
            started_at=w.started_at,
            last_heartbeat_at=w.last_heartbeat_at,
        )
        for w in w_rows
    ]
    return WorkQueueWorkerListResponseV2(workers=tuple(items), total_count=len(items))


@router.get("/work-queue/stats", response_model=WorkQueueStatsResponseV2)
async def get_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueStatsResponseV2:
    _require_work_queue_enabled()
    _require_gestor_or_admin(current_user)

    return await _queue_service.get_stats(session, current_user.tenant_id)


@router.post("/work-queue/drain", response_model=WorkQueueStatsResponseV2)
async def drain_queue(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WorkQueueStatsResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)

    now = datetime.now(timezone.utc)
    audit = WorkQueueAuditEventModelV2(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="QUEUE_DRAIN_REQUESTED",
        details_checksum=uuid.uuid4().hex * 2,
        occurred_at=now,
    )
    session.add(audit)
    await session.commit()

    return await _queue_service.get_stats(session, current_user.tenant_id)


@router.get("/performance/baselines", response_model=PerformanceBaselineResponseV2)
async def get_performance_baseline(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PerformanceBaselineResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)
    if settings.ENVIRONMENT != "test" or not settings.PERFORMANCE_CERTIFICATION_MODE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "PERFORMANCE_TEST_ONLY", "message": "Performance certification is available only in an isolated test environment."})

    harness = PerformanceCertificationServiceV2(get_db)  # type: ignore
    base = await harness.get_or_create_provisional_baseline()
    return PerformanceBaselineResponseV2(
        baseline_id=base.baseline_id,
        contract_version=base.contract_version,
        origin_commit=base.origin_commit,
        status=base.status,
        small_throughput_rps=base.small_throughput_rps,
        small_p95_latency_ms=base.small_p95_latency_ms,
        medium_throughput_rps=base.medium_throughput_rps,
        medium_p95_latency_ms=base.medium_p95_latency_ms,
        baseline_checksum=base.baseline_checksum,
        created_at=base.created_at,
    )


@router.post("/performance/runs", response_model=PerformanceRunResponseV2)
async def run_performance_benchmark(
    body: PerformanceRunRequestV2,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PerformanceRunResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)
    if settings.ENVIRONMENT != "test" or not settings.PERFORMANCE_CERTIFICATION_MODE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "PERFORMANCE_TEST_ONLY", "message": "Performance certification is available only in an isolated test environment."})

    harness = PerformanceCertificationServiceV2(lambda: session)  # type: ignore
    res = await harness.run_benchmark(
        load_level=body.load_level,
        total_jobs=body.total_jobs,
        concurrency_level=body.concurrency_level,
    )
    return PerformanceRunResponseV2(
        run_id=res.run_id,
        load_level=res.load_level,
        total_jobs_processed=res.total_jobs_processed,
        duration_seconds=res.duration_seconds,
        throughput_jobs_per_second=res.throughput_jobs_per_second,
        p50_latency_ms=res.p50_latency_ms,
        p95_latency_ms=res.p95_latency_ms,
        p99_latency_ms=res.p99_latency_ms,
        min_latency_ms=res.min_latency_ms,
        max_latency_ms=res.max_latency_ms,
        success_count=res.success_count,
        error_count=res.error_count,
        dead_letter_count=res.dead_letter_count,
        singleflight_coalesced_count=res.singleflight_coalesced_count,
        executed_at=res.executed_at,
    )


@router.get("/performance/runs/{run_id}", response_model=PerformanceRunResponseV2)
async def get_performance_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PerformanceRunResponseV2:
    _require_work_queue_enabled()
    _require_admin(current_user)
    if settings.ENVIRONMENT != "test" or not settings.PERFORMANCE_CERTIFICATION_MODE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "PERFORMANCE_TEST_ONLY", "message": "Performance certification is available only in an isolated test environment."})

    stmt = select(PerformanceRunModelV2).where(PerformanceRunModelV2.run_id == run_id)
    r = (await session.execute(stmt)).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PERFORMANCE_RUN_NOT_FOUND", "message": "Performance run not found."})

    return PerformanceRunResponseV2(
        run_id=r.run_id,
        load_level=r.load_level,  # type: ignore
        total_jobs_processed=r.total_jobs_processed,
        duration_seconds=r.duration_seconds,
        throughput_jobs_per_second=r.throughput_jobs_per_second,
        p50_latency_ms=r.p50_latency_ms,
        p95_latency_ms=r.p95_latency_ms,
        p99_latency_ms=r.p99_latency_ms,
        min_latency_ms=r.min_latency_ms,
        max_latency_ms=r.max_latency_ms,
        success_count=r.success_count,
        error_count=r.error_count,
        dead_letter_count=r.dead_letter_count,
        singleflight_coalesced_count=r.singleflight_coalesced_count,
        executed_at=r.executed_at,
    )
