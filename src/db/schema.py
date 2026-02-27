"""Database schema initialization for the double-entry bookkeeping system.

Core invariant: every journal entry must balance (total debits == total credits).

Tables
------
- accounts          : Chart of accounts (asset, liability, equity, income, expense).
- journal_entries   : Header for each balanced entry.
- journal_entry_lines : Individual debit / credit legs.
- transactions      : High-level user-facing records that reference journal entries.
- budgets           : Monthly budget targets per account.
"""

from __future__ import annotations

from .connection import get_pool

SCHEMA_SQL = """
-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Migration: Remove currency support (EGP-only, implicit) ───────
ALTER TABLE accounts DROP COLUMN IF EXISTS currency;
ALTER TABLE budgets DROP COLUMN IF EXISTS currency;

-- ─── Account Types ───────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE account_type AS ENUM (
        'asset', 'liability', 'equity', 'income', 'expense'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ─── Accounts (Chart of Accounts) ───────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT        NOT NULL UNIQUE,
    account_type  account_type NOT NULL,
    parent_id     UUID        REFERENCES accounts(id) ON DELETE SET NULL,
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_parent ON accounts(parent_id);

-- ─── Journal Entries (balanced double-entry header) ─────────────
CREATE TABLE IF NOT EXISTS journal_entries (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date          DATE        NOT NULL DEFAULT CURRENT_DATE,
    description   TEXT        NOT NULL DEFAULT '',
    is_posted     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_je_date ON journal_entries(date);

-- ─── Journal Entry Lines (debit / credit legs) ─────────────────
CREATE TABLE IF NOT EXISTS journal_entry_lines (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id    UUID        NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    debit         NUMERIC(15, 2) NOT NULL DEFAULT 0,
    credit        NUMERIC(15, 2) NOT NULL DEFAULT 0,
    memo          TEXT        NOT NULL DEFAULT '',
    CONSTRAINT positive_amounts CHECK (debit >= 0 AND credit >= 0),
    CONSTRAINT one_side_nonzero CHECK (debit > 0 OR credit > 0),
    CONSTRAINT one_side_only    CHECK (NOT (debit > 0 AND credit > 0))
);

CREATE INDEX IF NOT EXISTS idx_jel_entry ON journal_entry_lines(journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_jel_account ON journal_entry_lines(account_id);

-- ─── Transactions (user-facing layer) ───────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date            DATE        NOT NULL DEFAULT CURRENT_DATE,
    payee           TEXT        NOT NULL DEFAULT '',
    description     TEXT        NOT NULL DEFAULT '',
    category        TEXT        NOT NULL DEFAULT '',
    journal_entry_id UUID       REFERENCES journal_entries(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_txn_je ON transactions(journal_entry_id);

-- ─── Budgets ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS budgets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id    UUID        NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    year          INT         NOT NULL,
    month         INT         NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount        NUMERIC(15, 2) NOT NULL DEFAULT 0,
    notes         TEXT        NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, year, month)
);

CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(year, month);

-- ─── Helper: enforce balanced journal entries on post ────────────
CREATE OR REPLACE FUNCTION check_journal_balance()
RETURNS TRIGGER AS $$
DECLARE
    total_debit  NUMERIC;
    total_credit NUMERIC;
BEGIN
    IF NEW.is_posted = TRUE THEN
        SELECT COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
          INTO total_debit, total_credit
          FROM journal_entry_lines
         WHERE journal_entry_id = NEW.id;

        IF total_debit <> total_credit THEN
            RAISE EXCEPTION
                'Journal entry % is unbalanced: debits=% credits=%',
                NEW.id, total_debit, total_credit;
        END IF;

        IF total_debit = 0 THEN
            RAISE EXCEPTION
                'Journal entry % has no lines', NEW.id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_journal_balance ON journal_entries;
CREATE TRIGGER trg_check_journal_balance
    BEFORE UPDATE OF is_posted ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION check_journal_balance();
"""


async def initialize_schema() -> None:
    """Create all tables and indexes if they do not exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
