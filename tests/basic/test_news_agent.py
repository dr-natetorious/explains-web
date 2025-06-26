import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.prompts.prompts import Prompts
from src.agents.news_agent import NewsAgent, NewscastSegment

class DummyPrompts(Prompts):
    def __init__(self):
        pass
    
    def get_headlines_prompt(self):
        return "[DATE] {articles}"
    def get_context_prompt(self):
        return "{articles} {focus_stories}"

@pytest.mark.asyncio
async def test_generate_headlines_segment_success():
    agent = NewsAgent(prompts=DummyPrompts())
    dummy_articles = [
        MagicMock(title=f"Title {i}", source="Source", published_at="2025-06-25", description="Desc", url="url")
        for i in range(8)
    ]
    with patch.object(agent.search_service, 'search_headlines', new=AsyncMock(return_value=dummy_articles)):
        with patch.object(agent, '_call_claude', return_value="Generated headlines"):
            segment = await agent.generate_headlines_segment(region="american", category="general")
            assert segment.segment_type == 'headlines'
            assert segment.content == "Generated headlines"
            assert segment.duration_estimate == 60
            assert len(segment.stories_covered) == 6

@pytest.mark.asyncio
async def test_generate_headlines_segment_no_articles():
    agent = NewsAgent(prompts=DummyPrompts())
    with patch.object(agent.search_service, 'search_headlines', new=AsyncMock(return_value=[])):
        segment = await agent.generate_headlines_segment(region="american", category="general")
        assert segment.segment_type == 'headlines'
        assert "No current news available" in segment.content
        assert segment.stories_covered == []

@pytest.mark.asyncio
async def test_generate_context_segment_success():
    agent = NewsAgent(prompts=DummyPrompts())
    dummy_articles = [
        MagicMock(title=f"Title {i}", source="Source", published_at="2025-06-25", description="Desc", url="url")
        for i in range(12)
    ]
    with patch.object(agent.search_service, 'search_headlines', new=AsyncMock(return_value=dummy_articles)):
        with patch.object(agent, '_call_claude', return_value="Generated context"):
            segment = await agent.generate_context_segment(region="american", focus_stories=["Story1", "Story2"])
            assert segment.segment_type == 'context'
            assert segment.content == "Generated context"
            assert segment.duration_estimate == 300
            assert segment.stories_covered == ["Story1", "Story2"]

@pytest.mark.asyncio
async def test_generate_context_segment_no_articles():
    agent = NewsAgent(prompts=DummyPrompts())
    with patch.object(agent.search_service, 'search_headlines', new=AsyncMock(return_value=[])):
        segment = await agent.generate_context_segment(region="american", focus_stories=None)
        assert segment.segment_type == 'context'
        assert "Deep analysis unavailable" in segment.content
        assert segment.stories_covered == []

@pytest.mark.asyncio
async def test_generate_full_newscast():
    agent = NewsAgent(prompts=DummyPrompts())
    dummy_headlines = NewscastSegment(
        segment_type='headlines',
        content='Headlines',
        duration_estimate=60,
        stories_covered=["A", "B", "C", "D"]
    )
    dummy_context = NewscastSegment(
        segment_type='context',
        content='Context',
        duration_estimate=300,
        stories_covered=["A", "B", "C"]
    )
    with patch.object(agent, 'generate_headlines_segment', new=AsyncMock(return_value=dummy_headlines)):
        with patch.object(agent, 'generate_context_segment', new=AsyncMock(return_value=dummy_context)):
            newscast = await agent.generate_full_newscast(region="american", category="general")
            assert 'headlines' in newscast
            assert 'context' in newscast
            assert newscast['headlines'].content == 'Headlines'
            assert newscast['context'].content == 'Context'
