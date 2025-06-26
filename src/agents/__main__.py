from .news_agent import NewsAgent
import asyncio

agent = NewsAgent()
async def main():
    print("=== GENERATING HEADLINES SEGMENT ===")
    headlines = await agent.generate_headlines_segment('american', 'general')
    print(f"Duration: {headlines.duration_estimate}s")
    print(f"Stories: {len(headlines.stories_covered)}")
    print("Content:")
    print(headlines.content)
    print("\n" + "="*50 + "\n")
    
    print("=== GENERATING FULL NEWSCAST ===")
    newscast = await agent.generate_full_newscast('american', 'general')
    print("HEADLINES SEGMENT:")
    print(newscast['headlines'].content)
    print("\n" + "-"*30 + "\n")
    print("CONTEXT SEGMENT:")
    print(newscast['context'].content)

asyncio.run(main())