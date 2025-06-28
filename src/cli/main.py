import argparse
import asyncio
import logging
from agents.news_agent import NewsAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Explains Web CLI: Generate newscasts using AWS Bedrock Claude and TheNewsAPI.com"
    )
    parser.add_argument(
        "command",
        choices=["headlines", "context", "full"],
        help="Which segment to generate: headlines, context, or full newscast"
    )
    parser.add_argument(
        "--region",
        default="american",
        help="News region to focus on (default: american)"
    )
    parser.add_argument(
        "--category",
        default="general",
        help="News category (default: general)"
    )
    return parser.parse_args()

async def main():
    args = parse_args()
    agent = NewsAgent()

    if args.command == "headlines":
        segment = await agent.generate_headlines_segment(args.region, args.category)
        print("=== HEADLINES SEGMENT ===")
        print(segment.content)
        print(f"\nStories: {len(segment.stories_covered)} | Duration: {segment.duration_estimate}s")
    elif args.command == "context":
        # For context, use top 3 stories from headlines as focus
        headlines = await agent.generate_headlines_segment(args.region, args.category)
        focus_stories = headlines.stories_covered[:3]
        segment = await agent.generate_context_segment(args.region, focus_stories)
        print("=== CONTEXT SEGMENT ===")
        print(segment.content)
        print(f"\nStories: {len(segment.stories_covered)} | Duration: {segment.duration_estimate}s")
    elif args.command == "full":
        newscast = await agent.generate_full_newscast(args.region, args.category)
        print("=== HEADLINES SEGMENT ===")
        print(newscast['headlines'].content)
        print(f"\nStories: {len(newscast['headlines'].stories_covered)} | Duration: {newscast['headlines'].duration_estimate}s")
        print("\n" + "-"*40 + "\n")
        print("=== CONTEXT SEGMENT ===")
        print(newscast['context'].content)
        print(f"\nStories: {len(newscast['context'].stories_covered)} | Duration: {newscast['context'].duration_estimate}s")
    else:
        print("Unknown command.")
