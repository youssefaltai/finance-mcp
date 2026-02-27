"""End-to-end test for the finance MCP server.

Uses a separate test database — never touches production data.

Run:
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit test-runner
"""

import asyncio
import json
import os
import sys

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

MCP_URL = os.getenv("MCP_TEST_URL", "http://test-mcp:8000/mcp")
MAX_RETRIES = 10
RETRY_DELAY = 2


async def connect_with_retry():
    """Keep trying to connect until the MCP server is ready."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ctx = streamablehttp_client(MCP_URL)
            read, write, _ = await ctx.__aenter__()
            return ctx, read, write
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            print(f"  Waiting for MCP server (attempt {attempt}/{MAX_RETRIES})...")
            await asyncio.sleep(RETRY_DELAY)


async def main():
    print(f"Connecting to {MCP_URL}...")
    ctx, read, write = await connect_with_retry()

    try:
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Session initialized.\n")

            # 1. List tools
            tools = await session.list_tools()
            print(f"Tools registered: {len(tools.tools)}")
            for t in tools.tools:
                print(f"  - {t.name}")
            print()
            assert len(tools.tools) == 18, f"Expected 18 tools, got {len(tools.tools)}"

            # 2. Create accounts
            print("--- Creating accounts ---")
            checking = await session.call_tool("finance_create_account", {
                "params": {"name": "Checking", "account_type": "asset"}
            })
            checking_data = json.loads(checking.content[0].text)
            checking_id = checking_data["id"]
            print(f"  Created Checking: {checking_id}")

            groceries = await session.call_tool("finance_create_account", {
                "params": {"name": "Groceries", "account_type": "expense"}
            })
            groceries_data = json.loads(groceries.content[0].text)
            groceries_id = groceries_data["id"]
            print(f"  Created Groceries: {groceries_id}")

            salary = await session.call_tool("finance_create_account", {
                "params": {"name": "Salary", "account_type": "income"}
            })
            salary_data = json.loads(salary.content[0].text)
            salary_id = salary_data["id"]
            print(f"  Created Salary: {salary_id}")

            # 3. List accounts
            print("\n--- Listing accounts ---")
            accs = await session.call_tool("finance_list_accounts", {
                "params": {"response_format": "json"}
            })
            accs_data = json.loads(accs.content[0].text)
            print(f"  Total accounts: {len(accs_data)}")
            assert len(accs_data) == 3, f"Expected 3 accounts, got {len(accs_data)}"

            # 4. Record transactions
            print("\n--- Recording transactions ---")
            txn1 = await session.call_tool("finance_record_transaction", {
                "params": {
                    "amount": 5000.00,
                    "debit_account_id": checking_id,
                    "credit_account_id": salary_id,
                    "payee": "Employer",
                    "description": "February salary",
                    "category": "salary",
                    "date": "2026-02-01",
                }
            })
            txn1_data = json.loads(txn1.content[0].text)
            print(f"  Salary received: ${5000:.2f} (txn {txn1_data['id']})")

            txn2 = await session.call_tool("finance_record_transaction", {
                "params": {
                    "amount": 150.00,
                    "debit_account_id": groceries_id,
                    "credit_account_id": checking_id,
                    "payee": "Whole Foods",
                    "description": "Weekly groceries",
                    "category": "groceries",
                    "date": "2026-02-05",
                }
            })
            txn2_data = json.loads(txn2.content[0].text)
            print(f"  Groceries: ${150:.2f} (txn {txn2_data['id']})")

            # 5. Check balances
            print("\n--- Checking balances ---")
            bal = await session.call_tool("finance_get_account_balance", {
                "params": {"account_id": checking_id, "response_format": "json"}
            })
            bal_data = json.loads(bal.content[0].text)
            print(f"  Checking balance: ${bal_data['balance']:,.2f}")
            assert bal_data["balance"] == 4850.0, f"Expected 4850, got {bal_data['balance']}"

            bal2 = await session.call_tool("finance_get_account_balance", {
                "params": {"account_id": groceries_id, "response_format": "json"}
            })
            bal2_data = json.loads(bal2.content[0].text)
            print(f"  Groceries balance: ${bal2_data['balance']:,.2f}")
            assert bal2_data["balance"] == 150.0, f"Expected 150, got {bal2_data['balance']}"

            # 6. Set budget and check
            print("\n--- Budget operations ---")
            await session.call_tool("finance_set_budget", {
                "params": {
                    "account_id": groceries_id,
                    "year": 2026,
                    "month": 2,
                    "amount": 600.00,
                    "notes": "Monthly grocery budget",
                }
            })
            print("  Budget set: Groceries $600/month")

            bva = await session.call_tool("finance_budget_vs_actual", {
                "params": {"year": 2026, "month": 2, "response_format": "json"}
            })
            bva_data = json.loads(bva.content[0].text)
            print(f"  Budget vs Actual:")
            for row in bva_data:
                print(f"    {row['account_name']}: budgeted={row['budgeted']}, actual={row['actual']}, "
                      f"variance={row['variance']}, used={row['pct_used']}%")

            # 7. List journal entries
            print("\n--- Journal entries ---")
            jes = await session.call_tool("finance_list_journal_entries", {
                "params": {"response_format": "json"}
            })
            jes_data = json.loads(jes.content[0].text)
            print(f"  Total journal entries: {jes_data['total']}")
            assert jes_data["total"] == 2, f"Expected 2 journal entries, got {jes_data['total']}"

            # 8. Void a journal entry (from the groceries transaction)
            print("\n--- Void test ---")
            je_id = str(txn2_data["journal_entry_id"])
            void_result = await session.call_tool("finance_void_journal_entry", {
                "params": {"journal_entry_id": je_id}
            })
            void_data = json.loads(void_result.content[0].text)
            print(f"  Voided entry {je_id}")
            print(f"  Reversing entry: {void_data['reversing_entry']['id']}")

            # Check balance after void
            bal3 = await session.call_tool("finance_get_account_balance", {
                "params": {"account_id": checking_id, "response_format": "json"}
            })
            bal3_data = json.loads(bal3.content[0].text)
            print(f"  Checking balance after void: ${bal3_data['balance']:,.2f}")
            assert bal3_data["balance"] == 5000.0, f"Expected 5000, got {bal3_data['balance']}"

            # 9. Delete transaction
            print("\n--- Delete transaction test ---")
            txn1_id = txn1_data["id"]
            del_result = await session.call_tool("finance_delete_transaction", {
                "params": {"transaction_id": txn1_id}
            })
            del_data = json.loads(del_result.content[0].text)
            print(f"  Deleted transaction {txn1_id}")

            bal4 = await session.call_tool("finance_get_account_balance", {
                "params": {"account_id": checking_id, "response_format": "json"}
            })
            bal4_data = json.loads(bal4.content[0].text)
            print(f"  Checking balance after delete: ${bal4_data['balance']:,.2f}")
            assert bal4_data["balance"] == 0.0, f"Expected 0, got {bal4_data['balance']}"

            print("\n" + "=" * 50)
            print("ALL TESTS PASSED")
            print("=" * 50)
    finally:
        await ctx.__aexit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
