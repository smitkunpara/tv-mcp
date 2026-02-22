"""
Vercel deployment config — public URL and OpenAPI server base URL.

Used so OpenAPI spec and root endpoint show your stable alias
(e.g. https://tradingview-mcp.vercel.app) instead of the deployment URL.
"""

import os
import re


# Default when not on Vercel (e.g. local dev)
DEFAULT_PUBLIC_URL = "https://tradingview-mcp.vercel.app"


def get_public_url() -> str:
    """
    Base URL for the API (OpenAPI servers, root endpoint).

    Prefer PUBLIC_APP_URL so you can set your stable alias (e.g. tradingview-mcp.vercel.app).
    On Vercel, VERCEL_URL is set to the deployment hostname (no scheme); we add https.
    """
    url = os.getenv("PUBLIC_APP_URL") or os.getenv("VERCEL_URL")
    if not url:
        return DEFAULT_PUBLIC_URL
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url.rstrip("/")
