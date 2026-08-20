from __future__ import annotations

import re
from pathlib import Path

from main import app


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def test_openapi_exposes_enterprise_critical_routes():
    paths = set(app.openapi()["paths"].keys())

    required_paths = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/session",
        "/api/v1/query/",
        "/api/v1/query/cache/stats",
        "/api/v1/query/performance/center",
        "/api/v1/query/security/center",
        "/api/v1/catalog/",
        "/api/v1/users/",
        "/api/v1/metadata-catalog/summary",
        "/api/v1/metadata-catalog/health",
        "/api/v1/business-knowledge/dictionary",
        "/api/v1/business-knowledge/kpis",
        "/api/v1/analytical-packages",
        "/api/v1/dashboard-studio/templates",
        "/api/v1/dashboard-studio/instances",
        "/api/v1/dashboard/events",
        "/api/v1/dashboard/refresh",
        "/api/v1/dashboard/telemetry",
    }

    missing = required_paths - paths
    assert not missing, f"Missing critical API routes: {sorted(missing)}"


def test_ai_layer_does_not_execute_raw_data_access():
    ai_dir = ROOT / "backend/services/ai"
    forbidden_patterns = {
        "database_import": re.compile(r"from\s+database\s+import|import\s+database"),
        "oracle_import": re.compile(r"oracledb|services\.oracle_service"),
        "clone_import": re.compile(r"postgresql_clone_service|execute_clone_view|get_clone_db_connection"),
        "raw_execute": re.compile(r"\.execute\s*\("),
        "sql_text": re.compile(r"sqlalchemy\.text|(?<![A-Za-z0-9_])text\s*\("),
        "raw_dml": re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE)\s+(INTO|SET|FROM|TABLE|DATABASE|VIEW)\b", re.IGNORECASE),
    }

    violations: list[str] = []
    for file in ai_dir.rglob("*.py"):
        text = file.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in forbidden_patterns.items():
            if pattern.search(text):
                violations.append(f"{file.relative_to(ROOT)}::{name}")

    assert not violations, "AI layer must not execute raw data access: " + ", ".join(violations)


def test_dashboard_studio_is_visual_layer_only():
    files = [
        ROOT / "backend/services/dashboard_studio_service.py",
        ROOT / "backend/routers/dashboard_studio.py",
        ROOT / "frontend/app/dashboard/studio/page.tsx",
    ]
    forbidden_terms = [
        "business_formula",
        "business_kpi",
        "calculation_engine",
        "execute_blueprint",
        "execute_clone_view",
        "oracle_service",
    ]

    violations: list[str] = []
    for file in files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        for term in forbidden_terms:
            if term in text:
                violations.append(f"{file.relative_to(ROOT)}::{term}")

    assert not violations, "Dashboard Studio must not mutate analytical layers: " + ", ".join(violations)


def test_security_dependencies_and_deprecated_jwt_stack_are_clean():
    requirements = _read("backend/requirements.txt")
    assert "PyJWT==" in requirements
    assert "python-jose" not in requirements

    scanned_files = [
        p
        for p in ROOT.rglob("*")
        if p.is_file()
        and not any(part in {"node_modules", ".next", "playwright-report", "test-results", ".venv", "venv", "__pycache__"} for part in p.parts)
        and p.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".mjs", ".md", ".txt", ".yml", ".yaml", ".json"}
    ]
    offenders: list[str] = []
    for file in scanned_files:
        if file == Path(__file__):
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        if "from jose" in text or "datetime.utcnow" in text:
            offenders.append(str(file.relative_to(ROOT)))

    assert not offenders, "Deprecated JWT/date patterns found: " + ", ".join(offenders)


def test_documentation_links_and_generated_references_are_consistent():
    required_docs = [
        "README.md",
        "CHANGELOG.md",
        "docs/README.md",
        "docs/architecture.md",
        "docs/modules.md",
        "docs/api-reference.md",
        "docs/source-inventory.md",
        "docs/ai/README.md",
        "docs/backend/README.md",
        "docs/frontend/README.md",
        "docs/data-platform/README.md",
        "docs/analytical-database/README.md",
        "docs/blueprint-repository/README.md",
        "docs/business-layer/README.md",
        "docs/scheduler/README.md",
        "docs/cache/README.md",
        "docs/security.md",
        "docs/performance.md",
        "docs/flows.md",
        "docs/patterns.md",
        "docs/installation.md",
        "docs/deploy.md",
        "docs/operation.md",
        "docs/maintenance.md",
        "docs/developer-guide.md",
        "docs/governance.md",
        "docs/adrs/README.md",
    ]
    missing_docs = [doc for doc in required_docs if not (ROOT / doc).exists()]
    assert not missing_docs, f"Missing official docs: {missing_docs}"

    broken_links: list[str] = []
    markdown_files = [ROOT / "README.md", ROOT / "CHANGELOG.md", *list((ROOT / "docs").rglob("*.md"))]
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8", errors="ignore")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative_target = target.split("#", 1)[0]
            if not relative_target:
                continue
            if not (markdown.parent / relative_target).resolve().exists():
                broken_links.append(f"{markdown.relative_to(ROOT)} -> {target}")

    assert not broken_links, "Broken documentation links: " + ", ".join(broken_links)

    api_reference = _read("docs/api-reference.md")
    source_inventory = _read("docs/source-inventory.md")
    assert "/api/v1/query/" in api_reference
    assert "backend/services/ai/corporate_intelligence_engine.py" in source_inventory


def test_operational_quality_gate_artifacts_exist():
    required_artifacts = [
        "scripts/import_cycle_check.py",
        "scripts/load-smoke.mjs",
        "scripts/generate_docs_reference.py",
        "backend/scripts/explain_analyze_core.sql",
        "frontend/playwright.config.ts",
        "docker-compose.yml",
        "nginx.conf",
        "docs/final_production_readiness_review.md",
        "docs/enterprise_hardening_scorecard.md",
    ]
    missing = [artifact for artifact in required_artifacts if not (ROOT / artifact).exists()]
    assert not missing, f"Missing operational quality gate artifacts: {missing}"


def test_no_lint_report_artifacts_or_typescript_suppressions_remain():
    forbidden_files = {"lint-report.json", "eslint-report.json"}
    generated_reports = [
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*")
        if p.is_file()
        and p.name in forbidden_files
        and not any(part in {"node_modules", ".next", "playwright-report", "test-results", ".venv"} for part in p.parts)
    ]
    assert not generated_reports, "Generated lint reports should not be kept: " + ", ".join(generated_reports)

    source_files = [
        p
        for p in (ROOT / "frontend").rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".ts", ".tsx", ".js", ".mjs"}
        and not any(part in {"node_modules", ".next", "playwright-report", "test-results"} for part in p.parts)
    ]
    suppressions: list[str] = []
    for file in source_files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        if "eslint-disable" in text or "@ts-ignore" in text or "@ts-expect-error" in text:
            suppressions.append(str(file.relative_to(ROOT)))

    assert not suppressions, "Frontend source still contains suppressions: " + ", ".join(suppressions)
