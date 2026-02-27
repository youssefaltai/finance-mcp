"""Service layer for budget operations and budget-vs-actual reporting."""

from __future__ import annotations

from typing import Any, Optional

from ..db import get_pool


class BudgetService:
    """Set monthly budgets and compare them against actual spending."""

    # ── Set (upsert) ──────────────────────────────────────────────

    @staticmethod
    async def set_budget(
        account_id: str,
        year: int,
        month: int,
        amount: float,
        notes: str = "",
    ) -> dict[str, Any]:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            INSERT INTO budgets (account_id, year, month, amount, notes)
            VALUES ($1::uuid, $2, $3, $4, $5)
            ON CONFLICT (account_id, year, month)
            DO UPDATE SET amount = EXCLUDED.amount,
                         notes = EXCLUDED.notes,
                         updated_at = now()
            RETURNING *
            """,
            account_id, year, month, amount, notes,
        )
        return dict(row)

    # ── Read ──────────────────────────────────────────────────────

    @staticmethod
    async def get(account_id: str, year: int, month: int) -> Optional[dict[str, Any]]:
        pool = await get_pool()
        row = await pool.fetchrow(
            """
            SELECT b.*, a.name AS account_name
            FROM budgets b
            JOIN accounts a ON a.id = b.account_id
            WHERE b.account_id = $1::uuid AND b.year = $2 AND b.month = $3
            """,
            account_id, year, month,
        )
        return dict(row) if row else None

    @staticmethod
    async def list_all(year: int, month: Optional[int] = None) -> list[dict[str, Any]]:
        pool = await get_pool()
        query = """
            SELECT b.*, a.name AS account_name, a.account_type
            FROM budgets b
            JOIN accounts a ON a.id = b.account_id
            WHERE b.year = $1
        """
        params: list[Any] = [year]
        if month is not None:
            query += " AND b.month = $2"
            params.append(month)
        query += " ORDER BY b.month, a.name"
        rows = await pool.fetch(query, *params)
        return [dict(r) for r in rows]

    # ── Budget vs Actual ──────────────────────────────────────────

    @staticmethod
    async def budget_vs_actual(year: int, month: int) -> list[dict[str, Any]]:
        """Compare budgeted amounts with actual spending for a given month.

        Actual spending is computed from posted journal entry lines where
        the entry date falls within the specified month.
        """
        pool = await get_pool()
        rows = await pool.fetch(
            """
            WITH actual AS (
                SELECT
                    jel.account_id,
                    SUM(jel.debit)  AS actual_debit,
                    SUM(jel.credit) AS actual_credit
                FROM journal_entry_lines jel
                JOIN journal_entries je ON je.id = jel.journal_entry_id
                WHERE je.is_posted = TRUE
                  AND EXTRACT(YEAR FROM je.date)  = $1
                  AND EXTRACT(MONTH FROM je.date) = $2
                GROUP BY jel.account_id
            )
            SELECT
                a.id   AS account_id,
                a.name AS account_name,
                a.account_type,
                b.amount   AS budgeted,
                COALESCE(act.actual_debit, 0)  AS actual_debit,
                COALESCE(act.actual_credit, 0) AS actual_credit
            FROM budgets b
            JOIN accounts a ON a.id = b.account_id
            LEFT JOIN actual act ON act.account_id = a.id
            WHERE b.year = $1 AND b.month = $2
            ORDER BY a.account_type, a.name
            """,
            year, month,
        )

        results: list[dict[str, Any]] = []
        for r in rows:
            budgeted = float(r["budgeted"])
            if r["account_type"] in ("expense", "asset"):
                actual = float(r["actual_debit"]) - float(r["actual_credit"])
            else:
                actual = float(r["actual_credit"]) - float(r["actual_debit"])

            variance = budgeted - actual
            results.append({
                "account_id": str(r["account_id"]),
                "account_name": r["account_name"],
                "account_type": r["account_type"],
                "budgeted": budgeted,
                "actual": actual,
                "variance": variance,
                "pct_used": round((actual / budgeted * 100), 1) if budgeted else 0.0,
            })
        return results

    # ── Formatting ────────────────────────────────────────────────

    @staticmethod
    def format_budget_md(b: dict[str, Any]) -> str:
        return (
            f"**{b.get('account_name', b['account_id'])}** - "
            f"{b['year']}/{b['month']:02d}: "
            f"{float(b['amount']):,.2f}"
        )

    @staticmethod
    def format_bva_md(rows: list[dict[str, Any]], year: int, month: int) -> str:
        header = f"## Budget vs Actual - {year}/{month:02d}\n\n"
        header += "| Account | Type | Budgeted | Actual | Variance | % Used |\n"
        header += "|---|---|---:|---:|---:|---:|\n"
        for r in rows:
            header += (
                f"| {r['account_name']} | {r['account_type']} "
                f"| {r['budgeted']:,.2f} | {r['actual']:,.2f} "
                f"| {r['variance']:,.2f} | {r['pct_used']}% |\n"
            )
        return header
