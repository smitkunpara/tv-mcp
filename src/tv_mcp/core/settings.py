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

        # Security keys must come from environment variables.
        self.ADMIN_API_KEY: str = os.getenv("TV_ADMIN_KEY", "")
        self.CLIENT_API_KEY: str = os.getenv("TV_CLIENT_KEY", "")

        # Paper Trading Configuration
        self.PAPER_TRADING_CAPITAL: float = float(os.getenv("PAPER_TRADING_CAPITAL", "100000"))
        self.RISK_PER_TRADE_PCT: float = float(os.getenv("RISK_PER_TRADE_PCT", "2.0"))
        self.MIN_RISK_REWARD_RATIO: float = float(os.getenv("MIN_RISK_REWARD_RATIO", "1.5"))
        self.TRAILING_SL_ENABLED: bool = os.getenv("TRAILING_SL_ENABLED", "false").lower() == "true"
        self.TRAILING_SL_STEP_PCT: float = float(os.getenv("TRAILING_SL_STEP_PCT", "0.5"))
        self.MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "10"))
        
        # Alert Caching: when true, all MCP tools include triggered alerts in their response
        # When false, alerts are only returned by alert_manager
        self.INJECT_ALERTS_IN_ALL_TOOLS: bool = os.getenv("INJECT_ALERTS_IN_ALL_TOOLS", "false").lower() == "true"

        # Alert manager timeout in seconds — how long alert_manager waits before returning
        _raw_timeout = int(os.getenv("ALERT_MANAGER_TIMEOUT_SECONDS", "300"))
        if _raw_timeout < 0:
            print(
                f"\u26a0\ufe0f ALERT_MANAGER_TIMEOUT_SECONDS={_raw_timeout} is invalid "
                "(must be >= 0). Defaulting to 300 seconds."
            )
            _raw_timeout = 300
        self.ALERT_MANAGER_TIMEOUT_SECONDS: int = _raw_timeout

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
