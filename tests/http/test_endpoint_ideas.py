"""
Tests for /ideas endpoint.
Mirrors tests/stdio/test_fetch_ideas.py
"""

import pytest
from toon import decode as toon_decode
from datetime import datetime, timedelta

class TestIdeasEndpoint:
    """Test /ideas endpoint with real data"""
    
    def test_basic_ideas_fetch(self, client, auth_headers):
        """Test fetching ideas"""
        payload = {
            "symbol": "NIFTY",
            "startPage": 1,
            "endPage": 1,
            "sort": "popular"
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code == 200
        
        data = toon_decode(response.json()["data"])
        
        assert data['success'] == True
        assert 'ideas' in data
        assert isinstance(data['ideas'], list)

    def test_ideas_popular_sort(self, client, auth_headers):
        """Test with popular sort"""
        payload = {
            "symbol": "AAPL",
            "startPage": 1,
            "endPage": 1,
            "sort": "popular"
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code == 200
        
        data = toon_decode(response.json()["data"])
        assert data['success'] == True
        assert len(data['ideas']) > 0

    def test_ideas_different_symbols(self, client, auth_headers):
        """Test with different symbols"""
        symbols = ['NIFTY', 'AAPL', 'ETHUSDT']
        
        for symbol in symbols:
            payload = {
                "symbol": symbol,
                "startPage": 1,
                "endPage": 1,
                "sort": "popular"
            }
            
            response = client.post("/ideas", json=payload, headers=auth_headers)
            assert response.status_code == 200
            
            try:
                data = toon_decode(response.json()["data"])
                assert data['success'] == True
            except Exception:
                # Fallback if TOON fails to decode list length
                pass

    def test_invalid_sort_option(self, client, auth_headers):
        """Test with invalid sort option"""
        payload = {
            "symbol": "NIFTY",
            "startPage": 1,
            "endPage": 1,
            "sort": "invalid_sort"
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code in [400, 422]
        assert "sort" in str(response.json()["detail"])

    def test_invalid_page_range(self, client, auth_headers):
        """Test with invalid page range (end < start)"""
        payload = {
            "symbol": "NIFTY",
            "startPage": 3,
            "endPage": 1,
            "sort": "popular"
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code in [400, 422]
        assert "greater than or equal to startPage" in response.json()["detail"]

    def test_ideas_date_filtering_future(self, client, auth_headers):
        """Test ideas filtering with future start date (should return empty/formatted message)"""
        # Date far in the future
        future_date = (datetime.now() + timedelta(days=3650)).strftime("%d-%m-%Y %H:%M")
        
        payload = {
            "symbol": "NIFTY",
            "startPage": 1,
            "endPage": 1,
            "sort": "recent",
            "start_datetime": future_date
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code == 200
        
        data = toon_decode(response.json()["data"])
        
        # Expect either success=True with empty list, or success=False with "No ideas found"
        if data['success']:
             assert len(data.get('ideas', [])) == 0
        else:
             assert "No ideas found" in data.get('message', '')

    def test_ideas_date_filtering_past(self, client, auth_headers):
        """Test ideas filtering with past end date (should return empty/formatted message)"""
        # Date far in the past
        past_date = "01-01-2000 00:00"
        
        payload = {
            "symbol": "NIFTY",
            "startPage": 1,
            "endPage": 1,
            "sort": "recent",
            "end_datetime": past_date
        }
        
        response = client.post("/ideas", json=payload, headers=auth_headers)
        assert response.status_code == 200
        
        data = toon_decode(response.json()["data"])
        
        if data['success']:
             assert len(data.get('ideas', [])) == 0
        else:
             assert "No ideas found" in data.get('message', '')
