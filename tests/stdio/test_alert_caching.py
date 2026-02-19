"""
Tests for the alert caching system.

Verifies that alerts are cached when triggered and can be retrieved
by alert_manager or injected into other tool responses.
"""

import asyncio
import os
import pytest
from unittest.mock import patch

from src.tv_mcp.services.paper_trading import PaperTradingEngine
from src.tv_mcp.core.settings import settings


@pytest.fixture(autouse=True)
def fresh_engine(tmp_path):
    """Reset the singleton and use a temp DB for every test."""
    PaperTradingEngine._instance = None
    engine = PaperTradingEngine()
    engine._initialized = False
    engine.initialize()
    engine._db_path = str(tmp_path / "test_trades.db")
    engine._init_db()
    yield engine
    PaperTradingEngine._instance = None


@pytest.fixture
def enable_alert_injection():
    """Temporarily enable INJECT_ALERTS_IN_ALL_TOOLS for testing."""
    original = settings.INJECT_ALERTS_IN_ALL_TOOLS
    settings.INJECT_ALERTS_IN_ALL_TOOLS = True
    yield
    settings.INJECT_ALERTS_IN_ALL_TOOLS = original


@pytest.fixture
def disable_alert_injection():
    """Temporarily disable INJECT_ALERTS_IN_ALL_TOOLS for testing."""
    original = settings.INJECT_ALERTS_IN_ALL_TOOLS
    settings.INJECT_ALERTS_IN_ALL_TOOLS = False
    yield
    settings.INJECT_ALERTS_IN_ALL_TOOLS = original


class TestAlertCaching:
    """Test alert caching in the engine."""

    @pytest.mark.asyncio
    async def test_push_alert_event_caches(self, fresh_engine):
        """Verify that _push_alert_event caches events."""
        event = {"source": "test", "message": "test alert"}
        await fresh_engine._push_alert_event(event)
        
        cached = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached) == 1
        assert cached[0]["source"] == "test"

    @pytest.mark.asyncio
    async def test_get_cached_alerts_with_clear(self, fresh_engine):
        """Verify that get_cached_alerts can clear the cache."""
        event1 = {"source": "test1", "message": "first"}
        event2 = {"source": "test2", "message": "second"}
        await fresh_engine._push_alert_event(event1)
        await fresh_engine._push_alert_event (event2)
        
        # Get with clear
        cached = await fresh_engine.get_cached_alerts(clear_cache=True)
        assert len(cached) == 2
        
        # Cache should be empty now
        cached_after = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached_after) == 0

    @pytest.mark.asyncio
    async def test_clear_alert_cache(self, fresh_engine):
        """Verify clear_alert_cache method."""
        await fresh_engine._push_alert_event({"source": "test"})
        await fresh_engine.clear_alert_cache()
        
        cached = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached) == 0

    @pytest.mark.asyncio
    async def test_alert_manager_returns_cached_immediately(self, fresh_engine):
        """Verify alert_manager returns cached alerts without waiting."""
        # Push some events to cache
        await fresh_engine._push_alert_event({"source": "cached1", "message": "test1"})
        await fresh_engine._push_alert_event({"source": "cached2", "message": "test2"})
        
        # Call alert_manager - should return immediately with cached alerts
        result = await fresh_engine.alert_manager()
        
        assert result["success"] is True
        assert "triggered_events" in result
        assert len(result["triggered_events"]) == 2
        assert result.get("from_cache") is True
        
        # Cache should be cleared now
        cached = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached) == 0

    @pytest.mark.asyncio
    async def test_alert_manager_clears_queue_cache(self, fresh_engine):
        """Verify alert_manager clears cache even when getting from queue."""
        # Put event in cache
        await fresh_engine._push_alert_event({"source": "cached", "message": "pre-cached"})
        
        # Cache should have 1 item
        cached_before = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached_before) == 1
        
        # Now put event in queue for alert_manager to wait for  
        async def put_event():
            await asyncio.sleep(0.1)
            await fresh_engine._push_alert_event({"source": "new", "message": "new alert"})
        
        # Add a fake position so has_work is True
        from src.tv_mcp.services.paper_trading import Position
        fresh_engine._positions[1] = Position(
            1, "X", "NSE", "BUY", 100, 90, 200, 1, None, "test"
        )
        
        # Start put_event task and call alert_manager
        task = asyncio.create_task(put_event())
        result = await fresh_engine.alert_manager()
        await task
        
        # Should have received the events (including the one that was cached before)
        assert result["success"] is True
        # When getting from queue, it also drains the queue, so may get multiple events
        # But importantly, cache should be cleared by alert_manager
        # The new event added during wait is also in cache, so cache will have 1 item
        # (the alert manager clears cache before draining, so the new one stays)
        # Actually, looking at the code, clear happens AFTER draining
        # So cache should be cleared
        cached = await fresh_engine.get_cached_alerts(clear_cache=False)
        # The cache was cleared, but then the new event was added, so it has 1
        assert len(cached) == 1  # The new event that was just pushed


class TestAlertInjection:
    """Test alert injection in MCP tools."""

    @pytest.mark.asyncio
    async def test_injection_when_enabled(self, fresh_engine, enable_alert_injection):
        """Verify that alerts are injected when INJECT_ALERTS_IN_ALL_TOOLS is true."""
        from src.tv_mcp.mcp.tools.paper_trading import _inject_alerts_if_enabled
        
        # Push some cached alerts
        await fresh_engine._push_alert_event({"source": "test", "message": "alert1"})
        await fresh_engine._push_alert_event({"source": "test2", "message": "alert2"})
        
        # Mock result from a tool
        result = {"success": True, "data": "some data"}
        
        # Inject alerts
        injected = await _inject_alerts_if_enabled(result)
        
        assert "triggered_alerts" in injected
        assert len(injected["triggered_alerts"]) == 2
        assert "alert_notice" in injected

    @pytest.mark.asyncio
    async def test_no_injection_when_disabled(self, fresh_engine, disable_alert_injection):
        """Verify that alerts are NOT injected when INJECT_ALERTS_IN_ALL_TOOLS is false."""
        from src.tv_mcp.mcp.tools.paper_trading import _inject_alerts_if_enabled
        
        # Push some cached alerts
        await fresh_engine._push_alert_event({"source": "test", "message": "alert1"})
        
        # Mock result from a tool
        result = {"success": True, "data": "some data"}
        
        # Inject alerts (should do nothing)
        injected = await _inject_alerts_if_enabled(result)
        
        assert "triggered_alerts" not in injected
        assert "alert_notice" not in injected

    @pytest.mark.asyncio
    async def test_injection_doesnt_clear_cache(self, fresh_engine, enable_alert_injection):
        """Verify that injection does NOT clear the cache."""
        from src.tv_mcp.mcp.tools.paper_trading import _inject_alerts_if_enabled
        
        await fresh_engine._push_alert_event({"source": "test", "message": "alert"})
        
        result = {"success": True}
        await _inject_alerts_if_enabled(result)
        
        # Cache should still have the alert
        cached = await fresh_engine.get_cached_alerts(clear_cache=False)
        assert len(cached) == 1

    @pytest.mark.asyncio
    async def test_show_capital_with_injection(self, fresh_engine, enable_alert_injection):
        """Integration test: show_capital should include alerts when enabled."""
        from src.tv_mcp.mcp.tools.paper_trading import show_capital
        
        # Push a cached alert
        await fresh_engine._push_alert_event({
            "source": "trade_close",
            "message": "Position closed"
        })
        
        # Call show_capital
        result_str = await show_capital()
        
        # Check that serialized result contains alert info
        assert "triggered_alerts" in result_str or "trade_close" in result_str

    @pytest.mark.asyncio
    async def test_view_positions_with_injection(self, fresh_engine, enable_alert_injection):
        """Integration test: view_positions should include alerts when enabled."""
        from src.tv_mcp.mcp.tools.paper_trading import view_positions
        
        # Push a cached alert
        await fresh_engine._push_alert_event({
            "source": "price_alert",
            "message": "Price alert triggered"
        })
        
        # Call view_positions
        result_str = await view_positions(filter_type="all")
        
        # Check that serialized result contains alert info
        assert "triggered_alerts" in result_str or "price_alert" in result_str
