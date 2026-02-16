"""
Scaffold import tests – verify new packages are importable.
"""

import pytest


class TestTvScrapperScaffold:
    """Verify tv_scrapper package tree is importable."""

    def test_tv_scrapper_root(self):
        import src.tv_scrapper
        assert hasattr(src.tv_scrapper, "__version__")

    def test_tv_scrapper_core(self):
        import src.tv_scrapper.core
        assert src.tv_scrapper.core is not None

    def test_tv_scrapper_transforms(self):
        import src.tv_scrapper.transforms
        assert src.tv_scrapper.transforms is not None

    def test_tv_scrapper_services(self):
        import src.tv_scrapper.services
        assert src.tv_scrapper.services is not None

    def test_tv_scrapper_adapters(self):
        import src.tv_scrapper.adapters
        assert src.tv_scrapper.adapters is not None

    def test_tv_scrapper_mcp(self):
        import src.tv_scrapper.mcp
        assert src.tv_scrapper.mcp is not None

    def test_tv_scrapper_mcp_tools(self):
        import src.tv_scrapper.mcp.tools
        assert src.tv_scrapper.mcp.tools is not None
