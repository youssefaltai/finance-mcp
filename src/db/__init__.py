"""Database package — re-exports connection pool and schema initialization."""

from .connection import get_pool, close_pool
from .schema import initialize_schema

__all__ = ["get_pool", "close_pool", "initialize_schema"]
