"""
Tests for authenticated MCP HTTP server entrypoint.
"""

import pytest
from starlette.testclient import TestClient

from tv_mcp.mcp import http_server
from tv_mcp.core.settings import settings
from tv_mcp.mcp.http_server import _parse_transport, create_http_app


def test_health_endpoint_is_public() -> None:
    with TestClient(create_http_app()) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["transport"] == "http"
    assert body["mcp_mount_path"] == "/mcp"


def test_mcp_route_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "secret-key")
    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp")
    assert resp.status_code == 403


def test_mcp_route_accepts_x_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "secret-key")
    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp", headers={"x-api-key": "secret-key"})
    assert resp.status_code != 403
    assert resp.status_code != 500


def test_mcp_route_accepts_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "secret-key")
    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp", headers={"Authorization": "Bearer secret-key"})
    assert resp.status_code != 403
    assert resp.status_code != 500


def test_mcp_route_returns_503_without_configured_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "")
    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp")
    assert resp.status_code == 503


def test_sse_health_endpoint_is_public() -> None:
    with TestClient(create_http_app(transport="sse")) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["transport"] == "sse"
    assert body["mcp_mount_path"] == "/sse"


def test_sse_route_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "secret-key")
    with TestClient(create_http_app(transport="sse")) as client:
        resp = client.get("/sse")
    assert resp.status_code == 403


def test_parse_transport_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        _parse_transport("invalid-transport")


def test_mcp_route_accepts_valid_oauth_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_JWKS_URL", "https://issuer.example/jwks.json")
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "fallback-key")
    monkeypatch.setattr(http_server, "_validate_oauth_token", lambda token: token == "valid-token")

    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp", headers={"Authorization": "Bearer valid-token"})

    assert resp.status_code != 403
    assert resp.status_code != 500


def test_mcp_route_falls_back_to_api_key_when_oauth_invalid(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_JWKS_URL", "https://issuer.example/jwks.json")
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "fallback-key")
    monkeypatch.setattr(http_server, "_validate_oauth_token", lambda _token: False)

    with TestClient(create_http_app()) as client:
        resp = client.get(
            "/mcp",
            headers={
                "Authorization": "Bearer invalid-token",
                "X-Client-Key": "fallback-key",
            },
        )

    assert resp.status_code != 403
    assert resp.status_code != 500


def test_mcp_route_rejects_invalid_oauth_without_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_JWKS_URL", "https://issuer.example/jwks.json")
    monkeypatch.setattr(settings, "CLIENT_API_KEY", "fallback-key")
    monkeypatch.setattr(http_server, "_validate_oauth_token", lambda _token: False)

    with TestClient(create_http_app()) as client:
        resp = client.get("/mcp", headers={"Authorization": "Bearer invalid-token"})

    assert resp.status_code == 403
