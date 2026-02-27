"""Tool registration package — maps each domain's register() to named exports."""

from .accounts import register as register_account_tools
from .journal_entries import register as register_journal_tools
from .transactions import register as register_transaction_tools
from .budgets import register as register_budget_tools
from .guidance import register as register_guidance_tools

__all__ = [
    "register_account_tools",
    "register_journal_tools",
    "register_transaction_tools",
    "register_budget_tools",
    "register_guidance_tools",
]
