"""
Tests that verify both old and new entrypoints resolve correctly.

Ensures migration doesn't break script entrypoints or module execution paths.
"""

import importlib

import pytest


class TestMCPEntrypoints:
    """Verify MCP server entrypoints."""

    def test_new_mcp_server_importable(self):
        mod = importlib.import_module("src.tv_mcp.mcp.server")
        assert hasattr(mod, "mcp"), "FastMCP instance must be exported"
        assert hasattr(mod, "main"), "main() function must be exported"

    def test_new_mcp_init_exports(self):
        mod = importlib.import_module("src.tv_mcp.mcp")
        assert hasattr(mod, "mcp"), "mcp must be re-exported from __init__"
        assert hasattr(mod, "main"), "main must be re-exported from __init__"

    def test_legacy_mcp_main_still_importable(self):
        mod = importlib.import_module("src.tradingview_mcp.main")
        assert hasattr(mod, "mcp"), "Legacy mcp must still exist"
        assert hasattr(mod, "main"), "Legacy main must still exist"


class TestVercelEntrypoints:
    """Verify HTTP API entrypoints."""

    def test_new_vercel_app_importable(self):
        mod = importlib.import_module("new_vercel.app")
        assert hasattr(mod, "app"), "FastAPI app instance must be exported"
        assert hasattr(mod, "create_app"), "create_app factory must be exported"

    def test_new_vercel_init_exports(self):
        mod = importlib.import_module("new_vercel")
        assert hasattr(mod, "app"), "app must be re-exported from __init__"
        assert hasattr(mod, "create_app"), "create_app must be re-exported from __init__"

    def test_legacy_vercel_index_still_importable(self):
        mod = importlib.import_module("vercel.index")
        assert hasattr(mod, "app"), "Legacy vercel app must still exist"


class TestServiceImports:
    """Verify all service modules are importable from tv_mcp."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "src.tv_mcp.services.historical",
            "src.tv_mcp.services.news",
            "src.tv_mcp.services.ideas",
            "src.tv_mcp.services.minds",
            "src.tv_mcp.services.technicals",
            "src.tv_mcp.services.options",
        ],
    )
    def test_service_importable(self, module_path: str):
        mod = importlib.import_module(module_path)
        assert mod is not None

    @pytest.mark.parametrize(
        "module_path",
        [
            "src.tv_mcp.core.settings",
            "src.tv_mcp.core.validators",
            "src.tv_mcp.core.auth",
            "src.tv_mcp.core.contracts",
        ],
    )
    def test_core_importable(self, module_path: str):
        mod = importlib.import_module(module_path)
        assert mod is not None

    @pytest.mark.parametrize(
        "module_path",
        [
            "src.tv_mcp.transforms.ohlc",
            "src.tv_mcp.transforms.news",
            "src.tv_mcp.transforms.time",
        ],
    )
    def test_transform_importable(self, module_path: str):
        mod = importlib.import_module(module_path)
        assert mod is not None
