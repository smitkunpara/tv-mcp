"""
Shared fixtures and helpers for the new_test suite.
"""

import pytest
import sys
import os
from dotenv import load_dotenv

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load environment variables once
load_dotenv()


@pytest.fixture(scope="session")
def project_root():
    """Return absolute path to the project root."""
    return _PROJECT_ROOT
