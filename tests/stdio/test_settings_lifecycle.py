"""
Settings lifecycle tests for src.tv_mcp.core.settings.

Verifies environment loading, expected attributes, update_cookie(),
and singleton identity.
"""

import os
import pytest
from unittest.mock import patch


class TestSettingsFromEnv:
    """Settings loads values from environment variables."""

    def test_loads_cookie_from_env(self) -> None:
        with patch.dict(os.environ, {"TRADINGVIEW_COOKIE": "test_cookie_value"}):
            # Force a fresh instance
            from src.tv_mcp.core.settings import Settings

            inst = object.__new__(Settings)
            inst._initialize()
            assert inst.TRADINGVIEW_COOKIE == "test_cookie_value"

    def test_loads_client_key_from_env(self) -> None:
        with patch.dict(os.environ, {"TV_CLIENT_KEY": "my-client-key"}):
            from src.tv_mcp.core.settings import Settings

            inst = object.__new__(Settings)
            inst._initialize()
            assert inst.CLIENT_API_KEY == "my-client-key"

    def test_empty_keys_when_env_missing(self) -> None:
        """When env vars are absent, API key settings remain empty."""
        env_overrides = {"TV_CLIENT_KEY": ""}
        with patch.dict(os.environ, env_overrides, clear=False):
            from src.tv_mcp.core.settings import Settings

            inst = object.__new__(Settings)
            # Remove the keys entirely so getenv returns default
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TV_CLIENT_KEY", None)
                inst._initialize()
            assert inst.CLIENT_API_KEY == ""


class TestSettingsAttributes:
    """Settings has expected attributes."""

    def test_has_tradingview_cookie(self) -> None:
        from src.tv_mcp.core.settings import settings

        assert hasattr(settings, "TRADINGVIEW_COOKIE")
        assert isinstance(settings.TRADINGVIEW_COOKIE, str)

    def test_has_client_api_key(self) -> None:
        from src.tv_mcp.core.settings import settings

        assert hasattr(settings, "CLIENT_API_KEY")
        assert isinstance(settings.CLIENT_API_KEY, str)

    def test_has_user_agent(self) -> None:
        from src.tv_mcp.core.settings import settings

        assert hasattr(settings, "USER_AGENT")
        assert isinstance(settings.USER_AGENT, str)
        assert len(settings.USER_AGENT) > 0


class TestUpdateCookie:
    """update_cookie() changes the cookie value in memory and os.environ."""

    def test_update_changes_in_memory(self) -> None:
        from src.tv_mcp.core.settings import settings

        old_value = settings.TRADINGVIEW_COOKIE
        try:
            settings.update_cookie("new-cookie-string")
            assert settings.TRADINGVIEW_COOKIE == "new-cookie-string"
        finally:
            # Restore to avoid poisoning other tests
            settings.update_cookie(old_value)

    def test_update_changes_os_environ(self) -> None:
        from src.tv_mcp.core.settings import settings

        old_value = settings.TRADINGVIEW_COOKIE
        try:
            settings.update_cookie("env-cookie-test")
            assert os.environ["TRADINGVIEW_COOKIE"] == "env-cookie-test"
        finally:
            settings.update_cookie(old_value)


class TestSettingsSingleton:
    """Settings singleton returns the same instance."""

    def test_same_instance(self) -> None:
        from src.tv_mcp.core.settings import Settings

        a = Settings()
        b = Settings()
        assert a is b

    def test_global_settings_is_instance(self) -> None:
        from src.tv_mcp.core.settings import Settings, settings

        assert isinstance(settings, Settings)
