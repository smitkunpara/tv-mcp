"""
Scaffold import tests – verify new packages are importable.
"""

import pytest


class TestTvScrapperScaffold:
    """Verify tv_mcp package tree is importable."""

    def test_tv_mcp_root(self):
        import tv_mcp
        assert hasattr(tv_mcp, "__version__")

    def test_tv_mcp_core(self):
        import tv_mcp.core
        assert tv_mcp.core is not None

    def test_tv_mcp_transforms(self):
        import tv_mcp.transforms
        assert tv_mcp.transforms is not None

    def test_tv_mcp_services(self):
        import tv_mcp.services
        assert tv_mcp.services is not None

    def test_tv_mcp_adapters(self):
        import tv_mcp.adapters
        assert tv_mcp.adapters is not None

    def test_tv_mcp_mcp(self):
        import tv_mcp.mcp
        assert tv_mcp.mcp is not None

    def test_tv_mcp_mcp_tools(self):
        import tv_mcp.mcp.tools
        assert tv_mcp.mcp.tools is not None
