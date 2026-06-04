from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class AsyncDatabase:
    def __init__(
        self,
        url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/adult_platform",
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        echo: bool = False,
    ) -> None:
        self._url = url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_pre_ping = pool_pre_ping
        self._echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def create_engine(self) -> AsyncEngine:
        if self._engine is not None:
            return self._engine

        self._engine = create_async_engine(
            self._url,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_pre_ping=self._pool_pre_ping,
            echo=self._echo,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("Created async database engine with pool_size=%d", self._pool_size)
        return self._engine

    async def create_session(self) -> AsyncSession:
        if self._session_factory is None:
            await self.create_engine()
        assert self._session_factory is not None
        return self._session_factory()

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        session = await self.create_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return result

    async def health_check(self) -> dict[str, Any]:
        try:
            if self._engine is None:
                await self.create_engine()
            assert self._engine is not None

            async with self._engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()

            pool = self._engine.pool
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database engine disposed")
