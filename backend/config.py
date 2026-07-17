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

from pydantic import Field, field_validator
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
    DEBUG: bool = Field(default=False)
    NEW_PIPELINE_ACTIVE: bool = Field(default=False)
    ENABLE_DETERMINISTIC_PIPELINE: bool = Field(default=False)
    DB_ECHO: bool = Field(default=False, description="Habilita logs de todas as queries SQL no console")

    # ── Banco de Dados PostgreSQL (Async) ──────────────────────
    DATABASE_URL: str = Field(
        ...,
        description=(
            "URL de conexão assíncrona: "
            "postgresql+asyncpg://usuario:senha@host:5432/banco"
        ),
    )
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=50)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
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

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://192.168.0.36:3000",
            "http://192.168.18.103:3000",
            "http://192.168.1.5:3000",
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
        allowed = {"development", "staging", "production"}
        normalized = v.lower().strip()
        if normalized not in allowed:
            raise ValueError(
                f"ENVIRONMENT inválido: '{v}'. Deve ser um de: {sorted(allowed)}"
            )
        return normalized

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
            r")(?::(?:3000|5173))?$"
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
