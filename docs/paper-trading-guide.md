# Paper Trading Guide

This guide covers everything you need to know to use the paper trading system built into TradingView MCP Server. All trades are simulated — no real money is involved.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Available Tools / Endpoints](#available-tools--endpoints)
3. [Placing an Order](#placing-an-order)
4. [Monitoring Alerts](#monitoring-alerts)
5. [Configuration](#configuration)
6. [Database & Persistence](#database--persistence)
7. [Scripts Reference](#scripts-reference)

---

## How It Works

- **Open positions** are held in memory. If the server restarts, open positions are lost (this is by design for a simulated environment).
- **Closed trades** are persisted to `paper_trades.db` (SQLite) at the project root.
- **Capital, PnL, and counters** are also stored in the database so they survive server restarts.
- **Price monitoring** runs as a background asyncio task using TradingView price streaming. A trade closes automatically when its Stop Loss or Target price is hit.

---

## Available Tools / Endpoints

| MCP Tool | HTTP Endpoint | Description |
|---|---|---|
| `place_order` | `POST /paper-trading/place-order` | Place a paper trade |
| `close_position` | `POST /paper-trading/close-position` | Manually close a position |
| `view_positions` | `POST /paper-trading/view-positions` | View open / closed / all positions |
| `show_capital` | `GET /paper-trading/show-capital` | View capital & PnL summary |
| `set_alert` | `POST /paper-trading/set-alert` | Set a price or time alert |
| `alert_manager` | `GET /paper-trading/alert-manager` | Block & wait for the next alert event |
| `view_available_alerts` | `GET /paper-trading/view-alerts` | List all active alerts |
| `remove_alert` | `POST /paper-trading/remove-alert` | Remove a manual alert |

---

## Placing an Order

The system automatically determines BUY or SELL from the relationship between `entry_price` and `target`:

- `entry < target` → **BUY**
- `entry > target` → **SELL**

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `symbol` | string | e.g. `NIFTY`, `BTCUSD` |
| `exchange` | string | e.g. `NSE`, `BINANCE` |
| `entry_price` | float | Price at which the order is placed |
| `stop_loss` | float | SL price (below entry for BUY, above for SELL) |
| `target` | float | Target / take-profit price |
| `lot_size` | int | Number of lots / shares |
| `trailing_sl` | bool | (optional) Enable trailing stop loss. Default `false` |

**Validation rules:**
- Risk:Reward ratio must be ≥ `min_risk_reward_ratio` (default 1.5, configurable in DB).
- Cannot exceed `max_open_positions` (default 10).
- Sufficient capital must be available.

**Example (MCP):**
```json
{
  "symbol": "NIFTY",
  "exchange": "NSE",
  "entry_price": 22000,
  "stop_loss": 21800,
  "target": 22500,
  "lot_size": 50
}
```

---

## Monitoring Alerts

### `alert_manager`

This tool **blocks** until an alert fires or the timeout elapses, then returns all triggered events. It must be called repeatedly as long as there are open positions or active alerts.

**Timeout behaviour:**
- Default: `300` seconds (5 minutes).
- Override with the `ALERT_MANAGER_TIMEOUT_SECONDS` environment variable.
- Values `< 0` are treated as an error and fall back to `300`.

When an alert fires, the response includes:
```json
{
  "triggered_events": [...],
  "remaining_manual_alerts": 2,
  "open_positions": 1,
  "instruction": "IMPORTANT: ... You MUST call alert_manager again ..."
}
```

Follow the `instruction` field — keep calling `alert_manager` until all positions and alerts are cleared.

### Price Alerts

Set with `alert_type = "price"`:
```json
{
  "alert_type": "price",
  "symbol": "NIFTY",
  "exchange": "NSE",
  "price": 22500,
  "direction": "above"
}
```

### Time Alerts

Set with `alert_type = "time"`:
```json
{
  "alert_type": "time",
  "minutes": 30
}
```

### Alert Injection (Optional)

Set `INJECT_ALERTS_IN_ALL_TOOLS=true` in your environment to have triggered alert events automatically appended to any other tool's response. Useful for AI agents that are busy calling other tools.

---

## Configuration

Paper trading configuration is stored in the `trading_config` table inside `paper_trades.db`. On first run (or when the DB is missing), the following environment variables are used as defaults:

| DB Key | Env Var | Default | Description |
|---|---|---|---|
| `initial_capital` | `PAPER_TRADING_CAPITAL` | `100000` | Starting reference capital |
| `current_capital` | — | same as initial | Live balance (changes with each closed trade) |
| `min_risk_reward_ratio` | `MIN_RISK_REWARD_RATIO` | `1.5` | Minimum R:R required to place a trade |
| `max_open_positions` | `MAX_OPEN_POSITIONS` | `10` | Maximum simultaneous positions |
| `trailing_sl_step_pct` | `TRAILING_SL_STEP_PCT` | `0.5` | Trailing SL step as % of current price |
| `ALERT_MANAGER_TIMEOUT_SECONDS` | env only | `300` | Seconds alert_manager waits before returning |

To change these values at runtime (without touching env vars), use the [setup script](#setup_paper_tradingpy).

---

## Database & Persistence

The database file is `paper_trades.db` in the project root.

### Tables

#### `closed_trades`
Stores every trade that has been closed (SL hit, target hit, or manual close).

| Column | Type | Description |
|---|---|---|
| `order_id` | INTEGER | Unique order identifier |
| `symbol` | TEXT | Trading symbol |
| `exchange` | TEXT | Exchange |
| `side` | TEXT | BUY or SELL |
| `entry_price` | REAL | Entry price |
| `exit_price` | REAL | Exit price |
| `stop_loss` | REAL | Original stop loss |
| `target` | REAL | Target price |
| `lot_size` | INTEGER | Lots traded |
| `opened_at` | TEXT | Open timestamp (IST) |
| `closed_at` | TEXT | Close timestamp (IST) |
| `close_reason` | TEXT | SL_HIT / TARGET_HIT / TRAILING_SL_HIT / MANUAL_CLOSE |
| `pnl` | REAL | Profit or Loss |
| `pnl_percentage` | REAL | PnL as % of invested |

> **Note:** Open positions are NOT stored in the database. Only trades that have been fully closed are persisted.

#### `trading_config`
Stores engine state and configuration as key-value pairs (see [Configuration](#configuration) above).

---

## Scripts Reference

All scripts live in the `scripts/` directory and can be run directly from the project root.

### `setup_paper_trading.py`

Hardcode your desired configuration values in the script and run it once to update the database.

```bash
python scripts/setup_paper_trading.py
```

Key options inside the script:
```python
INITIAL_CAPITAL = 100_000.0       # Set starting capital
MIN_RISK_REWARD_RATIO = 1.5
MAX_OPEN_POSITIONS = 10
TRAILING_SL_STEP_PCT = 0.5
RESET_CAPITAL_TO_INITIAL = False  # Set True to also reset current balance
```

> ⚠️ `RESET_CAPITAL_TO_INITIAL=True` resets your live balance and PnL to defaults. Trade history is **not** affected.

---

### `export_trades.py`

Exports all closed trades to a CSV file inside the `export/` folder (created automatically).

```bash
python scripts/export_trades.py
```

Output example:
```
✅ Exported 42 trade(s) to:
   /path/to/project/export/trades_20260218_143022.csv

   Total trades : 42
   Winners      : 28
   Losers       : 14
   Total PnL    : +18,450.00
```

Set `OUTPUT_FILENAME = "my_trades"` inside the script for a fixed filename instead of a timestamp.

---

### `reset_orders.py`

Clears all closed trade history and resets the order ID counter to 1. **Capital, PnL, and configuration are not affected.**

```bash
python scripts/reset_orders.py
```

You will be prompted to confirm before any data is deleted:
```
⚠️   WARNING: This will permanently delete trade history!
...
Type 'yes' to confirm deletion, or anything else to cancel:
```

> Capital, total PnL, and all configuration settings are preserved by this script.
