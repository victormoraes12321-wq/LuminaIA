"""
LuminaAI Real-Data Capacity & Concurrency Load Harness
------------------------------------------------------
Executes real workload queries against the live LuminaAI preprod runtime
and analytical PostgreSQL clone without altering application logic or configuration.
"""
import os
import sys
import json
import time
import asyncio
import ctypes
import subprocess
from pathlib import Path
from statistics import mean
import httpx
import dotenv

BACKEND_DIR = Path("C:/LuminaAI/backend").resolve()
dotenv.load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from services.oracle_service import decrypt_connection_details
from services.postgresql_clone_service import get_clone_db_connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import settings

BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:3002"
OTHER_SYSTEM_URL = "http://127.0.0.1:3000"

QUESTIONS_POOL = [
    {"id": 1, "q": "Faturamento do mês 02/2026", "sentinel": "FAT_02_2026"},
    {"id": 2, "q": "Faturamento da filial 1", "sentinel": "FAT_FILIAL_1"},
    {"id": 3, "q": "Quantos vendedores existem?", "sentinel": "VENDEDORES"},
    {"id": 4, "q": "Quais são os 5 produtos mais vendidos?", "sentinel": "TOP_PRODUTOS"},
    {"id": 5, "q": "Quantos clientes temos cadastrados?", "sentinel": "CLIENTES"},
    {"id": 6, "q": "Faturamento deste mês", "sentinel": None},
    {"id": 7, "q": "Faturamento mensal de fevereiro de 2026", "sentinel": None},
    {"id": 8, "q": "Total faturado no ano de 2026", "sentinel": None},
    {"id": 9, "q": "Faturamento por filial em 2026", "sentinel": None},
    {"id": 10, "q": "Qual filial mais faturou em 2026?", "sentinel": None},
    {"id": 11, "q": "Quantidade total vendida em 2026", "sentinel": None},
    {"id": 12, "q": "Unidades vendidas por produto", "sentinel": None},
    {"id": 13, "q": "Preço médio dos produtos", "sentinel": None},
    {"id": 14, "q": "Preço unitário dos produtos", "sentinel": None},
    {"id": 15, "q": "Desconto médio aplicado nas vendas", "sentinel": None},
    {"id": 16, "q": "Custo total dos produtos vendidos", "sentinel": None},
    {"id": 17, "q": "Qual o cliente com maior volume de compras?", "sentinel": None},
    {"id": 18, "q": "Ranking dos top 10 produtos mais vendidos", "sentinel": None},
    {"id": 19, "q": "Faturamento de vendas no mês anterior", "sentinel": None},
    {"id": 20, "q": "Total faturado pela filial 2 em 2026", "sentinel": None},
]

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_system_memory():
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    total_gb = stat.ullTotalPhys / (1024 ** 3)
    avail_gb = stat.ullAvailPhys / (1024 ** 3)
    used_gb = total_gb - avail_gb
    return {
        "load_pct": stat.dwMemoryLoad,
        "total_gb": round(total_gb, 2),
        "avail_gb": round(avail_gb, 2),
        "used_gb": round(used_gb, 2),
    }

def get_process_metrics():
    # Native powershell query for Lumina processes
    ps_cmd = 'Get-Process -Name python,node -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, WorkingSet64, CPU | ConvertTo-Json'
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            procs = json.loads(res.stdout)
            if isinstance(procs, dict):
                procs = [procs]
            py_mem = sum(p.get("WorkingSet64", 0) for p in procs if "python" in p.get("ProcessName", "").lower()) / (1024**2)
            node_mem = sum(p.get("WorkingSet64", 0) for p in procs if "node" in p.get("ProcessName", "").lower()) / (1024**2)
            return {
                "py_mb": round(py_mem, 1),
                "node_mb": round(node_mem, 1),
                "proc_count": len(procs)
            }
    except Exception:
        pass
    return {"py_mb": 0.0, "node_mb": 0.0, "proc_count": 0}

async def get_pg_connections():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT count(*), state FROM pg_stat_activity GROUP BY state;"))
            rows = res.fetchall()
            active = sum(r[0] for r in rows if r[1] == 'active')
            idle = sum(r[0] for r in rows if r[1] == 'idle')
            total = sum(r[0] for r in rows)
            return {"active": active, "idle": idle, "total": total}
    except Exception:
        return {"active": 0, "idle": 0, "total": 0}

async def check_endpoint_health(client: httpx.AsyncClient):
    try:
        r_live = await client.get(f"{BASE_URL}/health", timeout=5.0)
        r_deep = await client.get(f"{BASE_URL}/health/deep", timeout=5.0)
        r_front = await client.get(f"{FRONTEND_URL}/healthz", timeout=5.0)
        return (
            r_live.status_code == 200 and
            r_deep.status_code == 200 and
            r_front.status_code == 200
        )
    except Exception:
        return False

async def check_port_3000(client: httpx.AsyncClient):
    try:
        r = await client.get(OTHER_SYSTEM_URL, timeout=3.0)
        return r.status_code in (200, 301, 302, 304, 404, 401, 403)
    except Exception:
        return False

def calculate_percentiles(latencies):
    if not latencies:
        return {"min": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}
    s = sorted(latencies)
    n = len(s)
    def pct(p):
        idx = int(n * p)
        return s[min(idx, n - 1)]
    return {
        "min": round(s[0], 3),
        "mean": round(mean(s), 3),
        "p50": round(pct(0.50), 3),
        "p95": round(pct(0.95), 3),
        "p99": round(pct(0.99), 3),
        "max": round(s[-1], 3),
    }

async def run_stage(concurrency: int, total_requests: int, jwt_token: str, tenant_id: str):
    print(f"\n" + "=" * 80)
    print(f"  STARTING STAGE C{concurrency} — {total_requests} REQUESTS (CONCURRENCY = {concurrency})")
    print("=" * 80)

    limits = httpx.Limits(max_connections=concurrency + 10, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(120.0, connect=10.0)

    semaphore = asyncio.Semaphore(concurrency)
    results = []
    sentinel_matches = 0
    sentinel_totals = 0

    req_counter = 0

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        async def send_single_query(req_id: int):
            nonlocal sentinel_matches, sentinel_totals
            item = QUESTIONS_POOL[req_id % len(QUESTIONS_POOL)]
            q_text = item["q"]
            sentinel_key = item["sentinel"]

            payload = {
                "pergunta": q_text,
                "tenant_id": tenant_id,
                "session_id": f"load-c{concurrency}-req-{req_id}",
                "history": [],
                "mode": "analytical",
                "parent_id": None,
                "client_message_id": tenant_id,
                "expected_context_version": 0
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            }

            t0 = time.perf_counter()
            async with semaphore:
                try:
                    resp = await client.post(f"{BASE_URL}/api/v1/query/", json=payload, headers=headers)
                    duration = time.perf_counter() - t0
                    status = resp.status_code
                    body_json = None
                    if status == 200:
                        body_json = resp.json()
                        if sentinel_key:
                            sentinel_totals += 1
                            # Validation that response has query_id or valid view/chart
                            if body_json.get("query_id") or body_json.get("view_name") or body_json.get("chart_type"):
                                sentinel_matches += 1
                    return {"status": status, "duration": duration, "error": None}
                except httpx.TimeoutException:
                    duration = time.perf_counter() - t0
                    return {"status": 0, "duration": duration, "error": "TIMEOUT"}
                except Exception as e:
                    duration = time.perf_counter() - t0
                    return {"status": 0, "duration": duration, "error": str(e)}

        start_time = time.perf_counter()
        tasks = [send_single_query(i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    # Calculate metrics
    completed = [r for r in results if r["status"] == 200]
    http_2xx = len(completed)
    http_422 = len([r for r in results if r["status"] == 422])
    http_429 = len([r for r in results if r["status"] == 429])
    http_5xx = len([r for r in results if 500 <= r["status"] < 600])
    timeouts = len([r for r in results if r["error"] == "TIMEOUT"])
    conn_errors = len([r for r in results if r["error"] and r["error"] != "TIMEOUT"])

    latencies = [r["duration"] for r in completed]
    pcts = calculate_percentiles(latencies)
    rps = round(total_requests / total_time, 2) if total_time > 0 else 0

    mem = get_system_memory()
    proc = get_process_metrics()
    pg = await get_pg_connections()

    stage_summary = {
        "concurrency": concurrency,
        "requests": total_requests,
        "completed": len(results),
        "2xx": http_2xx,
        "422": http_422,
        "429": http_429,
        "5xx": http_5xx,
        "timeouts": timeouts,
        "conn_errors": conn_errors,
        "rps": rps,
        "latencies": pcts,
        "sentinels": f"{sentinel_matches}/{sentinel_totals}" if sentinel_totals > 0 else "N/A",
        "memory": mem,
        "process": proc,
        "pg_conn": pg,
        "duration_sec": round(total_time, 2),
        "status": "PASSED" if (http_2xx == total_requests and timeouts == 0 and http_5xx == 0) else "FAILED"
    }

    print(f"  Results for C{concurrency}:")
    print(f"    Completed: {len(results)}/{total_requests} (2xx: {http_2xx}, 422: {http_422}, 429: {http_429}, 5xx: {http_5xx}, Timeouts: {timeouts})")
    print(f"    Throughput: {rps} RPS | Total Time: {round(total_time, 2)}s")
    print(f"    Latency: p50={pcts['p50']}s | p95={pcts['p95']}s | p99={pcts['p99']}s | max={pcts['max']}s | mean={pcts['mean']}s")
    print(f"    Sentinels Matched: {sentinel_matches}/{sentinel_totals}")
    print(f"    Memory: Used {mem['used_gb']}GB / {mem['total_gb']}GB (Avail: {mem['avail_gb']}GB) | Backend: {proc['py_mb']}MB, Frontend: {proc['node_mb']}MB")
    print(f"    PostgreSQL Connections: Total={pg['total']} (Active={pg['active']}, Idle={pg['idle']})")

    return stage_summary

async def main():
    print("=" * 80)
    print("      LUMINAAI REAL-DATA CAPACITY & CONCURRENCY LOAD ACCEPTANCE")
    print("=" * 80)

    # 1. Login
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL") or "ti@casadocampo.vet.br"
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{BASE_URL}/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
        if resp.status_code != 200:
            print(f"[FAIL] Authentication failed: {resp.status_code}")
            return
        jwt_token = resp.json()["access_token"]

        resp_sess = await client.get(f"{BASE_URL}/api/v1/auth/session", headers={"Authorization": f"Bearer {jwt_token}"})
        tenant_id = resp_sess.json()["tenant_id"]
        print("[OK] Authenticated successfully against LuminaAI.")

        # Initial Health Verification
        health_ok = await check_endpoint_health(client)
        port3000_ok = await check_port_3000(client)
        print(f"[PRECHECK] Lumina Health: {'PASSED' if health_ok else 'FAILED'} | Port 3000: {'PASSED' if port3000_ok else 'FAILED'}")

    stages = [
        (1, 30),
        (5, 50),
        (10, 100),
        (25, 150),
        (50, 200),
    ]

    all_stage_summaries = []
    c25_gate = "PASSED"
    c50_gate = "PASSED"

    for conc, req_count in stages:
        if conc == 50 and c25_gate != "PASSED":
            print("\n[BLOCKED] Gate C25 did not pass. Skipping C50 as required by safety protocol.")
            c50_gate = "SKIPPED"
            break

        summary = await run_stage(conc, req_count, jwt_token, tenant_id)
        all_stage_summaries.append(summary)

        if conc == 25 and summary["status"] != "PASSED":
            c25_gate = "FAILED"

        if conc == 50 and summary["status"] != "PASSED":
            c50_gate = "FAILED"

        # Cooldown & Health check between stages
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=5.0) as client:
            healthy = await check_endpoint_health(client)
            p3000 = await check_port_3000(client)
            print(f"  [COOLDOWN CHECK] Post-C{conc} Health: {'HEALTHY' if healthy else 'DEGRADED'} | Port 3000: {'OK' if p3000 else 'FAIL'}")

    # Post-load comprehensive health check
    print("\n" + "=" * 80)
    print("                     POST-LOAD FINAL VERIFICATION")
    print("=" * 80)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r_live = await client.get(f"{BASE_URL}/health")
        r_deep = await client.get(f"{BASE_URL}/health/deep")
        r_front = await client.get(f"{FRONTEND_URL}/healthz")
        r_login = await client.post(f"{BASE_URL}/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
        r_query = await client.post(
            f"{BASE_URL}/api/v1/query/",
            json={"pergunta": "Faturamento do mês 02/2026", "tenant_id": tenant_id, "session_id": "post-load-probe", "history": [], "mode": "analytical", "parent_id": None, "client_message_id": tenant_id, "expected_context_version": 0},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {jwt_token}"}
        )
        p3000 = await check_port_3000(client)

        print(f"  Backend /health       : HTTP {r_live.status_code} ({'PASSED' if r_live.status_code == 200 else 'FAILED'})")
        print(f"  Backend /health/deep  : HTTP {r_deep.status_code} ({'PASSED' if r_deep.status_code == 200 else 'FAILED'})")
        print(f"  Frontend /healthz     : HTTP {r_front.status_code} ({'PASSED' if r_front.status_code == 200 else 'FAILED'})")
        print(f"  Post-Load Login Probe : HTTP {r_login.status_code} ({'PASSED' if r_login.status_code == 200 else 'FAILED'})")
        print(f"  Post-Load Query Probe : HTTP {r_query.status_code} ({'PASSED' if r_query.status_code == 200 else 'FAILED'})")
        print(f"  Port 3000 Status      : {'UNCHANGED / OK' if p3000 else 'FAILED'}")

    # Final summary JSON output
    out_file = Path("C:/LuminaAI/runtime-logs/capacity-summary.json")
    out_file.write_text(json.dumps(all_stage_summaries, indent=2), encoding="utf-8")
    print(f"\nCapacity summary report saved to: {out_file}")

if __name__ == "__main__":
    asyncio.run(main())
