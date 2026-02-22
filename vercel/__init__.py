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

Do not import .app here to avoid circular import when Vercel loads vercel.app:
app.py imports .routers, which loads this package; importing .app here would
request app before app.py has finished defining app.
Use: from vercel.app import app, create_app
"""

__all__ = ["app", "create_app"]
