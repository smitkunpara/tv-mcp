# Plan: Paper Trading System + NSE OI Enhancement

**Created:** 17-Feb-2026  
**Status:** Ready for Atlas Execution

## Summary

Add a full paper trading engine to the TradingView MCP server. The system lets the AI place simulated trades (equities, options, crypto), tracks positions with SL/target via background screener threads, manages time/price alerts, persists closed trades to a SQLite database at the project root, and exposes 8 new MCP tools + corresponding Vercel REST endpoints. Additionally, enhance the existing NSE option chain OI tool and add comprehensive tests. The system uses `asyncio` primitives (not raw threads) for concurrency, with proper locking to avoid race conditions.

## Context & Analysis

**Relevant Files (existing, to modify):**
- `src/tv_mcp/mcp/server.py`: Register 8 new paper-trading MCP tools
- `src/tv_mcp/services/__init__.py`: Re-export new service functions
- `src/tv_mcp/core/settings.py`: Add risk management env vars (PAPER_TRADING_CAPITAL, RISK_PER_TRADE_PCT, MIN_RISK_REWARD_RATIO, TRAILING_SL_ENABLED)
- `vercel/app.py`: Include new paper-trading router
- `vercel/routers/public.py`: Add paper-trading endpoints to the root endpoint listing
- `pyproject.toml`: Add `aiosqlite` dependency (async SQLite driver)
- `tests/stdio/test_mcp_server.py`: Update expected tool count from 7 → 16 (8 existing + 8 new)

**New Files to Create:**
- `src/tv_mcp/services/paper_trading.py` — Core paper trading engine (order management, capital, DB, screener threads, alert system)
- `src/tv_mcp/mcp/tools/paper_trading.py` — 8 MCP tool handlers for paper trading
- `vercel/routers/paper_trading.py` — REST endpoints for paper trading
- `vercel/schemas.py` — Add request models for paper trading endpoints (append to existing)
- `paper_trades.db` — Auto-created SQLite database at project root (runtime, not committed)
- `tests/stdio/test_service_paper_trading.py` — Service-level unit tests
- `tests/stdio/test_paper_trading_tools.py` — MCP tool handler tests
- `tests/http/test_paper_trading_routes.py` — Vercel endpoint tests

**Key Functions/Classes to Create:**
- `PaperTradingEngine` (singleton class in `services/paper_trading.py`): Central engine managing all state
- `ScreenerThread` (background asyncio task): Monitors positions for SL/target/price-alert hits
- `AlertManager`: Manages all alerts (trade-auto, price, time), returns triggered events to AI

**Dependencies:**
- `aiosqlite>=0.20.0` — async SQLite for non-blocking DB writes (add to `pyproject.toml`)
- `sqlite3` (stdlib) — synchronous fallback for simple operations
- `asyncio` — async task management (replaces raw threading for better integration with FastMCP's async event loop)
- `threading.Lock` — for thread-safe access to shared state when sync code accesses engine state

**Patterns & Conventions:**
- Services return `{"success": True/False, ...}` dicts (follow existing pattern)
- MCP tool handlers are `async def` returning `str` via `serialize_success()`/`serialize_error()`
- Tool params use `Annotated[..., Field(description=...)]` pattern
- Vercel endpoints use `try/except ValidationError → 400, Exception → 500` pattern
- IST datetime throughout via `transforms/time.py` utilities
- Imports in tools use `src.tv_mcp.*` absolute paths
- All paper trading code is self-contained in separate files (not merged into existing domain files)

## Architecture Decision: asyncio vs Threading

**Decision: Use `asyncio` tasks instead of raw `threading.Thread`**

Rationale:
1. FastMCP runs an asyncio event loop — async tasks integrate naturally
2. `asyncio.Event` replaces centralized polling variables — tasks wait efficiently without busy-spinning
3. `asyncio.Lock` prevents race conditions without OS-level thread locks
4. Screener polling can use `asyncio.sleep()` without blocking the event loop
5. The alert manager tool can `await` an `asyncio.Event` to block until an alert triggers, then return

**Concurrency Model:**
- Each position gets an `asyncio.Task` that polls price via `get_current_spot_price()` every 2-5 seconds
- Time alerts spawn a `asyncio.Task` that sleeps for N minutes then sets an event
- Price alerts are folded into existing screener tasks for the same symbol (no duplicate tasks)
- A shared `asyncio.Queue` collects all triggered events
- The `alert_manager` tool awaits the queue — returns when something is available
- `asyncio.Lock` guards the positions dict and alert registry for concurrent access

## Implementation Phases

### Phase 1: Settings & Database Foundation

**Objective:** Add risk management env vars to Settings and create the SQLite database schema.

**Files to Modify:**
- `src/tv_mcp/core/settings.py`: Add paper trading config vars
- `pyproject.toml`: Add `aiosqlite` dependency

**Files to Create:**
- `src/tv_mcp/services/paper_trading.py`: Initial file with DB schema, `PaperTradingEngine` skeleton

**Steps:**

1. Add to `Settings._initialize()`:
```python
# Paper Trading Configuration
self.PAPER_TRADING_CAPITAL: float = float(os.getenv("PAPER_TRADING_CAPITAL", "100000"))
self.RISK_PER_TRADE_PCT: float = float(os.getenv("RISK_PER_TRADE_PCT", "2.0"))  # max % of capital risked per trade
self.MIN_RISK_REWARD_RATIO: float = float(os.getenv("MIN_RISK_REWARD_RATIO", "1.5"))  # minimum R:R to accept
self.TRAILING_SL_ENABLED: bool = os.getenv("TRAILING_SL_ENABLED", "false").lower() == "true"
self.TRAILING_SL_STEP_PCT: float = float(os.getenv("TRAILING_SL_STEP_PCT", "0.5"))  # trailing SL step %
```

2. Add `aiosqlite>=0.20.0` to `pyproject.toml` dependencies

3. Create `src/tv_mcp/services/paper_trading.py` with:
   - SQLite DB initialization (creates `paper_trades.db` at project root)
   - Schema: `closed_trades` table with columns:
     ```sql
     CREATE TABLE IF NOT EXISTS closed_trades (
         order_id INTEGER PRIMARY KEY,
         symbol TEXT NOT NULL,
         exchange TEXT NOT NULL,
         side TEXT NOT NULL,  -- 'BUY' or 'SELL'
         entry_price REAL NOT NULL,
         exit_price REAL NOT NULL,
         stop_loss REAL NOT NULL,
         target REAL NOT NULL,
         lot_size INTEGER NOT NULL,
         opened_at TEXT NOT NULL,  -- IST datetime string
         closed_at TEXT NOT NULL,  -- IST datetime string
         close_reason TEXT NOT NULL,  -- 'SL_HIT', 'TARGET_HIT', 'MANUAL_CLOSE', 'TRAILING_SL_HIT'
         pnl REAL NOT NULL,
         pnl_percentage REAL NOT NULL
     );
     ```
   - Note: Only closed trades go in DB. Open positions are in-memory only.
   - `PaperTradingEngine` class skeleton (singleton) with `_initialize_db()` async method

**Tests to Write (Phase 9):**
- `test_settings_paper_trading_defaults` — Verify default env var loading
- `test_db_initialization` — Verify table creation

**Acceptance Criteria:**
- [ ] Settings loads paper trading env vars with sensible defaults
- [ ] SQLite DB auto-created at project root when engine initializes
- [ ] `closed_trades` table schema is correct
- [ ] `aiosqlite` added to pyproject.toml
- [ ] Existing tests still pass (`uv run pytest`)

---

### Phase 2: Core Paper Trading Engine — Order Placement & Risk Management

**Objective:** Implement `place_order()`, capital tracking, and risk management validation.

**Files to Modify:**
- `src/tv_mcp/services/paper_trading.py`: Add `place_order()`, risk validation, capital tracking

**Key Design:**

```python
import asyncio
import sqlite3
import time
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from tv_mcp.core.settings import settings
from tv_mcp.transforms.time import convert_timestamp_to_indian_time, IST_TZ

class Position:
    """In-memory representation of an open position."""
    def __init__(self, order_id, symbol, exchange, side, entry_price, stop_loss, target,
                 lot_size, trailing_sl, opened_at_ist):
        self.order_id = order_id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side  # 'BUY' or 'SELL'
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.current_sl = stop_loss  # for trailing SL
        self.target = target
        self.lot_size = lot_size
        self.trailing_sl = trailing_sl
        self.opened_at_ist = opened_at_ist
        self.screener_task: Optional[asyncio.Task] = None

class PaperTradingEngine:
    """Singleton paper trading engine."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        self._next_order_id = 1
        self._positions: Dict[int, Position] = {}  # open positions
        self._capital = settings.PAPER_TRADING_CAPITAL
        self._total_pnl = 0.0
        self._positions_lock = asyncio.Lock()
        self._alert_queue = asyncio.Queue()
        self._alerts: Dict[int, dict] = {}  # alert_id → alert_info
        self._alert_ids: Set[int] = set()  # for O(1) lookup
        self._next_alert_id = 1
        self._alerts_lock = asyncio.Lock()
        self._screener_tasks: Dict[str, asyncio.Task] = {}  # symbol → task
        self._db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "paper_trades.db")
        self._init_db()

    def _init_db(self):
        """Create DB and table synchronously (called once at startup)."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS closed_trades (...)""")
        conn.commit()
        conn.close()
```

**`place_order()` logic:**
1. Validate inputs (symbol, exchange, entry_price > 0, stop_loss > 0, target > 0, lot > 0)
2. Determine side: If entry < target → BUY, if entry > target → SELL
3. Risk-reward check: `abs(target - entry) / abs(entry - stop_loss) >= MIN_RISK_REWARD_RATIO`
4. Capital check: `entry_price * lot_size <= available_capital` (simplified)
5. Create `Position` object, assign `order_id` (auto-increment int)
6. Immediately start a screener `asyncio.Task` for the position that monitors price
7. Return order confirmation with all details

**Risk Management Validation:**
```python
def _validate_risk_reward(self, entry, stop_loss, target) -> bool:
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    if risk == 0:
        raise ValidationError("Stop loss cannot equal entry price")
    ratio = reward / risk
    if ratio < settings.MIN_RISK_REWARD_RATIO:
        raise ValidationError(
            f"Risk:Reward ratio {ratio:.2f} is below minimum {settings.MIN_RISK_REWARD_RATIO}. "
            f"Adjust target or stop loss."
        )
    return True
```

**Acceptance Criteria:**
- [ ] `place_order()` validates all inputs
- [ ] Risk-reward ratio enforced from env settings
- [ ] Order ID auto-increments
- [ ] Position stored in-memory (not DB)
- [ ] Screener task spawned for the position
- [ ] Capital deducted (entry * lots reserved)
- [ ] Returns confirmation dict with order_id, entry, sl, target, side

---

### Phase 3: Screener Task & Position Monitoring

**Objective:** Implement the background screener that monitors positions for SL/target hits, trailing SL logic, and pushes events to the alert queue.

**Files to Modify:**
- `src/tv_mcp/services/paper_trading.py`: Add `_screener_loop()`, trailing SL logic

**Screener Task Design:**

```python
async def _screener_loop(self, order_id: int):
    """Background task monitoring a single position."""
    while True:
        await asyncio.sleep(3)  # poll interval
        async with self._positions_lock:
            pos = self._positions.get(order_id)
            if pos is None:
                return  # position closed manually

        try:
            # Get current price using existing service
            from tv_mcp.services.options import get_current_spot_price
            current_price = get_current_spot_price(pos.symbol, pos.exchange)
        except Exception:
            continue  # retry on failure

        # Check SL/Target hit
        hit = None
        if pos.side == "BUY":
            if current_price <= pos.current_sl:
                hit = "SL_HIT" if pos.current_sl == pos.stop_loss else "TRAILING_SL_HIT"
            elif current_price >= pos.target:
                hit = "TARGET_HIT"
            elif pos.trailing_sl and current_price > pos.entry_price:
                # Trailing SL: move SL up as price moves up
                new_sl = current_price * (1 - settings.TRAILING_SL_STEP_PCT / 100)
                if new_sl > pos.current_sl:
                    pos.current_sl = new_sl
        elif pos.side == "SELL":
            if current_price >= pos.current_sl:
                hit = "SL_HIT" if pos.current_sl == pos.stop_loss else "TRAILING_SL_HIT"
            elif current_price <= pos.target:
                hit = "TARGET_HIT"
            elif pos.trailing_sl and current_price < pos.entry_price:
                new_sl = current_price * (1 + settings.TRAILING_SL_STEP_PCT / 100)
                if new_sl < pos.current_sl:
                    pos.current_sl = new_sl

        # Also check any price alerts attached to this symbol
        async with self._alerts_lock:
            triggered_alerts = []
            for aid, alert in list(self._alerts.items()):
                if alert["type"] == "price" and alert["symbol"].upper() == pos.symbol.upper():
                    if (alert["direction"] == "above" and current_price >= alert["price"]) or \
                       (alert["direction"] == "below" and current_price <= alert["price"]):
                        triggered_alerts.append(aid)

            for aid in triggered_alerts:
                alert = self._alerts.pop(aid)
                self._alert_ids.discard(aid)
                await self._alert_queue.put({
                    "source": "price_alert",
                    "alert_id": aid,
                    "symbol": alert["symbol"],
                    "price": alert["price"],
                    "direction": alert["direction"],
                    "current_price": current_price,
                    "message": f"Price alert triggered: {alert['symbol']} {'reached above' if alert['direction'] == 'above' else 'dropped below'} {alert['price']} (current: {current_price})"
                })

        if hit:
            await self._close_position_internal(order_id, current_price, hit)
            return  # task done after position closed
```

**Price alert folding:** When a price alert is set for a symbol that already has a screener running, the alert is just added to `self._alerts` dict — the existing screener task will check it each loop iteration. No new task needed.

**When no screener exists for that symbol:** A lightweight price-only monitor task is spawned.

**Acceptance Criteria:**
- [ ] Screener polls price every 3 seconds via `get_current_spot_price()`
- [ ] SL hit detection for BUY and SELL positions
- [ ] Target hit detection for BUY and SELL positions
- [ ] Trailing SL moves SL in favorable direction by configured step %
- [ ] Events pushed to `asyncio.Queue` for alert_manager consumption
- [ ] Position auto-closed and persisted to DB on SL/target hit
- [ ] Price alerts checked within screener loop (no duplicate tasks per symbol)

---

### Phase 4: Close Position, View Positions, Show Capital

**Objective:** Implement `close_position()`, `view_positions()`, `show_capital()`.

**Files to Modify:**
- `src/tv_mcp/services/paper_trading.py`

**`close_position(order_id)`:**
1. Acquire `_positions_lock`
2. Find position by order_id (error if not found)
3. Get current price via `get_current_spot_price()`
4. Calculate PnL: `(current_price - entry_price) * lot_size` for BUY, inverse for SELL
5. Cancel the screener task: `pos.screener_task.cancel()`
6. Record to DB with `close_reason='MANUAL_CLOSE'`
7. Update capital: `self._capital += invested + pnl`
8. Update `self._total_pnl += pnl`
9. Remove from `self._positions`
10. Push event to alert queue so alert_manager can notify AI

**`_close_position_internal(order_id, exit_price, reason)`:**
- Same as above but used by screener (already has the exit price)
- Records to DB, updates capital, pushes to alert queue

**DB write function:**
```python
def _record_closed_trade(self, pos: Position, exit_price: float, reason: str):
    pnl = (exit_price - pos.entry_price) * pos.lot_size if pos.side == "BUY" else (pos.entry_price - exit_price) * pos.lot_size
    pnl_pct = (pnl / (pos.entry_price * pos.lot_size)) * 100
    closed_at = datetime.now(IST_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")
    conn = sqlite3.connect(self._db_path)
    conn.execute("""INSERT INTO closed_trades (...) VALUES (...)""",
                 (pos.order_id, pos.symbol, pos.exchange, pos.side,
                  pos.entry_price, exit_price, pos.stop_loss, pos.target,
                  pos.lot_size, pos.opened_at_ist, closed_at, reason, pnl, pnl_pct))
    conn.commit()
    conn.close()
```

**`view_positions(filter_type, order_id)`:**
1. Validate: if both `filter_type` AND `order_id` provided → error
2. If `order_id` provided: look up in open positions, if not found check DB for closed
3. If `filter_type == "open"`: return all `self._positions` as list of dicts
4. If `filter_type == "closed"`: query DB `SELECT * FROM closed_trades ORDER BY closed_at DESC`
5. If `filter_type == "all"`: open positions + DB query combined

**`show_capital()`:**
```python
def show_capital(self) -> Dict[str, Any]:
    initial = settings.PAPER_TRADING_CAPITAL
    invested = sum(p.entry_price * p.lot_size for p in self._positions.values())
    return {
        "success": True,
        "initial_capital": initial,
        "current_capital": self._capital,
        "invested_in_open_positions": invested,
        "available_fund": self._capital - invested,
        "total_realized_pnl": self._total_pnl,
        "total_pnl_percentage": (self._total_pnl / initial) * 100 if initial > 0 else 0,
        "open_positions_count": len(self._positions),
    }
```

**Acceptance Criteria:**
- [ ] `close_position()` cancels screener, records to DB, updates capital, pushes alert
- [ ] `view_positions()` returns open/closed/all/single based on filter
- [ ] `view_positions()` errors if both filter_type AND order_id provided
- [ ] `show_capital()` shows available fund, PnL, PnL%, open position count
- [ ] PnL calculated correctly for both BUY and SELL positions

---

### Phase 5: Alert System (set_alert, view_available_alerts, remove_alert)

**Objective:** Implement price alerts, time alerts, and alert management.

**Files to Modify:**
- `src/tv_mcp/services/paper_trading.py`

**`set_alert(alert_type, ...)`:**

Two alert types:
1. **Price alert:** `set_alert(type="price", symbol="NIFTY", exchange="NSE", price=23500, direction="above"|"below")`
   - If screener already running for this symbol → just add to `self._alerts`, screener will pick it up
   - If no screener running → spawn a lightweight price-monitor task
   - Each alert gets a unique int ID (1, 2, 3, ...)
   - Alert ID stored in `self._alert_ids` set for O(1) lookup

2. **Time alert:** `set_alert(type="time", minutes=5)`
   - Spawn an asyncio task that sleeps for N minutes then pushes event to queue
   - One-shot: automatically removed after triggering
   - Also assigned an alert ID

```python
async def set_alert(self, alert_type: str, **kwargs) -> Dict[str, Any]:
    async with self._alerts_lock:
        alert_id = self._next_alert_id
        self._next_alert_id += 1

        if alert_type == "price":
            symbol = kwargs["symbol"].upper()
            exchange = kwargs["exchange"].upper()
            price = float(kwargs["price"])
            direction = kwargs.get("direction", "above")  # "above" or "below"
            self._alerts[alert_id] = {
                "type": "price", "symbol": symbol, "exchange": exchange,
                "price": price, "direction": direction, "alert_id": alert_id
            }
            self._alert_ids.add(alert_id)
            # Check if screener already running for this symbol
            if symbol not in self._screener_tasks or self._screener_tasks[symbol].done():
                task = asyncio.create_task(self._price_only_monitor(symbol, exchange))
                self._screener_tasks[symbol] = task
        elif alert_type == "time":
            minutes = int(kwargs["minutes"])
            self._alerts[alert_id] = {
                "type": "time", "minutes": minutes, "alert_id": alert_id
            }
            self._alert_ids.add(alert_id)
            asyncio.create_task(self._time_alert_task(alert_id, minutes))
        else:
            raise ValidationError(f"Invalid alert type: {alert_type}. Use 'price' or 'time'.")

    return {"success": True, "alert_id": alert_id, "type": alert_type, "message": f"Alert #{alert_id} set."}
```

**`_time_alert_task(alert_id, minutes)`:**
```python
async def _time_alert_task(self, alert_id: int, minutes: int):
    await asyncio.sleep(minutes * 60)
    async with self._alerts_lock:
        if alert_id in self._alert_ids:
            self._alerts.pop(alert_id, None)
            self._alert_ids.discard(alert_id)
            await self._alert_queue.put({
                "source": "time_alert",
                "alert_id": alert_id,
                "minutes": minutes,
                "message": f"Time alert triggered: {minutes}m timer expired. Take appropriate action."
            })
```

**`_price_only_monitor(symbol, exchange)`:**
- Like `_screener_loop` but only checks price alerts, no position SL/target
- Runs until all price alerts for that symbol are consumed
- Polls every 3 seconds

**`view_available_alerts()`:**
```python
async def view_available_alerts(self) -> Dict[str, Any]:
    async with self._alerts_lock:
        alerts_list = list(self._alerts.values())
    # Also include auto-alerts from open positions
    auto_alerts = []
    async with self._positions_lock:
        for pos in self._positions.values():
            auto_alerts.append({
                "type": "auto_trade", "order_id": pos.order_id,
                "symbol": pos.symbol, "stop_loss": pos.current_sl,
                "target": pos.target, "side": pos.side
            })
    return {"success": True, "manual_alerts": alerts_list, "trade_auto_alerts": auto_alerts}
```

**`remove_alert(alert_id)`:**
```python
async def remove_alert(self, alert_id: int) -> Dict[str, Any]:
    async with self._alerts_lock:
        if alert_id not in self._alert_ids:
            return {"success": False, "message": f"Alert #{alert_id} not found."}
        removed = self._alerts.pop(alert_id)
        self._alert_ids.discard(alert_id)
    return {"success": True, "message": f"Alert #{alert_id} removed.", "removed_alert": removed}
```

**Acceptance Criteria:**
- [ ] Price alerts registered with unique int IDs stored in set for O(1) lookup
- [ ] Price alerts folded into existing screener tasks when possible
- [ ] Time alerts are one-shot (auto-removed after trigger)
- [ ] `view_available_alerts()` shows both manual alerts and trade auto-alerts
- [ ] `remove_alert()` removes by ID with O(1) set lookup
- [ ] All alert operations use `asyncio.Lock` for thread safety

---

### Phase 6: Alert Manager Tool

**Objective:** Implement the `alert_manager()` tool that blocks until an alert triggers, then returns the event to the AI with instructions to call again.

**Files to Modify:**
- `src/tv_mcp/services/paper_trading.py`

**Alert Manager Design:**

```python
async def alert_manager(self) -> Dict[str, Any]:
    """
    Block until at least one alert triggers.
    Returns the triggered event with instructions for the AI.
    """
    # Check if there are any alerts or open positions
    has_work = False
    async with self._alerts_lock:
        if self._alerts:
            has_work = True
    async with self._positions_lock:
        if self._positions:
            has_work = True

    if not has_work:
        return {
            "success": True,
            "message": "No alerts set and no open positions. Place a trade or set an alert first.",
            "active_threads": 0
        }

    # Wait for an event from the queue (blocks until something triggers)
    try:
        event = await asyncio.wait_for(self._alert_queue.get(), timeout=300)  # 5 min max wait
    except asyncio.TimeoutError:
        return {
            "success": True,
            "message": "No alerts triggered in 5 minutes. Call alert_manager again to continue monitoring.",
            "active_alerts": len(self._alerts),
            "open_positions": len(self._positions)
        }

    # Collect any additional events already in the queue (batch)
    events = [event]
    while not self._alert_queue.empty():
        try:
            events.append(self._alert_queue.get_nowait())
        except asyncio.QueueEmpty:
            break

    # Build response
    remaining_alerts = len(self._alerts)
    remaining_positions = len(self._positions)
    has_more = remaining_alerts > 0 or remaining_positions > 0

    response = {
        "success": True,
        "triggered_events": events,
        "remaining_manual_alerts": remaining_alerts,
        "open_positions": remaining_positions,
    }

    if has_more:
        response["instruction"] = (
            "IMPORTANT: There are still active monitors running "
            f"({remaining_positions} open positions, {remaining_alerts} manual alerts). "
            "You MUST call alert_manager again to receive further updates. "
            "Do NOT stop monitoring."
        )
    else:
        response["instruction"] = "All monitors completed. No further action needed."

    return response
```

**Key behavior:**
- Blocks (awaits) until an event is in the queue or 5min timeout
- Returns all pending events as a batch
- Includes clear instruction telling AI to call again if threads are still active
- Does NOT just poll — it truly waits using `asyncio.Queue.get()`
- If no alerts/positions exist, returns immediately telling AI to place a trade or set an alert

**Acceptance Criteria:**
- [ ] Blocks until an alert triggers (not busy-polling)
- [ ] Returns triggered events as a list
- [ ] Includes remaining count of alerts and open positions
- [ ] Instructs AI to call again when monitors are still active
- [ ] Returns immediately when nothing to monitor
- [ ] 5-minute timeout with re-call instruction

---

### Phase 7: MCP Tool Handlers

**Objective:** Create 8 MCP tool handler functions with proper Annotated+Field parameter typing.

**Files to Create:**
- `src/tv_mcp/mcp/tools/paper_trading.py`

**Files to Modify:**
- `src/tv_mcp/mcp/server.py`: Import and register 8 new tools

**Tools:**

```python
# src/tv_mcp/mcp/tools/paper_trading.py

async def place_order(
    symbol: Annotated[str, Field(description="Trading symbol (e.g., 'NIFTY', 'RELIANCE', 'BTCUSD'). REQUIRED.")],
    exchange: Annotated[str, Field(description="Exchange (e.g., 'NSE', 'BSE', 'CRYPTO'). REQUIRED.")],
    entry_price: Annotated[float, Field(description="Entry price (limit price at which to buy/sell). REQUIRED.")],
    stop_loss: Annotated[float, Field(description="Stop loss price. REQUIRED.")],
    target: Annotated[float, Field(description="Target/take-profit price. REQUIRED.")],
    lot_size: Annotated[int, Field(description="Number of lots/quantity. REQUIRED.")],
    trailing_sl: Annotated[bool, Field(description="Enable trailing stop loss. Use when strong directional movement expected. Default: false")] = False,
) -> str: ...

async def close_position(
    order_id: Annotated[int, Field(description="Order ID of the position to close. REQUIRED.")],
) -> str: ...

async def view_positions(
    filter_type: Annotated[Optional[str], Field(description="Filter: 'open', 'closed', or 'all'. Cannot be used with order_id.")] = None,
    order_id: Annotated[Optional[int], Field(description="Specific order ID to view. Cannot be used with filter_type.")] = None,
) -> str: ...

async def show_capital() -> str: ...

async def set_alert(
    alert_type: Annotated[str, Field(description="Alert type: 'price' or 'time'. REQUIRED.")],
    symbol: Annotated[Optional[str], Field(description="Symbol for price alert (e.g., 'NIFTY'). Required for price alerts.")] = None,
    exchange: Annotated[Optional[str], Field(description="Exchange for price alert. Required for price alerts.")] = None,
    price: Annotated[Optional[float], Field(description="Target price for price alert. Required for price alerts.")] = None,
    direction: Annotated[Optional[str], Field(description="'above' or 'below' for price alert. Default: 'above'.")] = None,
    minutes: Annotated[Optional[int], Field(description="Minutes for time alert. Required for time alerts.")] = None,
) -> str: ...

async def alert_manager() -> str:
    """
    Wait for and return triggered alerts (SL/target hits, price alerts, time alerts).
    This tool BLOCKS until an alert triggers. After receiving a response,
    if there are still active monitors, you MUST call this tool again.
    Do NOT stop calling until all monitors are resolved.
    """ ...

async def view_available_alerts() -> str: ...

async def remove_alert(
    alert_id: Annotated[int, Field(description="ID of the alert to remove. REQUIRED.")],
) -> str: ...
```

**In `server.py`, add:**
```python
from .tools.paper_trading import (
    place_order, close_position, view_positions, show_capital,
    set_alert, alert_manager, view_available_alerts, remove_alert,
)

mcp.tool()(place_order)
mcp.tool()(close_position)
mcp.tool()(view_positions)
mcp.tool()(show_capital)
mcp.tool()(set_alert)
mcp.tool()(alert_manager)
mcp.tool()(view_available_alerts)
mcp.tool()(remove_alert)
```

**Acceptance Criteria:**
- [ ] 8 new tools registered in MCP server (total: 16)
- [ ] All params use `Annotated[..., Field(description=...)]` pattern
- [ ] All return `serialize_success()` / `serialize_error()`
- [ ] Tool docstrings serve as tool descriptions for AI
- [ ] `alert_manager` docstring clearly instructs AI to call again

---

### Phase 8: Vercel REST Endpoints

**Objective:** Create REST API endpoints for paper trading, in a separate router file that can be commented out.

**Files to Create:**
- `vercel/routers/paper_trading.py` — All 8 endpoints in a dedicated router

**Files to Modify:**
- `vercel/app.py` — Include paper trading router (commentable import)
- `vercel/schemas.py` — Add request models for paper trading
- `vercel/routers/public.py` — Add paper trading endpoints to root listing

**Router file structure:**
```python
# vercel/routers/paper_trading.py
from fastapi import APIRouter, Depends, HTTPException
from toon import encode as toon_encode
from src.tv_mcp.core.validators import ValidationError
from src.tv_mcp.services.paper_trading import PaperTradingEngine
from ..auth import verify_client
from ..schemas import (
    PlaceOrderRequest, ClosePositionRequest, ViewPositionsRequest,
    SetAlertRequest, RemoveAlertRequest, GenericDataResponse,
)

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])
engine = PaperTradingEngine()
engine.initialize()

@router.post("/place-order", dependencies=[Depends(verify_client)], response_model=GenericDataResponse)
async def place_order_endpoint(request: PlaceOrderRequest) -> dict: ...

@router.post("/close-position", ...) ...
@router.post("/view-positions", ...) ...
@router.get("/show-capital", ...) ...
@router.post("/set-alert", ...) ...
@router.get("/alert-manager", ...) ...
@router.get("/view-alerts", ...) ...
@router.post("/remove-alert", ...) ...
```

**In `vercel/app.py`:**
```python
from .routers import public, client, admin
from .routers import paper_trading  # Comment this line to disable paper trading endpoints

# In create_app():
application.include_router(paper_trading.router)  # Comment this to disable
```

**Pydantic request models to add to `vercel/schemas.py`:**
```python
class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    entry_price: float = Field(..., gt=0, description="Entry price")
    stop_loss: float = Field(..., gt=0, description="Stop loss")
    target: float = Field(..., gt=0, description="Target price")
    lot_size: int = Field(..., gt=0, description="Lot size")
    trailing_sl: bool = Field(False, description="Enable trailing SL")

class ClosePositionRequest(BaseModel):
    order_id: int = Field(..., description="Order ID to close")

class ViewPositionsRequest(BaseModel):
    filter_type: Optional[str] = Field(None, description="'open', 'closed', 'all'")
    order_id: Optional[int] = Field(None, description="Specific order ID")

class SetAlertRequest(BaseModel):
    alert_type: str = Field(..., description="'price' or 'time'")
    symbol: Optional[str] = Field(None, description="Symbol for price alert")
    exchange: Optional[str] = Field(None, description="Exchange for price alert")
    price: Optional[float] = Field(None, description="Target price")
    direction: Optional[str] = Field(None, description="'above' or 'below'")
    minutes: Optional[int] = Field(None, description="Minutes for time alert")

class RemoveAlertRequest(BaseModel):
    alert_id: int = Field(..., description="Alert ID to remove")
```

**Acceptance Criteria:**
- [ ] All 8 endpoints in separate `paper_trading.py` router file
- [ ] Router uses `/paper-trading` prefix
- [ ] Can be disabled by commenting 2 lines in `app.py`
- [ ] Request validation via Pydantic models
- [ ] Uses `verify_client` auth dependency
- [ ] Added to root endpoint listing in `public.py`

---

### Phase 9: Tests

**Objective:** Write comprehensive tests for paper trading system.

**Files to Create:**
- `tests/stdio/test_service_paper_trading.py` — Unit tests for the engine
- `tests/stdio/test_paper_trading_tools.py` — MCP tool handler tests
- `tests/http/test_paper_trading_routes.py` — Vercel endpoint contract tests

**Files to Modify:**
- `tests/stdio/test_mcp_server.py` — Update expected tool count
- `tests/stdio/test_scaffold_imports.py` — Add paper trading imports
- `tests/http/test_scaffold_imports.py` — Add paper trading imports
- `tests/test_entrypoint_compatibility.py` — Add paper trading module imports

**Test Categories:**

**A. Service Unit Tests (`test_service_paper_trading.py`):**
```python
import pytest
import asyncio
import os

class TestPaperTradingEngine:
    """Unit tests for PaperTradingEngine (no network, mocked prices)."""

    def setup_method(self):
        """Fresh engine for each test."""
        # Reset singleton
        PaperTradingEngine._instance = None
        engine = PaperTradingEngine()
        engine.initialize()
        self.engine = engine

    def teardown_method(self):
        """Cleanup DB."""
        if os.path.exists(self.engine._db_path):
            os.remove(self.engine._db_path)
        PaperTradingEngine._instance = None

    @pytest.mark.asyncio
    async def test_place_order_success(self): ...

    @pytest.mark.asyncio
    async def test_place_order_risk_reward_fail(self): ...

    @pytest.mark.asyncio
    async def test_place_order_insufficient_capital(self): ...

    @pytest.mark.asyncio
    async def test_close_position(self): ...

    @pytest.mark.asyncio
    async def test_close_position_not_found(self): ...

    @pytest.mark.asyncio
    async def test_view_positions_open(self): ...

    @pytest.mark.asyncio
    async def test_view_positions_both_params_error(self): ...

    @pytest.mark.asyncio
    async def test_show_capital(self): ...

    @pytest.mark.asyncio
    async def test_set_price_alert(self): ...

    @pytest.mark.asyncio
    async def test_set_time_alert(self): ...

    @pytest.mark.asyncio
    async def test_remove_alert(self): ...

    @pytest.mark.asyncio
    async def test_remove_alert_not_found(self): ...

    @pytest.mark.asyncio
    async def test_view_available_alerts(self): ...

    @pytest.mark.asyncio
    async def test_sl_hit_detection(self):
        """Mock price to be below SL, verify position closes and DB records."""

    @pytest.mark.asyncio
    async def test_target_hit_detection(self): ...

    @pytest.mark.asyncio
    async def test_trailing_sl(self): ...

    @pytest.mark.asyncio
    async def test_alert_manager_no_alerts(self): ...

    @pytest.mark.asyncio
    async def test_alert_manager_receives_event(self): ...

    @pytest.mark.asyncio
    async def test_concurrent_order_locking(self): ...

    def test_db_schema(self):
        """Verify closed_trades table exists with correct columns."""

    def test_capital_defaults(self):
        """Verify default capital from settings."""
```

**B. MCP Tool Tests (`test_paper_trading_tools.py`):**
- Mock `PaperTradingEngine` methods
- Verify `serialize_success`/`serialize_error` wrapping
- Test each of 8 tool handlers

**C. Vercel Route Tests (`test_paper_trading_routes.py`):**
- Mock service layer, test request/response contract
- Test `verify_client` auth requirement
- Test validation errors → 400
- Test success → TOON-encoded response

**D. Existing Test Updates:**
- `test_mcp_server.py`: Change expected tool count assertion from 7 to 16
- Scaffold import tests: Add `src.tv_mcp.services.paper_trading`, `src.tv_mcp.mcp.tools.paper_trading`, `vercel.routers.paper_trading`
- Entrypoint compatibility: Add paper trading modules

**Important:** Add `pytest-asyncio>=0.23.0` to dev dependencies in `pyproject.toml` for `@pytest.mark.asyncio` support.

**Acceptance Criteria:**
- [ ] 15+ service-level unit tests covering all engine methods
- [ ] 8 MCP tool handler tests
- [ ] 8 Vercel endpoint contract tests
- [ ] All existing tests still pass
- [ ] Tool count assertion updated
- [ ] Scaffold imports updated
- [ ] `pytest-asyncio` added to dev deps
- [ ] All tests pass with `uv run pytest`

---

### Phase 10: Integration & Final Wiring

**Objective:** Final integration — ensure everything is wired, exports updated, no import errors.

**Files to Modify:**
- `src/tv_mcp/services/__init__.py`: Add paper trading exports
- `src/tv_mcp/mcp/tools/__init__.py`: Update docstring with paper trading tools
- Verify all cross-module imports work
- Update the `__all__` list if applicable

**Steps:**
1. Add to `src/tv_mcp/services/__init__.py`:
```python
from .paper_trading import PaperTradingEngine
```

2. Update `src/tv_mcp/mcp/tools/__init__.py` docstring to list paper trading tools

3. Run full test suite: `uv run pytest -v`

4. Fix any import issues or circular dependencies

5. Verify the MCP server starts: `uv run server.py` (should show 16 tools)

6. Verify Vercel app starts: `uv run uvicorn vercel.app:app`

**Acceptance Criteria:**
- [ ] No circular import errors
- [ ] `uv run pytest -v` — all tests pass
- [ ] MCP server registers 16 tools
- [ ] Vercel app includes paper trading endpoints
- [ ] Paper trading endpoints can be disabled by commenting 2 lines in `vercel/app.py`
- [ ] SQLite DB created at project root when engine initializes

---

## Open Questions

1. **Price source for crypto/international stocks?**
   - `get_current_spot_price()` uses `tv_scraper.Overview` which supports NSE/BSE and international exchanges, but not all crypto pairs may be available.
   - **Recommendation:** Use it as-is; document that supported symbols depend on TradingView's coverage. The `exchange` parameter handles routing (NSE/BSE/CRYPTO → TradingView exchange codes).

2. **Screener poll interval?**
   - 3 seconds per position means N concurrent HTTP requests every 3 seconds with N open positions.
   - **Option A:** 3 seconds (real-time feel, higher load)
   - **Option B:** 5 seconds (reasonable balance)
   - **Recommendation:** Default to 5 seconds, make configurable via env `SCREENER_POLL_INTERVAL_SECONDS`.

3. **Alert manager timeout?**
   - Currently set to 300 seconds (5 min) max wait.
   - **Recommendation:** Keep 5 min; AI can call again after timeout.

4. **Database: SQLite vs MongoDB?**
   - User mentioned "MongoDB" but also "create .db file at root level" which is SQLite terminology.
   - **Recommendation:** Use SQLite (`.db` file at root) — zero infrastructure, single file, perfect for paper trading. MongoDB would require a running server. If user truly wants MongoDB, the schema can be adapted later since the DB layer is isolated in one method.

5. **Capital tracking — lots vs shares?**
   - For option trading, 1 lot = 50 shares (NIFTY) or 15 shares (BANKNIFTY). The `lot_size` parameter should represent the number of lots.
   - **Recommendation:** Capital calculation uses `entry_price * lot_size` — user/AI is responsible for knowing what lot size means for their instrument.

## Risks & Mitigation

- **Risk:** `get_current_spot_price()` may fail for some symbols or during market hours
  - **Mitigation:** Screener task retries on failure, logs warning, continues polling

- **Risk:** Too many concurrent screener tasks could overwhelm TradingView API
  - **Mitigation:** Add max open positions limit (env: `MAX_OPEN_POSITIONS`, default 10)

- **Risk:** Server restart loses all open positions (in-memory only)
  - **Mitigation:** This is by design per user requirement — only closed trades persisted. Document that server restart = all open positions lost.

- **Risk:** asyncio event loop conflicts between FastMCP and paper trading tasks
  - **Mitigation:** Paper trading tasks run on the same event loop as FastMCP (which is asyncio-based). No separate threads needed.

- **Risk:** Race conditions between multiple tool calls modifying positions simultaneously
  - **Mitigation:** `asyncio.Lock` on positions dict and alerts dict. All mutations go through locked sections.

## Success Criteria

- [ ] 8 new MCP tools registered and functional (place_order, close_position, view_positions, show_capital, set_alert, alert_manager, view_available_alerts, remove_alert)
- [ ] Paper trading engine with risk management (R:R ratio, capital limits)
- [ ] Trailing SL support
- [ ] Background screener monitors SL/target/price hits
- [ ] Alert manager blocks until triggers, instructs AI to re-call
- [ ] SQLite DB at project root stores closed trades only
- [ ] Vercel endpoints in separate commentable file
- [ ] All new and existing tests pass
- [ ] No circular imports, clean modular separation

## Notes for Atlas

1. **Execution order matters.** Phases 1-6 build the core engine incrementally. Phase 7-8 wrap it for MCP/Vercel. Phase 9 adds tests. Phase 10 wires everything together. Follow this order.

2. **The PaperTradingEngine singleton must be initialized lazily** — `initialize()` should be called on first use (inside each tool handler or via a helper), not at module import time, to avoid DB creation during test imports.

3. **Use `asyncio.create_task()`** for background screener/alert tasks. These tasks run on the existing FastMCP event loop.

4. **The `alert_manager` tool is the most complex.** It must truly `await` (block the async call) until an event arrives. This is fine because MCP tool calls are async — the AI will wait for the response.

5. **Import paths:** MCP tool files use `src.tv_mcp.*` (absolute from project root). Service files use `tv_mcp.*` (package-relative). Follow this convention.

6. **The user wants IST datetime** used throughout — use `datetime.now(IST_TZ).strftime(...)` for all timestamps. The `transforms/time.py` utilities already handle this.

7. **Database path:** Use `os.path.join(project_root, "paper_trades.db")` where project_root is computed from `__file__` navigation. The file should be at `/home/smitkunpara/Desktop/tradingview-mcp/paper_trades.db`.

8. **NSE OI tool is already implemented.** The user's request about adding OI data for NIFTY is already fulfilled by the existing `fetch_nse_option_chain_oi()` and `get_nse_option_chain_oi()` functions. The existing implementation supports all 5 NSE indices and uses the exact NSE API endpoint and data structure the user described. No changes needed here — verify and confirm during execution.

9. **IST datetime filtering is already implemented** in news, minds, and ideas services. The existing `parse_ist_datetime_to_ts()` function handles DD-MM-YYYY HH:MM format. No changes needed here either.

10. **For tests:** Add `pytest-asyncio>=0.23.0` to dev deps. Use `@pytest.mark.asyncio` for async test methods. Mock `get_current_spot_price()` in unit tests to avoid network calls.

11. **Vercel paper trading router should be commentable.** The import in `app.py` should have a clear comment: `# Comment the next 2 lines to disable paper trading endpoints`.

12. **Run `uv run pytest -v` at the end** of each phase to verify nothing breaks.

## File Creation Summary

| File | Type | Purpose |
|------|------|---------|
| `src/tv_mcp/services/paper_trading.py` | NEW | Core engine: orders, positions, capital, alerts, screener, DB |
| `src/tv_mcp/mcp/tools/paper_trading.py` | NEW | 8 MCP tool handlers |
| `vercel/routers/paper_trading.py` | NEW | 8 REST endpoints |
| `tests/stdio/test_service_paper_trading.py` | NEW | Engine unit tests |
| `tests/stdio/test_paper_trading_tools.py` | NEW | MCP tool tests |
| `tests/http/test_paper_trading_routes.py` | NEW | Vercel endpoint tests |

## File Modification Summary

| File | Change |
|------|--------|
| `src/tv_mcp/core/settings.py` | Add 5 paper trading env vars |
| `src/tv_mcp/mcp/server.py` | Import + register 8 new tools |
| `src/tv_mcp/services/__init__.py` | Export `PaperTradingEngine` |
| `src/tv_mcp/mcp/tools/__init__.py` | Update docstring |
| `vercel/app.py` | Include paper trading router (commentable) |
| `vercel/schemas.py` | Add 5 request models |
| `vercel/routers/public.py` | Add endpoints to root listing |
| `pyproject.toml` | Add `aiosqlite`, `pytest-asyncio` |
| `tests/stdio/test_mcp_server.py` | Update tool count 7→16 |
| `tests/stdio/test_scaffold_imports.py` | Add paper trading import checks |
| `tests/http/test_scaffold_imports.py` | Add paper trading import checks |
| `tests/test_entrypoint_compatibility.py` | Add paper trading modules |
