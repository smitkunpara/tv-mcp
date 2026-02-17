"""
Unit tests for the Paper Trading Engine.

Screener loops use WebSocket streaming for real-time price monitoring.
Tests mock get_current_spot_price (used only in manual close_position calls).
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
    # Override DB path to temp dir
    engine._initialized = False
    engine.initialize()
    engine._db_path = str(tmp_path / "test_trades.db")
    engine._init_db()
    yield engine
    PaperTradingEngine._instance = None


# ── Position model tests ─────────────────────────────────────────


class TestPositionModel:
    def test_to_dict(self):
        pos = Position(
            order_id=1, symbol="NIFTY", exchange="NSE", side="BUY",
            entry_price=23000.0, stop_loss=22800.0, target=23500.0,
            lot_size=1, trailing_sl=False, opened_at_ist="17-02-2026 10:00:00 AM IST",
        )
        d = pos.to_dict()
        assert d["order_id"] == 1
        assert d["symbol"] == "NIFTY"
        assert d["status"] == "OPEN"
        assert d["side"] == "BUY"
        assert d["trailing_sl"] is False


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
        assert result["open_positions_count"] == 0
        assert result["total_realized_pnl"] == 0.0


# ── Place Order tests ────────────────────────────────────────────


class TestPlaceOrder:
    @pytest.mark.asyncio
    async def test_place_order_buy_success(self, fresh_engine):
        """BUY: entry < target, sl < entry."""
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            result = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        assert result["success"] is True
        assert result["side"] == "BUY"
        assert result["order_id"] == 1

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
        from tv_mcp.core.settings import settings
        original = settings.MAX_OPEN_POSITIONS
        settings.MAX_OPEN_POSITIONS = 1
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
            settings.MAX_OPEN_POSITIONS = original

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


# ── Close Position tests ─────────────────────────────────────────


class TestClosePosition:
    @pytest.mark.asyncio
    async def test_close_position_success(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        with patch(SPOT_PRICE_PATH, return_value=23200.0):
            result = await fresh_engine.close_position(order["order_id"])
        assert result["success"] is True
        assert result["exit_price"] == 23200.0

    @pytest.mark.asyncio
    async def test_close_position_not_found(self, fresh_engine):
        result = await fresh_engine.close_position(order_id=999)
        assert result["success"] is False
        assert "found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_close_position_records_to_db(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=23000.0):
            order = await fresh_engine.place_order(
                symbol="NIFTY", exchange="NSE",
                entry_price=23000, stop_loss=22700, target=23600,
                lot_size=1,
            )
        with patch(SPOT_PRICE_PATH, return_value=23200.0):
            await fresh_engine.close_position(order["order_id"])

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
        # Close with profit
        with patch(SPOT_PRICE_PATH, return_value=150.0):
            await fresh_engine.close_position(order["order_id"])

        # PnL = (150-100) * 10 = 500, invested = 100 * 10 = 1000
        # Implementation: _capital += invested + pnl (capital not deducted on open)
        invested = 100 * 10
        pnl = (150 - 100) * 10
        assert fresh_engine._capital == initial + invested + pnl
        assert fresh_engine._total_pnl == 500


# ── View Positions tests ─────────────────────────────────────────


class TestViewPositions:
    @pytest.mark.asyncio
    async def test_view_open_positions(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=1,
            )
        result = await fresh_engine.view_positions(filter_type="open")
        assert result["success"] is True
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
        with patch(SPOT_PRICE_PATH, return_value=150.0):
            await fresh_engine.close_position(order["order_id"])
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
        with patch(SPOT_PRICE_PATH, return_value=150.0):
            await fresh_engine.close_position(o1["order_id"])
        result = await fresh_engine.view_positions(filter_type="all")
        assert result["success"] is True
        assert result["count"] == 2  # 1 open + 1 closed


# ── Show Capital tests ───────────────────────────────────────────


class TestShowCapital:
    @pytest.mark.asyncio
    async def test_show_capital_after_order(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=5,
            )
        result = await fresh_engine.show_capital()
        assert result["invested_in_open_positions"] == 500.0
        assert result["open_positions_count"] == 1

    @pytest.mark.asyncio
    async def test_show_capital_pnl_percentage(self, fresh_engine):
        with patch(SPOT_PRICE_PATH, return_value=100.0):
            order = await fresh_engine.place_order(
                symbol="TEST", exchange="NSE",
                entry_price=100, stop_loss=90, target=200,
                lot_size=10,
            )
        with patch(SPOT_PRICE_PATH, return_value=200.0):
            await fresh_engine.close_position(order["order_id"])

        result = await fresh_engine.show_capital()
        assert result["total_realized_pnl"] == 1000.0
        assert result["total_pnl_percentage"] > 0


# ── Alert tests ──────────────────────────────────────────────────


class TestAlerts:
    @pytest.mark.asyncio
    async def test_set_price_alert(self, fresh_engine):
        result = await fresh_engine.set_alert(
            alert_type="price", symbol="NIFTY", exchange="NSE",
            price=23500, direction="above",
        )
        assert result["success"] is True
        assert result["alert_id"] == 1
        assert result["type"] == "price"

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
        await fresh_engine.set_alert(
            alert_type="price", symbol="NIFTY", exchange="NSE",
            price=23500, direction="above",
        )
        result = await fresh_engine.view_available_alerts()
        assert result["success"] is True
        assert len(result["manual_alerts"]) == 1
        assert result["total_count"] == 1

    @pytest.mark.asyncio
    async def test_remove_alert_success(self, fresh_engine):
        alert = await fresh_engine.set_alert(
            alert_type="price", symbol="NIFTY", exchange="NSE",
            price=23500, direction="above",
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
        await fresh_engine.set_alert(
            alert_type="price", symbol="X", exchange="NSE",
            price=100, direction="above",
        )
        assert 1 in fresh_engine._alert_ids

    @pytest.mark.asyncio
    async def test_price_alert_direction_validation(self, fresh_engine):
        with pytest.raises(ValidationError, match="above.*below"):
            await fresh_engine.set_alert(
                alert_type="price", symbol="X", exchange="NSE",
                price=100, direction="sideways",
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
            99, "X", "NSE", "BUY", 100, 90, 200, 1, False, "test"
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
