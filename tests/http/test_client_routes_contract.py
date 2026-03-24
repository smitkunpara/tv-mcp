"""
Contract parity tests for client POST endpoints.

Verifies every endpoint returns the ``{"data": "<toon_string>"}`` envelope,
handles ValidationError → 400, unexpected exceptions → 500,
and edge cases like empty headlines sentinel.
"""

import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from toon import encode as toon_encode

from src.tv_mcp.core.validators import ValidationError


# ── Helpers ─────────────────────────────────────────────────────────

# Minimal valid payloads that satisfy Pydantic models.
PAYLOADS: dict[str, dict] = {
    "/historical-data": {
        "exchange": "NSE",
        "symbol": "NIFTY",
        "timeframe": "1d",
        "numb_price_candles": 10,
    },
    "/news-headlines": {"symbol": "BTC", "exchange": "CRYPTO"},
    "/news-content": {"story_ids": ["/news/s1"]},
    "/all-indicators": {"symbol": "AAPL", "exchange": "NASDAQ", "timeframe": "1m"},
    "/ideas": {"symbol": "BTCUSD", "exchange": "BITSTAMP"},
    "/minds": {"symbol": "NIFTY", "exchange": "NSE"},
    "/option-chain-greeks": {"symbol": "NIFTY", "exchange": "NSE"},
    "/option-chain-oi": {
        "exchange": "NSE",
        "symbol": "NIFTY",
        "expiry_date": "2026-03-26",
    },
}

# Which service function each endpoint calls (module path for patching).
SERVICE_PATCHES: dict[str, str] = {
    "/historical-data": "vercel.routers.client.fetch_historical_data",
    "/news-headlines": "vercel.routers.client.fetch_news_headlines",
    "/news-content": "vercel.routers.client.fetch_news_content",
    "/all-indicators": "vercel.routers.client.fetch_all_indicators",
    "/ideas": "vercel.routers.client.fetch_ideas",
    "/minds": "vercel.routers.client.fetch_minds",
    "/option-chain-greeks": "vercel.routers.client.process_option_chain_with_analysis",
    "/option-chain-oi": "vercel.routers.client.fetch_option_chain_oi",
}


# ── TOON envelope tests ────────────────────────────────────────────


class TestToonEnvelopeContract:
    """Each POST endpoint must return {"data": toon_encode(result)}."""

    @pytest.mark.parametrize("endpoint", list(PAYLOADS.keys()))
    def test_data_key_in_response(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        endpoint: str,
    ) -> None:
        svc_path = SERVICE_PATCHES[endpoint]
        payload = PAYLOADS[endpoint]
        fake_return = {"success": True, "items": [1, 2, 3]}

        # news-headlines returns a list, others return a dict
        if endpoint == "/news-headlines":
            fake_return_value = [{"title": "T"}]  # type: ignore[assignment]
        elif endpoint == "/news-content":
            fake_return_value = [{"title": "A", "body": "B"}]  # type: ignore[assignment]
        else:
            fake_return_value = fake_return  # type: ignore[assignment]

        with patch(svc_path) as mock_svc:
            mock_svc.return_value = fake_return_value
            resp = client.post(endpoint, json=payload, headers=auth_headers)

        assert resp.status_code == 200, f"{endpoint}: {resp.text}"
        body = resp.json()
        assert "data" in body, f"{endpoint} missing 'data' key"
        assert isinstance(body["data"], str), f"{endpoint} 'data' should be a TOON string"


# ── ValidationError → 400 ──────────────────────────────────────────


class TestValidationError400:
    """Service raising ValidationError must yield HTTP 400."""

    @pytest.mark.parametrize("endpoint", list(PAYLOADS.keys()))
    def test_validation_error_returns_400(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        endpoint: str,
    ) -> None:
        svc_path = SERVICE_PATCHES[endpoint]
        payload = PAYLOADS[endpoint]

        with patch(svc_path) as mock_svc:
            mock_svc.side_effect = ValidationError("test validation failure")
            resp = client.post(endpoint, json=payload, headers=auth_headers)

        assert resp.status_code == 400, f"{endpoint}: expected 400, got {resp.status_code}"
        assert "test validation failure" in resp.json()["detail"]


# ── Unexpected exception → 500 ─────────────────────────────────────


class TestUnexpectedException500:
    """Service raising generic Exception must yield HTTP 500."""

    @pytest.mark.parametrize("endpoint", [ep for ep in PAYLOADS.keys() if ep != "/news-headlines"])
    def test_unexpected_exception_returns_500(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        endpoint: str,
    ) -> None:
        svc_path = SERVICE_PATCHES[endpoint]
        payload = PAYLOADS[endpoint]

        with patch(svc_path) as mock_svc:
            mock_svc.side_effect = RuntimeError("kaboom")
            resp = client.post(endpoint, json=payload, headers=auth_headers)

        assert resp.status_code == 500, f"{endpoint}: expected 500, got {resp.status_code}"


# ── Empty headlines sentinel ────────────────────────────────────────


class TestEmptyHeadlinesSentinel:
    """Empty headline list must return sentinel string."""

    def test_empty_headlines_returns_sentinel(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        with patch("vercel.routers.client.fetch_news_headlines") as mock_svc:
            mock_svc.return_value = []
            resp = client.post(
                "/news-headlines",
                json={"symbol": "BTC", "exchange": "CRYPTO"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == "headlines[0]:"


# ── Options endpoint success keys ──────────────────────────────────


class TestOptionsEndpointSuccess:
    """Option chain endpoint returns data key on success."""

    def test_returns_data_key(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ) -> None:
        fake_result = {"success": True, "data": [{"strike": 100}]}
        with patch(
            "vercel.routers.client.process_option_chain_with_analysis"
        ) as mock_svc:
            mock_svc.return_value = fake_result
            resp = client.post(
                "/option-chain-greeks",
                json={"symbol": "NIFTY", "exchange": "NSE"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["data"] == toon_encode(fake_result)
