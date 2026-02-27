"""Personal Finance MCP Server — double-entry bookkeeping over Postgres.

Startup:
    docker compose up          # Postgres + this server
    # or, for local dev:
    DATABASE_URL=... python -m src.server
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from .db import get_pool, close_pool, initialize_schema
from .tools import (
    register_account_tools,
    register_journal_tools,
    register_transaction_tools,
    register_budget_tools,
    register_guidance_tools,
)


# ── Lifespan: connect to Postgres, run migrations, tear down ─────

@asynccontextmanager
async def app_lifespan(server):
    """Initialize DB pool and schema on startup; clean up on shutdown."""
    pool = await get_pool()
    await initialize_schema()
    print("✅ Database connected and schema initialized.", file=sys.stderr)
    yield {"pool": pool}
    await close_pool()
    print("👋 Database pool closed.", file=sys.stderr)


# ── Create server and register tools ─────────────────────────────

port = int(os.getenv("MCP_PORT", "8000"))

mcp = FastMCP(
    "finance_mcp",
    lifespan=app_lifespan,
    host="0.0.0.0",
    port=port,
)

register_guidance_tools(mcp)
register_account_tools(mcp)
register_journal_tools(mcp)
register_transaction_tools(mcp)
register_budget_tools(mcp)


# ── Entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable_http")

    if transport == "streamable_http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio
