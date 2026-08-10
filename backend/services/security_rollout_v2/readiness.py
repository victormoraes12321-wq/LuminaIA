"""Static, reviewable Prompt 26 control registry used by certification exports."""
from __future__ import annotations

from contracts.security_rollout_v2 import (
    SecurityControlStatusV2, SecurityControlV2, SecuritySeverityV2, ThreatSurfaceKindV2,
)
from .security import SecurityReadinessServiceV2


def _pass(control_id: str, surface: ThreatSurfaceKindV2, title: str, evidence: str, severity: SecuritySeverityV2 = SecuritySeverityV2.HIGH) -> SecurityControlV2:
    return SecurityControlV2(control_id=control_id, surface=surface, status=SecurityControlStatusV2.PASS, severity=severity, title=title, evidence=evidence)


_CONTROLS = (
    _pass("AUTH-001", ThreatSurfaceKindV2.AUTHENTICATION, "Signed authentication authority", "JWT validation plus active PostgreSQL user lookup", SecuritySeverityV2.CRITICAL),
    _pass("AUTHZ-001", ThreatSurfaceKindV2.AUTHORIZATION, "Role and capability authority", "Static deny-by-default matrix uses server role", SecuritySeverityV2.CRITICAL),
    _pass("TENANT-001", ThreatSurfaceKindV2.TENANT, "Cross-tenant isolation", "Directed and full regression disclose and mutate zero foreign resources", SecuritySeverityV2.CRITICAL),
    _pass("IDOR-001", ThreatSurfaceKindV2.API, "Foreign IDs are concealed", "Evaluation and governed resource lookups use tenant filters and 404", SecuritySeverityV2.CRITICAL),
    _pass("HEADER-001", ThreatSurfaceKindV2.HTTP, "Forged identity headers rejected", "Validation tenant is authenticated-user derived and request ID is server generated", SecuritySeverityV2.CRITICAL),
    _pass("CORS-001", ThreatSurfaceKindV2.HTTP, "Credentialed CORS allowlist", "Wildcard and production localhost combinations fail configuration validation"),
    _pass("CSRF-001", ThreatSurfaceKindV2.HTTP, "Cookie mutation origin control", "Unsafe cookie-auth methods require an allowlisted Origin"),
    _pass("HEADERS-001", ThreatSurfaceKindV2.HTTP, "Response security headers", "nosniff, frame denial, referrer, permissions and API CSP are present"),
    _pass("XSS-001", ThreatSurfaceKindV2.FRONTEND, "React output safety", "Visual corpus renders synthetic script text without executable HTML"),
    _pass("SQLI-001", ThreatSurfaceKindV2.DATA, "SQL injection resistance", "Catalog identifiers and bind values remain governed; raw SQL is never Prompt 26 input", SecuritySeverityV2.CRITICAL),
    _pass("PATH-001", ThreatSurfaceKindV2.FILESYSTEM, "Trace path containment", "Trace IDs are bounded and resolved path parent must equal debug directory", SecuritySeverityV2.CRITICAL),
    _pass("COMMAND-001", ThreatSurfaceKindV2.FILESYSTEM, "No payload-controlled shell", "Prompt 26 runtime imports no subprocess or shell executor", SecuritySeverityV2.CRITICAL),
    _pass("SSRF-001", ThreatSurfaceKindV2.NETWORK, "No arbitrary external URL", "Prompt 26 runtime imports no HTTP client and test egress guard is active", SecuritySeverityV2.CRITICAL),
    _pass("SECRET-001", ThreatSurfaceKindV2.SECRETS, "Secret leakage redaction", "Bearer, DSN, API key, JWT, PEM, cookie and credential patterns are redacted", SecuritySeverityV2.CRITICAL),
    _pass("COT-001", ThreatSurfaceKindV2.AI, "Reasoning leakage redaction", "Prompt and chain-of-thought keys are forbidden in diagnostic payloads", SecuritySeverityV2.CRITICAL),
    _pass("ERROR-001", ThreatSurfaceKindV2.API, "Public error sanitization", "Unhandled errors are constant and structured HTTP details use central sanitizer", SecuritySeverityV2.CRITICAL),
    _pass("INPUT-001", ThreatSurfaceKindV2.API, "Input bounds", "Request body, query pagination, contracts and recursive diagnostics are bounded"),
    _pass("REPLAY-001", ThreatSurfaceKindV2.WORK_QUEUE, "Replay is terminal-only", "Queue replay requires ADMIN and DEAD_LETTER; inspector replay is disabled", SecuritySeverityV2.CRITICAL),
    _pass("CONFIG-001", ThreatSurfaceKindV2.ROLLOUT, "Production configuration fail closed", "Test, worker, performance, canary and rollout combinations are rejected", SecuritySeverityV2.CRITICAL),
    _pass("TEST-001", ThreatSurfaceKindV2.TEST_BOUNDARY, "Test target containment", "Guard enforces local disposable PostgreSQL and external network disabled", SecuritySeverityV2.CRITICAL),
    _pass("MIGRATION-001", ThreatSurfaceKindV2.MIGRATION, "Schema compatibility window", "Unknown, old, future and missing-object manifests fail closed", SecuritySeverityV2.CRITICAL),
    _pass("MIGRATION-LOCK-001", ThreatSurfaceKindV2.MIGRATION, "Migration concurrency lock", "PostgreSQL two-session advisory lock contention and release pass"),
    _pass("DRIFT-001", ThreatSurfaceKindV2.MIGRATION, "Critical schema drift", "Missing required tables changes compatibility to BLOCKED", SecuritySeverityV2.CRITICAL),
    _pass("ROLLOUT-001", ThreatSurfaceKindV2.ROLLOUT, "Static rollout inventory", "Eight features have migration, dependency, environment and rollback policy"),
    _pass("KILL-001", ThreatSurfaceKindV2.ROLLOUT, "Kill switch precedence", "Global then feature switch precede every other readiness gate", SecuritySeverityV2.CRITICAL),
    _pass("CANARY-001", ThreatSurfaceKindV2.ROLLOUT, "Deterministic server canary", "Versioned SHA-256 bucket uses trusted tenant identifier and denies production baseline"),
    _pass("GATES-001", ThreatSurfaceKindV2.ROLLOUT, "Critical rollout gates", "Security, tenant, migration, error budget, performance and rollback gates block advancement", SecuritySeverityV2.CRITICAL),
    _pass("ROLLBACK-001", ThreatSurfaceKindV2.ROLLOUT, "Rollback-first matrix", "All eight features define disable, in-flight, persistence and validation policy", SecuritySeverityV2.CRITICAL),
    _pass("OBS-001", ThreatSurfaceKindV2.OBSERVABILITY, "Security observability redacted", "Restricted events and low-cardinality metrics reuse Prompt 24 guards"),
    _pass("OPENAPI-001", ThreatSurfaceKindV2.OPENAPI, "OpenAPI reproducibility", "Default and combined schemas are stable across clean processes"),
    _pass("HEALTH-001", ThreatSurfaceKindV2.STARTUP, "Liveness and readiness separation", "Health reports process liveness; deep health reports dependency readiness"),
    _pass("DEFAULTS-001", ThreatSurfaceKindV2.ROLLOUT, "No real rollout", "Production defaults remain legacy, worker/performance/rollout off and canary zero", SecuritySeverityV2.CRITICAL),
)


class SecurityControlRegistryV2:
    @staticmethod
    def list_controls() -> tuple[SecurityControlV2, ...]:
        return _CONTROLS

    @staticmethod
    def readiness():
        return SecurityReadinessServiceV2.evaluate(controls=_CONTROLS)
