"""
FastAPI application factory for the vercel HTTP server.

Creates the ``app`` singleton used by the ASGI entrypoint.
"""

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

from .config import get_public_url
from .routers import public, client, admin
# Comment the next line to disable paper trading endpoints
from .routers import paper_trading


def _generate_operation_id(route: APIRoute) -> str:
    """Create short, deterministic operation IDs for OpenAPI consumers."""
    method = sorted(route.methods)[0].lower() if route.methods else "op"
    path = route.path_format.strip("/").replace("/", "_").replace("-", "_")
    if not path:
        path = "root"
    return f"{method}_{path}"


def create_app() -> FastAPI:
    """Build and return a fully-configured FastAPI application."""
    base_url = get_public_url()
    application = FastAPI(
        title="TradingView HTTP API",
        description="REST API for TradingView data scraping tools",
        version="1.0.0",
        servers=[{"url": base_url}],
        generate_unique_id_function=_generate_operation_id,
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
    # Comment the next line to disable paper trading endpoints
    # application.include_router(paper_trading.router)
    return application


app = create_app()
