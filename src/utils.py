"""Shared utilities used across services and tools."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional


def parse_date(d: Optional[str]) -> Optional[date]:
    """Convert a YYYY-MM-DD string to a date object, or None."""
    return date.fromisoformat(d) if d else None


def handle_tool_error(e: Exception) -> str:
    """Format an exception as a user-facing error string."""
    return f"Error: {type(e).__name__}: {e}"


def to_json(obj: Any) -> str:
    """Serialize any object to a JSON string, coercing non-primitives via str()."""
    return json.dumps(obj, indent=2, default=str)
