"""
Contract tests for paper trading Vercel endpoints.

Mocks the PaperTradingEngine to test request/response contracts.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient


ENGINE_PATH = "vercel.routers.paper_trading._engine"


def _mock_engine(**method_returns):
    """Create a mock engine with specified async method return values."""
    engine = MagicMock()
    for method, return_val in method_returns.items():
        setattr(engine, method, AsyncMock(return_value=return_val))
    return engine


class TestPlaceOrderEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(place_order={"success": True, "order_id": 1})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/place-order",
                json={
                    "symbol": "NIFTY", "exchange": "NSE",
                    "entry_price": 23000, "stop_loss": 22700,
                    "target": 23600, "lot_size": 1,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_validation_error(self, client: TestClient, auth_headers: dict):
        from src.tv_mcp.core.validators import ValidationError
        mock = _mock_engine()
        mock.place_order = AsyncMock(side_effect=ValidationError("bad"))
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/place-order",
                json={
                    "symbol": "NIFTY", "exchange": "NSE",
                    "entry_price": 23000, "stop_loss": 22700,
                    "target": 23600, "lot_size": 1,
                },
                headers=auth_headers,
            )
        assert resp.status_code == 400

    def test_no_auth(self, client: TestClient):
        resp = client.post(
            "/paper-trading/place-order",
            json={
                "symbol": "NIFTY", "exchange": "NSE",
                "entry_price": 23000, "stop_loss": 22700,
                "target": 23600, "lot_size": 1,
            },
        )
        assert resp.status_code == 403


class TestClosePositionEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(close_position={"success": True})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/close-position",
                json={"order_id": 1},
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestViewPositionsEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(view_positions={"success": True, "positions": []})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/view-positions",
                json={"filter_type": "all"},
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestShowCapitalEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(show_capital={"success": True})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.get(
                "/paper-trading/show-capital",
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestSetAlertEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(set_alert={"success": True, "alert_id": 1})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/set-alert",
                json={"alert_type": "time", "minutes": 5},
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestAlertManagerEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(alert_manager={"success": True, "message": "No alerts"})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.get(
                "/paper-trading/alert-manager",
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestViewAlertsEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(view_available_alerts={"success": True, "manual_alerts": []})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.get(
                "/paper-trading/view-alerts",
                headers=auth_headers,
            )
        assert resp.status_code == 200


class TestRemoveAlertEndpoint:
    def test_success(self, client: TestClient, auth_headers: dict):
        mock = _mock_engine(remove_alert={"success": True})
        with patch(ENGINE_PATH, return_value=mock):
            resp = client.post(
                "/paper-trading/remove-alert",
                json={"alert_id": 1},
                headers=auth_headers,
            )
        assert resp.status_code == 200

    def test_no_auth(self, client: TestClient):
        resp = client.post(
            "/paper-trading/remove-alert",
            json={"alert_id": 1},
        )
        assert resp.status_code == 403
