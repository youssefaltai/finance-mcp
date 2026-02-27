"""Pydantic input/output models for the journal entries domain."""

from __future__ import annotations

from typing import Optional
from pydantic import Field, field_validator

from . import FinanceBaseModel
from .accounts import ResponseFormat


class JournalLineInput(FinanceBaseModel):
    """A single debit or credit leg of a journal entry."""
    account_id: str = Field(..., description="UUID of the account for this line")
    debit: float = Field(default=0.0, description="Debit amount (≥ 0)", ge=0)
    credit: float = Field(default=0.0, description="Credit amount (≥ 0)", ge=0)
    memo: str = Field(default="", description="Optional memo for this line", max_length=500)

    @field_validator("credit")
    @classmethod
    def one_side_only(cls, v: float, info) -> float:
        debit = info.data.get("debit", 0.0)
        if debit > 0 and v > 0:
            raise ValueError("A line cannot have both debit and credit > 0")
        if debit == 0 and v == 0:
            raise ValueError("A line must have either debit or credit > 0")
        return v


class CreateJournalEntryInput(FinanceBaseModel):
    """Input for creating a new journal entry with its lines."""
    date: Optional[str] = Field(
        default=None,
        description="Entry date (YYYY-MM-DD). Defaults to today.",
    )
    description: str = Field(
        default="", description="Description / narration of the entry", max_length=500,
    )
    lines: list[JournalLineInput] = Field(
        ..., description="Debit and credit lines (must balance)", min_length=2,
    )
    auto_post: bool = Field(
        default=True,
        description="If True, immediately post the entry (enforces balance check).",
    )


class ListJournalEntriesInput(FinanceBaseModel):
    """Input for listing journal entries."""
    start_date: Optional[str] = Field(default=None, description="Start date filter (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date filter (YYYY-MM-DD)")
    is_posted: Optional[bool] = Field(default=None, description="Filter by posted status")
    limit: int = Field(default=25, ge=1, le=100, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class GetJournalEntryInput(FinanceBaseModel):
    """Input for retrieving a single journal entry with its lines."""
    journal_entry_id: str = Field(..., description="UUID of the journal entry")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class PostJournalEntryInput(FinanceBaseModel):
    """Input for posting (finalizing) a draft journal entry."""
    journal_entry_id: str = Field(..., description="UUID of the journal entry to post")


class VoidJournalEntryInput(FinanceBaseModel):
    """Input for voiding a posted journal entry (creates a reversing entry)."""
    journal_entry_id: str = Field(..., description="UUID of the journal entry to void")
