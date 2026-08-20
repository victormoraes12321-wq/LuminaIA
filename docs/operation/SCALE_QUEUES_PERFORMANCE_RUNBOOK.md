# Runbook: Governed Work Queue and Synthetic Performance Certification V2

- **Contract Version**: `lumina.scale-queues-performance/1.0`
- **Default Operational Mode**: `WORK_QUEUE_MODE=LEGACY_ONLY`

## 1. Operational Overview

The V2 Work Queue processes asynchronous background tasks (such as post-sync insights, cache warming, background materializations, and regression evaluations) using transactional PostgreSQL queues with `FOR UPDATE SKIP LOCKED`.

## 2. Configuration & Feature Flags

- `WORK_QUEUE_MODE`: Controls work queue engine mode (`LEGACY_ONLY`, `V2_QUEUE_ADMIN`, `V2_PERFORMANCE_CERTIFICATION`).
- `WORK_QUEUE_APIS_ENABLED`: Controls mounting of administrative API routes (`/api/v2/work-queue/*`). Default `False`.
- `WORK_QUEUE_WORKER_ENABLED`: Controls startup of autonomous worker loop in background. Default `False`.
- `PERFORMANCE_CERTIFICATION_MODE`: Controls synthetic load testing harness access. Default `False`.

## 3. Running Performance Certification CLI

To run the synthetic benchmark harness safely in isolated test environment:
```powershell
.\backend\.venv\Scripts\python.exe scripts/run_performance_certification.py --mode SMALL --concurrency 4
```

## 4. Monitoring & Troubleshooting

- Inspect stats via `GET /api/v2/work-queue/stats` (requires `ADMIN` or `GESTOR` role).
- View dead letters via `GET /api/v2/work-queue/dead-letter`.
- Replay failed jobs via `POST /api/v2/work-queue/jobs/{job_id}/replay`.
- Drain active queues via `POST /api/v2/work-queue/drain`.
