"""
Scaffold import tests – verify new packages are importable.
"""

import pytest


class TestTvScrapperScaffold:
    """Verify tv_mcp package tree is importable."""

    def test_tv_mcp_root(self):
        import src.tv_mcp
        assert hasattr(src.tv_mcp, "__version__")

    def test_tv_mcp_core(self):
        import src.tv_mcp.core
        assert src.tv_mcp.core is not None

    def test_tv_mcp_transforms(self):
        import src.tv_mcp.transforms
        assert src.tv_mcp.transforms is not None

    def test_tv_mcp_services(self):
        import src.tv_mcp.services
        assert src.tv_mcp.services is not None

    def test_tv_mcp_adapters(self):
        import src.tv_mcp.adapters
        assert src.tv_mcp.adapters is not None

    def test_tv_mcp_mcp(self):
        import src.tv_mcp.mcp
        assert src.tv_mcp.mcp is not None

    def test_tv_mcp_mcp_tools(self):
        import src.tv_mcp.mcp.tools
        assert src.tv_mcp.mcp.tools is not None

    def test_tv_mcp_services_paper_trading(self):
        import src.tv_mcp.services.paper_trading
        assert src.tv_mcp.services.paper_trading is not None

    def test_tv_mcp_mcp_tools_paper_trading(self):
        import src.tv_mcp.mcp.tools.paper_trading
        assert src.tv_mcp.mcp.tools.paper_trading is not None
