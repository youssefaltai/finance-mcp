"""Service layer for user-facing transactions.

A transaction is a friendly wrapper: it creates a balanced journal entry
(one debit line + one credit line) automatically.
"""

from __future__ import annotations

from typing import Any, Optional

from ..db import get_pool
from ..utils import parse_date, to_json
from .journal_entries import JournalEntryService


class TransactionService:
    """High-level transaction operations backed by double-entry journal entries."""

    # ── Record ────────────────────────────────────────────────────

    @staticmethod
    async def record(
        amount: float,
        debit_account_id: str,
        credit_account_id: str,
        date: Optional[str] = None,
        payee: str = "",
        description: str = "",
        category: str = "",
    ) -> dict[str, Any]:
        """Record a transaction, creating a balanced journal entry underneath."""
        je = await JournalEntryService.create(
            lines=[
                {"account_id": debit_account_id, "debit": amount, "credit": 0, "memo": description},
                {"account_id": credit_account_id, "debit": 0, "credit": amount, "memo": description},
            ],
            entry_date=date,
            description=description or f"Txn: {payee}",
            auto_post=True,
        )

        pool = await get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO transactions
                (date, payee, description, category, journal_entry_id)
            VALUES (COALESCE($1, CURRENT_DATE), $2, $3, $4, $5::uuid)
            RETURNING *
            """,
            parse_date(date), payee, description, category, str(je["id"]),
        )
        result = dict(row)
        result["journal_entry_id"] = str(je["id"])
        return result

    # ── Read ──────────────────────────────────────────────────────

    @staticmethod
    async def get(transaction_id: str) -> Optional[dict[str, Any]]:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM transactions WHERE id = $1::uuid",
            transaction_id,
        )
        return dict(row) if row else None

    @staticmethod
    async def list_all(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        account_id: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        pool = await get_pool()
        base_where = "WHERE TRUE"
        params: list[Any] = []
        idx = 0

        if start_date:
            idx += 1
            base_where += f" AND t.date >= ${idx}"
            params.append(parse_date(start_date))
        if end_date:
            idx += 1
            base_where += f" AND t.date <= ${idx}"
            params.append(parse_date(end_date))
        if category:
            idx += 1
            base_where += f" AND t.category ILIKE ${idx}"
            params.append(f"%{category}%")
        if payee:
            idx += 1
            base_where += f" AND t.payee ILIKE ${idx}"
            params.append(f"%{payee}%")

        join_clause = ""
        if account_id:
            join_clause = """
                JOIN journal_entry_lines jel
                    ON jel.journal_entry_id = t.journal_entry_id
            """
            idx += 1
            base_where += f" AND jel.account_id = ${idx}::uuid"
            params.append(account_id)

        count_q = f"SELECT COUNT(DISTINCT t.id) FROM transactions t {join_clause} {base_where}"
        total = await pool.fetchval(count_q, *params)

        data_q = f"""
            SELECT DISTINCT ON (t.date, t.created_at, t.id) t.*
            FROM transactions t {join_clause} {base_where}
            ORDER BY t.date DESC, t.created_at DESC, t.id
            LIMIT ${idx+1} OFFSET ${idx+2}
        """
        rows = await pool.fetch(data_q, *params, limit, offset)
        items = [dict(r) for r in rows]

        return {
            "total": total,
            "count": len(items),
            "offset": offset,
            "items": items,
            "has_more": total > offset + len(items),
        }

    # ── Delete ────────────────────────────────────────────────────

    @staticmethod
    async def delete(transaction_id: str) -> dict[str, Any]:
        """Delete a transaction and void its associated journal entry."""
        pool = await get_pool()
        txn = await TransactionService.get(transaction_id)
        if not txn:
            return {"error": "Transaction not found."}

        je_id = txn.get("journal_entry_id")
        void_result = {}
        if je_id:
            void_result = await JournalEntryService.void(str(je_id))

        await pool.execute("DELETE FROM transactions WHERE id = $1::uuid", transaction_id)

        return {
            "deleted_transaction_id": transaction_id,
            "void_result": void_result,
        }

    # ── Formatting ────────────────────────────────────────────────

    @staticmethod
    def format_md(txn: dict[str, Any]) -> str:
        return (
            f"**{txn.get('payee', '-')}** - {txn.get('description', '')}\n"
            f"  Date: {txn['date']} | Category: {txn.get('category', '-')} | "
            f"ID: `{txn['id']}`"
        )
