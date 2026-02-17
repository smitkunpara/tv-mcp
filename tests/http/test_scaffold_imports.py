"""
Scaffold import tests – verify vercel package is importable.
"""

import pytest


class TestVercelScaffold:
    """Verify vercel package tree is importable."""

    def test_vercel_root(self):
        import vercel
        assert vercel is not None

    def test_vercel_app(self):
        from vercel.app import app, create_app
        assert app is not None
        assert create_app is not None

    def test_vercel_routers(self):
        import vercel.routers
        assert vercel.routers is not None

    def test_vercel_services(self):
        import vercel.services
        assert vercel.services is not None

    def test_vercel_routers_paper_trading(self):
        import vercel.routers.paper_trading
        assert vercel.routers.paper_trading is not None
