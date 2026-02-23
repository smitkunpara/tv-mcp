"""
Edge-case authentication tests for vercel HTTP API.

Covers missing headers, wrong headers, cross-key confusion,
and public endpoints requiring no key.
"""

import pytest
from starlette.testclient import TestClient

from src.tv_mcp.core.settings import settings

_CLIENT_KEY = settings.CLIENT_API_KEY
_ADMIN_KEY = settings.ADMIN_API_KEY

CLIENT_POST_ENDPOINTS = [
    "/historical-data",
    "/news-headlines",
    "/news-content",
    "/all-indicators",
    "/ideas",
    "/minds",
    "/option-chain-greeks",
    "/nse-option-chain-oi",
    "/paper-trading/place-order",
    "/paper-trading/close-position",
    "/paper-trading/view-positions",
    "/paper-trading/set-alert",
    "/paper-trading/remove-alert",
]

CLIENT_GET_ENDPOINTS = [
    "/paper-trading/show-capital",
    "/paper-trading/alert-manager",
    "/paper-trading/view-alerts",
]

PUBLIC_ENDPOINTS = [
    "/health",
    "/openapi.json",
    "/privacy-policy",
    "/",
]


class TestMissingClientKey:
    """Missing X-Client-Key header must return 403 with correct detail."""

    @pytest.mark.parametrize("endpoint", CLIENT_POST_ENDPOINTS)
    def test_missing_header_returns_403_for_post(
        self, client: TestClient, endpoint: str
    ) -> None:
        resp = client.post(endpoint, json={})
        assert resp.status_code == 403
        assert "Unauthorized" in resp.json()["detail"]

    @pytest.mark.parametrize("endpoint", CLIENT_GET_ENDPOINTS)
    def test_missing_header_returns_403_for_get(
        self, client: TestClient, endpoint: str
    ) -> None:
        resp = client.get(endpoint)
        assert resp.status_code == 403
        assert "Unauthorized" in resp.json()["detail"]


class TestMissingAdminKey:
    """Missing X-Admin-Key header must return 403 with correct detail."""

    def test_missing_header_returns_403(self, client: TestClient) -> None:
        resp = client.post("/update-cookies", json={})
        assert resp.status_code == 403
        assert "Unauthorized" in resp.json()["detail"]


class TestBothKeysWrong:
    """Both headers present but with wrong values must still be 403."""

    @pytest.mark.parametrize("endpoint", CLIENT_POST_ENDPOINTS)
    def test_wrong_client_key_still_403_for_post(
        self, client: TestClient, endpoint: str
    ) -> None:
        resp = client.post(
            endpoint,
            json={},
            headers={
                "X-Client-Key": "wrong-client-key-xxx",
                "X-Admin-Key": "wrong-admin-key-yyy",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("endpoint", CLIENT_GET_ENDPOINTS)
    def test_wrong_client_key_still_403_for_get(
        self, client: TestClient, endpoint: str
    ) -> None:
        resp = client.get(
            endpoint,
            headers={
                "X-Client-Key": "wrong-client-key-xxx",
                "X-Admin-Key": "wrong-admin-key-yyy",
            },
        )
        assert resp.status_code == 403

    def test_wrong_admin_key_still_403(self, client: TestClient) -> None:
        resp = client.post(
            "/update-cookies",
            json={},
            headers={
                "X-Admin-Key": "wrong-admin-key-yyy",
                "X-Client-Key": "wrong-client-key-xxx",
            },
        )
        assert resp.status_code == 403


class TestCrossKeyConfusion:
    """Client key must NOT unlock admin endpoints and vice versa."""

    def test_client_key_on_admin_endpoint_returns_403(
        self, client: TestClient
    ) -> None:
        """Using client key on /update-cookies should fail."""
        resp = client.post(
            "/update-cookies",
            json={},
            headers={"X-Admin-Key": _CLIENT_KEY},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("endpoint", CLIENT_POST_ENDPOINTS)
    def test_admin_key_on_client_post_endpoint_returns_403(
        self, client: TestClient, endpoint: str
    ) -> None:
        """Using admin key on client endpoints should fail."""
        resp = client.post(
            endpoint,
            json={},
            headers={"X-Client-Key": _ADMIN_KEY},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("endpoint", CLIENT_GET_ENDPOINTS)
    def test_admin_key_on_client_get_endpoint_returns_403(
        self, client: TestClient, endpoint: str
    ) -> None:
        """Using admin key on client endpoints should fail."""
        resp = client.get(
            endpoint,
            headers={"X-Client-Key": _ADMIN_KEY},
        )
        assert resp.status_code == 403


class TestPublicEndpointsNoAuth:
    """Public endpoints must work with no key at all."""

    @pytest.mark.parametrize("endpoint", PUBLIC_ENDPOINTS)
    def test_public_endpoint_ok_without_any_key(
        self, client: TestClient, endpoint: str
    ) -> None:
        resp = client.get(endpoint)
        assert resp.status_code == 200
