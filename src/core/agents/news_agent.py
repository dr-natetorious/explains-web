"""
News Agent using AWS Bedrock Claude 4
Replicates the manual process of generating structured newscasts with dry humor.
"""

import boto3
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
from pydantic import BaseModel

from services import NewsArticle, NewsSearchService
from prompts import Prompts

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
                 model_id: str = 'anthropic.claude-3-5-sonnet-20241022-v2:0'):
        """
        Initialize the news agent
        
        Args:
            aws_region: AWS region for Bedrock
            model_id: Claude model ID (adjust when Claude 4 available)
        """
        self.prompts = prompts or Prompts()
        if not isinstance(self.prompts, Prompts):
            raise ValueError("prompts must be an instance of Prompts class")
        
        self.aws_region = aws_region
        self.model_id = model_id
        
        # Initialize AWS Bedrock client
        try:
            self.bedrock = boto3.client(service_name='bedrock-runtime')
            logger.info(f"Initialized Bedrock client in {aws_region}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
        
        # Initialize search service
        self.search_service = NewsSearchService()
    
    def _get_headlines_prompt(self) -> str:
        """Get the prompt for generating 1-minute headlines segment"""
        return self.prompts.get_headlines_prompt() 

    def _get_context_prompt(self) -> str:
        """Get the prompt for generating 5-minute context segment"""
        return self.prompts.get_context_prompt()

    def _call_claude(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Make a call to Claude via AWS Bedrock
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum response tokens
            
        Returns:
            Claude's response text
        """
        try:
            # Prepare the request body
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "top_p": 0.9
            })
            
            # Make the API call
            response = self.bedrock.invoke_model(
                body=body,
                modelId=self.model_id,
                accept='application/json',
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
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
            articles = await self.search_service.search_headlines(
                region=region,
                category=category,
                limit=10,
                hours_back=24
            )
            
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
            content = self._call_claude(prompt, max_tokens=300)
            
            # Extract story titles covered
            story_titles = [article.title for article in articles[:6]]
            
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
            general_articles = await self.search_service.search_headlines(
                region=region, category='general', limit=8, hours_back=48
            )
            political_articles = await self.search_service.search_headlines(
                region=region, category='politics', limit=5, hours_back=48
            )
            business_articles = await self.search_service.search_headlines(
                region=region, category='business', limit=5, hours_back=48
            )
            
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
            content = self._call_claude(prompt, max_tokens=1200)
            
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

