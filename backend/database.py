"""
LuminaAI — Gerenciador de Sessão PostgreSQL (Async SQLAlchemy 2.x)

Configura o engine assíncrono, a factory de sessões e a classe Base ORM.
Expõe duas formas de obter sessões:
  - `get_db`: dependency injection para rotas FastAPI
  - `get_db_context`: context manager para background tasks e scripts

Uso em routers FastAPI:
    from database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends

    @router.get("/exemplo")
    async def exemplo(db: AsyncSession = Depends(get_db)):
        ...

Uso em background tasks:
    from database import get_db_context

    async def minha_task():
        async with get_db_context() as session:
            ...
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


# ── Engine Assíncrono ──────────────────────────────────────────
# pool_pre_ping=True: SQLAlchemy verifica se a conexão está viva antes de
# reutilizá-la do pool, evitando erros após períodos de inatividade.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)


# ── Factory de Sessões Assíncronas ─────────────────────────────
# expire_on_commit=False: mantém atributos acessíveis após commit,
# essencial para async onde o objeto pode ser serializado depois do commit.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base Declarativa ORM ──────────────────────────────────────
class Base(DeclarativeBase):
    """
    Classe base para todos os modelos ORM do LuminaAI.
    Todos os models devem herdar desta classe.
    """
    pass


# ── Dependency FastAPI ─────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency FastAPI para injeção de sessão de banco de dados.

    Fluxo:
        1. Abre uma sessão assíncrona
        2. Injeta na rota via `yield`
        3. Em caso de sucesso: faz commit automático
        4. Em caso de exceção: faz rollback e relança a exceção
        5. Sempre fecha a sessão ao finalizar

    Exemplo:
        @router.get("/items")
        async def listar_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Erro na transação do banco de dados — rollback realizado"
            )
            raise
        finally:
            await session.close()


# ── Context Manager para Background Tasks ─────────────────────

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager para uso de sessão fora do contexto de requests HTTP.
    Use em: background tasks, scripts de migração, jobs agendados.

    Exemplo:
        async with get_db_context() as session:
            session.add(meu_objeto)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Erro no context manager do banco — rollback realizado"
            )
            raise
        finally:
            await session.close()
