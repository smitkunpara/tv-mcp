"""Vercel ASGI entrypoint for authenticated MCP over SSE."""

import os
import sys
from pathlib import Path

from fastapi import FastAPI

# Force local src package resolution on Vercel before vendored modules.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _PROJECT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from tv_mcp.mcp.http_server import create_http_app


def create_app() -> FastAPI:
    """Build a Vercel-ready FastAPI app with MCP SSE transport."""
    mount_path = os.getenv("MCP_SSE_PATH") or os.getenv("MCP_HTTP_PATH") or "/sse"
    return create_http_app(transport="sse", mcp_mount_path=mount_path)


app = create_app()
