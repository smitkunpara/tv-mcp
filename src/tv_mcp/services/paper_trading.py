"""
Paper Trading Engine for simulated order execution, position tracking,
alert management, and trade persistence.

This module is self-contained — all paper trading state and logic lives here.
Only closed trades are persisted to SQLite; open positions are in-memory.
"""

import asyncio
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from tv_scraper.streaming import Streamer
from tv_mcp.core.settings import settings
from tv_mcp.core.validators import ValidationError
from tv_mcp.transforms.time import IST_TZ


class Position:
    """In-memory representation of an open paper trading position."""

    def __init__(
        self,
        order_id: int,
        symbol: str,
        exchange: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        lot_size: int,
        trailing_sl_step_pct: Optional[float],
        opened_at_ist: str,
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.exchange = exchange
        self.side = side  # 'BUY' or 'SELL'
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.current_sl = stop_loss  # updated by trailing SL logic
        self.target = target
        self.lot_size = lot_size
        # trailing_sl_step_pct > 0 auto-enables trailing SL with that step percentage
        self.trailing_sl_step_pct: Optional[float] = trailing_sl_step_pct
        self.trailing_sl: bool = bool(trailing_sl_step_pct and trailing_sl_step_pct > 0)
        self.opened_at_ist = opened_at_ist
        self.screener_task: Optional[asyncio.Task] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize position to a plain dict for API responses."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "current_sl": self.current_sl,
            "target": self.target,
            "lot_size": self.lot_size,
            "trailing_sl": self.trailing_sl,
            "trailing_sl_step_pct": self.trailing_sl_step_pct,
            "opened_at": self.opened_at_ist,
            "status": "OPEN",
        }


def _get_project_root() -> str:
    """Return the project root directory (4 levels up from this file)."""
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )


class PaperTradingEngine:
    """Singleton paper trading engine managing orders, positions, alerts, and DB."""

    _instance: Optional["PaperTradingEngine"] = None

    def __new__(cls) -> "PaperTradingEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # ── Initialization ────────────────────────────────────────────

    def initialize(self) -> None:
        """Set up engine state. Safe to call multiple times (idempotent)."""
        if self._initialized:
            return
        self._initialized = True

        # Concurrency primitives (must be set before _load_state_from_db call)
        self._positions_lock = asyncio.Lock()
        self._alerts_lock = asyncio.Lock()
        self._alert_queue: asyncio.Queue = asyncio.Queue()

        # Position and alert containers
        self._positions: Dict[int, Position] = {}
        self._alerts: Dict[int, dict] = {}
        self._alert_ids: Set[int] = set()

        # Alert caching for recovery when AI is busy
        self._triggered_alerts_cache: List[Dict[str, Any]] = []
        self._cache_lock = asyncio.Lock()

        # Background tasks keyed by symbol
        self._screener_tasks: Dict[str, asyncio.Task] = {}

        # Database — init tables first, then load persisted state
        self._db_path: str = os.path.join(_get_project_root(), "paper_trades.db")
        self._init_db()
        self._load_state_from_db()  # populates _capital, _total_pnl, _next_order_id, etc.

    def _init_db(self) -> None:
        """Create the SQLite database, closed_trades and trading_config tables if needed."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS closed_trades (
                order_id    INTEGER PRIMARY KEY,
                symbol      TEXT    NOT NULL,
                exchange    TEXT    NOT NULL,
                side        TEXT    NOT NULL,
                entry_price REAL    NOT NULL,
                exit_price  REAL    NOT NULL,
                stop_loss   REAL    NOT NULL,
                target      REAL    NOT NULL,
                lot_size    INTEGER NOT NULL,
                opened_at   TEXT    NOT NULL,
                closed_at   TEXT    NOT NULL,
                close_reason TEXT   NOT NULL,
                pnl         REAL    NOT NULL,
                pnl_percentage REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trading_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    def _load_state_from_db(self) -> None:
        """Load persisted capital, PnL, counters, and config from DB.

        If the trading_config table is empty (first run or new DB), seeds it with
        defaults derived from environment variables / settings.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.execute("SELECT key, value FROM trading_config")
            cfg: dict = {row[0]: row[1] for row in cur.fetchall()}
        finally:
            conn.close()

        # Defaults derived from env-based settings (used when DB has no rows yet)
        defaults = {
            "initial_capital":      str(settings.PAPER_TRADING_CAPITAL),
            "current_capital":      str(settings.PAPER_TRADING_CAPITAL),
            "total_pnl":            "0.0",
            "next_order_id":        "1",
            "next_alert_id":        "1",
            "min_risk_reward_ratio": str(settings.MIN_RISK_REWARD_RATIO),
            "max_open_positions":   str(settings.MAX_OPEN_POSITIONS),
            "trailing_sl_step_pct": str(settings.TRAILING_SL_STEP_PCT),
        }

        is_empty = not cfg
        for key, default_val in defaults.items():
            if key not in cfg:
                cfg[key] = default_val

        if is_empty:
            # First-time setup: seed DB with defaults
            self._write_config_rows(cfg)

        self._initial_capital:      float = float(cfg["initial_capital"])
        self._capital:              float = float(cfg["current_capital"])
        self._total_pnl:            float = float(cfg["total_pnl"])
        self._next_order_id:        int   = int(cfg["next_order_id"])
        self._next_alert_id:        int   = int(cfg["next_alert_id"])
        self._min_risk_reward_ratio: float = float(cfg["min_risk_reward_ratio"])
        self._max_open_positions:   int   = int(cfg["max_open_positions"])
        self._trailing_sl_step_pct: float = float(cfg["trailing_sl_step_pct"])

    def _write_config_rows(self, data: dict) -> None:
        """Upsert arbitrary key/value pairs into trading_config."""
        conn = sqlite3.connect(self._db_path)
        try:
            for key, value in data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO trading_config (key, value) VALUES (?, ?)",
                    (key, str(value)),
                )
            conn.commit()
        finally:
            conn.close()

    def _save_state_to_db(self) -> None:
        """Persist runtime state (capital, PnL, counters) to the DB."""
        self._write_config_rows({
            "current_capital": str(self._capital),
            "total_pnl":       str(self._total_pnl),
            "next_order_id":   str(self._next_order_id),
            "next_alert_id":   str(self._next_alert_id),
        })

    async def _stream_price_async(self, exchange: str, symbol: str):
        """Async generator wrapper for sync Streamer.stream_realtime_price().
        
        Runs the blocking streaming generator in a thread pool executor
        to avoid blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Create streamer and get the sync generator
            def create_stream():
                streamer = Streamer(export_result=False)
                return streamer.stream_realtime_price(exchange, symbol)
            
            price_stream = await loop.run_in_executor(executor, create_stream)
            
            # Convert sync iteration to async
            while True:
                try:
                    update = await loop.run_in_executor(executor, lambda: next(price_stream))
                    yield update
                except StopIteration:
                    break
                except Exception:
                    break

    # ── Risk Management ───────────────────────────────────────────

    def _validate_risk_reward(
        self, entry: float, stop_loss: float, target: float
    ) -> None:
        """Raise ValidationError if risk:reward ratio is below the configured minimum."""
        risk = abs(entry - stop_loss)
        reward = abs(target - entry)
        if risk == 0:
            raise ValidationError("Stop loss cannot equal entry price.")
        ratio = round(reward / risk, 2)
        if ratio < self._min_risk_reward_ratio:
            raise ValidationError(
                f"Risk:Reward ratio {ratio} is below minimum "
                f"{self._min_risk_reward_ratio}. Adjust target or stop loss."
            )

    # ── Alert Caching ─────────────────────────────────────────────

    async def _push_alert_event(self, event: Dict[str, Any]) -> None:
        """Push an alert event to the queue AND cache it for later retrieval."""
        await self._alert_queue.put(event)
        async with self._cache_lock:
            self._triggered_alerts_cache.append(event)

    async def get_cached_alerts(self, clear_cache: bool = False) -> List[Dict[str, Any]]:
        """Retrieve cached alert events. Optionally clear the cache after retrieval."""
        async with self._cache_lock:
            cached = list(self._triggered_alerts_cache)
            if clear_cache:
                self._triggered_alerts_cache.clear()
            return cached

    async def clear_alert_cache(self) -> None:
        """Clear the triggered alerts cache."""
        async with self._cache_lock:
            self._triggered_alerts_cache.clear()

    # ── Order Placement ───────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        exchange: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        lot_size: int,
        trailing_sl_step_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place a paper trade order and start a background screener."""
        # Input validation
        symbol = symbol.strip().upper()
        exchange = exchange.strip().upper()
        if not symbol:
            raise ValidationError("Symbol is required.")
        if not exchange:
            raise ValidationError("Exchange is required.")
        if entry_price <= 0:
            raise ValidationError("Entry price must be greater than 0.")
        if stop_loss <= 0:
            raise ValidationError("Stop loss must be greater than 0.")
        if target <= 0:
            raise ValidationError("Target must be greater than 0.")
        if lot_size <= 0:
            raise ValidationError("Lot size must be greater than 0.")

        # Determine side
        if entry_price < target:
            side = "BUY"
            if stop_loss >= entry_price:
                raise ValidationError(
                    "For a BUY order, stop loss must be below entry price."
                )
        elif entry_price > target:
            side = "SELL"
            if stop_loss <= entry_price:
                raise ValidationError(
                    "For a SELL order, stop loss must be above entry price."
                )
        else:
            raise ValidationError("Target cannot equal entry price.")

        # Risk-reward validation
        self._validate_risk_reward(entry_price, stop_loss, target)

        async with self._positions_lock:
            # Max open positions check
            if len(self._positions) >= self._max_open_positions:
                raise ValidationError(
                    f"Maximum open positions ({self._max_open_positions}) reached. "
                    "Close an existing position first."
                )

            # Capital check
            required = entry_price * lot_size
            invested = sum(
                p.entry_price * p.lot_size for p in self._positions.values()
            )
            available = self._capital - invested
            if required > available:
                raise ValidationError(
                    f"Insufficient capital. Required: {required:.2f}, "
                    f"Available: {available:.2f}."
                )

            # Create position
            order_id = self._next_order_id
            self._next_order_id += 1
            opened_at = datetime.now(IST_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")

            pos = Position(
                order_id=order_id,
                symbol=symbol,
                exchange=exchange,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                lot_size=lot_size,
                trailing_sl_step_pct=trailing_sl_step_pct,
                opened_at_ist=opened_at,
            )

            # Start screener task
            task = asyncio.create_task(self._screener_loop(order_id))
            pos.screener_task = task
            self._positions[order_id] = pos
            # Track screener by symbol for price alert folding
            self._screener_tasks[symbol] = task

        # Persist updated order counter to DB
        self._save_state_to_db()

        return {
            "success": True,
            "order_id": order_id,
            "symbol": symbol,
            "exchange": exchange,
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "lot_size": lot_size,
            "trailing_sl": bool(trailing_sl_step_pct and trailing_sl_step_pct > 0),
            "trailing_sl_step_pct": trailing_sl_step_pct,
            "opened_at": opened_at,
            "message": (
                f"Order #{order_id} placed: {side} {lot_size} lots of "
                f"{exchange}:{symbol} @ {entry_price}. "
                f"SL: {stop_loss}, Target: {target}. "
                + (
                    f"Trailing SL enabled at {trailing_sl_step_pct}% step. "
                    if trailing_sl_step_pct and trailing_sl_step_pct > 0
                    else ""
                )
                + "Screener monitoring started automatically."
            ),
        }

    # ── Screener / Position Monitoring ────────────────────────────

    async def _screener_loop(self, order_id: int) -> None:
        """Background task: monitor one position for SL / target hits via streaming."""
        # Get position info
        async with self._positions_lock:
            pos = self._positions.get(order_id)
            if pos is None:
                return

        # Stream price updates
        try:
            async for update in self._stream_price_async(pos.exchange, pos.symbol):
                # Check if position still exists
                async with self._positions_lock:
                    pos = self._positions.get(order_id)
                    if pos is None:
                        return  # position was closed manually

                current_price = update.get("price")
                if current_price is None:
                    continue

                # ── Check SL / Target / Trailing SL ──
                hit: Optional[str] = None

                if pos.side == "BUY":
                    if current_price <= pos.current_sl:
                        hit = (
                            "SL_HIT"
                            if pos.current_sl == pos.stop_loss
                            else "TRAILING_SL_HIT"
                        )
                    elif current_price >= pos.target:
                        hit = "TARGET_HIT"
                    elif pos.trailing_sl and pos.trailing_sl_step_pct and current_price > pos.entry_price:
                        new_sl = round(
                            current_price * (1 - pos.trailing_sl_step_pct / 100), 2
                        )
                        if new_sl > pos.current_sl:
                            pos.current_sl = new_sl
                else:  # SELL
                    if current_price >= pos.current_sl:
                        hit = (
                            "SL_HIT"
                            if pos.current_sl == pos.stop_loss
                            else "TRAILING_SL_HIT"
                        )
                    elif current_price <= pos.target:
                        hit = "TARGET_HIT"
                    elif pos.trailing_sl and pos.trailing_sl_step_pct and current_price < pos.entry_price:
                        new_sl = round(
                            current_price * (1 + pos.trailing_sl_step_pct / 100), 2
                        )
                        if new_sl < pos.current_sl:
                            pos.current_sl = new_sl

                # ── Check price alerts for this symbol ──
                async with self._alerts_lock:
                    triggered: List[int] = []
                    for aid, alert in list(self._alerts.items()):
                        if (
                            alert["type"] == "price"
                            and alert["symbol"] == pos.symbol
                        ):
                            if (
                                alert["direction"] == "above"
                                and current_price >= alert["price"]
                            ) or (
                                alert["direction"] == "below"
                                and current_price <= alert["price"]
                            ):
                                triggered.append(aid)

                    for aid in triggered:
                        alert = self._alerts.pop(aid)
                        self._alert_ids.discard(aid)
                        await self._push_alert_event(
                            {
                                "source": "price_alert",
                                "alert_id": aid,
                                "symbol": alert["symbol"],
                                "price": alert["price"],
                                "direction": alert["direction"],
                                "current_price": current_price,
                                "message": (
                                    f"Price alert triggered: {alert['symbol']} "
                                    f"{'reached above' if alert['direction'] == 'above' else 'dropped below'} "
                                    f"{alert['price']} (current: {current_price})"
                                ),
                            }
                        )

                # ── Close position if SL / Target hit ──
                if hit:
                    await self._close_position_internal(order_id, current_price, hit)
                    return
        except Exception:
            pass  # Stream ended or error occurred

    async def _price_only_monitor(self, symbol: str, exchange: str) -> None:
        """Lightweight background task that only checks price alerts via streaming."""
        # Stream price updates
        try:
            async for update in self._stream_price_async(exchange, symbol):
                # Check if any price alerts remain for this symbol
                async with self._alerts_lock:
                    has_alerts = any(
                        a["type"] == "price" and a["symbol"] == symbol
                        for a in self._alerts.values()
                    )
                    if not has_alerts:
                        return  # no more alerts — stop task

                current_price = update.get("price")
                if current_price is None:
                    continue

                async with self._alerts_lock:
                    triggered: List[int] = []
                    for aid, alert in list(self._alerts.items()):
                        if alert["type"] == "price" and alert["symbol"] == symbol:
                            if (
                                alert["direction"] == "above"
                                and current_price >= alert["price"]
                            ) or (
                                alert["direction"] == "below"
                                and current_price <= alert["price"]
                            ):
                                triggered.append(aid)

                    for aid in triggered:
                        alert = self._alerts.pop(aid)
                        self._alert_ids.discard(aid)
                        await self._push_alert_event(
                            {
                                "source": "price_alert",
                                "alert_id": aid,
                                "symbol": alert["symbol"],
                                "price": alert["price"],
                                "direction": alert["direction"],
                                "current_price": current_price,
                                "message": (
                                    f"Price alert triggered: {alert['symbol']} "
                                    f"{'reached above' if alert['direction'] == 'above' else 'dropped below'} "
                                    f"{alert['price']} (current: {current_price})"
                                ),
                            }
                        )
        except Exception:
            pass  # Stream ended or error occurred

    # ── Close Position ────────────────────────────────────────────

    async def _close_position_internal(
        self, order_id: int, exit_price: float, reason: str
    ) -> None:
        """Close a position, persist to DB, update capital, push alert."""
        async with self._positions_lock:
            pos = self._positions.pop(order_id, None)
            if pos is None:
                return

            # Cancel screener if still running
            if pos.screener_task and not pos.screener_task.done():
                pos.screener_task.cancel()

            # Calculate PnL
            if pos.side == "BUY":
                pnl = (exit_price - pos.entry_price) * pos.lot_size
            else:
                pnl = (pos.entry_price - exit_price) * pos.lot_size

            invested = pos.entry_price * pos.lot_size
            pnl_pct = (pnl / invested) * 100 if invested > 0 else 0.0

            # Update capital (return invested + pnl)
            self._capital += invested + pnl
            self._total_pnl += pnl

        # Persist updated capital/PnL to DB
        self._save_state_to_db()

        # Persist to DB
        self._record_closed_trade(pos, exit_price, reason, pnl, pnl_pct)

        # Push event to alert queue and cache
        await self._push_alert_event(
            {
                "source": "trade_close",
                "order_id": order_id,
                "symbol": pos.symbol,
                "exchange": pos.exchange,
                "side": pos.side,
                "entry_price": pos.entry_price,
                "exit_price": exit_price,
                "close_reason": reason,
                "pnl": round(pnl, 2),
                "pnl_percentage": round(pnl_pct, 2),
                "message": (
                    f"Position #{order_id} closed ({reason}): "
                    f"{pos.side} {pos.lot_size} lots of {pos.exchange}:{pos.symbol} "
                    f"@ entry {pos.entry_price} → exit {exit_price}. "
                    f"PnL: {pnl:+.2f} ({pnl_pct:+.2f}%)"
                ),
            }
        )

    async def close_position(self, order_id: int) -> Dict[str, Any]:
        """Manually close a position at current market price."""
        async with self._positions_lock:
            pos = self._positions.get(order_id)
            if pos is None:
                return {
                    "success": False,
                    "message": f"No open position found with order_id {order_id}.",
                }
            symbol = pos.symbol
            exchange = pos.exchange

        # Fetch current price
        try:
            from tv_mcp.services.options import get_current_spot_price

            current_price = get_current_spot_price(symbol, exchange)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to fetch current price for {exchange}:{symbol}: {e}",
            }

        await self._close_position_internal(order_id, current_price, "MANUAL_CLOSE")
        return {
            "success": True,
            "message": f"Position #{order_id} closed manually at {current_price}.",
            "order_id": order_id,
            "exit_price": current_price,
        }

    def _record_closed_trade(
        self,
        pos: Position,
        exit_price: float,
        reason: str,
        pnl: float,
        pnl_pct: float,
    ) -> None:
        """Insert a closed trade record into SQLite."""
        closed_at = datetime.now(IST_TZ).strftime("%d-%m-%Y %I:%M:%S %p IST")
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO closed_trades
                    (order_id, symbol, exchange, side, entry_price, exit_price,
                     stop_loss, target, lot_size, opened_at, closed_at,
                     close_reason, pnl, pnl_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pos.order_id,
                    pos.symbol,
                    pos.exchange,
                    pos.side,
                    pos.entry_price,
                    exit_price,
                    pos.stop_loss,
                    pos.target,
                    pos.lot_size,
                    pos.opened_at_ist,
                    closed_at,
                    reason,
                    round(pnl, 2),
                    round(pnl_pct, 2),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # ── View Positions ────────────────────────────────────────────

    async def view_positions(
        self,
        filter_type: Optional[str] = None,
        order_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return open, closed, or all positions. Provide filter_type OR order_id, not both."""
        if filter_type is not None and order_id is not None:
            return {
                "success": False,
                "message": "Provide either filter_type or order_id, not both.",
            }

        # Default to 'all' if neither provided
        if filter_type is None and order_id is None:
            filter_type = "all"

        # Single order lookup
        if order_id is not None:
            async with self._positions_lock:
                pos = self._positions.get(order_id)
                if pos:
                    return {"success": True, "positions": [pos.to_dict()]}

            # Check closed trades
            row = self._query_closed_trade(order_id)
            if row:
                return {"success": True, "positions": [row]}
            return {
                "success": False,
                "message": f"No position found with order_id {order_id}.",
            }

        # Filter-based lookup
        result: List[Dict[str, Any]] = []

        if filter_type in ("open", "all"):
            async with self._positions_lock:
                result.extend(p.to_dict() for p in self._positions.values())

        if filter_type in ("closed", "all"):
            result.extend(self._query_all_closed_trades())

        return {"success": True, "positions": result, "count": len(result)}

    def _query_closed_trade(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single closed trade by order_id."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT * FROM closed_trades WHERE order_id = ?", (order_id,)
            )
            row = cur.fetchone()
            if row:
                d = dict(row)
                d["status"] = "CLOSED"
                return d
            return None
        finally:
            conn.close()

    def _query_all_closed_trades(self) -> List[Dict[str, Any]]:
        """Fetch all closed trades from DB."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT * FROM closed_trades ORDER BY order_id DESC"
            )
            rows = cur.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["status"] = "CLOSED"
                result.append(d)
            return result
        finally:
            conn.close()

    # ── Show Capital ──────────────────────────────────────────────

    async def show_capital(self) -> Dict[str, Any]:
        """Return current capital, PnL, and position summary."""
        async with self._positions_lock:
            invested = sum(
                p.entry_price * p.lot_size for p in self._positions.values()
            )
            open_count = len(self._positions)

        initial = self._initial_capital
        return {
            "success": True,
            "initial_capital": initial,
            "current_capital": round(self._capital, 2),
            "invested_in_open_positions": round(invested, 2),
            "available_fund": round(self._capital - invested, 2),
            "total_realized_pnl": round(self._total_pnl, 2),
            "total_pnl_percentage": (
                round((self._total_pnl / initial) * 100, 2) if initial > 0 else 0.0
            ),
            "open_positions_count": open_count,
        }

    # ── Alert System ──────────────────────────────────────────────

    async def set_alert(
        self,
        alert_type: str,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        price: Optional[float] = None,
        minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a price or time alert.

        For price alerts the trigger direction is auto-detected:
          - current_price < alert_price  →  triggers when price rises ABOVE alert_price
          - current_price > alert_price  →  triggers when price falls BELOW alert_price
        """
        async with self._alerts_lock:
            alert_id = self._next_alert_id
            self._next_alert_id += 1

            if alert_type == "price":
                if not symbol or not exchange or price is None:
                    raise ValidationError(
                        "Price alerts require symbol, exchange, and price."
                    )
                sym = symbol.strip().upper()
                exch = exchange.strip().upper()

                # Auto-detect direction from current market price
                try:
                    from tv_mcp.services.options import get_current_spot_price
                    current_price = get_current_spot_price(sym, exch)
                except Exception:
                    current_price = None

                if current_price is not None and current_price == float(price):
                    raise ValidationError(
                        f"Alert price ({price}) equals current price ({current_price}). "
                        "Set an alert price above or below the current price."
                    )

                if current_price is not None:
                    dir_ = "above" if current_price < float(price) else "below"
                else:
                    # Fallback: if we can't fetch current price, default to above
                    dir_ = "above"
                    current_price = None

                self._alerts[alert_id] = {
                    "type": "price",
                    "symbol": sym,
                    "exchange": exch,
                    "price": float(price),
                    "direction": dir_,
                    "alert_id": alert_id,
                }
                self._alert_ids.add(alert_id)

                # Spawn monitor if no screener running for this symbol
                existing_task = self._screener_tasks.get(sym)
                if existing_task is None or existing_task.done():
                    task = asyncio.create_task(
                        self._price_only_monitor(sym, exch)
                    )
                    self._screener_tasks[sym] = task

            elif alert_type == "time":
                if minutes is None or minutes <= 0:
                    raise ValidationError(
                        "Time alerts require a positive 'minutes' value."
                    )
                self._alerts[alert_id] = {
                    "type": "time",
                    "minutes": int(minutes),
                    "alert_id": alert_id,
                }
                self._alert_ids.add(alert_id)
                asyncio.create_task(self._time_alert_task(alert_id, int(minutes)))
            else:
                raise ValidationError(
                    f"Invalid alert type '{alert_type}'. Use 'price' or 'time'."
                )

        # Persist updated alert counter to DB
        self._save_state_to_db()

        result: Dict[str, Any] = {
            "success": True,
            "alert_id": alert_id,
            "type": alert_type,
            "message": f"Alert #{alert_id} ({alert_type}) set successfully.",
        }
        if alert_type == "price":
            result["alert_price"] = float(price)
            result["direction"] = dir_
            if current_price is not None:
                result["current_price"] = current_price
                result["message"] = (
                    f"Alert #{alert_id} set: will trigger when {sym} "
                    f"{'rises above' if dir_ == 'above' else 'drops below'} "
                    f"{float(price)} (current price: {current_price})."
                )
        return result

    async def _time_alert_task(self, alert_id: int, minutes: int) -> None:
        """Sleep for *minutes* then push a time-alert event."""
        await asyncio.sleep(minutes * 60)
        async with self._alerts_lock:
            if alert_id in self._alert_ids:
                self._alerts.pop(alert_id, None)
                self._alert_ids.discard(alert_id)
                await self._push_alert_event(
                    {
                        "source": "time_alert",
                        "alert_id": alert_id,
                        "minutes": minutes,
                        "message": (
                            f"Time alert triggered: {minutes}m timer expired. "
                            "Take appropriate action."
                        ),
                    }
                )

    async def view_available_alerts(self) -> Dict[str, Any]:
        """Return all active manual alerts and auto-trade alerts."""
        async with self._alerts_lock:
            manual_alerts = list(self._alerts.values())

        auto_alerts: List[Dict[str, Any]] = []
        async with self._positions_lock:
            for pos in self._positions.values():
                auto_alerts.append(
                    {
                        "type": "auto_trade",
                        "order_id": pos.order_id,
                        "symbol": pos.symbol,
                        "exchange": pos.exchange,
                        "stop_loss": pos.current_sl,
                        "target": pos.target,
                        "side": pos.side,
                    }
                )

        return {
            "success": True,
            "manual_alerts": manual_alerts,
            "trade_auto_alerts": auto_alerts,
            "total_count": len(manual_alerts) + len(auto_alerts),
        }

    async def remove_alert(self, alert_id: int) -> Dict[str, Any]:
        """Remove a manual alert by ID."""
        async with self._alerts_lock:
            if alert_id not in self._alert_ids:
                return {
                    "success": False,
                    "message": f"Alert #{alert_id} not found.",
                }
            removed = self._alerts.pop(alert_id)
            self._alert_ids.discard(alert_id)

        return {
            "success": True,
            "message": f"Alert #{alert_id} removed.",
            "removed_alert": removed,
        }

    # ── Alert Manager ─────────────────────────────────────────────

    async def alert_manager(self) -> Dict[str, Any]:
        """Block until an alert triggers, then return events with re-call instruction.
        
        If there are cached alerts from previous triggers, return them immediately.
        This prevents losing alerts when the AI is busy with other tasks.
        """
        # First, check if there are cached alerts from previous triggers
        cached_alerts = await self.get_cached_alerts(clear_cache=True)
        if cached_alerts:
            remaining_alerts = len(self._alerts)
            remaining_positions = len(self._positions)
            has_more = remaining_alerts > 0 or remaining_positions > 0

            response: Dict[str, Any] = {
                "success": True,
                "triggered_events": cached_alerts,
                "remaining_manual_alerts": remaining_alerts,
                "open_positions": remaining_positions,
                "from_cache": True,
            }

            if has_more:
                response["instruction"] = (
                    "IMPORTANT: There are still active monitors running "
                    f"({remaining_positions} open positions, "
                    f"{remaining_alerts} manual alerts). "
                    "You MUST call alert_manager again to receive further updates. "
                    "Do NOT stop monitoring."
                )
            else:
                response["instruction"] = (
                    "All monitors completed. No further action needed."
                )

            return response

        # Check if there is anything to monitor
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
                "message": (
                    "No alerts set and no open positions. "
                    "Place a trade or set an alert first."
                ),
                "active_threads": 0,
            }

        # Wait for an event (configurable timeout via ALERT_MANAGER_TIMEOUT_SECONDS)
        timeout = settings.ALERT_MANAGER_TIMEOUT_SECONDS
        try:
            event = await asyncio.wait_for(self._alert_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return {
                "success": True,
                "message": (
                    f"No alerts triggered in {timeout} seconds. "
                    "Call alert_manager again to continue monitoring."
                ),
                "active_alerts": len(self._alerts),
                "open_positions": len(self._positions),
            }

        # Drain queue for any additional events
        events: List[Dict[str, Any]] = [event]
        while not self._alert_queue.empty():
            try:
                events.append(self._alert_queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Also clear the cache since we're returning events from the queue
        await self.clear_alert_cache()

        remaining_alerts = len(self._alerts)
        remaining_positions = len(self._positions)
        has_more = remaining_alerts > 0 or remaining_positions > 0

        response: Dict[str, Any] = {
            "success": True,
            "triggered_events": events,
            "remaining_manual_alerts": remaining_alerts,
            "open_positions": remaining_positions,
        }

        if has_more:
            response["instruction"] = (
                "IMPORTANT: There are still active monitors running "
                f"({remaining_positions} open positions, "
                f"{remaining_alerts} manual alerts). "
                "You MUST call alert_manager again to receive further updates. "
                "Do NOT stop monitoring."
            )
        else:
            response["instruction"] = (
                "All monitors completed. No further action needed."
            )

        return response
