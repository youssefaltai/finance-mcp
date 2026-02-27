"""Service layer for journal entry operations — the heart of double-entry bookkeeping."""

from __future__ import annotations

from typing import Any, Optional

from ..db import get_pool
from ..utils import parse_date, to_json


class JournalEntryService:
    """Create, list, post, and void journal entries with their debit/credit lines."""

    # ── Create ────────────────────────────────────────────────────

    @staticmethod
    async def create(
        lines: list[dict[str, Any]],
        entry_date: Optional[str] = None,
        description: str = "",
        auto_post: bool = True,
    ) -> dict[str, Any]:
        """Create a journal entry with its lines inside a single transaction.

        If *auto_post* is True, the entry is immediately posted (triggers the
        database-level balance check). If balance check fails, returns detailed
        error with actual totals.
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # 1) Insert header
                je_row = await conn.fetchrow(
                    """
                    INSERT INTO journal_entries (date, description)
                    VALUES (COALESCE($1, CURRENT_DATE), $2)
                    RETURNING *
                    """,
                    parse_date(entry_date), description,
                )
                je_id = str(je_row["id"])

                # 2) Insert lines
                inserted_lines: list[dict[str, Any]] = []
                for line in lines:
                    lr = await conn.fetchrow(
                        """
                        INSERT INTO journal_entry_lines
                            (journal_entry_id, account_id, debit, credit, memo)
                        VALUES ($1::uuid, $2::uuid, $3, $4, $5)
                        RETURNING *
                        """,
                        je_id, line["account_id"],
                        line.get("debit", 0), line.get("credit", 0),
                        line.get("memo", ""),
                    )
                    inserted_lines.append(dict(lr))

                # 3) Optionally post (triggers balance check via DB trigger)
                if auto_post:
                    try:
                        await conn.execute(
                            "UPDATE journal_entries SET is_posted = TRUE WHERE id = $1::uuid",
                            je_id,
                        )
                    except Exception as e:
                        # If balance check failed, provide context
                        if "unbalanced" in str(e).lower():
                            total_debit = sum(float(line.get("debit", 0)) for line in inserted_lines)
                            total_credit = sum(float(line.get("credit", 0)) for line in inserted_lines)
                            difference = abs(total_debit - total_credit)
                            return {
                                "error": (
                                    f"Journal entry is unbalanced:\n"
                                    f"  Total debits:  {total_debit:,.2f}\n"
                                    f"  Total credits: {total_credit:,.2f}\n"
                                    f"  Difference:    {difference:,.2f}\n"
                                    f"\nAdjust the amounts so debits equal credits, then post again."
                                ),
                                "entry_id": je_id,
                                "created_as_draft": True,
                            }
                        raise

                je = dict(je_row)
                je["is_posted"] = auto_post
                je["lines"] = inserted_lines
                return je

    # ── Read ──────────────────────────────────────────────────────

    @staticmethod
    async def get(journal_entry_id: str) -> Optional[dict[str, Any]]:
        pool = await get_pool()
        je = await pool.fetchrow(
            "SELECT * FROM journal_entries WHERE id = $1::uuid",
            journal_entry_id,
        )
        if not je:
            return None

        lines = await pool.fetch(
            """
            SELECT jel.*, a.name AS account_name
            FROM journal_entry_lines jel
            JOIN accounts a ON a.id = jel.account_id
            WHERE jel.journal_entry_id = $1::uuid
            ORDER BY jel.debit DESC, jel.credit DESC
            """,
            journal_entry_id,
        )
        result = dict(je)
        result["lines"] = [dict(line) for line in lines]
        return result

    @staticmethod
    async def list_all(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_posted: Optional[bool] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        pool = await get_pool()
        query = "SELECT * FROM journal_entries WHERE TRUE"
        count_query = "SELECT COUNT(*) FROM journal_entries WHERE TRUE"
        params: list[Any] = []
        idx = 0

        if start_date:
            idx += 1
            query += f" AND date >= ${idx}"
            count_query += f" AND date >= ${idx}"
            params.append(parse_date(start_date))
        if end_date:
            idx += 1
            query += f" AND date <= ${idx}"
            count_query += f" AND date <= ${idx}"
            params.append(parse_date(end_date))
        if is_posted is not None:
            idx += 1
            query += f" AND is_posted = ${idx}"
            count_query += f" AND is_posted = ${idx}"
            params.append(is_posted)

        total = await pool.fetchval(count_query, *params)

        query += f" ORDER BY date DESC, created_at DESC LIMIT ${idx+1} OFFSET ${idx+2}"
        rows = await pool.fetch(query, *params, limit, offset)
        items = [dict(r) for r in rows]

        return {
            "total": total,
            "count": len(items),
            "offset": offset,
            "items": items,
            "has_more": total > offset + len(items),
        }

    # ── Post / Void ───────────────────────────────────────────────

    @staticmethod
    async def post(journal_entry_id: str) -> dict[str, Any]:
        """Post a draft journal entry (triggers balance check).

        If the entry is unbalanced, returns detailed error with totals.
        """
        pool = await get_pool()
        try:
            row = await pool.fetchrow(
                """
                UPDATE journal_entries SET is_posted = TRUE
                WHERE id = $1::uuid AND is_posted = FALSE
                RETURNING *
                """,
                journal_entry_id,
            )
            if not row:
                return {"error": "Entry not found or already posted."}
            return dict(row)
        except Exception as e:
            error_msg = str(e)
            # If it's a balance error, provide detailed context
            if "unbalanced" in error_msg.lower():
                # Fetch the lines to calculate actual totals
                lines = await pool.fetch(
                    """
                    SELECT debit, credit FROM journal_entry_lines
                    WHERE journal_entry_id = $1::uuid
                    """,
                    journal_entry_id,
                )
                total_debit = sum(float(line["debit"]) for line in lines)
                total_credit = sum(float(line["credit"]) for line in lines)
                difference = abs(total_debit - total_credit)
                return {
                    "error": (
                        f"Journal entry is unbalanced:\n"
                        f"  Total debits:  {total_debit:,.2f}\n"
                        f"  Total credits: {total_credit:,.2f}\n"
                        f"  Difference:    {difference:,.2f}\n"
                        f"\nReview the lines and adjust amounts so debits equal credits."
                    )
                }
            return {"error": error_msg}

    @staticmethod
    async def void(journal_entry_id: str) -> dict[str, Any]:
        """Void a posted entry by creating a reversing journal entry."""
        original = await JournalEntryService.get(journal_entry_id)
        if not original:
            return {"error": "Journal entry not found."}
        if not original["is_posted"]:
            return {"error": "Cannot void an unposted entry."}

        reversed_lines = [
            {
                "account_id": str(line["account_id"]),
                "debit": float(line["credit"]),
                "credit": float(line["debit"]),
                "memo": f"Reversal of {journal_entry_id}",
            }
            for line in original["lines"]
        ]

        reversing = await JournalEntryService.create(
            lines=reversed_lines,
            entry_date=str(original["date"]),
            description=f"VOID: {original['description']}",
            auto_post=True,
        )
        return {"voided_entry_id": journal_entry_id, "reversing_entry": reversing}

    # ── Formatting ────────────────────────────────────────────────

    @staticmethod
    def format_md(je: dict[str, Any]) -> str:
        status = "Posted" if je.get("is_posted") else "Draft"
        header = (
            f"### Journal Entry `{je['id']}`\n"
            f"Date: {je['date']} | {status}\n"
            f"Description: {je.get('description', '-')}\n"
        )
        if "lines" in je:
            header += "\n| Account | Debit | Credit | Memo |\n|---|---|---|---|\n"
            for line in je["lines"]:
                acct = line.get("account_name", str(line["account_id"]))
                header += f"| {acct} | {float(line['debit']):,.2f} | {float(line['credit']):,.2f} | {line.get('memo', '')} |\n"
        return header
