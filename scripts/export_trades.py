#!/usr/bin/env python3
"""
Export all closed paper trades to a CSV file.

The CSV is written to the export/ directory at the project root.
The directory is created automatically if it does not exist.

Usage:
    python scripts/export_trades.py

Options (edit constants below):
    OUTPUT_FILENAME  – name of the CSV file  (default: auto-timestamped)
"""

import csv
import os
import sqlite3
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
#  Optional: set a fixed filename, or leave empty for auto-naming
OUTPUT_FILENAME: str = ""   # e.g. "trades.csv"  |  "" = auto-timestamp
# ─────────────────────────────────────────────────────────────────


def get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path() -> str:
    return os.path.join(get_project_root(), "paper_trades.db")


def get_export_path() -> str:
    export_dir = os.path.join(get_project_root(), "export")
    os.makedirs(export_dir, exist_ok=True)

    if OUTPUT_FILENAME:
        filename = OUTPUT_FILENAME if OUTPUT_FILENAME.endswith(".csv") else OUTPUT_FILENAME + ".csv"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trades_{timestamp}.csv"

    return os.path.join(export_dir, filename)


COLUMNS = [
    "order_id",
    "symbol",
    "exchange",
    "side",
    "entry_price",
    "exit_price",
    "stop_loss",
    "target",
    "lot_size",
    "opened_at",
    "closed_at",
    "close_reason",
    "pnl",
    "pnl_percentage",
]


def main() -> None:
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("   Run the server at least once to create it, then try again.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM closed_trades ORDER BY order_id ASC"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("ℹ️  No closed trades found in the database. Nothing to export.")
        return

    export_path = get_export_path()

    with open(export_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row[col] for col in COLUMNS})

    print(f"✅ Exported {len(rows)} trade(s) to:")
    print(f"   {export_path}")

    # Print a quick summary
    total_pnl = sum(row["pnl"] for row in rows)
    winners = sum(1 for row in rows if row["pnl"] > 0)
    losers = sum(1 for row in rows if row["pnl"] < 0)
    print()
    print(f"   Total trades : {len(rows)}")
    print(f"   Winners      : {winners}")
    print(f"   Losers       : {losers}")
    print(f"   Total PnL    : {total_pnl:+,.2f}")


if __name__ == "__main__":
    main()
