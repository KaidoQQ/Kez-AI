from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg


class BaseDatabase:
    """Базовый asyncpg-слой с единым пулом соединений PostgreSQL."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Создаёт пул соединений один раз при старте приложения."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )

    async def close(self) -> None:
        """Закрывает пул соединений при штатной остановке приложения."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def _get_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized. Call connect() first.")
        return self.pool

    async def execute(self, query: str, *args: object) -> str:
        """Выполняет запрос без возврата строк и возвращает статус PostgreSQL."""
        async with self._get_pool().acquire() as connection:
            return await connection.execute(query, *args)

    async def fetchone(self, query: str, *args: object) -> asyncpg.Record | None:
        """Возвращает одну строку или None, если запись не найдена."""
        async with self._get_pool().acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchall(self, query: str, *args: object) -> list[asyncpg.Record]:
        """Возвращает все строки результата запроса."""
        async with self._get_pool().acquire() as connection:
            return await connection.fetch(query, *args)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Предоставляет транзакцию для операций, которые должны быть атомарными."""
        async with self._get_pool().acquire() as connection:
            async with connection.transaction():
                yield connection
