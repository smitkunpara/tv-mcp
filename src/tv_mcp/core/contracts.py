"""
Standardized internal response contracts for tv_mcp services.

All domain service functions return a ``ServiceResponse`` dict that follows
the tv_scraper v1 response envelope convention:

    {
        "status": "success" | "failed",
        "data":   <payload or None>,
        "metadata": { ... },
        "error":  <error string or None>,
    }

Helper constructors are provided instead of raw dict literals to keep the
shape consistent across the codebase.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# Type alias for readability
ServiceResponse = Dict[str, Any]


def success_response(
    data: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> ServiceResponse:
    """Build a successful service response envelope."""
    return {
        "status": "success",
        "data": data,
        "metadata": metadata or {},
        "error": None,
    }


def error_response(
    error: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ServiceResponse:
    """Build a failed service response envelope."""
    return {
        "status": "failed",
        "data": None,
        "metadata": metadata or {},
        "error": error,
    }
