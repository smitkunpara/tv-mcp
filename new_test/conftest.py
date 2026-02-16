"""
Shared fixtures and helpers for the new_test suite.
"""

import pytest
import sys
import os
from dotenv import load_dotenv
from starlette.testclient import TestClient

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load environment variables once
load_dotenv()


@pytest.fixture(scope="session")
def project_root() -> str:
    """Return absolute path to the project root."""
    return _PROJECT_ROOT


@pytest.fixture()
def client() -> TestClient:
    """TestClient for the new_vercel FastAPI app."""
    from new_vercel.app import app

    return TestClient(app)


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Headers with a valid X-Client-Key."""
    from src.tv_mcp.core.settings import settings

    return {"X-Client-Key": settings.CLIENT_API_KEY}


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    """Headers with a valid X-Admin-Key."""
    from src.tv_mcp.core.settings import settings

    return {"X-Admin-Key": settings.ADMIN_API_KEY}
