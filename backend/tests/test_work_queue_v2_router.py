"""API router and OpenAPI isolation tests for V2 Governed Work Queue."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app, include_work_queue_v2_router_if_enabled

client = TestClient(app)


def test_work_queue_router_legacy_only_default() -> None:
    # By default in LEGACY_ONLY mode, endpoints are unmounted and return 404
    resp = client.get("/api/v2/work-queue/stats")
    assert resp.status_code == 404


def test_openapi_default_vs_experimental_isolation() -> None:
    # Run isolated python processes to extract OpenAPI JSON in DEFAULT and EXPERIMENTAL modes
    root_dir = Path(__file__).resolve().parents[1]
    python_exe = str(root_dir / ".venv" / "Scripts" / "python.exe")
    if not Path(python_exe).exists():
        python_exe = sys.executable

    script = (
        "import json, os, sys, hashlib\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, r'{str(root_dir)}')\n"
        "from main import app\n"
        "schema = app.openapi()\n"
        "paths = schema.get('paths', {})\n"
        "p25_paths = [p for p in paths if p.startswith('/api/v2/work-queue') or p.startswith('/api/v2/performance')]\n"
        "ops = sum(len(methods) for methods in paths.values())\n"
        "p25_ops = sum(len(methods) for p, methods in paths.items() if p.startswith('/api/v2/work-queue') or p.startswith('/api/v2/performance'))\n"
        "digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode('utf-8')).hexdigest()\n"
        "print(json.dumps({\n"
        "    'paths_count': len(paths),\n"
        "    'ops_count': ops,\n"
        "    'p25_paths_count': len(p25_paths),\n"
        "    'p25_ops_count': p25_ops,\n"
        "    'hash': digest\n"
        "}))\n"
    )

    # DEFAULT Run (LEGACY_ONLY)
    env_default = dict(os.environ)
    env_default["WORK_QUEUE_MODE"] = "LEGACY_ONLY"
    env_default["WORK_QUEUE_APIS_ENABLED"] = "false"
    env_default["PERFORMANCE_CERTIFICATION_MODE"] = "false"
    env_default["POST_SYNC_INSIGHTS_MODE"] = "LEGACY_ONLY"
    env_default["POST_SYNC_INSIGHTS_APIS_ENABLED"] = "false"
    env_default["OBSERVABILITY_MODE"] = "LEGACY_ONLY"
    env_default["OBSERVABILITY_APIS_ENABLED"] = "false"
    env_default["DASHBOARD_BACKEND_MODE"] = "LEGACY_ONLY"
    env_default["DASHBOARD_ADMIN_APIS_ENABLED"] = "false"
    env_default["DASHBOARD_RUNTIME_APIS_ENABLED"] = "false"
    env_default["SMART_CACHE_MATERIALIZATION_MODE"] = "LEGACY_ONLY"
    env_default["SMART_CACHE_ADMIN_ENABLED"] = "false"
    env_default["DASHBOARD_AI_ASSISTANCE_MODE"] = "LEGACY_ONLY"
    env_default["DASHBOARD_AI_APIS_ENABLED"] = "false"

    out_def = subprocess.check_output([python_exe, "-c", script], env=env_default, text=True)
    res_def = json.loads(out_def.strip())

    # PROMPT25_ONLY Run
    env_p25 = dict(os.environ)
    env_p25.update(env_default)
    env_p25["WORK_QUEUE_MODE"] = "V2_PERFORMANCE_CERTIFICATION"
    env_p25["WORK_QUEUE_APIS_ENABLED"] = "true"
    env_p25["PERFORMANCE_CERTIFICATION_MODE"] = "true"

    out_p25 = subprocess.check_output([python_exe, "-c", script], env=env_p25, text=True)
    res_p25 = json.loads(out_p25.strip())

    # COMBINED Run
    env_comb = dict(os.environ)
    env_comb.update(env_p25)
    env_comb["POST_SYNC_INSIGHTS_MODE"] = "V2_INSIGHTS_PUBLISH"
    env_comb["POST_SYNC_INSIGHTS_APIS_ENABLED"] = "true"
    env_comb["OBSERVABILITY_MODE"] = "V2_EVALUATIONS"
    env_comb["OBSERVABILITY_APIS_ENABLED"] = "true"
    env_comb["DASHBOARD_BACKEND_MODE"] = "V2_RUNTIME"
    env_comb["DASHBOARD_ADMIN_APIS_ENABLED"] = "true"
    env_comb["DASHBOARD_RUNTIME_APIS_ENABLED"] = "true"
    env_comb["SMART_CACHE_MATERIALIZATION_MODE"] = "V2_MATERIALIZATION"
    env_comb["SMART_CACHE_ADMIN_ENABLED"] = "true"
    env_comb["DASHBOARD_AI_ASSISTANCE_MODE"] = "AI_ASSISTED_EDIT"
    env_comb["DASHBOARD_AI_APIS_ENABLED"] = "true"

    out_comb = subprocess.check_output([python_exe, "-c", script], env=env_comb, text=True)
    res_comb = json.loads(out_comb.strip())

    # Structural & isolation assertions
    assert res_def["paths_count"] == 190
    assert res_def["ops_count"] == 216
    assert res_def["p25_paths_count"] == 0
    assert res_def["hash"] == "ab2ed7a6f3f67828ab3837f9b9f12e6746c1198449beb74fd66a0ef1cf718f0b"

    assert res_p25["paths_count"] == 201
    assert res_p25["ops_count"] == 227
    assert res_p25["p25_paths_count"] == 11
    assert res_p25["hash"] == "0fa5116d7fa01e03ae86dcc38596515608f89f810bce2dc54828d616737ef724"

    assert res_comb["paths_count"] == 256
    assert res_comb["ops_count"] == 289
    assert res_comb["hash"] == "c4f7c6731be6a074d9f589d6def0dcedcbaf0ab1269581854524ac538c26b52c"
