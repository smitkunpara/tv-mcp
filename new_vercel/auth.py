"""
Auth dependencies for the new_vercel FastAPI application.

Provides ``verify_admin`` and ``verify_client`` dependency functions
that validate API keys sent via custom HTTP headers.
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from src.tv_mcp.core.settings import settings

admin_header_scheme = APIKeyHeader(name="X-Admin-Key", auto_error=False)
client_header_scheme = APIKeyHeader(name="X-Client-Key", auto_error=False)


async def verify_admin(key: str = Security(admin_header_scheme)) -> str:
    """Only allows access if X-Admin-Key matches the configured value."""
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid Admin Key")
    return key


async def verify_client(key: str = Security(client_header_scheme)) -> str:
    """Only allows access if X-Client-Key matches the configured value."""
    if key != settings.CLIENT_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid Client Key")
    return key
