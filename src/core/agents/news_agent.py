"""
News Agent using AWS Bedrock Claude 4
Replicates the manual process of generating structured newscasts with dry humor.
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio

from ..services.news_service import NewsArticle, NewsSearchService
from ..prompts import Prompts
from .conversation import AgentConversation, ModelNames

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewscastSegment(BaseModel):
    """Structure for a newscast segment"""
    segment_type: str  # 'headlines' or 'context'
    content: str
    duration_estimate: int  # seconds
    stories_covered: List[str]  # story titles

class NewsAgent:
    """AWS Bedrock Claude 4 agent for generating newscasts"""
    
    def __init__(self,
                 *,
                 prompts: Optional[Prompts] = None,
                 aws_region: str = 'us-east-1',
                 model_id: str = ModelNames.SONNET_35):
        """
        Initialize the news agent
        
        Args:
            aws_region: AWS region for Bedrock
            model_id: Claude model ID (default: Sonnet 4)
        """
        self.prompts = prompts or Prompts()
        if not isinstance(self.prompts, Prompts):
            raise ValueError("prompts must be an instance of Prompts class")
        self.aws_region = aws_region
        self.model_id = model_id
        self.conversation = AgentConversation(model_id=self.model_id, region=self.aws_region)
        
        # Initialize search service
        self.search_service = NewsSearchService()
    
    def _get_headlines_prompt(self) -> str:
        """Get the prompt for generating 1-minute headlines segment"""
        return self.prompts.get_headlines_prompt() 

    def _get_context_prompt(self) -> str:
        """Get the prompt for generating 5-minute context segment"""
        return self.prompts.get_context_prompt()

    async def _call_claude(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Async: Make a call to Claude via AgentConversation.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum response tokens
            
        Returns:
            Claude's response text
        """
        try:
            async with self.conversation as conv:
                response_chunks = []
                async for chunk in conv.send_message(prompt, max_tokens=max_tokens):
                    response_chunks.append(chunk)
                full_content = ''.join(response_chunks)
                if full_content:
                    return full_content
                logger.error("No content received from Claude streaming.")
                return "Error: No content received from Bedrock streaming."
        except Exception as e:
            logger.error(f"Claude streaming API call failed: {e}")
            return f"Error generating content: {e}"

    def _format_articles_for_prompt(self, articles: List[NewsArticle]) -> str:
        """Format articles for inclusion in prompts"""
        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(f"""
ARTICLE {i}:
Title: {article.title}
Source: {article.source}
Published: {article.published_at}
Description: {article.description}
URL: {article.url}
""")
        return "\n".join(formatted)

    async def generate_headlines_segment(self, 
                                 region: str = 'american',
                                 category: str = 'general') -> NewscastSegment:
        """
        Generate 1-minute headlines segment
        
        Args:
            region: News region to focus on
            category: News category
            
        Returns:
            NewscastSegment with headlines content
        """
        try:
            # Get latest news articles
            logger.info(f"Fetching {region} {category} news for headlines")
            response = await self.search_service.search_headlines(
                region=region,
                category=category,
                limit=10,
                hours_back=24
            )
            articles = response.articles
            
            if not articles:
                return NewscastSegment(
                    segment_type='headlines',
                    content="No current news available. Technical difficulties in the newsroom.",
                    duration_estimate=10,
                    stories_covered=[]
                )
            
            # Format articles for prompt
            articles_text = self._format_articles_for_prompt(articles[:8])
            
            # Add current date to prompt
            current_date = datetime.now().strftime("%B %d, %Y")
            prompt = self.prompts.get_headlines_prompt().replace('[DATE]', current_date)
            prompt = prompt.replace('{articles}', articles_text)
            
            # Generate content with Claude
            logger.info("Generating headlines segment with Claude")
            content = await self._call_claude(prompt, max_tokens=300)
            
            # Extract story titles covered
            story_titles = [article.title for article in articles[:6] if article.title]
            
            return NewscastSegment(
                segment_type='headlines',
                content=content,
                duration_estimate=60,
                stories_covered=story_titles
            )
            
        except Exception as e:
            logger.error(f"Failed to generate headlines segment: {e}")
            return NewscastSegment(
                segment_type='headlines',
                content=f"Headlines segment generation failed: {e}",
                duration_estimate=10,
                stories_covered=[]
            )

    async def generate_context_segment(self, 
                               region: str = 'american',
                               focus_stories: Optional[List[str]] = None) -> NewscastSegment:
        """
        Generate 5-minute context segment
        
        Args:
            region: News region to focus on
            focus_stories: Specific stories to analyze (from headlines)
            
        Returns:
            NewscastSegment with context content
        """
        try:
            # Get comprehensive news for analysis
            logger.info(f"Fetching {region} news for context analysis")
            
            # Get both general and political news for richer context
            general_response = await self.search_service.search_headlines(
                region=region, category='general', limit=8, hours_back=48
            )
            political_response = await self.search_service.search_headlines(
                region=region, category='politics', limit=5, hours_back=48
            )
            business_response = await self.search_service.search_headlines(
                region=region, category='business', limit=5, hours_back=48
            )
            general_articles = general_response.articles
            political_articles = political_response.articles
            business_articles = business_response.articles
            
            # Combine and deduplicate
            all_articles = general_articles + political_articles + business_articles
            seen_titles = set()
            unique_articles = []
            for article in all_articles:
                if article.title not in seen_titles:
                    unique_articles.append(article)
                    seen_titles.add(article.title)
            
            if not unique_articles:
                return NewscastSegment(
                    segment_type='context',
                    content="Deep analysis unavailable due to technical issues.",
                    duration_estimate=30,
                    stories_covered=[]
                )
            
            # Format articles and focus stories for prompt
            articles_text = self._format_articles_for_prompt(unique_articles[:12])
            focus_text = ', '.join(focus_stories) if focus_stories else "Top 2-3 most significant stories"
            
            prompt = self.prompts.get_context_prompt().replace('{articles}', articles_text)
            prompt = prompt.replace('{focus_stories}', focus_text)
            
            # Generate content with Claude
            logger.info("Generating context segment with Claude")
            content = await self._call_claude(prompt, max_tokens=1200)
            
            return NewscastSegment(
                segment_type='context',
                content=content,
                duration_estimate=300,
                stories_covered=focus_stories or [a.title for a in unique_articles[:3]]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate context segment: {e}")
            return NewscastSegment(
                segment_type='context',
                content=f"Context analysis failed: {e}",
                duration_estimate=30,
                stories_covered=[]
            )

    async def generate_full_newscast(self, 
                             region: str = 'american',
                             category: str = 'general') -> Dict[str, NewscastSegment]:
        """
        Generate complete 1+5 minute newscast
        
        Args:
            region: News region focus
            category: Primary news category
            
        Returns:
            Dictionary with 'headlines' and 'context' segments
        """
        logger.info(f"Generating full newscast for {region} {category} news")
        
        # Generate headlines first
        headlines_segment = await self.generate_headlines_segment(region, category)
        
        # Use headlines stories as focus for context
        focus_stories = headlines_segment.stories_covered[:3]
        context_segment = await self.generate_context_segment(region, focus_stories)
        
        return {
            'headlines': headlines_segment,
            'context': context_segment
        }