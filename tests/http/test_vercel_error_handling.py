
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient
from vercel.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    from src.tv_mcp.core.settings import settings
    return {"X-Client-Key": settings.CLIENT_API_KEY}

@pytest.fixture
def admin_headers():
    from src.tv_mcp.core.settings import settings
    return {"X-Admin-Key": settings.ADMIN_API_KEY}

def test_historical_data_failure_returns_400(client, auth_headers):
    with patch("vercel.routers.client.fetch_historical_data") as mock_svc:
        mock_svc.return_value = {"success": False, "message": "Symbol not found"}
        resp = client.post(
            "/historical-data",
            json={"exchange": "NSE", "symbol": "INVALID", "timeframe": "1d", "numb_price_candles": 10},
            headers=auth_headers
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Symbol not found"

def test_news_headlines_failure_returns_500(client, auth_headers):
    with patch("vercel.routers.client.fetch_news_headlines") as mock_svc:
        mock_svc.side_effect = Exception("Service error")
        resp = client.post(
            "/news-headlines",
            json={"symbol": "INVALID", "exchange": "NSE"},
            headers=auth_headers
        )
    assert resp.status_code == 500
    assert "Service error" in resp.json()["detail"]

def test_news_content_all_failed_returns_400(client, auth_headers):
    with patch("vercel.routers.client.fetch_news_content") as mock_svc:
        mock_svc.return_value = [{"success": False, "error": "Story not found"}]
        resp = client.post(
            "/news-content",
            json={"story_ids": ["id1"]},
            headers=auth_headers
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Story not found"

def test_update_cookies_failure_returns_400(client, admin_headers):
    with patch("vercel.routers.admin.fetch_ideas") as mock_svc:
        mock_svc.return_value = {"success": False, "message": "Invalid cookies"}
        resp = client.post(
            "/update-cookies",
            json={"cookies": [{"name": "n", "value": "v"}]},
            headers=admin_headers
        )
    assert resp.status_code == 400
    assert "Invalid cookies" in resp.json()["detail"]
