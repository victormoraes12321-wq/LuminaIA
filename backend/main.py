"""
LuminaAI — Aplicação Principal FastAPI

Ponto de entrada da API. Configura:
  - Lifespan: startup (verifica conexão DB) e shutdown (fecha engine)
  - Middlewares: CORS e request timing
  - Exception handlers globais: HTTPException e erros genéricos
  - Routers: /api/v1/query
  - Endpoints utilitários: /health, /

Para iniciar em desenvolvimento:
    uvicorn main:app --reload --port 8000

Para produção (com workers Gunicorn + Uvicorn):
    gunicorn main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import sqlalchemy
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import engine
from routers import query as query_router
from routers import auth as auth_router
from routers import users as users_router
from routers import catalog as catalog_router
from routers import tenant as tenant_router
from routers import metadata_catalog as metadata_catalog_router
from routers import analytical_packages as analytical_packages_router
from routers import business_knowledge as business_knowledge_router
from routers import enterprise_knowledge as enterprise_knowledge_router
from routers import dashboard_studio as dashboard_studio_router
from routers import dashboard as dashboard_router
from routers import dashboard_preferences as dashboard_preferences_router
from routers import svr as svr_router
from routers import conversations as conversations_router
from routers import user_analytical_profile as user_analytical_profile_router
from routers import supervised_feedback as supervised_feedback_router
from routers import semantic_retrieval as semantic_retrieval_router
from routers import ai_tool_registry as ai_tool_registry_router
from routers import safe_analytical_postgresql as safe_analytical_postgresql_router
from routers import ai_orchestration as ai_orchestration_router
from routers import validation_provenance as validation_provenance_router
from routers import logistics as logistics_router
from routers import sentinel as sentinel_router
from services.ai_credential_manager import ai_credential_manager
from services.ai_invocation_manager import ai_invocation_manager
from services.scheduler import start_scheduler, stop_scheduler
from services.enterprise_knowledge.errors import EnterpriseKnowledgeError
from services.user_analytical_profile.errors import UserProfileError
from services.supervised_feedback.errors import GovernedFeedbackError
from services.semantic_retrieval.errors import SemanticRetrievalError
from services.ai_tool_registry import AIToolException
from services.safe_analytical_postgresql.exceptions import AnalyticalError
from routers.dependencies import AUTH_COOKIE_NAME
from services.security_rollout_v2.sanitization import security_payload_sanitizer


# ── Configuração de Logging ────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Silencia logs verbosos e problemáticos de bibliotecas externas (previne UnicodeEncodeError no Windows)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger("luminaai.main")

EXPLICIT_MIGRATION_ONLY_TABLES = frozenset({
    "dashboards_v2", "dashboard_revisions_v2", "dashboard_reviews_v2",
    "dashboard_approvals_v2", "dashboard_publications_v2",
    "dashboard_active_publications_v2", "dashboard_collaborators_v2",
    "dashboard_access_policies_v2", "dashboard_audit_events_v2",
    "dashboard_runtime_executions_v2", "dashboard_widget_executions_v2",
    "dashboard_evaluation_cases_v2", "dashboard_evaluation_results_v2",
    "dashboard_ai_proposals_v2", "dashboard_ai_proposal_versions_v2",
    "dashboard_ai_clarifications_v2", "dashboard_ai_evidence_v2",
    "dashboard_ai_decisions_v2", "dashboard_ai_runs_v2",
    "dashboard_ai_audit_events_v2", "dashboard_ai_evaluation_cases_v2",
    "dashboard_ai_evaluation_results_v2",
})


MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024
RATE_LIMIT_WINDOW_SECONDS = 60.0
RATE_LIMITS_BY_SCOPE = {
    "auth_login": 30,
    "query": 90,
    "general": 300,
}
_rate_limit_store: dict[str, deque[float]] = defaultdict(deque)


# ── Lifespan (Startup / Shutdown) ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.

    Startup:
      - Verifica conectividade com o PostgreSQL
      - Loga configuração do ambiente

    Shutdown:
      - Fecha e descarta o pool de conexões do engine
    """
    # ── Startup ───────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("🌟 LuminaAI v%s — Iniciando", settings.APP_VERSION)
    logger.info("   Ambiente  : %s", settings.ENVIRONMENT.upper())
    logger.info("   Debug     : %s", settings.DEBUG)
    logger.info("   Modelo IA : %s", settings.OPENAI_MODEL)
    logger.info("=" * 60)

    startup_database_ready = False
    try:
        if settings.is_testing:
            from testing.database_guard import guard_engine_before_write

            await guard_engine_before_write(engine)
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
            from database import Base
            import models  # Garante registro de todos os modelos ORM
            startup_tables = [
                table for table in Base.metadata.tables.values()
                if table.name not in EXPLICIT_MIGRATION_ONLY_TABLES
            ]
            await conn.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=startup_tables))
        startup_database_ready = True
        logger.info("✅ PostgreSQL conectado e tabelas sincronizadas com sucesso")
    except Exception as exc:
        # Log de erro mas não impede o startup —
        # permite healthcheck expor o problema sem crashar imediatamente
        logger.critical("â Œ Falha ao conectar ao PostgreSQL: %s", exc)

    if not startup_database_ready and settings.ENVIRONMENT in {"staging", "production", "test"}:
        raise RuntimeError("PostgreSQL startup readiness failed")

    if not settings.is_testing:
        try:
            aicm_report = await ai_credential_manager.startup_validate()
            logger.info("[AICM] Startup validation status: %s", aicm_report.get("status"))
        except Exception as exc:
            logger.warning("[AICM] Startup validation failed in degraded mode: %s", exc)
        # Inicia o agendador de sincronização em background
        try:
            start_scheduler()
        except Exception as exc:
            logger.error("Falha ao iniciar o agendador: %s", exc)

    # Sincroniza o SemanticCatalog com o dicionário semântico em memória
    if not settings.is_testing:
        try:
            from services.semantic_layer import sync_from_semantic_catalog
            # Usa o tenant demo padrão para carregamento inicial de sinônimos
            demo_tenant = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
            synced = await sync_from_semantic_catalog(demo_tenant)
            logger.info("✅ SemanticCatalog sincronizado: %d conceitos carregados", synced)
        except Exception as exc:
            logger.warning("Falha ao sincronizar o catálogo semântico legado no startup: %s", exc)

    # Inicializa o Corporate Knowledge Catalog (CKC)
    try:
        from services.metadata_catalog.loader import load_corporate_catalog
        load_corporate_catalog()
        logger.info("✅ Corporate Knowledge Catalog (CKC) carregado com sucesso no startup")
    except Exception as exc:
        logger.error("❌ Falha crítica ao inicializar o Corporate Knowledge Catalog: %s", exc, exc_info=True)

    yield  # Aplicação em execução

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("🛑 LuminaAI — Encerrando...")
    # Desliga o agendador
    if not settings.is_testing:
        await stop_scheduler()
    await ai_credential_manager.close_all()
    await engine.dispose()
    logger.info("✅ Pool de conexões PostgreSQL fechado. Até logo!")


# ── Instância da Aplicação ─────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    # Swagger/ReDoc desabilitados em produção
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
    # Metadados para o Swagger UI
    contact={
        "name": "LuminaAI Engineering",
        "email": "engineering@luminaai.com",
    },
    license_info={
        "name": "Proprietary",
    },
    openapi_tags=[
        {
            "name": "🔍 Query Engine",
            "description": "Consulta inteligente via Motor de Intenção com IA",
        },
        {
            "name": "Sistema",
            "description": "Endpoints de sistema: health check e informações",
        },
    ],
)


# ── Middlewares ────────────────────────────────────────────────

allow_origins_list = list(settings.CORS_ORIGINS)
allow_origin_regex = settings.cors_allow_origin_regex

# Se ambiente for desenvolvimento, força o regex para aceitar qualquer IP local e loopback nas requisições CORS
if settings.ENVIRONMENT == "development":
    allow_origin_regex = r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins_list,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


@app.middleware("http")
async def request_timing_and_logging(request: Request, call_next):
    """
    Middleware de observabilidade:
      - Mede o tempo de processamento de cada requisição
      - Adiciona headers de diagnóstico na resposta
      - Loga método, path, status e latência
    """
    start = time.perf_counter()
    # Client-supplied correlation IDs are never trusted as authority.
    request_id = f"req_{uuid.uuid4().hex}"
    path = request.url.path

    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        cookie_authenticated = bool(request.cookies.get(AUTH_COOKIE_NAME)) and not bool(
            request.headers.get("authorization")
        )
        if cookie_authenticated:
            origin = request.headers.get("origin")
            origin_allowed = bool(origin and origin in allow_origins_list)
            if origin and allow_origin_regex:
                origin_allowed = origin_allowed or bool(re.fullmatch(allow_origin_regex, origin))
            if not origin_allowed:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "error": {
                            "code": 403,
                            "message": "Origem da sessao nao autorizada.",
                            "type": "CsrfOriginDenied",
                            "path": path,
                        },
                    },
                    headers={"X-Request-ID": request_id},
                )

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size_bytes = int(content_length)
        except ValueError:
            size_bytes = 0
        if size_bytes > MAX_REQUEST_BODY_BYTES:
            logger.warning(
                "Payload rejeitado por tamanho | path=%s | size=%d | max=%d",
                path,
                size_bytes,
                MAX_REQUEST_BODY_BYTES,
            )
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "success": False,
                    "error": {
                        "code": 413,
                        "message": "Payload excede o limite permitido.",
                        "type": "PayloadTooLarge",
                        "path": path,
                    },
                },
                headers={"X-Request-ID": request_id},
            )

    client_host = request.client.host if request.client else "unknown"
    scope = "general"
    if path.endswith("/auth/login"):
        scope = "auth_login"
    elif path.startswith("/api/v1/query"):
        scope = "query"

    rate_key = f"{client_host}:{scope}"
    now = time.monotonic()
    history = _rate_limit_store[rate_key]
    while history and now - history[0] > RATE_LIMIT_WINDOW_SECONDS:
        history.popleft()
    limit = RATE_LIMITS_BY_SCOPE[scope]
    if len(history) >= limit:
        logger.warning("Rate limit excedido | key=%s | limit=%d", rate_key, limit)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "code": 429,
                    "message": "Muitas requisicoes em curto periodo. Tente novamente em instantes.",
                    "type": "RateLimitExceeded",
                    "path": path,
                },
            },
            headers={"Retry-After": "60", "X-Request-ID": request_id},
        )
    history.append(now)

    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start) * 1000

    # Headers de diagnóstico (úteis para debug e monitoramento)
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
    response.headers["X-LuminaAI-Version"] = settings.APP_VERSION
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path.startswith("/api/") or path in {"/health", "/"}:
        response.headers["Cache-Control"] = "no-store"

    log_fn = logger.warning if response.status_code >= 400 else logger.info
    log_fn(
        "%s %s → %d | %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        process_time_ms,
    )

    return response


# ── Exception Handlers Globais ─────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """
    Handler para HTTPExceptions lançadas explicitamente nos routers.
    Formata resposta de erro de forma consistente para o frontend.
    """
    safe_detail = security_payload_sanitizer.sanitize(exc.detail)
    logger.warning(
        "HTTP %d em %s %s",
        exc.status_code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": safe_detail,
                "type": "HTTPException",
                "path": str(request.url.path),
            },
        },
        headers=exc.headers,
    )


@app.exception_handler(EnterpriseKnowledgeError)
async def enterprise_knowledge_exception_handler(
    request: Request,
    exc: EnterpriseKnowledgeError,
) -> JSONResponse:
    logger.warning(
        "Enterprise Knowledge %s em %s %s",
        exc.code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            },
        },
    )


@app.exception_handler(UserProfileError)
async def user_profile_exception_handler(
    request: Request,
    exc: UserProfileError,
) -> JSONResponse:
    logger.warning(
        "User Profile %s em %s %s",
        exc.code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            },
        },
    )


@app.exception_handler(GovernedFeedbackError)
async def governed_feedback_exception_handler(
    request: Request,
    exc: GovernedFeedbackError,
) -> JSONResponse:
    logger.warning(
        "Governed Feedback %s em %s %s",
        exc.code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=int(exc.status_code),
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            },
        },
    )


@app.exception_handler(SemanticRetrievalError)
async def semantic_retrieval_exception_handler(
    request: Request,
    exc: SemanticRetrievalError,
) -> JSONResponse:
    logger.warning(
        "Semantic Retrieval %s em %s %s",
        exc.code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "path": str(request.url.path),
            },
        },
    )


@app.exception_handler(AIToolException)
async def ai_tool_exception_handler(
    request: Request,
    exc: AIToolException,
) -> JSONResponse:
    logger.warning(
        "AI Tool Registry %s em %s %s",
        exc.code,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            },
        },
    )


async def dashboard_backend_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    code = getattr(exc, "code", "DASHBOARD_RUNTIME_UNAVAILABLE")
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    public_payload = getattr(exc, "public_payload", None)
    payload = public_payload() if callable(public_payload) else {
        "code": code,
        "message": "Dashboard backend indisponivel.",
    }
    logger.warning("Dashboard Backend %s em %s %s", code, request.method, request.url.path)
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {**payload, "path": str(request.url.path)}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handler para exceções não tratadas (catch-all).
    Em produção, NÃO expõe detalhes técnicos ao cliente.
    Loga o traceback completo para diagnóstico interno.
    """
    logger.error(
        "Excecao nao tratada em %s %s | tipo=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Erro interno do servidor. Nossa equipe foi notificada.",
                "type": "InternalServerError",
                "path": str(request.url.path),
            },
        },
    )


# ── Registro de Routers ────────────────────────────────────────

def include_smart_cache_materialization_router_if_enabled(
    application: FastAPI,
) -> bool:
    """Registra o router experimental somente com duas flags server-controlled."""
    if settings.SMART_CACHE_MATERIALIZATION_MODE == "LEGACY_ONLY":
        return False
    if not settings.SMART_CACHE_ADMIN_ENABLED:
        return False

    from routers import smart_cache_materialization as smart_cache_router

    application.include_router(smart_cache_router.router)
    return True


def include_dashboard_backend_v2_router_if_enabled(application: FastAPI) -> bool:
    """Keep the governed V2 API absent from the default production surface."""
    if settings.DASHBOARD_BACKEND_MODE == "LEGACY_ONLY":
        return False
    if not (settings.DASHBOARD_ADMIN_APIS_ENABLED or settings.DASHBOARD_RUNTIME_APIS_ENABLED):
        return False
    from routers import dashboard_backend_v2 as dashboard_backend_router
    from services.dashboard_backend_v2.errors import DashboardBackendError

    application.add_exception_handler(DashboardBackendError, dashboard_backend_exception_handler)
    application.include_router(dashboard_backend_router.router)
    return True


def include_dashboard_ai_assistance_v2_router_if_enabled(application: FastAPI) -> bool:
    """Keep all Prompt 22 paths absent from the default OpenAPI surface."""
    if settings.DASHBOARD_AI_ASSISTANCE_MODE == "LEGACY_ONLY" or not settings.DASHBOARD_AI_APIS_ENABLED:
        return False
    from routers import dashboard_ai_assistance_v2 as dashboard_ai_router
    from services.dashboard_ai_assistance_v2.errors import DashboardAiAssistanceError

    async def handler(_request: Request, exc: DashboardAiAssistanceError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content={"detail": {"code": exc.code, "message": exc.message}})

    application.add_exception_handler(DashboardAiAssistanceError, handler)
    application.include_router(dashboard_ai_router.router)
    return True


def include_post_sync_insights_v2_router_if_enabled(application: FastAPI) -> bool:
    """Keep all Prompt 23 paths absent from the default OpenAPI surface."""
    if settings.POST_SYNC_INSIGHTS_MODE == "LEGACY_ONLY" or not settings.POST_SYNC_INSIGHTS_APIS_ENABLED:
        return False
    from routers import post_sync_insights_v2 as post_sync_router

    application.include_router(post_sync_router.router)
    return True


def include_observability_v2_router_if_enabled(application: FastAPI) -> bool:
    """Keep all Prompt 24 paths absent from the default OpenAPI surface."""
    if settings.OBSERVABILITY_MODE == "LEGACY_ONLY" or not settings.OBSERVABILITY_APIS_ENABLED:
        return False
    from routers import observability_v2 as observability_router

    application.include_router(observability_router.router)
    return True


def include_work_queue_v2_router_if_enabled(application: FastAPI) -> bool:
    """Keep all Prompt 25 paths absent from the default OpenAPI surface."""
    if (settings.WORK_QUEUE_MODE == "LEGACY_ONLY" and not settings.WORK_QUEUE_APIS_ENABLED and not settings.PERFORMANCE_CERTIFICATION_MODE):
        return False
    from routers import work_queue_v2 as work_queue_router

    application.include_router(work_queue_router.router)
    return True


app.include_router(
    query_router.router,
    prefix="/api/v1",
)

# Compatibilidade com clientes que já montam a URL com /api/v1 no base_url
# e ainda chamam /api/v1/query/.
app.include_router(
    query_router.router,
    prefix="/api/v1/api/v1",
    include_in_schema=False,
)

app.include_router(
    auth_router.router,
    prefix="/api/v1",
)

app.include_router(
    users_router.router,
    prefix="/api/v1",
)

app.include_router(
    catalog_router.router,
    prefix="/api/v1",
)

app.include_router(
    tenant_router.router,
    prefix="/api/v1",
)

app.include_router(
    metadata_catalog_router.router,
    prefix="/api/v1",
)

app.include_router(
    analytical_packages_router.router,
)

app.include_router(
    business_knowledge_router.router,
)
app.include_router(
    enterprise_knowledge_router.router,
)
app.include_router(
    user_analytical_profile_router.router,
)
app.include_router(
    supervised_feedback_router.router,
)
app.include_router(
    semantic_retrieval_router.router,
)
app.include_router(
    ai_tool_registry_router.router,
)
app.include_router(
    ai_tool_registry_router.admin_router,
)
app.include_router(
    safe_analytical_postgresql_router.router,
)
app.include_router(
    ai_orchestration_router.router,
)
app.include_router(
    validation_provenance_router.router,
)
app.include_router(
    logistics_router.router,
)
app.include_router(
    sentinel_router.router,
)
include_smart_cache_materialization_router_if_enabled(app)
include_dashboard_backend_v2_router_if_enabled(app)
include_dashboard_ai_assistance_v2_router_if_enabled(app)
include_post_sync_insights_v2_router_if_enabled(app)
include_observability_v2_router_if_enabled(app)
include_work_queue_v2_router_if_enabled(app)

app.include_router(
    dashboard_studio_router.router,
    prefix="/api/v1",
)

app.include_router(
    dashboard_router.router,
    prefix="/api/v1",
)

app.include_router(
    dashboard_preferences_router.router,
    prefix="/api/v1",
)

app.include_router(
    svr_router.router,
    prefix="/api/v1",
)

app.include_router(
    conversations_router.router,
    prefix="/api/v1",
)



# ── Endpoints Utilitários ────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Verificação de saúde da API",
    description="Endpoint para health checks de load balancers e orquestradores (K8s, ECS, etc.)",
    response_description="Status de saúde e informações do sistema",
)
async def health_check() -> dict[str, Any]:
    """
    Retorna o status de saúde da API.

    Pode ser estendido para verificar:
      - Conectividade com PostgreSQL
      - Conectividade com a API da OpenAI
      - Uso de memória e CPU
    """
    return {
        "status": "healthy",
        "kind": "liveness",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "deep_health": "/health/deep",
    }


@app.get(
    "/health/deep",
    tags=["Sistema"],
    summary="Verificação profunda de saúde da API",
    description="Valida componentes essenciais para diagnosticar queda ou degradação do sistema.",
    response_description="Status detalhado dos componentes essenciais",
)
async def deep_health_check() -> dict[str, Any]:
    from services.readiness import (
        dependency_component,
        migration_readiness_component,
        overall_readiness,
    )
    from services.security_rollout_v2 import ConfigurationReadinessServiceV2

    components: dict[str, Any] = {
        "api": dependency_component(
            raw_status="healthy",
            required=True,
            reason="API process is serving requests",
        ),
    }

    ai_status = ai_credential_manager.get_status()
    ai_required = not (
        settings.MOCK_OPENAI
        or settings.LUMINA_DISABLE_EXTERNAL_NETWORK
    )
    components["ai"] = dependency_component(
        raw_status=ai_status.get("status_geral"),
        required=ai_required,
        reason=(
            "real AI provider is required by the active environment"
            if ai_required
            else "AI provider is disabled or mocked by test policy"
        ),
        details={"provider_state": ai_status.get("status_geral", "UNKNOWN")},
    )

    invocation_status = ai_invocation_manager.get_status()
    components["ai_invocation"] = dependency_component(
        raw_status=invocation_status.get("status"),
        required=ai_required,
        reason=(
            "AI invocation governance is required with a real provider"
            if ai_required
            else "AI invocation is not required while provider access is disabled"
        ),
        details={"invocation_state": invocation_status.get("status", "UNKNOWN")},
    )

    table_names: tuple[str, ...] = ()
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
            table_names = tuple(
                (await conn.execute(sqlalchemy.text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
                ))).scalars().all()
            )
        components["postgres"] = dependency_component(
            raw_status="healthy",
            required=True,
            reason="authenticated application PostgreSQL is reachable",
        )
    except Exception as exc:
        logger.warning("Health deep: PostgreSQL degradado | type=%s", type(exc).__name__)
        components["postgres"] = dependency_component(
            raw_status="degraded",
            required=True,
            reason="authenticated application PostgreSQL is unavailable",
            details={"error_type": type(exc).__name__},
        )

    from services.scheduler import get_scheduler_status
    scheduler_status = get_scheduler_status()
    scheduler_required = not settings.is_testing
    components["scheduler"] = dependency_component(
        raw_status=scheduler_status.get("status"),
        required=scheduler_required,
        reason=(
            "legacy synchronization scheduler is required outside test mode"
            if scheduler_required
            else "scheduler execution is disabled by test policy"
        ),
        details={"running": scheduler_status.get("running", False)},
    )

    snapshot = ConfigurationReadinessServiceV2.from_settings(settings)
    configuration = ConfigurationReadinessServiceV2.evaluate(snapshot)
    configuration_ready = configuration.state.value == "READY"
    components["security_configuration"] = dependency_component(
        raw_status="ready" if configuration_ready else "blocked",
        required=True,
        reason=(
            "server-controlled feature configuration is coherent"
            if configuration_ready
            else "server-controlled feature configuration is invalid"
        ),
        details={"blocking_reasons": list(configuration.blocking_reasons)},
    )
    components["migration_compatibility"] = migration_readiness_component(
        snapshot,
        table_names,
    )

    overall = overall_readiness(components)

    return {
        "status": overall,
        "kind": "readiness",
        "ready_for_traffic": overall == "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }


@app.get(
    "/",
    include_in_schema=False,
    description="Redireciona para a documentação da API",
)
async def root() -> dict[str, str]:
    """Endpoint raiz com links de navegação."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1/query",
    }
