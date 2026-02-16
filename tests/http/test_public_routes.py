"""
Detailed public route tests for vercel HTTP API.

Verifies exact response shapes for GET /health, GET /privacy-policy,
and GET / (root).
"""

import pytest
from starlette.testclient import TestClient


DOCUMENTED_ENDPOINTS = [
    "/historical-data",
    "/news-headlines",
    "/news-content",
    "/all-indicators",
    "/ideas",
    "/option-chain-greeks",
    "/privacy-policy",
]


class TestHealthEndpoint:
    """GET /health returns exact shape."""

    def test_status_healthy(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"status": "healthy", "service": "TradingView HTTP API"}

    def test_health_has_exactly_two_keys(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert set(data.keys()) == {"status", "service"}


class TestPrivacyPolicyEndpoint:
    """GET /privacy-policy contains specific text fragments."""

    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/privacy-policy").status_code == 200

    def test_contains_privacy_policy_key(self, client: TestClient) -> None:
        data = client.get("/privacy-policy").json()
        assert "privacy_policy" in data

    def test_not_financial_advice(self, client: TestClient) -> None:
        text: str = client.get("/privacy-policy").json()["privacy_policy"]
        assert "not financial advice" in text.lower()

    def test_mentions_tradingview(self, client: TestClient) -> None:
        text: str = client.get("/privacy-policy").json()["privacy_policy"]
        assert "tradingview" in text.lower()

    def test_mentions_data_collection(self, client: TestClient) -> None:
        text: str = client.get("/privacy-policy").json()["privacy_policy"]
        assert "data collection" in text.lower()

    def test_mentions_liability(self, client: TestClient) -> None:
        text: str = client.get("/privacy-policy").json()["privacy_policy"]
        assert "liability" in text.lower()


class TestRootEndpoint:
    """GET / returns version, endpoints list, servers array."""

    def test_returns_200(self, client: TestClient) -> None:
        assert client.get("/").status_code == 200

    def test_has_message(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert data["message"] == "TradingView HTTP API Server"

    def test_has_version(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert data["version"] == "1.0.0"

    def test_has_servers_array(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert isinstance(data["servers"], list)
        assert len(data["servers"]) >= 1

    def test_has_endpoints_list(self, client: TestClient) -> None:
        data = client.get("/").json()
        assert isinstance(data["endpoints"], list)
        assert len(data["endpoints"]) >= 7

    @pytest.mark.parametrize("ep", DOCUMENTED_ENDPOINTS)
    def test_documented_endpoint_listed(
        self, client: TestClient, ep: str
    ) -> None:
        endpoints: list[str] = client.get("/").json()["endpoints"]
        assert ep in endpoints, f"Expected {ep} in root endpoints list"
