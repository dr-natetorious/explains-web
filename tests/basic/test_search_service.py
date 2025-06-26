import pytest
import asyncio
from src.services import NewsSearchService, NewsArticle

import httpx
from unittest.mock import patch

@pytest.mark.asyncio
async def test_search_headlines_success(monkeypatch):
    # Mock httpx.AsyncClient.get to return a fake response
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "data": [
                    {
                        "title": "Test Headline",
                        "description": "Test Description",
                        "url": "http://example.com",
                        "source": "Example Source",
                        "published_at": "2025-06-25T12:00:00Z",
                        "image_url": "http://example.com/image.jpg",
                        "categories": ["general"]
                    }
                ]
            }
    async def mock_get(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.get", new=mock_get):
        service = NewsSearchService(api_key="fake")
        articles = await service.search_headlines(region="american", category="general", limit=1)
        assert len(articles) == 1
        assert articles[0].title == "Test Headline"
        assert articles[0].category == "general"

@pytest.mark.asyncio
async def test_search_headlines_empty(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": []}
    async def mock_get(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.get", new=mock_get):
        service = NewsSearchService(api_key="fake")
        articles = await service.search_headlines(region="american", category="general", limit=1)
        assert articles == []

@pytest.mark.asyncio
async def test_search_by_keywords_success(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {
                "data": [
                    {
                        "title": "AI News",
                        "description": "AI Description",
                        "url": "http://example.com/ai",
                        "source": "AI Source",
                        "published_at": "2025-06-25T12:00:00Z",
                        "image_url": None,
                        "categories": ["technology"]
                    }
                ]
            }
    async def mock_get(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.get", new=mock_get):
        service = NewsSearchService(api_key="fake")
        articles = await service.search_by_keywords("AI", region="american", limit=1)
        assert len(articles) == 1
        assert articles[0].title == "AI News"
        assert articles[0].category == "technology"

@pytest.mark.asyncio
async def test_search_headlines_http_error(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            raise httpx.RequestError("error")
        def json(self):
            return {}
    async def mock_get(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.get", new=mock_get):
        service = NewsSearchService(api_key="fake")
        articles = await service.search_headlines(region="american", category="general", limit=1)
        assert articles == []

@pytest.mark.asyncio
async def test_search_by_keywords_http_error(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            raise httpx.RequestError("error")
        def json(self):
            return {}
    async def mock_get(*args, **kwargs):
        return MockResponse()
    with patch("httpx.AsyncClient.get", new=mock_get):
        service = NewsSearchService(api_key="fake")
        articles = await service.search_by_keywords("AI", region="american", limit=1)
        assert articles == []
