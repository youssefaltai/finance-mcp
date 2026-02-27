"""MCP tools for managing the chart of accounts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..models.accounts import (
    CreateAccountInput,
    GetAccountBalanceInput,
    GetAccountInput,
    ListAccountsInput,
    UpdateAccountInput,
)
from ..services.accounts import AccountService
from ..utils import handle_tool_error, to_json


def register(mcp: FastMCP) -> None:
    """Register all account-related tools on the given MCP server."""

    @mcp.tool(
        name="finance_create_account",
        annotations={
            "title": "Create Account",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def finance_create_account(params: CreateAccountInput) -> str:
        """Create a new account to track money flow.

        **WHEN TO USE**: Before recording any transactions, set up your accounts.
        **ACCOUNT TYPES**:
        - asset: Money you own (Checking, Savings, Cash, Credit Card)
        - expense: Money you spend (Groceries, Gas, Rent, Entertainment)
        - income: Money you earn (Salary, Freelance, Bonus)
        - liability: Money you owe (Credit Card, Loan)
        - equity: Starting balance / net worth

        **EXAMPLES**:
        - "Create a Checking account (asset) to track my bank account"
        - "Create a Groceries account (expense) to track grocery spending"
        - "Create a Salary account (income) to track paychecks"

        Args:
            params (CreateAccountInput): name, account_type
                (asset|liability|equity|income|expense), optional parent_id

        Returns:
            str: JSON of the newly created account with ID.
        """
        try:
            acc = await AccountService.create(
                name=params.name,
                account_type=params.account_type.value,
                parent_id=params.parent_id,
            )
            return to_json(acc)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_list_accounts",
        annotations={
            "title": "List Accounts",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_list_accounts(params: ListAccountsInput) -> str:
        """List all accounts, optionally filtered by type or active status.

        Args:
            params (ListAccountsInput): Optional account_type filter,
                is_active filter, and response_format (markdown|json).

        Returns:
            str: Formatted list of accounts.
        """
        try:
            accs = await AccountService.list_all(
                account_type=params.account_type.value if params.account_type else None,
                is_active=params.is_active,
            )
            if params.response_format.value == "json":
                return to_json(accs)
            return "\n\n".join(AccountService.format_md(a) for a in accs) or "No accounts found."
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_get_account",
        annotations={
            "title": "Get Account",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_account(params: GetAccountInput) -> str:
        """Retrieve details for a single account by ID.

        Args:
            params (GetAccountInput): account_id (UUID), response_format.

        Returns:
            str: Account details in the requested format.
        """
        try:
            acc = await AccountService.get(params.account_id)
            if not acc:
                return "Error: Account not found. Check the UUID."
            if params.response_format.value == "json":
                return to_json(acc)
            return AccountService.format_md(acc)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_update_account",
        annotations={
            "title": "Update Account",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_update_account(params: UpdateAccountInput) -> str:
        """Update an account's name or active status.

        Args:
            params (UpdateAccountInput): account_id, optional name, optional is_active.

        Returns:
            str: Updated account record as JSON.
        """
        try:
            acc = await AccountService.update(
                account_id=params.account_id,
                name=params.name,
                is_active=params.is_active,
            )
            if not acc:
                return "Error: Account not found."
            return to_json(acc)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_get_account_balance",
        annotations={
            "title": "Get Account Balance",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_account_balance(params: GetAccountBalanceInput) -> str:
        """Check how much money is in an account.

        **WHEN TO USE**: After recording transactions, check balances to verify.
        **INTERPRETATION**:
        - Asset (Checking): Higher balance = more money in the account
        - Expense (Groceries): Higher balance = more money spent on groceries
        - Income (Salary): Higher balance = more money earned

        **EXAMPLES**:
        - "What's my Checking account balance?" → Shows money available
        - "How much have I spent on groceries?" → Shows balance in Groceries account

        Args:
            params (GetAccountBalanceInput): account_id, optional as_of_date (YYYY-MM-DD),
                response_format (markdown/json)

        Returns:
            str: Current balance, total debits, total credits, and date.
        """
        try:
            result = await AccountService.balance(
                account_id=params.account_id,
                as_of_date=params.as_of_date,
            )
            if "error" in result:
                return f"Error: {result['error']}"
            if params.response_format.value == "json":
                return to_json(result)
            return (
                f"**{result['name']}** ({result['account_type']})\n"
                f"Balance: **{result['balance']:,.2f}**\n"
                f"Total debits: {result['total_debit']:,.2f} | "
                f"Total credits: {result['total_credit']:,.2f}\n"
                f"As of: {result['as_of_date']}"
            )
        except Exception as e:
            return handle_tool_error(e)
