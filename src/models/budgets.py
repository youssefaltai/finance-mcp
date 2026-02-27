"""Pydantic input/output models for the budgets domain."""

from __future__ import annotations

from typing import Optional
from pydantic import Field

from . import FinanceBaseModel
from .accounts import ResponseFormat


class SetBudgetInput(FinanceBaseModel):
    """Input for setting or updating a monthly budget for an account."""
    account_id: str = Field(..., description="UUID of the account (typically an expense account)")
    year: int = Field(..., description="Budget year (e.g. 2026)", ge=2000, le=2100)
    month: int = Field(..., description="Budget month (1-12)", ge=1, le=12)
    amount: float = Field(..., description="Budget amount (≥ 0)", ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    notes: str = Field(default="", max_length=500)


class GetBudgetInput(FinanceBaseModel):
    """Input for getting a single budget entry."""
    account_id: str = Field(..., description="UUID of the account")
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ListBudgetsInput(FinanceBaseModel):
    """Input for listing budgets for a given period."""
    year: int = Field(..., description="Budget year", ge=2000, le=2100)
    month: Optional[int] = Field(default=None, description="Budget month (omit for full year)", ge=1, le=12)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class BudgetVsActualInput(FinanceBaseModel):
    """Input for budget-vs-actual comparison report."""
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
