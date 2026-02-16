"""
Tests for the modular new_vercel FastAPI application.

Covers auth, public routes, client routes (with mocked services),
admin route, TOON envelope format, empty headlines sentinel, and
validation error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from toon import encode as toon_encode

from new_vercel.app import app, create_app
from src.tv_mcp.core.settings import settings

# Use the actual keys loaded by the settings singleton so tests match.
_CLIENT_KEY = settings.CLIENT_API_KEY
_ADMIN_KEY = settings.ADMIN_API_KEY


@pytest.fixture()
def client() -> TestClient:
    """Create a TestClient for the new_vercel app."""
    return TestClient(app)


@pytest.fixture()
def client_headers() -> dict[str, str]:
    """Headers with a valid client key."""
    return {"X-Client-Key": _CLIENT_KEY}


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    """Headers with a valid admin key."""
    return {"X-Admin-Key": _ADMIN_KEY}


# ── App factory ─────────────────────────────────────────────────────


class TestAppFactory:
    """Verify create_app returns a working FastAPI instance."""

    def test_create_app_returns_fastapi(self) -> None:
        from fastapi import FastAPI

        a = create_app()
        assert isinstance(a, FastAPI)

    def test_create_app_title(self) -> None:
        a = create_app()
        assert a.title == "TradingView HTTP API"


# ── Auth tests ──────────────────────────────────────────────────────


class TestClientAuth:
    """Client-key authentication on business endpoints."""

    ENDPOINTS = [
        "/historical-data",
        "/news-headlines",
        "/news-content",
        "/all-indicators",
        "/ideas",
        "/minds",
        "/option-chain-greeks",
    ]

    def test_no_header_returns_403(self, client: TestClient) -> None:
        for ep in self.ENDPOINTS:
            resp = client.post(ep, json={})
            assert resp.status_code == 403, f"{ep} did not return 403 without header"

    def test_wrong_key_returns_403(self, client: TestClient) -> None:
        for ep in self.ENDPOINTS:
            resp = client.post(ep, json={}, headers={"X-Client-Key": "definitely-wrong-key-xyz"})
            assert resp.status_code == 403, f"{ep} did not return 403 with wrong key"


class TestAdminAuth:
    """Admin-key authentication on the update-cookies endpoint."""

    def test_no_header_returns_403(self, client: TestClient) -> None:
        resp = client.post("/update-cookies", json={})
        assert resp.status_code == 403

    def test_wrong_key_returns_403(self, client: TestClient) -> None:
        resp = client.post(
            "/update-cookies", json={}, headers={"X-Admin-Key": "definitely-wrong-key-xyz"}
        )
        assert resp.status_code == 403


# ── Public routes ───────────────────────────────────────────────────


class TestPublicRoutes:
    """GET /, /health, /privacy-policy — no auth required."""

    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TradingView HTTP API"

    def test_root(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "TradingView HTTP API Server"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "/historical-data" in data["endpoints"]

    def test_privacy_policy(self, client: TestClient) -> None:
        resp = client.get("/privacy-policy")
        assert resp.status_code == 200
        data = resp.json()
        assert "privacy_policy" in data
        assert "not financial advice" in data["privacy_policy"].lower()


# ── Client routes (mocked services) ────────────────────────────────


class TestHistoricalDataEndpoint:
    """POST /historical-data with mocked service."""

    @patch("new_vercel.routers.client.fetch_historical_data")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = {"success": True, "data": [{"close": 100}]}
        resp = client.post(
            "/historical-data",
            json={
                "exchange": "NSE",
                "symbol": "NIFTY",
                "timeframe": "1d",
                "numb_price_candles": 10,
                "indicators": [],
            },
            headers=client_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        mock_fetch.assert_called_once()

    @patch("new_vercel.routers.client.fetch_historical_data")
    def test_toon_envelope(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        payload = {"success": True, "data": [1, 2, 3]}
        mock_fetch.return_value = payload
        resp = client.post(
            "/historical-data",
            json={
                "exchange": "NSE",
                "symbol": "NIFTY",
                "timeframe": "1d",
                "numb_price_candles": 10,
            },
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == toon_encode(payload)

    @patch("new_vercel.routers.client.fetch_historical_data")
    def test_service_exception_returns_500(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.side_effect = RuntimeError("boom")
        resp = client.post(
            "/historical-data",
            json={
                "exchange": "NSE",
                "symbol": "NIFTY",
                "timeframe": "1d",
                "numb_price_candles": 10,
            },
            headers=client_headers,
        )
        assert resp.status_code == 500

    def test_validation_error_returns_422(
        self,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        """Missing required fields triggers Pydantic 422."""
        resp = client.post(
            "/historical-data",
            json={},
            headers=client_headers,
        )
        assert resp.status_code == 422

    @patch("new_vercel.routers.client.fetch_historical_data")
    def test_string_coercion_numb_candles(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        """numb_price_candles sent as string should be coerced to int."""
        mock_fetch.return_value = {"success": True}
        resp = client.post(
            "/historical-data",
            json={
                "exchange": "NSE",
                "symbol": "NIFTY",
                "timeframe": "1d",
                "numb_price_candles": "50",
            },
            headers=client_headers,
        )
        assert resp.status_code == 200
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[1]["numb_price_candles"] == 50 or call_kwargs[0][3] == 50


class TestNewsHeadlinesEndpoint:
    """POST /news-headlines with mocked service."""

    @patch("new_vercel.routers.client.fetch_news_headlines")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = [{"title": "BTC surges"}]
        resp = client.post(
            "/news-headlines",
            json={"symbol": "BTC", "exchange": "BINANCE"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @patch("new_vercel.routers.client.fetch_news_headlines")
    def test_empty_headlines_sentinel(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = []
        resp = client.post(
            "/news-headlines",
            json={"symbol": "BTC"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "headlines[0]:"

    @patch("new_vercel.routers.client.fetch_news_headlines")
    def test_exception_returns_500(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.side_effect = RuntimeError("Network error")
        resp = client.post(
            "/news-headlines",
            json={"symbol": "BTC"},
            headers=client_headers,
        )
        assert resp.status_code == 500


class TestNewsContentEndpoint:
    """POST /news-content with mocked service."""

    @patch("new_vercel.routers.client.fetch_news_content")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = [{"title": "Article", "body": "text"}]
        resp = client.post(
            "/news-content",
            json={"story_paths": ["/news/story1"]},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("new_vercel.routers.client.fetch_news_content")
    def test_toon_envelope(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        articles = [{"title": "A", "body": "B"}]
        mock_fetch.return_value = articles
        resp = client.post(
            "/news-content",
            json={"story_paths": ["/news/s1"]},
            headers=client_headers,
        )
        assert resp.json()["data"] == toon_encode({"articles": articles})


class TestAllIndicatorsEndpoint:
    """POST /all-indicators with mocked service."""

    @patch("new_vercel.routers.client.fetch_all_indicators")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = {"success": True, "data": {"RSI": 55}}
        resp = client.post(
            "/all-indicators",
            json={"symbol": "AAPL", "exchange": "NASDAQ", "timeframe": "1d"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("new_vercel.routers.client.fetch_all_indicators")
    def test_exception_returns_500(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.side_effect = RuntimeError("fail")
        resp = client.post(
            "/all-indicators",
            json={"symbol": "AAPL", "exchange": "NASDAQ", "timeframe": "1d"},
            headers=client_headers,
        )
        assert resp.status_code == 500


class TestIdeasEndpoint:
    """POST /ideas with mocked service."""

    @patch("new_vercel.routers.client.fetch_ideas")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = {"success": True, "ideas": [{"title": "Buy"}]}
        resp = client.post(
            "/ideas",
            json={"symbol": "BTCUSD"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("new_vercel.routers.client.fetch_ideas")
    def test_page_coercion(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        """Pages sent as strings are coerced to int."""
        mock_fetch.return_value = {"success": True}
        resp = client.post(
            "/ideas",
            json={"symbol": "BTCUSD", "startPage": "2", "endPage": "3"},
            headers=client_headers,
        )
        assert resp.status_code == 200


class TestMindsEndpoint:
    """POST /minds with mocked service."""

    @patch("new_vercel.routers.client.fetch_minds")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = {"success": True, "data": []}
        resp = client.post(
            "/minds",
            json={"symbol": "NIFTY", "exchange": "NSE"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("new_vercel.routers.client.fetch_minds")
    def test_limit_coercion(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        """limit sent as string is coerced to int."""
        mock_fetch.return_value = {"success": True, "data": []}
        resp = client.post(
            "/minds",
            json={"symbol": "NIFTY", "exchange": "NSE", "limit": "10"},
            headers=client_headers,
        )
        assert resp.status_code == 200


class TestOptionChainEndpoint:
    """POST /option-chain-greeks with mocked service."""

    @patch("new_vercel.routers.client.process_option_chain_with_analysis")
    def test_success(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        mock_fetch.return_value = {"success": True, "data": []}
        resp = client.post(
            "/option-chain-greeks",
            json={"symbol": "NIFTY", "exchange": "NSE"},
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    @patch("new_vercel.routers.client.process_option_chain_with_analysis")
    def test_itm_otm_coercion(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        """no_of_ITM / no_of_OTM sent as strings are coerced."""
        mock_fetch.return_value = {"success": True, "data": []}
        resp = client.post(
            "/option-chain-greeks",
            json={
                "symbol": "NIFTY",
                "exchange": "NSE",
                "no_of_ITM": "3",
                "no_of_OTM": "4",
            },
            headers=client_headers,
        )
        assert resp.status_code == 200


# ── Admin route ─────────────────────────────────────────────────────


class TestUpdateCookiesEndpoint:
    """POST /update-cookies with mocked verification."""

    @patch("new_vercel.routers.admin.fetch_ideas")
    @patch("new_vercel.routers.admin.settings")
    def test_success(
        self,
        mock_settings: MagicMock,
        mock_ideas: MagicMock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        mock_ideas.return_value = {"success": True, "ideas": [{"t": 1}]}
        resp = client.post(
            "/update-cookies",
            json={"cookies": [{"name": "a", "value": "b"}], "source": "ext"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @patch("new_vercel.routers.admin.fetch_ideas")
    def test_empty_cookies(
        self,
        mock_ideas: MagicMock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        resp = client.post(
            "/update-cookies",
            json={"cookies": [], "source": "ext"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    @patch("new_vercel.routers.admin.fetch_ideas")
    def test_verification_failure(
        self,
        mock_ideas: MagicMock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        mock_ideas.side_effect = RuntimeError("bad cookie")
        resp = client.post(
            "/update-cookies",
            json={"cookies": [{"name": "x", "value": "y"}], "source": "ext"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


# ── Validation error through ValidationError ────────────────────────


class TestValidationErrorHandling:
    """ValidationError from validators → 400 status."""

    @patch("new_vercel.routers.client.fetch_historical_data")
    def test_validation_error_400(
        self,
        mock_fetch: MagicMock,
        client: TestClient,
        client_headers: dict[str, str],
    ) -> None:
        from src.tv_mcp.core.validators import ValidationError

        mock_fetch.side_effect = ValidationError("bad param")
        resp = client.post(
            "/historical-data",
            json={
                "exchange": "NSE",
                "symbol": "NIFTY",
                "timeframe": "1d",
                "numb_price_candles": 10,
            },
            headers=client_headers,
        )
        assert resp.status_code == 400
        assert "bad param" in resp.json()["detail"]
