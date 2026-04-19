"""
Internal contract tests for src.tv_mcp.core.contracts.

Verifies ServiceResponse helpers produce correct envelope shapes and
that all service modules return dicts with a ``success`` key (via mocks).
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tv_mcp.core.contracts import (
    ServiceResponse,
    success_response,
    error_response,
)


# ── success_response shape ──────────────────────────────────────────


class TestSuccessResponse:
    """success_response() must return the standard envelope."""

    def test_has_status_success(self) -> None:
        resp = success_response(data={"foo": 1})
        assert resp["status"] == "success"

    def test_has_data(self) -> None:
        resp = success_response(data=[1, 2, 3])
        assert resp["data"] == [1, 2, 3]

    def test_has_metadata_default_empty(self) -> None:
        resp = success_response(data=None)
        assert resp["metadata"] == {}

    def test_has_error_none(self) -> None:
        resp = success_response(data="x")
        assert resp["error"] is None

    def test_custom_metadata(self) -> None:
        resp = success_response(data="x", metadata={"pages": 5})
        assert resp["metadata"] == {"pages": 5}

    def test_keys_exactly(self) -> None:
        resp = success_response(data=1)
        assert set(resp.keys()) == {"status", "data", "metadata", "error"}


# ── error_response shape ───────────────────────────────────────────


class TestErrorResponse:
    """error_response() must return the standard error envelope."""

    def test_has_status_failed(self) -> None:
        resp = error_response(error="boom")
        assert resp["status"] == "failed"

    def test_has_data_none(self) -> None:
        resp = error_response(error="boom")
        assert resp["data"] is None

    def test_has_error_string(self) -> None:
        resp = error_response(error="connection lost")
        assert resp["error"] == "connection lost"

    def test_has_metadata_default_empty(self) -> None:
        resp = error_response(error="x")
        assert resp["metadata"] == {}

    def test_custom_metadata(self) -> None:
        resp = error_response(error="x", metadata={"retry": True})
        assert resp["metadata"] == {"retry": True}

    def test_keys_exactly(self) -> None:
        resp = error_response(error="x")
        assert set(resp.keys()) == {"status", "data", "metadata", "error"}


# ── ServiceResponse is a dict ─────────────────────────────────────


class TestServiceResponseType:
    """ServiceResponse is a Dict[str, Any] alias — results are dicts."""

    def test_success_is_dict(self) -> None:
        resp = success_response(data=1)
        assert isinstance(resp, dict)

    def test_error_is_dict(self) -> None:
        resp = error_response(error="x")
        assert isinstance(resp, dict)


# ── All services return dicts with 'success' key ──────────────────


class TestServicesReturnSuccess:
    """Mocked service calls must return dicts containing a 'success' key."""

    @patch("src.tv_mcp.services.historical.Streamer")
    @patch("src.tv_mcp.services.historical.merge_ohlc_with_indicators")
    def test_historical_returns_success_key(
        self, mock_merge: MagicMock, mock_streamer_cls: MagicMock
    ) -> None:
        instance = MagicMock()
        mock_streamer_cls.return_value = instance
        instance.get_candles.return_value = {
            "status": "success",
            "data": {
                "ohlcv": [{"timestamp": 1, "open": 1, "high": 2, "low": 0, "close": 1, "volume": 1, "index": 0}],
                "indicators": {},
            },
        }
        mock_merge.return_value = [{"open": 1}]
        from src.tv_mcp.services.historical import fetch_historical_data

        result = fetch_historical_data("NSE", "RELIANCE", "1d", 1, [])
        assert isinstance(result, dict)
        assert "success" in result

    @patch("src.tv_mcp.services.ideas.Ideas")
    def test_ideas_returns_success_key(self, mock_cls: MagicMock) -> None:
        instance = MagicMock()
        mock_cls.return_value = instance
        instance.get_ideas.return_value = {"status": "success", "data": []}
        from src.tv_mcp.services.ideas import fetch_ideas

        result = fetch_ideas(symbol="AAPL", exchange="NASDAQ")
        assert isinstance(result, dict)
        assert "success" in result

    @patch("src.tv_mcp.services.minds.Minds")
    def test_minds_returns_success_key(self, mock_cls: MagicMock) -> None:
        instance = MagicMock()
        mock_cls.return_value = instance
        instance.get_minds.return_value = {"status": "success", "data": [{"text": "hi"}]}
        from src.tv_mcp.services.minds import fetch_minds

        result = fetch_minds(symbol="AAPL", exchange="NASDAQ")
        assert isinstance(result, dict)
        assert "success" in result

    @patch("src.tv_mcp.services.technicals.Technicals")
    def test_technicals_returns_success_key(self, mock_cls: MagicMock) -> None:
        instance = MagicMock()
        mock_cls.return_value = instance
        instance.get_technicals.return_value = {"status": "success", "data": {"RSI": 55}}
        from src.tv_mcp.services.technicals import fetch_all_indicators

        result = fetch_all_indicators(exchange="NSE", symbol="NIFTY", timeframe="1m")
        assert isinstance(result, dict)
        assert "success" in result


# ── Error envelope contains expected keys ──────────────────────────


class TestErrorEnvelopeKeys:
    """Error envelopes must contain 'status', 'error', 'data' keys."""

    def test_error_response_has_status(self) -> None:
        resp = error_response(error="fail")
        assert "status" in resp

    def test_error_response_has_error(self) -> None:
        resp = error_response(error="fail")
        assert "error" in resp

    def test_error_response_has_data_none(self) -> None:
        resp = error_response(error="fail")
        assert "data" in resp
        assert resp["data"] is None
