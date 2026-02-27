"""Service layer for account operations."""

from __future__ import annotations

from typing import Any, Optional

from ..db import get_pool
from ..utils import parse_date, to_json


class AccountService:
    """CRUD and balance operations for the chart of accounts."""

    # ── Create ────────────────────────────────────────────────────

    @staticmethod
    async def create(
        name: str,
        account_type: str,
        currency: str = "USD",
        parent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO accounts (name, account_type, currency, parent_id)
            VALUES ($1, $2::account_type, $3, $4::uuid)
            RETURNING id, name, account_type, currency, parent_id, is_active,
                      created_at, updated_at
            """,
            name, account_type, currency, parent_id,
        )
        return dict(row)

    # ── Read ──────────────────────────────────────────────────────

    @staticmethod
    async def get(account_id: str) -> Optional[dict[str, Any]]:
        pool = await get_pool()
        row = await pool.fetchrow(
            "SELECT * FROM accounts WHERE id = $1::uuid", account_id,
        )
        return dict(row) if row else None

    @staticmethod
    async def list_all(
        account_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        pool = await get_pool()
        query = "SELECT * FROM accounts WHERE TRUE"
        params: list[Any] = []
        idx = 0

        if account_type is not None:
            idx += 1
            query += f" AND account_type = ${idx}::account_type"
            params.append(account_type)
        if is_active is not None:
            idx += 1
            query += f" AND is_active = ${idx}"
            params.append(is_active)

        query += " ORDER BY account_type, name"
        rows = await pool.fetch(query, *params)
        return [dict(r) for r in rows]

    # ── Update ────────────────────────────────────────────────────

    @staticmethod
    async def update(
        account_id: str,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[dict[str, Any]]:
        pool = await get_pool()
        sets: list[str] = ["updated_at = now()"]
        params: list[Any] = []
        idx = 0

        if name is not None:
            idx += 1
            sets.append(f"name = ${idx}")
            params.append(name)
        if is_active is not None:
            idx += 1
            sets.append(f"is_active = ${idx}")
            params.append(is_active)

        idx += 1
        params.append(account_id)
        query = f"UPDATE accounts SET {', '.join(sets)} WHERE id = ${idx}::uuid RETURNING *"
        row = await pool.fetchrow(query, *params)
        return dict(row) if row else None

    # ── Balance ───────────────────────────────────────────────────

    @staticmethod
    async def balance(account_id: str, as_of_date: Optional[str] = None) -> dict[str, Any]:
        """Compute account balance from posted journal entry lines.

        For asset/expense accounts: balance = debits - credits
        For liability/income/equity accounts: balance = credits - debits
        """
        pool = await get_pool()
        date_clause = ""
        params: list[Any] = [account_id]
        if as_of_date:
            date_clause = "AND je.date <= $2"
            params.append(parse_date(as_of_date))

        row = await pool.fetchrow(
            f"""
            SELECT
                a.name,
                a.account_type,
                a.currency,
                COALESCE(SUM(jel.debit), 0)  AS total_debit,
                COALESCE(SUM(jel.credit), 0) AS total_credit
            FROM accounts a
            LEFT JOIN journal_entry_lines jel ON jel.account_id = a.id
            LEFT JOIN journal_entries je ON je.id = jel.journal_entry_id
                AND je.is_posted = TRUE {date_clause}
            WHERE a.id = $1::uuid
            GROUP BY a.id
            """,
            *params,
        )
        if not row:
            return {"error": "Account not found"}

        total_debit = float(row["total_debit"])
        total_credit = float(row["total_credit"])
        atype = row["account_type"]

        if atype in ("asset", "expense"):
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        return {
            "account_id": account_id,
            "name": row["name"],
            "account_type": atype,
            "currency": row["currency"],
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance": balance,
            "as_of_date": as_of_date or "today",
        }

    # ── Formatting helpers ────────────────────────────────────────

    @staticmethod
    def format_md(acc: dict[str, Any]) -> str:
        return (
            f"**{acc['name']}** (`{acc['id']}`)\n"
            f"  Type: {acc['account_type']} | Currency: {acc['currency']} | "
            f"Active: {'yes' if acc['is_active'] else 'no'}"
        )
