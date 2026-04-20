"""
HTTP entrypoint for remote MCP connections with OAuth/API-key authentication.
"""

import logging
import os
from functools import lru_cache
from typing import Any, Literal, cast

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.settings import settings
from .server import mcp

SupportedHTTPTransport = Literal["http", "streamable-http", "sse"]
_SUPPORTED_HTTP_TRANSPORTS = {"http", "streamable-http", "sse"}

logger = logging.getLogger(__name__)


class MCPAPIKeyMiddleware(BaseHTTPMiddleware):
    """Protect mounted MCP routes using OAuth bearer token or API key."""

    async def dispatch(self, request: Request, call_next):
        protected_prefix = getattr(request.app.state, "mcp_mount_path", "/mcp")

        if _path_matches_prefix(request.url.path, protected_prefix):
            bearer_token = _extract_bearer_token(request)
            if _oauth_enabled() and bearer_token and _validate_oauth_token(bearer_token):
                return await call_next(request)

            expected_key = settings.CLIENT_API_KEY.strip()
            provided_key = _extract_api_key(request)
            if expected_key and provided_key == expected_key:
                return await call_next(request)

            if _oauth_enabled() and not expected_key:
                return JSONResponse({"detail": "Unauthorized MCP access"}, status_code=403)

            if not expected_key and not _oauth_enabled():
                return JSONResponse(
                    {"detail": "MCP API key is not configured. Set TV_CLIENT_KEY."},
                    status_code=503,
                )

            return JSONResponse({"detail": "Unauthorized MCP access"}, status_code=403)

        return await call_next(request)


def _extract_api_key(request: Request) -> str:
    x_api_key = request.headers.get("x-api-key", "")
    if x_api_key:
        return x_api_key.strip()

    x_client_key = request.headers.get("x-client-key", "")
    if x_client_key:
        return x_client_key.strip()

    return _extract_bearer_token(request)


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    return ""


def _oauth_enabled() -> bool:
    return bool(settings.OAUTH_JWKS_URL.strip())


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str):
    import jwt

    return jwt.PyJWKClient(jwks_url)


def _scope_is_authorized(scope_claim: object, required_scope: str) -> bool:
    if not required_scope:
        return True

    if isinstance(scope_claim, str):
        scopes = set(scope_claim.split())
    elif isinstance(scope_claim, list):
        scopes = {str(item) for item in scope_claim}
    else:
        scopes = set()

    return required_scope in scopes


def _validate_oauth_token(token: str) -> bool:
    """Validate JWT bearer token against configured JWKS/issuer/audience."""
    if not token or not _oauth_enabled():
        return False

    jwks_url = settings.OAUTH_JWKS_URL.strip()
    if not jwks_url:
        return False

    try:
        import jwt

        jwks_client = _get_jwks_client(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token).key

        decode_options: dict[str, bool] = {}
        decode_kwargs: dict[str, Any] = {
            "key": signing_key,
            "algorithms": settings.OAUTH_ALGORITHMS,
            "options": decode_options,
            "leeway": settings.OAUTH_LEEWAY_SECONDS,
        }

        audience = settings.OAUTH_AUDIENCE.strip()
        if audience:
            decode_kwargs["audience"] = audience
        else:
            decode_options["verify_aud"] = False

        issuer = settings.OAUTH_ISSUER.strip()
        if issuer:
            decode_kwargs["issuer"] = issuer
        else:
            decode_options["verify_iss"] = False

        claims = jwt.decode(token, **decode_kwargs)

        required_scope = settings.OAUTH_REQUIRED_SCOPE.strip()
        if required_scope and not _scope_is_authorized(
            claims.get("scope") or claims.get("scp"), required_scope
        ):
            return False

        return True
    except Exception as exc:
        logger.debug("OAuth token validation failed: %s", exc)
        return False


def _normalize_mount_path(path: str) -> str:
    normalized = "/" + path.strip("/")
    return "/" if normalized == "//" else normalized


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _default_mount_path(transport: SupportedHTTPTransport) -> str:
    if transport == "sse":
        return "/sse"
    return "/mcp"


def _parse_transport(raw_value: str) -> SupportedHTTPTransport:
    normalized = raw_value.strip().lower()
    if normalized not in _SUPPORTED_HTTP_TRANSPORTS:
        supported = ", ".join(sorted(_SUPPORTED_HTTP_TRANSPORTS))
        raise ValueError(f"Unsupported transport '{raw_value}'. Supported: {supported}")
    return cast(SupportedHTTPTransport, normalized)


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
        description="Remote MCP endpoint with OAuth/API-key authentication",
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
            "auth": "oauth-or-api-key",
        }

    return app


app = create_http_app()


def main() -> None:
    """Run the authenticated MCP HTTP server (streamable HTTP default)."""
    host = os.getenv("MCP_HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_HTTP_PORT", "8000"))
    transport = _parse_transport(os.getenv("MCP_HTTP_TRANSPORT", "http"))
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
