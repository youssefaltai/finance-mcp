"""Database connection pool management using asyncpg."""

from __future__ import annotations

import os
import asyncpg

_pool: asyncpg.Pool | None = None

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://finance:finance_secret@localhost:5432/finance_db",
)


async def get_pool() -> asyncpg.Pool:
    """Return the global connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Gracefully close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
