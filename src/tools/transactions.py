"""MCP tools for high-level transaction recording and browsing."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..models.transactions import (
    DeleteTransactionInput,
    GetTransactionInput,
    ListTransactionsInput,
    RecordTransactionInput,
)
from ..services.transactions import TransactionService
from ..utils import handle_tool_error, to_json


def register(mcp: FastMCP) -> None:
    """Register all transaction-related tools."""

    @mcp.tool(
        name="finance_record_transaction",
        annotations={
            "title": "Record Transaction",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def finance_record_transaction(params: RecordTransactionInput) -> str:
        """Record a financial transaction (e.g., purchase, payment, transfer).

        This is the primary way to log day-to-day financial activity. Under
        the hood it creates a balanced journal entry: the debit_account is
        debited and the credit_account is credited for the given amount.

        Example: Buying groceries for $50
          debit_account_id  = <Groceries expense account UUID>
          credit_account_id = <Checking asset account UUID>
          amount = 50.00, payee = "Whole Foods", category = "groceries"

        Args:
            params (RecordTransactionInput): date, amount (>0),
                debit_account_id, credit_account_id, payee, description,
                category.

        Returns:
            str: JSON of the created transaction and linked journal entry ID.
        """
        try:
            txn = await TransactionService.record(
                amount=params.amount,
                debit_account_id=params.debit_account_id,
                credit_account_id=params.credit_account_id,
                date=params.date,
                payee=params.payee,
                description=params.description,
                category=params.category,
            )
            return to_json(txn)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_list_transactions",
        annotations={
            "title": "List Transactions",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_list_transactions(params: ListTransactionsInput) -> str:
        """List transactions with optional date, category, payee, and account filters.

        Args:
            params (ListTransactionsInput): start_date, end_date, category,
                payee, account_id, limit, offset, response_format.

        Returns:
            str: Paginated list of transactions.
        """
        try:
            result = await TransactionService.list_all(
                start_date=params.start_date,
                end_date=params.end_date,
                category=params.category,
                payee=params.payee,
                account_id=params.account_id,
                limit=params.limit,
                offset=params.offset,
            )
            if params.response_format.value == "json":
                return to_json(result)
            lines = [f"Total: {result['total']} | Showing: {result['count']} (offset {result['offset']})\n"]
            for txn in result["items"]:
                lines.append(TransactionService.format_md(txn))
            if result["has_more"]:
                lines.append(f"\n*More results available (next offset: {result['offset'] + result['count']})*")
            return "\n\n".join(lines)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_get_transaction",
        annotations={
            "title": "Get Transaction",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_transaction(params: GetTransactionInput) -> str:
        """Retrieve a single transaction by ID.

        Args:
            params (GetTransactionInput): transaction_id, response_format.

        Returns:
            str: Full transaction details.
        """
        try:
            txn = await TransactionService.get(params.transaction_id)
            if not txn:
                return "Error: Transaction not found."
            if params.response_format.value == "json":
                return to_json(txn)
            return TransactionService.format_md(txn)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_delete_transaction",
        annotations={
            "title": "Delete Transaction",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def finance_delete_transaction(params: DeleteTransactionInput) -> str:
        """Delete a transaction and void its underlying journal entry.

        The journal entry is not deleted — a reversing entry is created to
        preserve the audit trail.

        Args:
            params (DeleteTransactionInput): transaction_id.

        Returns:
            str: Confirmation with void details.
        """
        try:
            result = await TransactionService.delete(params.transaction_id)
            if "error" in result:
                return f"Error: {result['error']}"
            return to_json(result)
        except Exception as e:
            return handle_tool_error(e)
