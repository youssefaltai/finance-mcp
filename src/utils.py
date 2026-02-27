"""Shared utilities used across services and tools."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Optional


def parse_date(d: Optional[str]) -> Optional[date]:
    """Convert a YYYY-MM-DD string to a date object, or None."""
    return date.fromisoformat(d) if d else None


def handle_tool_error(e: Exception) -> str:
    """Format an exception as a user-facing error message.

    Translates cryptic database errors into friendly, actionable messages.
    """
    error_name = type(e).__name__
    error_msg = str(e)

    # Map database error patterns to friendly messages
    if "UniqueViolationError" in error_name or "duplicate key" in error_msg.lower():
        if "accounts_name_key" in error_msg:
            return "Error: Account name already exists. Choose a different name."
        if "budgets_account_id_year_month_key" in error_msg:
            return "Error: Budget already exists for this account in this month/year. Use finance_set_budget to update it."
        return "Error: This record already exists. Check for duplicates."

    if "ForeignKeyViolationError" in error_name or "foreign key constraint" in error_msg.lower():
        if "account_id" in error_msg.lower():
            return "Error: Account not found. Check that the account ID exists and is valid."
        if "journal_entry_id" in error_msg.lower():
            return "Error: Journal entry not found."
        return "Error: Referenced record not found. Check all IDs are valid."

    if "CheckViolationError" in error_name or "check constraint" in error_msg.lower():
        if "month" in error_msg.lower():
            return "Error: Month must be between 1 and 12."
        if "positive_amounts" in error_msg.lower():
            return "Error: Amounts cannot be negative."
        return f"Error: Constraint violated: {error_msg}"

    if "Journal entry" in error_msg and "unbalanced" in error_msg.lower():
        # This is a balance error - the message should be enhanced elsewhere
        return f"Error: {error_msg}"

    if "not found" in error_msg.lower():
        return f"Error: Not found. {error_msg}"

    # Fallback for unknown errors
    return f"Error: {error_name}: {error_msg}"


def to_json(obj: Any) -> str:
    """Serialize any object to a JSON string, coercing non-primitives via str()."""
    return json.dumps(obj, indent=2, default=str)
