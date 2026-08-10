# ADR 0028: Governed PostgreSQL Work Queue and Synthetic Performance Certification Harness

- **Status**: Approved / Certified
- **Contract Version**: `lumina.scale-queues-performance/1.0`
- **Origin Commit**: `880477a980aeaef840ac0a5c66f8541eb6c7c349`
- **Date**: 2026-08-08

## Context

LuminaAI required a scalable, governed, persistent multi-tenant background work queue and performance certification harness to process long-running analytical jobs, post-sync insights, cache warming, background materializations, and evaluation runs without relying on Redis or external broker dependencies.

## Key Architecture Decisions

1. **Transactional PostgreSQL Storage with `FOR UPDATE SKIP LOCKED`**:
   - Built on `governed_work_queue_jobs_v2`, `governed_work_queue_attempts_v2`, `governed_work_queue_workers_v2`, `governed_work_queue_dead_letters_v2`, `governed_work_queue_audit_events_v2`, `performance_baselines_v2`, `performance_runs_v2`.
   - Migration `v26_0` enforces constraints, indexes, and strict multi-tenant scoping.

2. **Lease Versioning & Heartbeats**:
   - Workers claim jobs via `FOR UPDATE SKIP LOCKED` and maintain atomic lease versioning (`lease_version`).
   - Lease reclaimer scans expired active leases and reclaims them to `RETRY_WAIT` or moves them to `DEAD_LETTER` if `max_attempts` is reached.
   - Stale worker completion attempts are rejected via compare-and-swap (CAS).

3. **Multi-Tenant Fairness & Admission Control**:
   - Prevents tenant starvation via `per_tenant_limit` bounded concurrency semaphores.
   - `WorkQueueBackpressureServiceV2` monitors queue depth, oldest job age, active workers, and DB pool utilization to emit backpressure states (`NORMAL`, `ELEVATED`, `SATURATED`, `REJECTING`, `DRAINING`) and admission decisions (`ACCEPT`, `ACCEPT_DELAYED`, `DEFER`, `REJECT_RETRYABLE`, `BLOCK`).

4. **Singleflight Background Coalescing**:
   - `WorkQueueSingleFlightServiceV2` deduplicates concurrent background requests sharing identical tenant and idempotency keys, avoiding duplicate background work.

5. **Server-Controlled Multi-Mode Rollout & OpenAPI Isolation**:
   - Feature flags (`WORK_QUEUE_MODE`, `WORK_QUEUE_APIS_ENABLED`, `PERFORMANCE_CERTIFICATION_MODE`, `WORK_QUEUE_WORKER_ENABLED`) default to `LEGACY_ONLY`.
   - Experimental V2 work queue and performance endpoints remain absent from default OpenAPI schema.

6. **Synthetic Performance Certification Harness**:
   - `PerformanceCertificationServiceV2` and `scripts/run_performance_certification.py` provide CLI and API performance benchmarking across `SMALL`, `MEDIUM`, and `LARGE` workloads.
