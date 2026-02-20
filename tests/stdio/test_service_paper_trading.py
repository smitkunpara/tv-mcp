"""
Unit tests for the Paper Trading Engine.

Screener loops use WebSocket streaming for real-time price monitoring.
Tests mock get_current_spot_price (used for place_order, close_position,
and set_alert spot-price lookups).
close_position now fetches the current price via get_current_spot_price
and closes immediately, returning PnL details to the caller.
"""

import asyncio
import os
import sqlite3
from unittest.mock import patch, MagicMock

import pytest

from src.tv_mcp.services.paper_trading import PaperTradingEngine, Position, _get_project_root
from src.tv_mcp.core.validators import ValidationError

# The function is imported locally inside engine methods from this path
SPOT_PRICE_PATH = "tv_mcp.services.options.get_current_spot_price"


@pytest.fixture(autouse=True)
def fresh_engine(tmp_path):
    """Reset the singleton and use a temp DB for every test."""
    PaperTradingEngine._instance = None
    engine = PaperTradingEngine()
    # Override DB path to temp dir BEFORE state is loaded
    engine._initialized = False
    engine.initialize()
    engine._db_path = str(tmp_path / "test_trades.db")
    engine._init_db()
    engine._load_state_from_db()  # reload counters from empty temp DB → starts at 1
    yield engine
    PaperTradingEngine._instance = None


# ── Position model tests ─────────────────────────────────────────


class TestPositionModel:
    def test_to_dict_default_pending(self):
        pos = Position(
            order_id=1, symbol="NIFTY", exchange="NSE", side="BUY",
            entry_price=23000.0, stop_loss=22800.0, target=23500.0,
            lot_size=1, trailing_sl_step_pct=None, opened_at_ist="17-02-2026 10:00:00 AM IST",
        )
        d = pos.to_dict()
        assert d["order_id"] == 1
        assert d["symbol"] == "NIFTY"
        assert d["status"] == "PENDING"  # default is PENDING
        assert d["side"] == "BUY"
        assert d["trailing_sl"] is False
        assert d["trailing_sl_step_pct"] is None
        assert "placed_at" in d
        assert "filled_at" not in d  # not filled yet

    def test_to_dict_open_with_filled_at(self):
        pos = Position(
            order_id=2, symbol="NIFTY", exchange="NSE", side="BUY",
            entry_price=23000.0, stop_loss=22800.0, target=23500.0,
            lot_size=1, trailing_sl_step_pct=None, opened_at_ist="17-02-2026 10:00:00 AM IST",
        )
        pos.status = "OPEN"
        pos.filled_at_ist = "17-02-2026 10:05:00 AM IST"
        d = pos.to_dict()
        assert d["status"] == "OPEN"
        assert d["filled_at"] == "17-02-2026 10:05:00 AM IST"

    def test_to_dict_with_trailing(self):
        pos = Position(
            order_id=3, symbol="NIFTY", exchange="NSE", side="BUY",
            entry_price=23000.0, stop_loss=22800.0, target=23500.0,
            lot_size=1, trailing_sl_step_pct=0.5, opened_at_ist="17-02-2026 10:00:00 AM IST",
        )
        d = pos.to_dict()
        assert d["trailing_sl"] is True
        assert d["trailing_sl_step_pct"] == 0.5


class TestProjectRoot:
    def test_get_project_root(self):
        root = _get_project_root()
        assert os.path.isdir(root)
        assert os.path.exists(os.path.join(root, "pyproject.toml"))


# ── DB initialization tests ──────────────────────────────────────


class TestDBInitialization:
    def test_db_file_created(self, fresh_engine):
        assert os.path.exists(fresh_engine._db_path)

    def test_closed_trades_table_exists(self, fresh_engine):
        conn = sqlite3.connect(fresh_engine._db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='closed_trades'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_table_columns(self, fresh_engine):
        conn = sqlite3.connect(fresh_engine._db_path)
        cur = conn.execute("PRAGMA table_info(closed_trades)")
        cols = {row[1] for row in cur.fetchall()}
        expected = {
            "order_id", "symbol", "exchange", "side", "entry_price",
            "exit_price", "stop_loss", "target", "lot_size", "opened_at",
            "closed_at", "close_reason", "pnl", "pnl_percentage",
        }
        assert expected.issubset(cols)
        conn.close()


# ── Capital defaults ─────────────────────────────────────────────


class TestCapitalDefaults:
    @pytest.mark.asyncio
    async def test_initial_capital(self, fresh_engine):
        result = await fresh_engine.show_capital()
        assert result["success"] is True
        assert result["initial_capital"] > 0
        assert result["current_capital"] == result["initial_capital"]
        assert result["pending_orders_count"] == 0
        assert result["open_positions_count"] == 0
        assert result["total_realized_pnl"] == 0.0


# ── Place Order tests ────────────────────────────────────────────


class TestPlaceOrder:
    @pytest.mark.asyncio
    async def test_place_order_buy_success(self, fresh_engine):
        """BUY: entry < target, sl < entry. Starts as PENDING."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            result = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        assert result["success"] is True
        assert result["side"] == "BUY"
        assert result["order_id"] == 1
        assert result["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_place_order_sell_success(self, fresh_engine):
        """SELL: entry > target, sl > entry."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            result = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=23300, target=22400,
                lot_size=1,
            )
        assert result["success"] is True
        assert result["side"] == "SELL"

    @pytest.mark.asyncio
    async def test_place_order_risk_reward_fail(self, fresh_engine):
        """Risk:Reward below minimum should raise ValidationError."""
        with pytest.raises(ValidationError, match="Risk:Reward"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22900, target=23050,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_invalid_sl_buy(self, fresh_engine):
        """BUY with SL >= entry should fail."""
        with pytest.raises(ValidationError, match="stop loss must be below"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=23100, target=24000,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_invalid_sl_sell(self, fresh_engine):
        """SELL with SL <= entry should fail."""
        with pytest.raises(ValidationError, match="stop loss must be above"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22900, target=22000,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_zero_price(self, fresh_engine):
        with pytest.raises(ValidationError, match="greater than 0"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=0, stop_loss=100, target=200,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_empty_symbol(self, fresh_engine):
        with pytest.raises(ValidationError, match="Symbol is required"):
            await fresh_engine.place_order(
                symbol="", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_target_equals_entry(self, fresh_engine):
        with pytest.raises(ValidationError, match="Target cannot equal"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22800, target=23000,
                lot_size=1,
            )

    @pytest.mark.asyncio
    async def test_place_order_insufficient_capital(self, fresh_engine):
        """Should fail if required capital exceeds available."""
        fresh_engine._capital = 100  # set very low
        with pytest.raises(ValidationError, match="Insufficient capital"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=10,
            )

    @pytest.mark.asyncio
    async def test_place_order_max_positions(self, fresh_engine):
        """Should fail when max open positions exceeded."""
        original = fresh_engine._max_open_positions
        fresh_engine._max_open_positions = 1
        try:
            with patch(SPOT_PRICE_PATH, return_value=100.0):
                await fresh_engine.place_order(
                    symbol="A", exchange="NSE",
                    entry_price=100, stop_loss=90, target=200,
                    lot_size=1,
                )
                with pytest.raises(ValidationError, match="Maximum open positions"):
                    await fresh_engine.place_order(
                        symbol="B", exchange="NSE",
                        entry_price=100, stop_loss=90, target=200,
                        lot_size=1,
                    )
        finally:
            fresh_engine._max_open_positions = original

    @pytest.mark.asyncio
    async def test_order_id_increments(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            r1 = await fresh_engine.place_order(
                symbol="A", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
            r2 = await fresh_engine.place_order(
                symbol="B", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        assert r2["order_id"] == r1["order_id"] + 1

    @pytest.mark.asyncio
    async def test_market_order_success(self, fresh_engine):
        """MARKET order fills immediately at current price."""
        with patch(SPOT_PRICE_PATH, return_value=25000.0):
            result = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                stop_loss=24500, target=26000,
                lot_size=1,
                order_type="MARKET",
            )
        assert result["success"] is True
        assert result["order_type"] == "MARKET"
        assert result["status"] == "OPEN"
        assert result["entry_price"] == 25000.0
        assert result["side"] == "BUY"
        assert "filled_at" in result

    @pytest.mark.asyncio
    async def test_market_order_sell(self, fresh_engine):
        """MARKET SELL: target < entry (fetched price)."""
        with patch(SPOT_PRICE_PATH, return_value=25000.0):
            result = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                stop_loss=25300, target=24000,
                lot_size=1,
                order_type="MARKET",
            )
        assert result["success"] is True
        assert result["side"] == "SELL"
        assert result["status"] == "OPEN"

    @pytest.mark.asyncio
    async def test_market_order_price_fetch_failure(self, fresh_engine):
        """MARKET order fails gracefully if current price cannot be fetched."""
        with patch(SPOT_PRICE_PATH, side_effect=Exception("unavailable")):
            with pytest.raises(ValidationError, match="failed to fetch"):
                await fresh_engine.place_order(
                    symbol="NIFTY", exchange="NSE",
                    stop_loss=24500, target=26000,
                    lot_size=1,
                    order_type="MARKET",
                )

    @pytest.mark.asyncio
    async def test_limit_order_requires_entry_price(self, fresh_engine):
        """LIMIT order without entry_price should fail."""
        with pytest.raises(ValidationError, match="entry_price is required"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                stop_loss=22700, target=23600,
                lot_size=1,
                order_type="LIMIT",
            )

    @pytest.mark.asyncio
    async def test_invalid_order_type(self, fresh_engine):
        """Invalid order_type should fail."""
        with pytest.raises(ValidationError, match="Invalid order_type"):
            await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
                order_type="FOK",
            )


# ── Close Position tests ─────────────────────────────────────────


class TestClosePosition:
    @pytest.mark.asyncio
    async def test_cancel_pending_position(self, fresh_engine):
        """Closing a PENDING position cancels it without PnL."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        result = await fresh_engine.close_position(order["order_id"])
        assert result["success"] is True
        assert result["source"] == "order_cancelled"
        assert "never triggered" in result["message"].lower()
        async with fresh_engine._positions_lock:
            assert order["order_id"] not in fresh_engine._positions

    @pytest.mark.asyncio
    async def test_close_open_position(self, fresh_engine):
        """Closing an OPEN position fetches price and records PnL."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        # Transition to OPEN
        async with fresh_engine._positions_lock:
            fresh_engine._positions[order["order_id"]].status = "OPEN"
        with patch(SPOT_PRICE_PATH, return_value=23200.0):
            result = await fresh_engine.close_position(order["order_id"])
        assert result["success"] is True
        assert result["exit_price"] == 23200.0
        assert result["close_reason"] == "MANUAL_CLOSE"
        assert result["pnl"] == 200.0
        async with fresh_engine._positions_lock:
            assert order["order_id"] not in fresh_engine._positions

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, fresh_engine):
        result = await fresh_engine.close_position(order_id=999)
        assert result["success"] is False
        assert "found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_close_open_position_price_fetch_failure(self, fresh_engine):
        """If get_current_spot_price fails for an OPEN position, it stays open."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        async with fresh_engine._positions_lock:
            fresh_engine._positions[order["order_id"]].status = "OPEN"
        with patch(SPOT_PRICE_PATH, side_effect=Exception("network error")):
            result = await fresh_engine.close_position(order["order_id"])
        assert result["success"] is False
        assert "failed" in result["message"].lower()
        async with fresh_engine._positions_lock:
            assert order["order_id"] in fresh_engine._positions

    @pytest.mark.asyncio
    async def test_close_position_records_to_db(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        # Simulate screener closing at live price
        await fresh_engine._close_position_internal(order["order_id"], 23200.0, "MANUAL_CLOSE")

        # Verify DB
        conn = sqlite3.connect(fresh_engine._db_path)
        cur = conn.execute("SELECT * FROM closed_trades WHERE order_id = ?", (order["order_id"],))
        row = cur.fetchone()
        conn.close()
        assert row is not None

    @pytest.mark.asyncio
    async def test_close_position_updates_capital(self, fresh_engine):
        initial = fresh_engine._capital
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=10,
            )
        # Simulate screener closing at live price
        await fresh_engine._close_position_internal(order["order_id"], 150.0, "MANUAL_CLOSE")

        # PnL = (150-100) * 10 = 500
        # Capital is never deducted on open; only PnL is added on close.
        pnl = (150 - 100) * 10
        assert fresh_engine._capital == initial + pnl
        assert fresh_engine._total_pnl == 500


# ── View Positions tests ─────────────────────────────────────────


class TestViewPositions:
    @pytest.mark.asyncio
    async def test_view_pending_positions(self, fresh_engine):
        """Newly placed order appears as PENDING."""
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        result = await fresh_engine.view_positions(filter_type="pending")
        assert result["success"] is True
        assert len(result["positions"]) == 1
        assert result["positions"][0]["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_view_open_positions(self, fresh_engine):
        """OPEN filter only returns positions that have been filled."""
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        # Still PENDING — should NOT show under 'open'
        result = await fresh_engine.view_positions(filter_type="open")
        assert result["success"] is True
        assert len(result["positions"]) == 0
        # Transition to OPEN
        async with fresh_engine._positions_lock:
            fresh_engine._positions[order["order_id"]].status = "OPEN"
        result = await fresh_engine.view_positions(filter_type="open")
        assert len(result["positions"]) == 1
        assert result["positions"][0]["status"] == "OPEN"

    @pytest.mark.asyncio
    async def test_view_closed_positions(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        await fresh_engine._close_position_internal(order["order_id"], 150.0, "MANUAL_CLOSE")
        result = await fresh_engine.view_positions(filter_type="closed")
        assert result["success"] is True
        assert len(result["positions"]) == 1
        assert result["positions"][0]["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_view_positions_by_order_id(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        result = await fresh_engine.view_positions(order_id=order["order_id"])
        assert result["success"] is True
        assert result["positions"][0]["order_id"] == order["order_id"]

    @pytest.mark.asyncio
    async def test_view_positions_both_params_error(self, fresh_engine):
        result = await fresh_engine.view_positions(filter_type="open", order_id=1)
        assert result["success"] is False
        assert "not both" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_view_positions_not_found(self, fresh_engine):
        result = await fresh_engine.view_positions(order_id=999)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_view_all_positions(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            o1 = await fresh_engine.place_order(
                symbol="A", exchange="NSE",
                entry_price=100, stop_loss=90, target=200, lot_size=1,
            )
            o2 = await fresh_engine.place_order(
                symbol="B", exchange="NSE",
                entry_price=100, stop_loss=90, target=200, lot_size=1,
            )
        await fresh_engine._close_position_internal(o1["order_id"], 150.0, "MANUAL_CLOSE")
        result = await fresh_engine.view_positions(filter_type="all")
        assert result["success"] is True
        assert result["count"] == 2  # 1 pending + 1 closed


# ── Show Capital tests ───────────────────────────────────────────


class TestShowCapital:
    @pytest.mark.asyncio
    async def test_show_capital_after_pending_order(self, fresh_engine):
        """Pending orders reserve capital but are not 'invested'."""
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=5,
            )
        result = await fresh_engine.show_capital()
        assert result["reserved_for_pending_orders"] == 500.0
        assert result["invested_in_open_positions"] == 0.0
        assert result["pending_orders_count"] == 1
        assert result["open_positions_count"] == 0

    @pytest.mark.asyncio
    async def test_show_capital_pnl_percentage(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=10,
            )
        await fresh_engine._close_position_internal(order["order_id"], 200.0, "MANUAL_CLOSE")

        result = await fresh_engine.show_capital()
        assert result["total_realized_pnl"] == 1000.0
        assert result["total_pnl_percentage"] > 0


# ── Alert tests ──────────────────────────────────────────────────


class TestAlerts:
    @pytest.mark.asyncio
    async def test_set_price_alert(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            result = await fresh_engine.set_alert(
                alert_type="price", symbol="NIFTY", exchange="NSE",
                price=23500,
            )
        assert result["success"] is True
        assert result["alert_id"] == 1
        assert result["type"] == "price"
        assert result["direction"] == "above"  # 23000 < 23500

    @pytest.mark.asyncio
    async def test_set_time_alert(self, fresh_engine):
        result = await fresh_engine.set_alert(alert_type="time", minutes=5)
        assert result["success"] is True
        assert result["type"] == "time"

    @pytest.mark.asyncio
    async def test_set_alert_invalid_type(self, fresh_engine):
        with pytest.raises(ValidationError, match="Invalid alert type"):
            await fresh_engine.set_alert(alert_type="invalid")

    @pytest.mark.asyncio
    async def test_set_price_alert_missing_symbol(self, fresh_engine):
        with pytest.raises(ValidationError, match="require symbol"):
            await fresh_engine.set_alert(alert_type="price", price=100)

    @pytest.mark.asyncio
    async def test_set_time_alert_invalid_minutes(self, fresh_engine):
        with pytest.raises(ValidationError, match="positive"):
            await fresh_engine.set_alert(alert_type="time", minutes=0)

    @pytest.mark.asyncio
    async def test_view_available_alerts(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            await fresh_engine.set_alert(
                alert_type="price", symbol="NIFTY", exchange="NSE",
                price=23500,
            )
        result = await fresh_engine.view_available_alerts()
        assert result["success"] is True
        assert len(result["manual_alerts"]) == 1
        assert result["total_count"] == 1

    @pytest.mark.asyncio
    async def test_remove_alert_success(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            alert = await fresh_engine.set_alert(
                alert_type="price", symbol="NIFTY", exchange="NSE",
                price=23500,
            )
        result = await fresh_engine.remove_alert(alert["alert_id"])
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_remove_alert_not_found(self, fresh_engine):
        result = await fresh_engine.remove_alert(alert_id=999)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_alert_id_uses_set_for_fast_lookup(self, fresh_engine):
        """Verify alert IDs are tracked in a set."""
        assert isinstance(fresh_engine._alert_ids, set)
        with patch(SPOT_PRICE_PATH, return_value=80.0):
            await fresh_engine.set_alert(
                alert_type="price", symbol="X", exchange="NSE",
                price=100,
            )
        assert 1 in fresh_engine._alert_ids

    @pytest.mark.asyncio
    async def test_price_alert_auto_direction_above(self, fresh_engine):
        """When current < alert price, direction should be auto-set to 'above'."""
        with patch(SPOT_PRICE_PATH, return_value=80.0):
            result = await fresh_engine.set_alert(
                alert_type="price", symbol="X", exchange="NSE",
                price=100,
            )
        assert result["direction"] == "above"

    @pytest.mark.asyncio
    async def test_price_alert_auto_direction_below(self, fresh_engine):
        """When current > alert price, direction should be auto-set to 'below'."""
        with patch(SPOT_PRICE_PATH, return_value=120.0):
            result = await fresh_engine.set_alert(
                alert_type="price", symbol="X", exchange="NSE",
                price=100,
            )
        assert result["direction"] == "below"

    @pytest.mark.asyncio
    async def test_price_alert_equal_to_current_raises(self, fresh_engine):
        """Alert price equal to current price should raise ValidationError."""
        with pytest.raises(ValidationError, match="equals current price"):
            with patch(SPOT_PRICE_PATH, return_value=100.0):
                await fresh_engine.set_alert(
                    alert_type="price", symbol="X", exchange="NSE",
                    price=100,
                )


# ── Alert Manager tests ─────────────────────────────────────────


class TestAlertManager:
    @pytest.mark.asyncio
    async def test_alert_manager_no_alerts(self, fresh_engine):
        result = await fresh_engine.alert_manager()
        assert result["success"] is True
        assert "no alerts" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_alert_manager_receives_event(self, fresh_engine):
        """Put an event in the queue and verify alert_manager returns it."""
        await fresh_engine._alert_queue.put({
            "source": "test", "message": "test event"
        })
        # Add a fake position so has_work is True
        fresh_engine._positions[99] = Position(
            99, "X", "NSE", "BUY", 100, 90, 200, 1, None, "test"
        )
        result = await fresh_engine.alert_manager()
        assert result["success"] is True
        assert len(result["triggered_events"]) == 1
        assert result["triggered_events"][0]["source"] == "test"


# ── Risk Reward Validation tests ─────────────────────────────────


class TestRiskReward:
    def test_valid_ratio(self, fresh_engine):
        # Should not raise: risk=300, reward=600, ratio=2.0 >= 1.5
        fresh_engine._validate_risk_reward(23000, 22700, 23600)

    def test_invalid_ratio(self, fresh_engine):
        with pytest.raises(ValidationError, match="Risk:Reward"):
            # risk=100, reward=50, ratio=0.5 < 1.5
            fresh_engine._validate_risk_reward(23000, 22900, 23050)

    def test_zero_risk(self, fresh_engine):
        with pytest.raises(ValidationError, match="cannot equal"):
            fresh_engine._validate_risk_reward(23000, 23000, 23500)
