"""
FastAPI application factory for the new_vercel HTTP server.

Creates the ``app`` singleton used by the ASGI entrypoint.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import public, client, admin


def create_app() -> FastAPI:
    """Build and return a fully-configured FastAPI application."""
    vercel_backend_url = os.getenv("VERCEL_URL", None)
    application = FastAPI(
        title="TradingView HTTP API",
        description="REST API for TradingView data scraping tools",
        version="1.0.0",
        servers=[{"url": vercel_backend_url}] if vercel_backend_url else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(public.router)
    application.include_router(client.router)
    application.include_router(admin.router)
    return application


app = create_app()
