"""
Centralized Configuration Manager for tv_mcp.

Provides a singleton Settings class that loads environment variables once
and supports runtime cookie updates.  This is a direct extraction from
the legacy src/tradingview_mcp/config.py – the legacy module will become
a thin re-export shim.
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

        # Security keys (defaults provided for local dev)
        self.ADMIN_API_KEY: str = os.getenv("TV_ADMIN_KEY", "admin-secret-123")
        self.CLIENT_API_KEY: str = os.getenv("TV_CLIENT_KEY", "client-secret-123")

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
