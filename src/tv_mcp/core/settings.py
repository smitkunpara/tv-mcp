"""
Centralized Configuration Manager for tv_mcp.

Provides a singleton Settings class that loads environment variables once
and supports runtime cookie updates.
"""

import os
from dotenv import load_dotenv, set_key

# Load .env file immediately
load_dotenv()


class Settings:
    """Singleton application settings loaded from environment variables."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initial load of configuration from environment."""
        self.TRADINGVIEW_COOKIE: str = os.getenv("TRADINGVIEW_COOKIE", "")
        self.TRADINGVIEW_URL: str = os.getenv(
            "TRADINGVIEW_URL", "https://in.tradingview.com/chart/"
        )
        self.USER_AGENT: str = os.getenv(
            "TRADINGVIEW_USER_AGENT",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.ENV_FILE_PATH: str = os.path.join(os.getcwd(), ".env")

        # Client key for authenticated MCP HTTP/SSE access.
        self.CLIENT_API_KEY: str = os.getenv("TV_CLIENT_KEY", "")

        # Optional OAuth JWT validation config (with API key fallback).
        self.OAUTH_JWKS_URL: str = os.getenv("TV_OAUTH_JWKS_URL", "")
        self.OAUTH_ISSUER: str = os.getenv("TV_OAUTH_ISSUER", "")
        self.OAUTH_AUDIENCE: str = os.getenv("TV_OAUTH_AUDIENCE", "")
        self.OAUTH_REQUIRED_SCOPE: str = os.getenv("TV_OAUTH_REQUIRED_SCOPE", "")

        oauth_algorithms_raw = os.getenv("TV_OAUTH_ALGORITHMS", "RS256")
        self.OAUTH_ALGORITHMS: list[str] = [
            algo.strip() for algo in oauth_algorithms_raw.split(",") if algo.strip()
        ] or ["RS256"]

        leeway_raw = os.getenv("TV_OAUTH_LEEWAY_SECONDS", "30")
        try:
            self.OAUTH_LEEWAY_SECONDS: int = max(0, int(leeway_raw))
        except ValueError:
            self.OAUTH_LEEWAY_SECONDS = 30

    def update_cookie(self, new_cookie_string: str):
        """Update cookie in memory, env var, and optionally persist to .env."""
        # 1. In-memory (immediate effect for all modules)
        self.TRADINGVIEW_COOKIE = new_cookie_string

        # 2. Environment variable (for libraries checking os.environ)
        os.environ["TRADINGVIEW_COOKIE"] = new_cookie_string

        # 3. Persist to file (works locally, ignored on read-only envs like Vercel)
        try:
            if os.path.exists(self.ENV_FILE_PATH):
                set_key(self.ENV_FILE_PATH, "TRADINGVIEW_COOKIE", new_cookie_string)
                print("✅ Updated .env file locally.")
            else:
                print("⚠️ .env file not found, skipping persistence.")
        except Exception as e:
            print(
                f"⚠️ Could not write to .env (expected on Vercel/ReadOnly): {e}"
            )


# Global singleton instance
settings = Settings()
