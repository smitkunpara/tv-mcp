"""
Authentication module for tv_mcp.

Handles JWT token extraction from TradingView, token validation/caching,
and expiry management.  Extracted from legacy auth.py + the token cache
logic that previously lived in tradingview_tools.py.
"""

import base64
import json
import re
import threading
import time
from typing import Dict, Optional

import jwt as pyjwt
import requests

from .settings import settings


# ── Token cache (module-level, thread-safe) ─────────────────────────
_token_cache: Dict[str, object] = {
    "token": None,
    "expiry": 0,
}
_token_lock = threading.Lock()


def extract_jwt_token() -> Optional[str]:
    """Extract JWT token from TradingView using cookies from settings.

    Returns:
        JWT token string if successful, None otherwise.

    Raises:
        ValueError: If cookies are not set or token extraction fails.
    """
    cookie = settings.TRADINGVIEW_COOKIE
    if not cookie:
        raise ValueError(
            "Account is not connected with MCP. Please set TRADINGVIEW_COOKIE "
            "environment variable to connect your account."
        )

    url = settings.TRADINGVIEW_URL
    if not url:
        raise ValueError(
            "TRADINGVIEW_URL environment variable is not set. "
            "Please set it to a valid TradingView chart URL."
        )

    headers = {
        "Cookie": cookie,
        "User-Agent": settings.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=0, i",
        "Te": "trailers",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text

        jwt_pattern = r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+"
        potential_tokens = re.findall(jwt_pattern, html_content)

        def _verify_jwt(token: str) -> bool:
            try:
                parts = token.split(".")
                if len(parts) != 3:
                    return False
                header_b64, payload_b64, _ = parts
                header_b64 += "=" * (4 - len(header_b64) % 4)
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                header = json.loads(base64.urlsafe_b64decode(header_b64))
                json.loads(base64.urlsafe_b64decode(payload_b64))
                return "alg" in header and "typ" in header
            except Exception:
                return False

        for token in potential_tokens:
            if _verify_jwt(token):
                return token

        raise ValueError(
            "Token is not generated with cookies. Please verify your cookies "
            "and ensure they are valid and not expired."
        )

    except requests.RequestException as e:
        raise ValueError(
            f"Failed to extract JWT token from TradingView: {e}. "
            "Please verify your cookies and network connection."
        )


def get_token_info(token: str) -> Dict:
    """Decode JWT token and extract expiry information."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {"valid": False, "error": "Invalid token format"}
        payload_b64 = parts[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return {
            "valid": True,
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "user_id": payload.get("user_id"),
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def get_valid_jwt_token(force_refresh: bool = False) -> str:
    """Get a valid JWT token, reusing cached token if not expired.

    Args:
        force_refresh: Force token refresh even if cached token is valid.

    Raises:
        ValueError: If unable to generate token.
    """
    global _token_cache

    with _token_lock:
        current_time = int(time.time())

        if (
            not force_refresh
            and _token_cache["token"]
            and _token_cache["expiry"] > (current_time + 60)
        ):
            return _token_cache["token"]

        try:
            token = extract_jwt_token()
            if not token:
                raise ValueError("Failed to extract JWT token")

            token_info = get_token_info(token)
            if not token_info.get("valid"):
                raise ValueError(
                    f"Invalid token: {token_info.get('error', 'Unknown error')}"
                )

            _token_cache["token"] = token
            _token_cache["expiry"] = token_info.get(
                "exp", current_time + 3600
            )
            return token

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"Token is not generated with cookies. Please verify your cookies. Error: {e}"
            )


def is_jwt_token_valid(token: str) -> bool:
    """Check if the provided JWT token is valid (not expired)."""
    try:
        decoded = pyjwt.decode(token, options={"verify_signature": False})
        exp = decoded.get("exp")
        return exp is not None and exp > int(time.time())
    except Exception:
        return False
