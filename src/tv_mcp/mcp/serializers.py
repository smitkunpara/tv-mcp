"""
Shared TOON encoding and error serialization utilities.

All MCP tool handlers use these helpers to produce consistent,
token-efficient responses.
"""

from typing import Any, Dict, Optional

from toon import encode as _toon_encode


def toon_encode(data: Any) -> str:
    """Wrap python-toon's encoder for consistent usage across tools."""
    return _toon_encode(data)


def serialize_success(data: Any) -> str:
    """Return a TOON-encoded string for a successful result."""
    return toon_encode(data)


def serialize_error(error_msg: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Return a TOON-encoded error dict.

    Args:
        error_msg: Human-readable error description.
        details: Optional extra context (e.g. valid values, help text).
    """
    payload: Dict[str, Any] = {
        "success": False,
        "error": error_msg,
    }
    if details is not None:
        payload["details"] = details
    return toon_encode(payload)
