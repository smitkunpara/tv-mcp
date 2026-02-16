"""
Tests that verify entrypoints and imports resolve correctly.

Ensures the modular tv_mcp and vercel packages are properly importable.
"""

import importlib

import pytest


class TestMCPEntrypoints:
    """Verify MCP server entrypoints."""

    def test_mcp_server_importable(self):
        mod = importlib.import_module("src.tv_mcp.mcp.server")
        assert hasattr(mod, "mcp"), "FastMCP instance must be exported"
        assert hasattr(mod, "main"), "main() function must be exported"

    def test_mcp_init_exports(self):
        mod = importlib.import_module("src.tv_mcp.mcp")
        assert hasattr(mod, "mcp"), "mcp must be re-exported from __init__"
        assert hasattr(mod, "main"), "main must be re-exported from __init__"


class TestVercelEntrypoints:
    """Verify HTTP API entrypoints."""

    def test_vercel_app_importable(self):
        mod = importlib.import_module("vercel.app")
        assert hasattr(mod, "app"), "FastAPI app instance must be exported"
        assert hasattr(mod, "create_app"), "create_app factory must be exported"

    def test_vercel_init_exports(self):
        mod = importlib.import_module("vercel")
        assert hasattr(mod, "app"), "app must be re-exported from __init__"
        assert hasattr(mod, "create_app"), "create_app must be re-exported from __init__"


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
        ],
    )
    def test_transform_importable(self, module_path: str):
        mod = importlib.import_module(module_path)
        assert mod is not None
