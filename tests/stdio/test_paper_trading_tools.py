"""
Tests for paper trading MCP tool handlers.

Mocks the PaperTradingEngine to test serialization and error handling.
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.tv_mcp.core.validators import ValidationError


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# We patch the engine singleton at the module level so tool handlers use the mock.
ENGINE_PATH = "src.tv_mcp.mcp.tools.paper_trading._engine"


class TestPlaceOrderTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import place_order
        mock_engine = MagicMock()
        mock_engine.place_order = AsyncMock(return_value={"success": True, "order_id": 1})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(place_order(
                symbol="NIFTY", exchange="NSE", entry_price=23000,
                stop_loss=22700, target=23600, lot_size=1,
            ))
        assert "success" in result.lower()

    def test_validation_error(self):
        from src.tv_mcp.mcp.tools.paper_trading import place_order
        mock_engine = MagicMock()
        mock_engine.place_order = AsyncMock(side_effect=ValidationError("bad input"))
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(place_order(
                symbol="", exchange="NSE", entry_price=0,
                stop_loss=0, target=0, lot_size=0,
            ))
        assert "bad input" in result.lower()


class TestClosePositionTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import close_position
        mock_engine = MagicMock()
        mock_engine.close_position = AsyncMock(return_value={"success": True})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(close_position(order_id=1))
        assert "success" in result.lower()


class TestViewPositionsTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import view_positions
        mock_engine = MagicMock()
        mock_engine.view_positions = AsyncMock(return_value={"success": True, "positions": []})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(view_positions(filter_type="all"))
        assert "success" in result.lower()


class TestShowCapitalTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import show_capital
        mock_engine = MagicMock()
        mock_engine.show_capital = AsyncMock(return_value={"success": True, "capital": 100000})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(show_capital())
        assert "success" in result.lower()


class TestSetAlertTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import set_alert
        mock_engine = MagicMock()
        mock_engine.set_alert = AsyncMock(return_value={"success": True, "alert_id": 1})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(set_alert(alert_type="price", symbol="NIFTY", exchange="NSE", price=23000, direction="above"))
        assert "success" in result.lower()

    def test_validation_error(self):
        from src.tv_mcp.mcp.tools.paper_trading import set_alert
        mock_engine = MagicMock()
        mock_engine.set_alert = AsyncMock(side_effect=ValidationError("invalid"))
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(set_alert(alert_type="bad"))
        assert "invalid" in result.lower()


class TestAlertManagerTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import alert_manager
        mock_engine = MagicMock()
        mock_engine.alert_manager = AsyncMock(return_value={"success": True, "message": "No alerts"})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(alert_manager())
        assert "success" in result.lower()


class TestViewAvailableAlertsTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import view_available_alerts
        mock_engine = MagicMock()
        mock_engine.view_available_alerts = AsyncMock(return_value={"success": True, "manual_alerts": []})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(view_available_alerts())
        assert "success" in result.lower()


class TestRemoveAlertTool:
    def test_success(self):
        from src.tv_mcp.mcp.tools.paper_trading import remove_alert
        mock_engine = MagicMock()
        mock_engine.remove_alert = AsyncMock(return_value={"success": True})
        with patch(ENGINE_PATH, return_value=mock_engine):
            result = _run(remove_alert(alert_id=1))
        assert "success" in result.lower()
