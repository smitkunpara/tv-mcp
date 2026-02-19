#!/usr/bin/env python3
"""
Setup script for paper trading configuration.

Edit the values in the CONFIGURATION section below and run this script once
to persist them into the database. Changes take effect the next time the
server starts (or re-initialises the engine).

Usage:
    python scripts/setup_paper_trading.py

WARNING: Setting RESET_CAPITAL_TO_INITIAL=True will reset your current capital
         back to INITIAL_CAPITAL and wipe accumulated PnL. Trade history in the
         closed_trades table is NOT affected by this script.
"""

import os
import sqlite3
import sys

# ═══════════════════════════════════════════════════════════════════
#  ↓↓↓  EDIT THESE VALUES BEFORE RUNNING  ↓↓↓
# ═══════════════════════════════════════════════════════════════════

INITIAL_CAPITAL: float = 100_000.0      # Starting / reference capital
MIN_RISK_REWARD_RATIO: float = 1.5      # Minimum acceptable risk:reward ratio
MAX_OPEN_POSITIONS: int = 10            # Maximum simultaneous open positions
TRAILING_SL_STEP_PCT: float = 0.5       # Trailing stop-loss step percentage

# Set to True to also reset current_capital and total_pnl back to INITIAL_CAPITAL.
# Useful when you want a completely fresh start without deleting trade history.
RESET_CAPITAL_TO_INITIAL: bool = False

# ═══════════════════════════════════════════════════════════════════
#  ↑↑↑  STOP EDITING HERE  ↑↑↑
# ═══════════════════════════════════════════════════════════════════


def get_db_path() -> str:
    """Return the absolute path to paper_trades.db at the project root."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "paper_trades.db")


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist (mirrors engine _init_db logic)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trading_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS closed_trades (
            order_id     INTEGER PRIMARY KEY,
            symbol       TEXT    NOT NULL,
            exchange     TEXT    NOT NULL,
            side         TEXT    NOT NULL,
            entry_price  REAL    NOT NULL,
            exit_price   REAL    NOT NULL,
            stop_loss    REAL    NOT NULL,
            target       REAL    NOT NULL,
            lot_size     INTEGER NOT NULL,
            opened_at    TEXT    NOT NULL,
            closed_at    TEXT    NOT NULL,
            close_reason TEXT    NOT NULL,
            pnl          REAL    NOT NULL,
            pnl_percentage REAL  NOT NULL
        )
        """
    )
    conn.commit()


def upsert(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO trading_config (key, value) VALUES (?, ?)",
        (key, value),
    )


def main() -> None:
    # Validate inputs
    if INITIAL_CAPITAL <= 0:
        print("❌ INITIAL_CAPITAL must be > 0.")
        sys.exit(1)
    if MIN_RISK_REWARD_RATIO <= 0:
        print("❌ MIN_RISK_REWARD_RATIO must be > 0.")
        sys.exit(1)
    if MAX_OPEN_POSITIONS <= 0:
        print("❌ MAX_OPEN_POSITIONS must be > 0.")
        sys.exit(1)
    if TRAILING_SL_STEP_PCT <= 0:
        print("❌ TRAILING_SL_STEP_PCT must be > 0.")
        sys.exit(1)

    db_path = get_db_path()
    is_new = not os.path.exists(db_path)

    conn = sqlite3.connect(db_path)
    try:
        ensure_tables(conn)

        upsert(conn, "initial_capital",       str(INITIAL_CAPITAL))
        upsert(conn, "min_risk_reward_ratio",  str(MIN_RISK_REWARD_RATIO))
        upsert(conn, "max_open_positions",     str(MAX_OPEN_POSITIONS))
        upsert(conn, "trailing_sl_step_pct",   str(TRAILING_SL_STEP_PCT))

        if RESET_CAPITAL_TO_INITIAL:
            upsert(conn, "current_capital", str(INITIAL_CAPITAL))
            upsert(conn, "total_pnl",       "0.0")
            print(
                f"⚠️  Capital reset to {INITIAL_CAPITAL:,.2f} and total PnL set to 0."
            )

        conn.commit()
    finally:
        conn.close()

    status = "created" if is_new else "updated"
    print(f"✅ Database {status}: {db_path}")
    print(f"   initial_capital      = {INITIAL_CAPITAL:,.2f}")
    print(f"   min_risk_reward_ratio = {MIN_RISK_REWARD_RATIO}")
    print(f"   max_open_positions    = {MAX_OPEN_POSITIONS}")
    print(f"   trailing_sl_step_pct  = {TRAILING_SL_STEP_PCT}")

    if not RESET_CAPITAL_TO_INITIAL:
        print()
        print(
            "ℹ️  current_capital and total_pnl were NOT changed. "
            "Set RESET_CAPITAL_TO_INITIAL=True to reset them."
        )


if __name__ == "__main__":
    main()
