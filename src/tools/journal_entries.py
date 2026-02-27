"""MCP tools for journal entry operations — the double-entry core."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..models.journal_entries import (
    CreateJournalEntryInput,
    GetJournalEntryInput,
    ListJournalEntriesInput,
    PostJournalEntryInput,
    VoidJournalEntryInput,
)
from ..services.journal_entries import JournalEntryService
from ..utils import handle_tool_error, to_json


def register(mcp: FastMCP) -> None:
    """Register all journal-entry tools."""

    @mcp.tool(
        name="finance_create_journal_entry",
        annotations={
            "title": "Create Journal Entry",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def finance_create_journal_entry(params: CreateJournalEntryInput) -> str:
        """Create a journal entry with debit and credit lines.

        The entry must balance (total debits == total credits) if auto_post
        is True. Each line targets an account_id with either a debit or credit
        amount (not both).

        Args:
            params (CreateJournalEntryInput): date, description, lines
                (list of {account_id, debit, credit, memo}), auto_post.

        Returns:
            str: The created journal entry with all lines as JSON.
        """
        try:
            lines = [line.model_dump() for line in params.lines]
            je = await JournalEntryService.create(
                lines=lines,
                entry_date=params.date,
                description=params.description,
                auto_post=params.auto_post,
            )
            return to_json(je)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_list_journal_entries",
        annotations={
            "title": "List Journal Entries",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_list_journal_entries(params: ListJournalEntriesInput) -> str:
        """List journal entries with optional date and status filters.

        Args:
            params (ListJournalEntriesInput): start_date, end_date, is_posted,
                limit, offset, response_format.

        Returns:
            str: Paginated list of journal entries.
        """
        try:
            result = await JournalEntryService.list_all(
                start_date=params.start_date,
                end_date=params.end_date,
                is_posted=params.is_posted,
                limit=params.limit,
                offset=params.offset,
            )
            if params.response_format.value == "json":
                return to_json(result)
            lines = [f"Total: {result['total']} | Showing: {result['count']} (offset {result['offset']})\n"]
            for je in result["items"]:
                status = "Posted" if je.get("is_posted") else "Draft"
                lines.append(f"- [{status}] `{je['id']}` - {je['date']} - {je.get('description', '')}")
            if result["has_more"]:
                lines.append(f"\n*More results available (next offset: {result['offset'] + result['count']})*")
            return "\n".join(lines)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_get_journal_entry",
        annotations={
            "title": "Get Journal Entry",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_journal_entry(params: GetJournalEntryInput) -> str:
        """Retrieve a single journal entry with all its debit/credit lines.

        Args:
            params (GetJournalEntryInput): journal_entry_id, response_format.

        Returns:
            str: Full journal entry with lines.
        """
        try:
            je = await JournalEntryService.get(params.journal_entry_id)
            if not je:
                return "Error: Journal entry not found."
            if params.response_format.value == "json":
                return to_json(je)
            return JournalEntryService.format_md(je)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_post_journal_entry",
        annotations={
            "title": "Post Journal Entry",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_post_journal_entry(params: PostJournalEntryInput) -> str:
        """Post (finalize) a draft journal entry. This triggers the balance check.

        Args:
            params (PostJournalEntryInput): journal_entry_id.

        Returns:
            str: Posted entry or error message.
        """
        try:
            result = await JournalEntryService.post(params.journal_entry_id)
            if "error" in result:
                return f"Error: {result['error']}"
            return to_json(result)
        except Exception as e:
            return handle_tool_error(e)

    @mcp.tool(
        name="finance_void_journal_entry",
        annotations={
            "title": "Void Journal Entry",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
    async def finance_void_journal_entry(params: VoidJournalEntryInput) -> str:
        """Void a posted journal entry by creating a reversing entry.

        This does not delete the original — it creates a new entry with
        debits and credits swapped, preserving the audit trail.

        Args:
            params (VoidJournalEntryInput): journal_entry_id.

        Returns:
            str: Details of the voided and reversing entries.
        """
        try:
            result = await JournalEntryService.void(params.journal_entry_id)
            if "error" in result:
                return f"Error: {result['error']}"
            return to_json(result)
        except Exception as e:
            return handle_tool_error(e)
