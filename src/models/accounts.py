"""Pydantic input/output models for the accounts domain."""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import Field

from . import FinanceBaseModel


class AccountType(str, Enum):
    """The five fundamental account types in double-entry bookkeeping."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# ── Tool input models ────────────────────────────────────────────

class CreateAccountInput(FinanceBaseModel):
    """Input for creating a new account."""
    name: str = Field(
        ..., description="Unique account name (e.g., 'Checking', 'Rent Expense')",
        min_length=1, max_length=120,
    )
    account_type: AccountType = Field(
        ..., description="One of: asset, liability, equity, income, expense",
    )
    currency: str = Field(
        default="USD", description="ISO 4217 currency code", min_length=3, max_length=3,
    )
    parent_id: Optional[str] = Field(
        default=None, description="UUID of parent account for sub-accounts",
    )


class ListAccountsInput(FinanceBaseModel):
    """Input for listing / filtering accounts."""
    account_type: Optional[AccountType] = Field(
        default=None, description="Filter by account type",
    )
    is_active: Optional[bool] = Field(
        default=None, description="Filter by active status",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'",
    )


class GetAccountInput(FinanceBaseModel):
    """Input for retrieving a single account."""
    account_id: str = Field(..., description="UUID of the account")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class UpdateAccountInput(FinanceBaseModel):
    """Input for updating an existing account."""
    account_id: str = Field(..., description="UUID of the account to update")
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_active: Optional[bool] = Field(default=None)


class GetAccountBalanceInput(FinanceBaseModel):
    """Input for computing an account's running balance."""
    account_id: str = Field(..., description="UUID of the account")
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional cut-off date (YYYY-MM-DD). Defaults to today.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
