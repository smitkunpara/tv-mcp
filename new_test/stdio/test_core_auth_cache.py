"""
Tests for tv_scrapper.core.auth token cache and helpers.

Uses only deterministic (non-network) behaviors:
- get_token_info decoding
- is_jwt_token_valid expiry logic
"""

import pytest
import time
import base64
import json

from src.tv_scrapper.core.auth import get_token_info, is_jwt_token_valid


def _make_jwt(payload: dict, header: dict | None = None) -> str:
    """Build a minimal unsigned JWT for testing."""
    hdr = header or {"alg": "HS256", "typ": "JWT"}
    h = base64.urlsafe_b64encode(json.dumps(hdr).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{h}.{p}.fakesig"


class TestGetTokenInfo:
    def test_valid_token(self):
        payload = {"exp": 9999999999, "iat": 1000000000, "user_id": 42}
        token = _make_jwt(payload)
        info = get_token_info(token)
        assert info["valid"] is True
        assert info["exp"] == 9999999999
        assert info["user_id"] == 42

    def test_invalid_format(self):
        info = get_token_info("not.a.jwt.at.all")
        assert info["valid"] is False

    def test_two_parts_only(self):
        info = get_token_info("abc.def")
        assert info["valid"] is False


class TestIsJwtTokenValid:
    def test_future_expiry_is_valid(self):
        payload = {"exp": int(time.time()) + 3600}
        token = _make_jwt(payload)
        assert is_jwt_token_valid(token) is True

    def test_past_expiry_is_invalid(self):
        payload = {"exp": int(time.time()) - 3600}
        token = _make_jwt(payload)
        assert is_jwt_token_valid(token) is False

    def test_no_exp_is_invalid(self):
        payload = {"iat": int(time.time())}
        token = _make_jwt(payload)
        assert is_jwt_token_valid(token) is False

    def test_garbage_is_invalid(self):
        assert is_jwt_token_valid("garbage") is False
