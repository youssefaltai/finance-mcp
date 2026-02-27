"""MCP guidance tool for onboarding and understanding the finance system."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register the guidance tool."""

    @mcp.tool(
        name="finance_get_guidance",
        annotations={
            "title": "Get Finance System Guidance",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def finance_get_guidance() -> str:
        """Learn how to use the finance system effectively.

        **CALL THIS FIRST** if you're unsure how to track finances.
        Returns the recommended workflow, account types, and best practices.
        """
        return """
╔════════════════════════════════════════════════════════════════════════╗
║           PERSONAL FINANCE TRACKING - GETTING STARTED GUIDE            ║
╚════════════════════════════════════════════════════════════════════════╝

## CORE CONCEPT: Double-Entry Bookkeeping

Every transaction affects TWO accounts:
- Money OUT (debit expense, credit asset)
- Money IN (debit asset, credit income)
- Money MOVES (debit destination, credit source)

The system ALWAYS BALANCES - debits always equal credits.

═══════════════════════════════════════════════════════════════════════════

## STEP 1: UNDERSTAND ACCOUNT TYPES

📦 ASSET (Money you own)
   - Checking, Savings, Cash, Credit Card
   - Higher balance = more money

💸 EXPENSE (Money you spend)
   - Groceries, Gas, Rent, Entertainment, Utilities
   - Higher balance = more spent

💰 INCOME (Money you earn)
   - Salary, Freelance, Bonus, Interest
   - Higher balance = more earned

💳 LIABILITY (Money you owe)
   - Credit Card Debt, Loan
   - Higher balance = more owed

📊 EQUITY (Net worth / starting balance)
   - Opening Balance
   - Starting positions in accounts

═══════════════════════════════════════════════════════════════════════════

## STEP 2: CREATE YOUR ACCOUNTS

Use finance_create_account to set up:

1. Asset accounts:
   ✓ Create account "Checking" (asset)
   ✓ Create account "Savings" (asset)

2. Expense accounts:
   ✓ Create account "Groceries" (expense)
   ✓ Create account "Gas" (expense)
   ✓ Create account "Utilities" (expense)

3. Income accounts:
   ✓ Create account "Salary" (income)

═══════════════════════════════════════════════════════════════════════════

## STEP 3: RECORD TRANSACTIONS

Use finance_record_transaction for everyday activity.

**SPENDING**: Debit expense, credit asset
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"I spent $50 on groceries from my Checking account"
→ Debit: Groceries (expense)
→ Credit: Checking (asset)
→ Amount: 50

Result: Checking balance ↓ 50, Groceries balance ↑ 50

**INCOME**: Debit asset, credit income
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"I received $2000 salary in my Checking account"
→ Debit: Checking (asset)
→ Credit: Salary (income)
→ Amount: 2000

Result: Checking balance ↑ 2000, Salary balance ↑ 2000

**TRANSFER**: Debit destination, credit source
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"I transferred $500 from Checking to Savings"
→ Debit: Savings (asset)
→ Credit: Checking (asset)
→ Amount: 500

Result: Checking ↓ 500, Savings ↑ 500

═══════════════════════════════════════════════════════════════════════════

## STEP 4: CHECK YOUR BALANCES

Use finance_get_account_balance to verify:

"What's my Checking balance?"
→ Shows current balance, total debits, total credits

"How much have I spent on groceries?"
→ Shows Groceries expense account balance

═══════════════════════════════════════════════════════════════════════════

## STEP 5: SET BUDGETS & COMPARE

Use finance_set_budget to set monthly limits:
"Set a budget of 500 for Groceries in Feb 2026"

Use finance_budget_vs_actual to compare:
"Show budget vs actual for Feb 2026"

═══════════════════════════════════════════════════════════════════════════

## QUICK REFERENCE: WHICH TOOL TO USE?

┌─────────────────────────────────────────────────────────────────┐
│ I want to...                      │ Use this tool                 │
├─────────────────────────────────────────────────────────────────┤
│ Create an account                 │ finance_create_account        │
│ List all my accounts              │ finance_list_accounts         │
│ Record an expense/income/transfer  │ finance_record_transaction    │
│ Check an account balance          │ finance_get_account_balance   │
│ Set a monthly budget              │ finance_set_budget            │
│ Compare budget vs actual spending │ finance_budget_vs_actual      │
│ Get list of transactions          │ finance_list_transactions     │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════

## IMPORTANT RULES

✓ ALWAYS create accounts before recording transactions
✓ ALWAYS think: "Where is money going?" when recording
✓ ALWAYS use finance_record_transaction for daily activity
✓ NEVER use finance_create_journal_entry unless you have 3+ accounts in one transaction
✓ System ALWAYS balances (debits == credits)
✓ All amounts are in EGP (Egyptian Pound)

═══════════════════════════════════════════════════════════════════════════

## YOUR WORKFLOW

1. Create accounts (Checking, Salary, Groceries, etc.)
2. Record transactions as they happen
3. Check balances to verify
4. Review with budget vs actual to analyze spending

That's it! Start simple, then add complexity as needed.
"""
