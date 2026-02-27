"""MCP tools for budget management and budget-vs-actual reporting."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..models.budgets import (
    BudgetVsActualInput,
    GetBudgetInput,
    ListBudgetsInput,
    SetBudgetInput,
)
from ..services.budgets import BudgetService
from ..utils import handle_tool_error, to_json


def register(mcp: FastMCP) -> None:
    """Register all budget-related tools."""

    @mcp.tool(
        name="finance_set_budget",
        annotations={
            "title": "Set Monthly Budget",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_set_budget(params: SetBudgetInput) -> str:
        """Set or update the monthly budget for an account.

        If a budget already exists for the given account/year/month, it will
        be updated (upsert).

        Args:
            params (SetBudgetInput): account_id, year, month (1-12),
                amount (>= 0), notes.

        Returns:
            str: JSON of the budget record.
        """
        try:
            b = await BudgetService.set_budget(
                account_id=params.account_id,
                year=params.year,
                month=params.month,
                amount=params.amount,
                notes=params.notes,
            )
            return to_json(b)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_get_budget",
        annotations={
            "title": "Get Budget",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_budget(params: GetBudgetInput) -> str:
        """Retrieve the budget for a specific account, year, and month.

        Args:
            params (GetBudgetInput): account_id, year, month, response_format.

        Returns:
            str: Budget details or not-found message.
        """
        try:
            b = await BudgetService.get(
                account_id=params.account_id,
                year=params.year,
                month=params.month,
            )
            if not b:
                return f"No budget found for account {params.account_id} in {params.year}/{params.month:02d}."
            if params.response_format.value == "json":
                return to_json(b)
            return BudgetService.format_budget_md(b)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_list_budgets",
        annotations={
            "title": "List Budgets",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_list_budgets(params: ListBudgetsInput) -> str:
        """List all budgets for a given year (optionally filtered by month).

        Args:
            params (ListBudgetsInput): year, optional month, response_format.

        Returns:
            str: List of budgets.
        """
        try:
            budgets = await BudgetService.list_all(year=params.year, month=params.month)
            if params.response_format.value == "json":
                return to_json(budgets)
            if not budgets:
                return f"No budgets set for {params.year}."
            return "\n\n".join(BudgetService.format_budget_md(b) for b in budgets)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_budget_vs_actual",
        annotations={
            "title": "Budget vs Actual Report",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_budget_vs_actual(params: BudgetVsActualInput) -> str:
        """Generate a budget-vs-actual comparison for a given month.

        Shows budgeted amount, actual spending (from posted journal entries),
        variance, and percentage used for each budgeted account.

        Args:
            params (BudgetVsActualInput): year, month, response_format.

        Returns:
            str: Tabular comparison of budget vs actual spending.
        """
        try:
            rows = await BudgetService.budget_vs_actual(year=params.year, month=params.month)
            if not rows:
                return f"No budget data for {params.year}/{params.month:02d}."
            if params.response_format.value == "json":
                return to_json(rows)
            return BudgetService.format_bva_md(rows, params.year, params.month)
        except Exception as e:
            return handle_tool_error(e)
