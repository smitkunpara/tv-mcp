"""
vercel - Modular FastAPI HTTP server for TradingView MCP.

Replaces the monolithic vercel/index.py with organized routers,
services, schemas, and auth while preserving the same external API
surface and deployment entrypoint.

Sub-packages:
    routers   – public, client, and admin route modules
    services  – per-domain endpoint service functions
    auth      – API key header verification dependencies
    schemas   – Pydantic request models
    app       – FastAPI application factory
"""

# Don't import app at module level to avoid circular import issues
# Import directly from vercel.app when needed
__all__: list[str] = []
