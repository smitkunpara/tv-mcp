"""
Integration tests for client HTTP routes using REAL data.
"""

import os
import pytest
from starlette.testclient import TestClient

# Skip if no cookie or no app
pytestmark = pytest.mark.skipif(
    not os.getenv("TRADINGVIEW_COOKIE"),
    reason="TRADINGVIEW_COOKIE not set"
)

def test_http_historical_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/historical-data",
        json={
            "exchange": "BINANCE",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "numb_price_candles": 2
        },
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()
    # Decode data would verify it's TOON but just checking existence is good integration check

def test_http_news_headlines_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/news-headlines",
        json={"symbol": "AAPL", "exchange": "NASDAQ"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()

def test_http_all_indicators_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/all-indicators",
        json={"symbol": "NIFTY", "exchange": "NSE", "timeframe": "1m"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()

def test_http_ideas_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/ideas",
        json={"symbol": "BTCUSD"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()

def test_http_minds_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/minds",
        json={"symbol": "TSLA", "exchange": "NASDAQ", "limit": 2},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()

def test_http_options_real(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/option-chain-greeks",
        json={"symbol": "NIFTY", "exchange": "NSE"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert "data" in resp.json()
