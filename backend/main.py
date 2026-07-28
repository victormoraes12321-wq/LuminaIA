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
from routers import dashboard_studio as dashboard_studio_router
from routers import dashboard as dashboard_router
from routers import dashboard_preferences as dashboard_preferences_router
from routers import svr as svr_router
from routers import conversations as conversations_router
from services.ai_credential_manager import ai_credential_manager
from services.ai_invocation_manager import ai_invocation_manager
from services.scheduler import start_scheduler, stop_scheduler


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

    try:
        if settings.is_testing:
            from testing.database_guard import guard_engine_before_write

            await guard_engine_before_write(engine)
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
            from database import Base
            import models  # Garante registro de todos os modelos ORM
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ PostgreSQL conectado e tabelas sincronizadas com sucesso")
    except Exception as exc:
        # Log de erro mas não impede o startup —
        # permite healthcheck expor o problema sem crashar imediatamente
        logger.critical("â Œ Falha ao conectar ao PostgreSQL: %s", exc)

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
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex}"
    path = request.url.path

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
    logger.warning(
        "HTTP %d em %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
                "path": str(request.url.path),
            },
        },
        headers=exc.headers,
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
    logger.exception(
        "Exceção não tratada em %s %s | tipo=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )

    # Em desenvolvimento, expõe o tipo de exceção para facilitar debug
    error_detail = (
        f"[DEV] {type(exc).__name__}: {exc}"
        if settings.is_development
        else "Erro interno do servidor. Nossa equipe foi notificada."
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": error_detail,
                "type": type(exc).__name__,
                "path": str(request.url.path),
            },
        },
    )


# ── Registro de Routers ────────────────────────────────────────

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
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "ai": ai_credential_manager.get_status(),
        "ai_invocation": ai_invocation_manager.get_status(),
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
    components: dict[str, Any] = {
        "api": {"status": "healthy"},
        "ai": ai_credential_manager.get_status(),
        "ai_invocation": ai_invocation_manager.get_status(),
    }

    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        components["postgres"] = {"status": "healthy"}
    except Exception as exc:
        logger.warning("Health deep: PostgreSQL degradado: %s", exc)
        components["postgres"] = {
            "status": "degraded",
            "error_type": type(exc).__name__,
        }

    from services.scheduler import get_scheduler_status
    components["scheduler"] = get_scheduler_status()

    component_statuses = [
        str(value.get("status", "unknown")).lower()
        for value in components.values()
        if isinstance(value, dict)
    ]
    overall = "healthy" if all(item in {"healthy", "ok", "ready", "active"} for item in component_statuses) else "degraded"

    return {
        "status": overall,
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
