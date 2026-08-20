"""
LuminaAI — Configurações Centralizadas via Pydantic Settings v2.

Todas as variáveis de ambiente são carregadas aqui, validadas e expostas
como uma instância singleton `settings` para uso em toda a aplicação.

Uso:
    from config import settings
    print(settings.APP_NAME)
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Configurações centralizadas do LuminaAI.
    Carregadas do arquivo .env na raiz do projeto.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicação ─────────────────────────────────────────────
    APP_NAME: str = "LuminaAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Business Intelligence Inteligente baseado em IA — "
        "Motor de Intenções para análise de dados empresariais."
    )
    ENVIRONMENT: str = Field(default="development")
    LUMINA_TESTING: bool = Field(default=False)
    LUMINA_DISABLE_EXTERNAL_NETWORK: bool = Field(default=False)
    DEBUG: bool = Field(default=False)
    NEW_PIPELINE_ACTIVE: bool = Field(default=False)
    ENABLE_DETERMINISTIC_PIPELINE: bool = Field(default=False)
    ANALYTICAL_CONTRACTS_V2_ENABLED: bool = Field(default=False)
    ANALYTICAL_CONTRACTS_V2_SHADOW_MODE: bool = Field(default=True)
    ANALYTICAL_CONTRACTS_V2_FRONTEND_ENABLED: bool = Field(default=False)
    ANALYTICAL_COMPARISON_V2_EXECUTION_ENABLED: bool = Field(default=False)
    TEMPORAL_NORMALIZER_V2_ENABLED: bool = Field(default=True)
    TEMPORAL_NORMALIZER_V2_SHADOW_MODE: bool = Field(default=True)
    COMPARISON_PLANNER_V2_ENABLED: bool = Field(default=True)
    COMPARISON_PLANNER_V2_SHADOW_MODE: bool = Field(default=True)
    COMPARISON_EXECUTOR_V2_ENABLED: bool = Field(default=False)
    COMPARISON_EXECUTOR_V2_SHADOW_MODE: bool = Field(default=False)
    CONVERSATION_STATE_MODE: str = Field(default="LEGACY_ONLY")
    CONTEXT_RESOLUTION_V2_ENABLED: bool = Field(default=False)
    CONTEXT_RESOLUTION_V2_SHADOW_MODE: bool = Field(default=False)
    CONTEXT_RESOLUTION_V2_FRONTEND_ENABLED: bool = Field(default=False)
    CONTEXT_RESOLUTION_MAXIMUM_DEPTH: int = Field(default=20, ge=1, le=100)
    CONTEXT_RESOLUTION_MAXIMUM_INHERITED_FIELDS: int = Field(default=50, ge=1, le=200)
    ENTERPRISE_KNOWLEDGE_MODE: str = Field(default="LEGACY_ONLY")
    ENTERPRISE_KNOWLEDGE_FRONTEND_ENABLED: bool = Field(default=False)
    ENTERPRISE_KNOWLEDGE_IMPORT_ENABLED: bool = Field(default=False)
    ENTERPRISE_KNOWLEDGE_EXPORT_ENABLED: bool = Field(default=False)
    ENTERPRISE_KNOWLEDGE_CACHE_ENABLED: bool = Field(default=False)
    ENTERPRISE_KNOWLEDGE_CACHE_TTL_SECONDS: int = Field(default=60, ge=1, le=3600)
    ENTERPRISE_KNOWLEDGE_EMERGENCY_OVERRIDE: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_MODE: str = Field(default="LEGACY_ONLY")
    USER_ANALYTICAL_PROFILE_FRONTEND_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_DEFAULTS_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_SAVED_FILTERS_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_EXPORT_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_DELETION_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_LEGACY_IMPORT_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_CACHE_ENABLED: bool = Field(default=False)
    USER_ANALYTICAL_PROFILE_CACHE_TTL_SECONDS: int = Field(default=30, ge=1, le=600)
    SUPERVISED_FEEDBACK_MODE: str = Field(default="LEGACY_ONLY")
    SUPERVISED_FEEDBACK_FRONTEND_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_ADMIN_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_DATASET_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_EXPORT_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_SHADOW_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_CACHE_ENABLED: bool = Field(default=False)
    SUPERVISED_FEEDBACK_CACHE_TTL_SECONDS: int = Field(default=30, ge=1, le=300)
    SUPERVISED_FEEDBACK_MAX_PAGE_SIZE: int = Field(default=100, ge=1, le=500)
    SEMANTIC_RETRIEVAL_MODE: str = Field(default="LEGACY_ONLY")
    SEMANTIC_RETRIEVAL_FRONTEND_ENABLED: bool = Field(default=False)
    SEMANTIC_ENTITY_INSTANCE_INDEXING_ENABLED: bool = Field(default=False)
    SEMANTIC_VECTOR_CHANNEL_ENABLED: bool = Field(default=False)
    SEMANTIC_PROFILE_TIE_BREAKER_ENABLED: bool = Field(default=False)
    SEMANTIC_APPROVED_FEEDBACK_CORPUS_ENABLED: bool = Field(default=False)
    SEMANTIC_RESTRICTED_ENTITIES_ENABLED: bool = Field(default=False)
    SEMANTIC_ADMIN_INSPECTOR_ENABLED: bool = Field(default=False)
    SEMANTIC_RETRIEVAL_CACHE_ENABLED: bool = Field(default=False)
    SEMANTIC_RETRIEVAL_CACHE_TTL_SECONDS: int = Field(default=30, ge=1, le=300)
    SEMANTIC_INCREMENTAL_BUILD_ENABLED: bool = Field(default=False)
    SEMANTIC_RETRIEVAL_MAX_QUERY_LENGTH: int = Field(default=500, ge=32, le=1000)
    AI_TOOL_REGISTRY_MODE: str = Field(default="LEGACY_ONLY")
    AI_TOOL_REGISTRY_FRONTEND_ENABLED: bool = Field(default=False)
    AI_TOOL_REGISTRY_ADMIN_ENABLED: bool = Field(default=False)
    AI_TOOL_REGISTRY_INSPECTOR_ENABLED: bool = Field(default=False)
    AI_TOOL_REGISTRY_CACHE_ENABLED: bool = Field(default=False)
    AI_TOOL_REGISTRY_CACHE_TTL_SECONDS: int = Field(default=60, ge=1, le=600)
    AI_TOOL_CIRCUIT_BREAKER_ENABLED: bool = Field(default=True)
    AI_TOOL_RATE_LIMITING_ENABLED: bool = Field(default=True)
    AI_TOOL_MAX_EXECUTION_TIME_SECONDS: float = Field(default=10.0, ge=0.5, le=60.0)
    SMART_CACHE_MATERIALIZATION_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_OBSERVE",
        "V2_CACHE_READ",
        "V2_CACHE_READ_WRITE",
        "V2_MATERIALIZATION",
    ] = Field(default="LEGACY_ONLY")
    SMART_CACHE_FRONTEND_ENABLED: bool = Field(default=False)
    SMART_CACHE_ADMIN_ENABLED: bool = Field(default=False)
    SMART_CACHE_INSPECTOR_ENABLED: bool = Field(default=False)
    SMART_CACHE_READ_ENABLED: bool = Field(default=False)
    SMART_CACHE_WRITE_ENABLED: bool = Field(default=False)
    SMART_MATERIALIZATION_READ_ENABLED: bool = Field(default=False)
    SMART_MATERIALIZATION_BUILD_ENABLED: bool = Field(default=False)
    DASHBOARD_BACKEND_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_VALIDATE",
        "V2_AUTHORING",
        "V2_PUBLISHED_READ",
        "V2_RUNTIME",
    ] = Field(default="LEGACY_ONLY")
    DASHBOARD_ADMIN_APIS_ENABLED: bool = Field(default=False)
    DASHBOARD_RUNTIME_APIS_ENABLED: bool = Field(default=False)
    DASHBOARD_PUBLISHING_ENABLED: bool = Field(default=False)
    DASHBOARD_ROLLBACK_ENABLED: bool = Field(default=False)
    DASHBOARD_COLLABORATORS_ENABLED: bool = Field(default=False)
    DASHBOARD_RUNTIME_CACHE_ENABLED: bool = Field(default=False)
    DASHBOARD_MATERIALIZATION_ENABLED: bool = Field(default=False)
    DASHBOARD_AUDIT_ENABLED: bool = Field(default=False)
    DASHBOARD_LEGACY_IMPORT_DRY_RUN_ENABLED: bool = Field(default=False)
    DASHBOARD_TENANT_ALLOWLIST: tuple[str, ...] = Field(default=())
    DASHBOARD_AI_ASSISTANCE_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_ANALYZE",
        "AI_PROPOSAL_PREVIEW",
        "AI_DRAFT_CREATE",
        "AI_ASSISTED_EDIT",
    ] = Field(default="LEGACY_ONLY")
    DASHBOARD_AI_APIS_ENABLED: bool = Field(default=False)
    DASHBOARD_AI_FRONTEND_ENABLED: bool = Field(default=False)
    DASHBOARD_AI_FAKE_PROVIDER_ENABLED: bool = Field(default=False)
    DASHBOARD_AI_FEEDBACK_ENABLED: bool = Field(default=False)
    DASHBOARD_AI_EVALUATIONS_ENABLED: bool = Field(default=False)
    DASHBOARD_AI_TENANT_ALLOWLIST: tuple[str, ...] = Field(default=())
    DASHBOARD_AI_MAX_INPUT_CHARACTERS: int = Field(default=4000, ge=128, le=20000)
    DASHBOARD_AI_MAX_OUTPUT_TOKENS: int = Field(default=1200, ge=64, le=4000)
    DASHBOARD_AI_MAX_TOOL_CALLS: int = Field(default=12, ge=0, le=32)
    DASHBOARD_AI_MAX_DURATION_MS: int = Field(default=15000, ge=100, le=60000)
    POST_SYNC_INSIGHTS_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_DETECT",
        "V2_INSIGHTS_READ",
        "V2_INSIGHTS_PUBLISH",
        "V2_INSIGHTS_AUTO_RUN",
    ] = Field(default="LEGACY_ONLY")
    POST_SYNC_INSIGHTS_APIS_ENABLED: bool = Field(default=False)
    POST_SYNC_INSIGHTS_FRONTEND_ENABLED: bool = Field(default=False)
    POST_SYNC_INSIGHTS_OUTBOX_CONSUMER_ENABLED: bool = Field(default=False)
    POST_SYNC_INSIGHTS_AUTO_RUN_ENABLED: bool = Field(default=False)
    POST_SYNC_INSIGHTS_TENANT_ALLOWLIST: tuple[str, ...] = Field(default=())
    OBSERVABILITY_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_OBSERVE",
        "V2_OBSERVABILITY_READ",
        "V2_EVALUATIONS",
    ] = Field(default="LEGACY_ONLY")
    OBSERVABILITY_APIS_ENABLED: bool = Field(default=False)
    OBSERVABILITY_FRONTEND_ENABLED: bool = Field(default=False)
    WORK_QUEUE_MODE: Literal[
        "LEGACY_ONLY",
        "SHADOW_QUEUE",
        "V2_BACKGROUND_JOBS",
        "V2_QUEUE_ADMIN",
        "V2_PERFORMANCE_CERTIFICATION",
    ] = Field(default="LEGACY_ONLY")
    WORK_QUEUE_APIS_ENABLED: bool = Field(default=False)
    WORK_QUEUE_FRONTEND_ENABLED: bool = Field(default=False)
    WORK_QUEUE_WORKER_ENABLED: bool = Field(default=False)
    WORK_QUEUE_MAX_CONCURRENCY: int = Field(default=10, ge=1, le=100)
    WORK_QUEUE_PER_TENANT_CONCURRENCY: int = Field(default=3, ge=1, le=50)
    WORK_QUEUE_LEASE_DURATION_SECONDS: int = Field(default=60, ge=5, le=3600)
    WORK_QUEUE_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=15, ge=1, le=600)
    WORK_QUEUE_TENANT_ALLOWLIST: tuple[str, ...] = Field(default=())
    PERFORMANCE_CERTIFICATION_MODE: bool = Field(default=False)
    SECURITY_ROLLOUT_MODE: Literal[
        "LEGACY_ONLY",
        "AUDIT_ONLY",
        "V2_READINESS",
    ] = Field(default="LEGACY_ONLY")
    SECURITY_ROLLOUT_APIS_ENABLED: bool = Field(default=False)
    ROLLOUT_EXECUTION_ENABLED: bool = Field(default=False)
    ROLLOUT_STAGE: Literal[
        "DISABLED",
        "AUDIT_ONLY",
        "SHADOW",
        "INTERNAL",
        "CANARY",
        "EXPANDED",
        "FULL",
        "PAUSED",
        "ROLLED_BACK",
    ] = Field(default="DISABLED")
    ROLLOUT_CANARY_PERCENTAGE: int = Field(default=0, ge=0, le=100)
    ROLLOUT_CANARY_TENANT_ALLOWLIST: tuple[str, ...] = Field(default=())
    V2_GLOBAL_EMERGENCY_DISABLE: bool = Field(default=True)
    KILL_SWITCH_DASHBOARD_V2_READ: bool = Field(default=True)
    KILL_SWITCH_DASHBOARD_V2_AUTHORING: bool = Field(default=True)
    KILL_SWITCH_DASHBOARD_AI: bool = Field(default=True)
    KILL_SWITCH_POST_SYNC_INSIGHTS: bool = Field(default=True)
    KILL_SWITCH_OBSERVABILITY_V2: bool = Field(default=True)
    KILL_SWITCH_EVALUATIONS_V2: bool = Field(default=True)
    KILL_SWITCH_WORK_QUEUE_V2: bool = Field(default=True)
    KILL_SWITCH_PERFORMANCE_CERTIFICATION: bool = Field(default=True)
    INSPECTOR_REPLAY_ENABLED: bool = Field(default=False)
    SEMANTIC_RETRIEVAL_MAX_PAGE_SIZE: int = Field(default=100, ge=1, le=500)
    CONVERSATION_PERSIST_CONTENT: bool = Field(default=True)
    CONVERSATION_CONTENT_KEY_VERSION: str = Field(default="v1", min_length=1, max_length=32)
    CONVERSATION_ACTIVE_TTL_HOURS: int = Field(default=24, ge=1, le=8760)
    CONVERSATION_ARCHIVE_AFTER_DAYS: int = Field(default=30, ge=1, le=3650)
    CONVERSATION_SOFT_DELETE_AFTER_DAYS: int = Field(default=180, ge=1, le=3650)
    CONVERSATION_PURGE_AFTER_DAYS: int = Field(default=365, ge=1, le=7300)
    CONVERSATION_MAX_CONTENT_BYTES: int = Field(default=12000, ge=256, le=1000000)
    CONVERSATION_MAX_NODES: int = Field(default=10000, ge=10, le=1000000)
    CONVERSATION_PURGE_BATCH_SIZE: int = Field(default=100, ge=1, le=1000)
    CONVERSATION_RETENTION_JOB_ENABLED: bool = Field(default=False)
    CONVERSATION_LEGACY_IMPORT_ENABLED: bool = Field(default=False)
    DB_ECHO: bool = Field(default=False, description="Habilita logs de todas as queries SQL no console")

    # ── Banco de Dados PostgreSQL (Async) ──────────────────────
    DATABASE_URL: str = Field(
        default="",
        description=(
            "URL de conexão assíncrona: "
            "postgresql+asyncpg://usuario:senha@host:5432/banco"
        ),
    )
    TEST_DATABASE_URL: str | None = Field(default=None)
    DB_POOL_SIZE: int = Field(default=25, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=35, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5, le=120)
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        description="Reusa conexões após N segundos (evita conexões stale)",
    )

    # ── Segurança ─────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Chave secreta para assinatura de JWT (mín. 256 bits)",
    )
    ENCRYPTION_KEY: str = Field(
        ...,
        description="Chave Fernet base64 para criptografia de oracle_conn",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=5, le=1440)
    ALGORITHM: str = Field(default="HS256")

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = Field(
        ...,
        min_length=20,
        description="Chave de API da OpenAI (sk-...)",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Modelo com suporte a Structured Outputs",
    )
    OPENAI_MAX_TOKENS: int = Field(default=1024, ge=256, le=4096)
    OPENAI_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="0.0 para respostas determinísticas (recomendado para Motor de Intenções)",
    )
    OPENAI_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Timeout em segundos para chamadas à API da OpenAI",
    )

    # ── Oracle Simulação (Mock) ──────────────────────────────
    MOCK_ORACLE: bool = Field(
        default=False,
        description="Se True, intercepta qualquer conexão Oracle e usa a base mock local. Para produção/Oracle real, manter False."
    )
    MOCK_OPENAI: bool = Field(
        default=False,
        description="Usa provedor deterministico de IA durante testes.",
    )

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description="Lista de origens permitidas para CORS",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: list[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default=["*"])
    CORS_ALLOW_ORIGIN_REGEX: str | None = Field(
        default=None,
        description=(
            "Regex opcional para origens permitidas. Em desenvolvimento, quando vazio, "
            "o LuminaAI aceita automaticamente localhost e IPs privados nas portas do frontend."
        ),
    )

    # ── Validadores ───────────────────────────────────────────

    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug_flag(cls, v: object) -> object:
        """Aceita aliases comuns de ambiente sem quebrar o bootstrap."""
        if isinstance(v, str):
            normalized = v.lower().strip()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Garante que o ambiente seja um valor válido."""
        allowed = {"development", "staging", "production", "test"}
        normalized = v.lower().strip()
        if normalized not in allowed:
            raise ValueError(
                f"ENVIRONMENT inválido: '{v}'. Deve ser um de: {sorted(allowed)}"
            )
        return normalized

    @field_validator("CONVERSATION_STATE_MODE")
    @classmethod
    def validate_conversation_state_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {
            "LEGACY_ONLY",
            "SHADOW_WRITE",
            "DUAL_WRITE_LEGACY_READ",
            "POSTGRES_READ_WRITE",
            "POSTGRES_ONLY",
        }
        if normalized not in allowed:
            raise ValueError("CONVERSATION_STATE_MODE invalido")
        return normalized

    @field_validator("ENTERPRISE_KNOWLEDGE_MODE")
    @classmethod
    def validate_enterprise_knowledge_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {"LEGACY_ONLY", "SHADOW_READ", "V2_READ", "V2_READ_WRITE"}
        if normalized not in allowed:
            raise ValueError("ENTERPRISE_KNOWLEDGE_MODE invalido")
        return normalized

    @field_validator("USER_ANALYTICAL_PROFILE_MODE")
    @classmethod
    def validate_user_analytical_profile_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {"LEGACY_ONLY", "SHADOW", "V2_READ", "V2_READ_WRITE"}
        if normalized not in allowed:
            raise ValueError("USER_ANALYTICAL_PROFILE_MODE invalido")
        return normalized

    @field_validator("SUPERVISED_FEEDBACK_MODE")
    @classmethod
    def validate_supervised_feedback_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {
            "LEGACY_ONLY",
            "SHADOW",
            "V2_COLLECT",
            "V2_REVIEW",
            "V2_CURATE",
        }
        if normalized not in allowed:
            raise ValueError("SUPERVISED_FEEDBACK_MODE invalido")
        return normalized

    @field_validator("SEMANTIC_RETRIEVAL_MODE")
    @classmethod
    def validate_semantic_retrieval_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {"LEGACY_ONLY", "SHADOW", "HYBRID_READ", "V2_AUTHORITATIVE"}
        if normalized not in allowed:
            raise ValueError("SEMANTIC_RETRIEVAL_MODE invalido")
        return normalized

    @field_validator("SMART_CACHE_MATERIALIZATION_MODE")
    @classmethod
    def validate_smart_cache_materialization_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {
            "LEGACY_ONLY",
            "SHADOW_OBSERVE",
            "V2_CACHE_READ",
            "V2_CACHE_READ_WRITE",
            "V2_MATERIALIZATION",
        }
        if normalized not in allowed:
            raise ValueError("SMART_CACHE_MATERIALIZATION_MODE invalido")
        return normalized

    @field_validator("DASHBOARD_BACKEND_MODE")
    @classmethod
    def validate_dashboard_backend_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {"LEGACY_ONLY", "SHADOW_VALIDATE", "V2_AUTHORING", "V2_PUBLISHED_READ", "V2_RUNTIME"}
        if normalized not in allowed:
            raise ValueError("DASHBOARD_BACKEND_MODE invalido")
        return normalized

    @field_validator("DASHBOARD_AI_ASSISTANCE_MODE")
    @classmethod
    def validate_dashboard_ai_assistance_mode(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        allowed = {"LEGACY_ONLY", "SHADOW_ANALYZE", "AI_PROPOSAL_PREVIEW", "AI_DRAFT_CREATE", "AI_ASSISTED_EDIT"}
        if normalized not in allowed:
            raise ValueError("DASHBOARD_AI_ASSISTANCE_MODE invalido")
        return normalized

    @model_validator(mode="after")
    def validate_database_contract(self) -> "Settings":
        if self.ENVIRONMENT == "test" or self.LUMINA_TESTING:
            if self.ENVIRONMENT != "test" or not self.LUMINA_TESTING:
                raise ValueError(
                    "Modo de teste exige ENVIRONMENT=test e LUMINA_TESTING=true."
                )
            if not self.TEST_DATABASE_URL:
                raise ValueError("TEST_DATABASE_URL e obrigatoria no modo de teste.")
            self.DATABASE_URL = self.TEST_DATABASE_URL
            self.MOCK_ORACLE = True
            self.MOCK_OPENAI = True
            self.LUMINA_DISABLE_EXTERNAL_NETWORK = True
        elif not self.DATABASE_URL:
            raise ValueError("DATABASE_URL e obrigatoria fora do modo de teste.")
        if not (
            self.CONVERSATION_ARCHIVE_AFTER_DAYS
            <= self.CONVERSATION_SOFT_DELETE_AFTER_DAYS
            <= self.CONVERSATION_PURGE_AFTER_DAYS
        ):
            raise ValueError("Conversation retention periods must be ordered.")
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.CORS_ORIGINS:
            raise ValueError("CORS com credentials exige allowlist explicita; wildcard e proibido.")
        if self.ENVIRONMENT == "production":
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.CORS_ORIGINS):
                raise ValueError("CORS de producao exige origins explicitas do deployment, sem localhost.")
            unsafe_test_flags = (
                self.LUMINA_TESTING
                or self.MOCK_ORACLE
                or self.MOCK_OPENAI
                or self.DASHBOARD_AI_FAKE_PROVIDER_ENABLED
                or self.PERFORMANCE_CERTIFICATION_MODE
            )
            unsafe_rollout = (
                self.ROLLOUT_EXECUTION_ENABLED
                or self.ROLLOUT_STAGE != "DISABLED"
                or self.ROLLOUT_CANARY_PERCENTAGE != 0
                or bool(self.ROLLOUT_CANARY_TENANT_ALLOWLIST)
                or self.WORK_QUEUE_WORKER_ENABLED
            )
            if unsafe_test_flags:
                raise ValueError("Flags de teste, provider fake ou performance sao proibidas em producao.")
            if unsafe_rollout:
                raise ValueError("Worker, canary e rollout real sao proibidos no baseline de producao.")
        return self

    # ── Propriedades Derivadas ─────────────────────────────────

    @property
    def is_production(self) -> bool:
        """Retorna True se rodando em ambiente de produção."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Retorna True se rodando em ambiente de desenvolvimento."""
        return self.ENVIRONMENT == "development"

    @property
    def is_staging(self) -> bool:
        """Retorna True se rodando em ambiente de staging."""
        return self.ENVIRONMENT == "staging"

    @property
    def is_testing(self) -> bool:
        """Retorna True somente para o modo de teste explicitamente habilitado."""
        return self.ENVIRONMENT == "test" and self.LUMINA_TESTING

    @property
    def cors_allow_origin_regex(self) -> str | None:
        """Permite acesso via IP local em desenvolvimento sem editar o .env a cada rede."""
        if self.CORS_ALLOW_ORIGIN_REGEX:
            return self.CORS_ALLOW_ORIGIN_REGEX
        if not self.is_development:
            return None
        return (
            r"^https?://("
            r"localhost|127\.0\.0\.1|"
            r"10(?:\.\d{1,3}){3}|"
            r"192\.168(?:\.\d{1,3}){2}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
            r")(?::(?:3000|3001|3002|5173))?$"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna a instância singleton das configurações (cached com lru_cache).
    O cache garante que as variáveis de ambiente são lidas apenas uma vez.
    """
    _settings = Settings()
    logger.info(
        "✅ LuminaAI Settings carregadas | env=%s | debug=%s | model=%s",
        _settings.ENVIRONMENT,
        _settings.DEBUG,
        _settings.OPENAI_MODEL,
    )
    return _settings


# Instância global — importe esta em vez de chamar get_settings() diretamente
settings: Settings = get_settings()
