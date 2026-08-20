# Contract Specification: LuminaAI Work Queue and Performance Platform V2

- **Contract ID**: `lumina.scale-queues-performance/1.0`
- **Scope**: Persistent multi-tenant work queue, background worker loops, backpressure admission control, singleflight coalescing, and synthetic load certification harness.
- **Authoritative Location**: `backend/contracts/work_queue_v2/`

## 1. Storage & Concurrency Model

All background jobs are stored in PostgreSQL table `governed_work_queue_jobs_v2`.
Workers claim jobs using:
```sql
SELECT * FROM governed_work_queue_jobs_v2
WHERE status IN ('QUEUED', 'RETRY_WAIT') AND available_at <= now()
ORDER BY priority ASC, available_at ASC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 10;
```
Claims run in short dedicated transactions. Job execution takes place completely outside the claim transaction.

## 2. Job Lifecycle States

```
QUEUED --> CLAIMED --> RUNNING --> SUCCEEDED
   |          |           |
   |          v           v
   +----> RETRY_WAIT -> DEAD_LETTER / EXPIRED / CANCELLED
```

## 3. Backpressure & Admission Control

`WorkQueueBackpressureServiceV2` computes state dynamically:
- `NORMAL`
- `ELEVATED`
- `SATURATED`
- `REJECTING`
- `DRAINING`

Admission decisions:
- `ACCEPT`
- `ACCEPT_DELAYED`
- `DEFER`
- `REJECT_RETRYABLE`
- `BLOCK`

## 4. Singleflight Coalescing

Concurrent requests sharing the same tenant and idempotency key join the in-flight background execution future, executing the task exactly once.
# Hardening Prompt 26

Stats de jobs são tenant-scoped; replay exige ADMIN e estado `DEAD_LETTER`; mensagens
de erro/reason reutilizam redaction. Worker inventory exige ADMIN. Performance requer
ADMIN, `ENVIRONMENT=test` e modo explícito, permanecendo impossível em produção.
