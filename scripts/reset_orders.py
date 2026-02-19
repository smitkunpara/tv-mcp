#!/usr/bin/env python3
"""
Reset closed trade history only.

This script deletes all rows from the closed_trades table and resets the
next_order_id counter to 1. It does NOT touch:

    • current_capital   – your balance is preserved
    • total_pnl         – your accumulated PnL is preserved
    • trading_config    – all configuration is preserved

Use this when you want to start a fresh batch of trades without losing
your existing capital balance.

Usage:
    python scripts/reset_orders.py
"""

import os
import sqlite3
import sys


def get_db_path() -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "paper_trades.db")


def main() -> None:
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("   Nothing to reset.")
        return

    conn = sqlite3.connect(db_path)
    try:
        count_row = conn.execute("SELECT COUNT(*) FROM closed_trades").fetchone()
        trade_count = count_row[0] if count_row else 0
    finally:
        conn.close()

    if trade_count == 0:
        print("ℹ️  closed_trades table is already empty. Nothing to reset.")
        return

    # ── Warning prompt ────────────────────────────────────────────────────────
    print("=" * 60)
    print("⚠️   WARNING: This will permanently delete trade history!")
    print("=" * 60)
    print()
    print(f"   Trades to be deleted  : {trade_count}")
    print()
    print("   The following will NOT be deleted:")
    print("     • current_capital  (your balance is safe)")
    print("     • total_pnl        (accumulated PnL is safe)")
    print("     • trading_config   (all settings are safe)")
    print()

    answer = input("Type 'yes' to confirm deletion, or anything else to cancel: ").strip().lower()
    if answer != "yes":
        print("❌ Reset cancelled. No data was changed.")
        return

    # ── Perform reset ─────────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM closed_trades")
        # Reset order counter so new orders start from 1
        conn.execute(
            "INSERT OR REPLACE INTO trading_config (key, value) VALUES ('next_order_id', '1')"
        )
        conn.commit()
    finally:
        conn.close()

    print()
    print(f"✅ Deleted {trade_count} closed trade(s) and reset order ID counter to 1.")
    print("   Capital and configuration remain unchanged.")


if __name__ == "__main__":
    main()
