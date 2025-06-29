"""
News Search Service using TheNewsAPI.com
Provides simple interface for fetching news headlines by region and topic.
"""

from enum import StrEnum
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os
import asyncio
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsSource(BaseModel):
    id: Optional[str]=None
    name: Optional[str]=None

class NewsSearchResponse(BaseModel):
    """Data structure for news headlines"""
    status: str
    total_results: int = Field(..., description="Total number of results found", alias="totalResults")
    articles: List['NewsArticle']  = Field(default_factory=list, description="List of news articles")

class NewsArticle(BaseModel):
    """Data structure for a news article"""
    title: Optional[str] = None
    
    description: Optional[str] = None
    published_at: Optional[str]=None

    url: str
    source: Optional[NewsSource] = None
    urlToImage: Optional[str] = None
    author: Optional[str] = None

    category: Optional[str] = None
    content: Optional[str] = None

class Endpoints(StrEnum):
    TOP_HEADLINES = 'top-headlines'
    EVERYTHING = 'everything'

class NewsSearchService:
    """Service for searching news using TheNewsAPI.com"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the news search service
        
        Args:
            api_key: TheNewsAPI key (optional - free tier works without key)
        """
        self.api_key = api_key or os.getenv('THENEWSAPI_KEY')
        self.base_url = "https://newsapi.org/v2/"
        
        # Regional mappings for news sources
        self.regions = {
            'american': {
                'countries': ['us'],
                'sources': ['cnn.com', 'nytimes.com', 'washingtonpost.com', 'reuters.com', 'ap.org']
            },
            'european': {
                'countries': ['gb', 'de', 'fr', 'it', 'es'],
                'sources': ['bbc.com', 'theguardian.com', 'reuters.com', 'dw.com']
            },
            'asian': {
                'countries': ['jp', 'kr', 'sg', 'in', 'cn'],
                'sources': ['reuters.com', 'nikkei.com', 'scmp.com']
            }
        }
        
        # Category mappings
        self.categories = {
            'general': 'general',
            'politics': 'politics', 
            'business': 'business',
            'technology': 'tech',
            'sports': 'sports',
            'entertainment': 'entertainment',
            'health': 'health',
            'science': 'science'
        }

    async def search_headlines(self, 
                        region: str = 'american',
                        category: str = 'general',
                        limit: int = 20,
                        hours_back: int = 72) -> NewsSearchResponse:
        """
        Search for top headlines by region and category
        
        Args:
            region: 'american', 'european', or 'asian'
            category: news category (general, politics, business, etc.)
            limit: number of articles to return
            hours_back: how many hours back to search
            
        Returns:
            NewsSearchResponse object
        """
        try:
            # Build API parameters
            params = {
                'language': 'en',
                'limit': limit,
                'sort': 'published_at',
                'order': 'desc'
            }
            
            # Add API key if available
            if self.api_key:
                params['apiKey'] = self.api_key
            
            # Set category if not general
            if category != 'general' and category in self.categories:
                params['categories'] = self.categories[category]
            
            # Set regional parameters
            if region in self.regions:
                countries = ','.join(self.regions[region]['countries'])
                params['countries'] = countries
            
            # Set time range
            published_after = datetime.now() - timedelta(hours=hours_back)
            params['published_after'] = published_after.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Make API request
            logger.info(f"Searching {region} {category} news with params: {params}")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.base_url + Endpoints.TOP_HEADLINES, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Use NewsSearchResponse for parsing
            news_response = NewsSearchResponse(**data)
            logger.info(f"Found {len(news_response.articles)} articles")
            return news_response
            
        except httpx.RequestError as e:
            logger.error(f"API request failed: {e}")
            return NewsSearchResponse(status="error", totalResults=0, articles=[])
        except Exception as e:
            logger.error(f"Unexpected error in search_headlines: {e}")
            return NewsSearchResponse(status="error", totalResults=0, articles=[])

    async def search_by_keywords(self, 
                          keywords: str,
                          region: str = 'american',
                          limit: int = 10,
                          hours_back: int = 24) -> List[NewsArticle]:
        """
        Search for articles by keywords
        
        Args:
            keywords: search terms
            region: regional focus
            limit: number of results
            hours_back: time range
            
        Returns:
            List of NewsArticle objects
        """
        try:
            params = {
                'search': keywords,
                'language': 'en',
                'limit': limit,
                'sort': 'relevance_score',
                'order': 'desc'
            }
            
            if self.api_key:
                params['apkKey'] = self.api_key
            
            if region in self.regions:
                countries = ','.join(self.regions[region]['countries'])
                params['countries'] = countries
            
            published_after = datetime.now() - timedelta(hours=hours_back)
            params['published_after'] = published_after.strftime('%Y-%m-%dT%H:%M:%S')
            
            logger.info(f"Searching for keywords '{keywords}' in {region}")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.base_url + Endpoints.EVERYTHING, params=params)
                response.raise_for_status()
                data = response.json()
            
            articles = []
            for item in data.get('data', []):
                article = NewsArticle(
                    title=item.get('title', ''),
                    description=item.get('description', ''),
                    url=item.get('url', ''),
                    source=item.get('source', ''),
                    published_at=item.get('published_at', ''),
                    urlToImage=item.get('image_url'),
                    category=item.get('categories', [None])[0] if item.get('categories') else None
                )
                articles.append(article)
            
            logger.info(f"Found {len(articles)} articles for '{keywords}'")
            return articles
            
        except httpx.RequestError as e:
            logger.error(f"Keyword search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in search_by_keywords: {e}")
            return []

    async def get_top_stories(self, region: str = 'american', limit: int = 10) -> List[NewsArticle]:
        """
        Get top breaking news stories for a region
        
        Args:
            region: target region
            limit: number of stories
            
        Returns:
            List of top NewsArticle objects
        """
        news_response = await self.search_headlines(
            region=region,
            category='general',
            limit=limit,
            hours_back=12  # Focus on very recent breaking news
        )
        return news_response.articles

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize service
        service = NewsSearchService()
        
        # Test American headlines
        print("=== TOP AMERICAN HEADLINES ===")
        articles = await service.get_top_stories('american', limit=5)
        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source}")
            print(f"   Published: {article.published_at}")
            print()
        
        # Test keyword search
        print("=== SEARCH RESULTS FOR 'AI' ===")
        ai_articles = await service.search_by_keywords('artificial intelligence', 'american', limit=3)
        for article in ai_articles:
            print(f"• {article.title}")
            print(f"  {article.description[:100]}...")
            print()
    
    # Run the main function
    asyncio.run(main())