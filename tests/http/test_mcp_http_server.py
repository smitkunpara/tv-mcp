"""
Tests for authenticated MCP HTTP server entrypoint.
"""

from starlette.testclient import TestClient

from tv_mcp.core.settings import settings
from tv_mcp.mcp.http_server import create_http_app


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
