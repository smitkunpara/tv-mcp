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
