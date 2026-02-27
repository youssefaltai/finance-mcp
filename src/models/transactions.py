"""Pydantic input/output models for the transactions domain."""

from __future__ import annotations

from typing import Optional
from pydantic import Field

from . import FinanceBaseModel
from .accounts import ResponseFormat


class RecordTransactionInput(FinanceBaseModel):
    """Input for recording a user-facing transaction.

    This is the high-level convenience tool — it creates a journal entry
    under the hood with one debit and one credit line.
    """
    date: Optional[str] = Field(
        default=None, description="Transaction date (YYYY-MM-DD). Defaults to today.",
    )
    amount: float = Field(
        ..., description="Transaction amount (> 0)", gt=0,
    )
    debit_account_id: str = Field(
        ..., description="UUID of the account to debit",
    )
    credit_account_id: str = Field(
        ..., description="UUID of the account to credit",
    )
    payee: str = Field(
        default="", description="Who was paid / received from", max_length=200,
    )
    description: str = Field(
        default="", description="Transaction description", max_length=500,
    )
    category: str = Field(
        default="", description="Category tag (e.g. 'groceries', 'salary')", max_length=100,
    )


class ListTransactionsInput(FinanceBaseModel):
    """Input for listing transactions with optional filters."""
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    category: Optional[str] = Field(default=None, description="Filter by category")
    payee: Optional[str] = Field(default=None, description="Filter by payee (partial match)")
    account_id: Optional[str] = Field(
        default=None,
        description="Filter to transactions that touch this account",
    )
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetTransactionInput(FinanceBaseModel):
    """Input for retrieving a single transaction."""
    transaction_id: str = Field(..., description="UUID of the transaction")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class DeleteTransactionInput(FinanceBaseModel):
    """Input for deleting a transaction (and voiding its journal entry)."""
    transaction_id: str = Field(..., description="UUID of the transaction to delete")
