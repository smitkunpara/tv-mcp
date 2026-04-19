"""
HTTP entrypoint for remote MCP connections with API-key authentication.
"""

import os
from typing import Literal

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.settings import settings
from .server import mcp

SupportedHTTPTransport = Literal["http", "streamable-http", "sse"]
_SUPPORTED_HTTP_TRANSPORTS = {"http", "streamable-http", "sse"}


class MCPAPIKeyMiddleware(BaseHTTPMiddleware):
    """Protect mounted MCP routes using TV_CLIENT_KEY."""

    async def dispatch(self, request: Request, call_next):
        protected_prefix = getattr(request.app.state, "mcp_mount_path", "/mcp")

        if _path_matches_prefix(request.url.path, protected_prefix):
            expected_key = settings.CLIENT_API_KEY.strip()
            provided_key = _extract_api_key(request)

            if not expected_key:
                return JSONResponse(
                    {"detail": "MCP API key is not configured. Set TV_CLIENT_KEY."},
                    status_code=503,
                )

            if provided_key != expected_key:
                return JSONResponse({"detail": "Unauthorized MCP access"}, status_code=403)

        return await call_next(request)


def _extract_api_key(request: Request) -> str:
    x_api_key = request.headers.get("x-api-key", "")
    if x_api_key:
        return x_api_key.strip()

    x_client_key = request.headers.get("x-client-key", "")
    if x_client_key:
        return x_client_key.strip()

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    return ""


def _normalize_mount_path(path: str) -> str:
    normalized = "/" + path.strip("/")
    return "/" if normalized == "//" else normalized


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _default_mount_path(transport: SupportedHTTPTransport) -> str:
    if transport == "sse":
        return "/sse"
    return "/mcp"


def create_http_app(
    transport: SupportedHTTPTransport = "http",
    mcp_mount_path: str | None = None,
) -> FastAPI:
    """Create FastAPI app that mounts authenticated MCP transport."""
    if transport not in _SUPPORTED_HTTP_TRANSPORTS:
        raise ValueError(f"Unsupported transport: {transport}")

    mount_path = _normalize_mount_path(mcp_mount_path or _default_mount_path(transport))
    mcp_app = mcp.http_app(path="/", transport=transport)

    app = FastAPI(
        title="TradingView MCP HTTP Server",
        version="1.0.0",
        description="Remote MCP endpoint with API-key authentication",
        lifespan=mcp_app.lifespan,
    )
    app.state.mcp_mount_path = mount_path
    app.state.mcp_transport = transport
    app.add_middleware(MCPAPIKeyMiddleware)
    app.mount(mount_path, mcp_app)

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "healthy",
            "service": "TradingView MCP HTTP Server",
            "transport": transport,
            "mcp_mount_path": mount_path,
            "auth": "api-key",
        }

    return app


app = create_http_app()


def main() -> None:
    """Run the authenticated MCP HTTP server (streamable HTTP default)."""
    host = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_HTTP_PORT", "8000"))
    transport = os.getenv("MCP_HTTP_TRANSPORT", "http").strip().lower()
    mount_path = os.getenv("MCP_HTTP_PATH")

    http_app = create_http_app(transport=transport, mcp_mount_path=mount_path)
    uvicorn.run(http_app, host=host, port=port)


def main_sse() -> None:
    """Run the authenticated MCP SSE server."""
    host = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_HTTP_PORT", "8000"))
    mount_path = os.getenv("MCP_SSE_PATH") or os.getenv("MCP_HTTP_PATH") or "/sse"

    sse_app = create_http_app(transport="sse", mcp_mount_path=mount_path)
    uvicorn.run(sse_app, host=host, port=port)
