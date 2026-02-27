# 💰 Personal Finance MCP Server

A **Model Context Protocol (MCP)** server that gives Claude (or any MCP-compatible LLM) the ability to manage your personal finances through a proper **double-entry bookkeeping** system backed by **PostgreSQL**.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  MCP Client (Claude, Claude Code, etc.)                  │
└────────────────────────┬─────────────────────────────────┘
                         │  MCP Protocol (streamable HTTP / stdio)
┌────────────────────────▼─────────────────────────────────┐
│  FastMCP Server  (src/server.py)                         │
│                                                          │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────┐  │
│  │ tools/      │ │ tools/       │ │ tools/            │  │
│  │  accounts   │ │  journal_    │ │  transactions     │  │
│  │  budgets    │ │  entries     │ │                   │  │
│  └──────┬──────┘ └──────┬───────┘ └────────┬──────────┘  │
│         │               │                  │             │
│  ┌──────▼──────┐ ┌──────▼───────┐ ┌────────▼──────────┐  │
│  │ services/   │ │ services/    │ │ services/         │  │
│  │  accounts   │ │  journal_    │ │  transactions     │  │
│  │  budgets    │ │  entries     │ │                   │  │
│  └──────┬──────┘ └──────┬───────┘ └────────┬──────────┘  │
│         │               │                  │             │
│  ┌──────▼───────────────▼──────────────────▼──────────┐  │
│  │ db/  (asyncpg connection pool + schema)            │  │
│  └────────────────────────┬───────────────────────────┘  │
└───────────────────────────┼──────────────────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │   PostgreSQL 16     │
                 │   (Docker)          │
                 └─────────────────────┘
```

### Layer Responsibilities

| Layer | Path | Role |
|-------|------|------|
| **Models** | `src/models/` | Pydantic input validation schemas for each tool |
| **Services** | `src/services/` | Business logic, SQL queries, formatting helpers |
| **Tools** | `src/tools/` | MCP tool definitions with annotations and docstrings |
| **DB** | `src/db/` | Connection pool management and schema migrations |

## Double-Entry Bookkeeping

Every financial event is recorded as a **journal entry** with balanced debit and credit lines:

- **Assets & Expenses**: Normal debit balance (↑ debit, ↓ credit)
- **Liabilities, Equity & Income**: Normal credit balance (↑ credit, ↓ debit)
- **Invariant**: Every posted journal entry must satisfy `Σ debits = Σ credits`
- **Audit trail**: Voiding creates a reversing entry rather than deleting

## Available Tools (18 total)

### Accounts (5)
| Tool | Description |
|------|-------------|
| `finance_create_account` | Create asset, liability, equity, income, or expense accounts |
| `finance_list_accounts` | List/filter accounts by type and status |
| `finance_get_account` | Get details for a single account |
| `finance_update_account` | Rename or deactivate an account |
| `finance_get_account_balance` | Compute running balance from posted entries |

### Journal Entries (5)
| Tool | Description |
|------|-------------|
| `finance_create_journal_entry` | Create multi-line debit/credit entries |
| `finance_list_journal_entries` | List entries with date/status filters |
| `finance_get_journal_entry` | Get full entry with all lines |
| `finance_post_journal_entry` | Post a draft entry (triggers balance check) |
| `finance_void_journal_entry` | Void via reversing entry (preserves audit trail) |

### Transactions (4)
| Tool | Description |
|------|-------------|
| `finance_record_transaction` | Quick-record a payment/transfer (auto-creates journal entry) |
| `finance_list_transactions` | Browse by date, category, payee, or account |
| `finance_get_transaction` | Get details for a single transaction |
| `finance_delete_transaction` | Delete transaction + void underlying journal entry |

### Budgets (4)
| Tool | Description |
|------|-------------|
| `finance_set_budget` | Set/update monthly budget for an account |
| `finance_get_budget` | Get budget for a specific account/month |
| `finance_list_budgets` | List all budgets for a year or month |
| `finance_budget_vs_actual` | Compare budgeted vs actual spending |

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env to set your Postgres credentials
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

This starts Postgres and the MCP server on port `8000`.

### 3. Connect from Claude

Add to your MCP client config:

```json
{
  "mcpServers": {
    "finance": {
      "type": "url",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### 4. Local development (without Docker)

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://finance:finance_secret@localhost:5432/finance_db
python -m src.server
```

## Example Conversation

> **You:** Set up my accounts — I have a checking account, a credit card, and I want to track rent, groceries, and salary.

Claude will call `finance_create_account` five times:
- Checking (asset), Credit Card (liability), Rent (expense), Groceries (expense), Salary (income)

> **You:** I got paid $5,000 on Feb 1st.

Claude calls `finance_record_transaction`:
- Debit: Checking, Credit: Salary, Amount: 5000, Payee: "Employer"

> **You:** I paid $1,200 rent on Feb 3rd from checking.

Claude calls `finance_record_transaction`:
- Debit: Rent, Credit: Checking, Amount: 1200

> **You:** Set a $1,500 budget for rent and $600 for groceries this month.

Claude calls `finance_set_budget` twice.

> **You:** How am I doing against my budget this month?

Claude calls `finance_budget_vs_actual` → gets a table showing budgeted vs actual with variance and % used.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://finance:finance_secret@localhost:5432/finance_db` | Postgres connection string (auto-set in Docker) |
| `MCP_TRANSPORT` | `streamable_http` | Transport: `streamable_http` or `stdio` |
| `MCP_PORT` | `8000` | HTTP port (streamable_http mode) |
| `POSTGRES_USER` | `finance` | Postgres username (Docker) |
| `POSTGRES_PASSWORD` | `finance_secret` | Postgres password (Docker) |
| `POSTGRES_DB` | `finance_db` | Postgres database name (Docker) |
| `DB_PORT` | `5432` | Host port for Postgres (Docker) |
