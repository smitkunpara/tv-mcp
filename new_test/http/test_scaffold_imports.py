"""
Scaffold import tests – verify new_vercel package is importable.
"""

import pytest


class TestNewVercelScaffold:
    """Verify new_vercel package tree is importable."""

    def test_new_vercel_root(self):
        import new_vercel
        assert new_vercel is not None

    def test_new_vercel_routers(self):
        import new_vercel.routers
        assert new_vercel.routers is not None

    def test_new_vercel_services(self):
        import new_vercel.services
        assert new_vercel.services is not None
