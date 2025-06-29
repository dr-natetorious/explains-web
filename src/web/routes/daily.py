from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
from datetime import datetime

# Add path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.agents import NewsAgent

router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Initialize services
news_agent = NewsAgent()

@router.get("/")
async def daily_home(request: Request):
    """Daily articles home page"""
    return templates.TemplateResponse(
        "daily/home.html",
        {
            "request": request,
            "current_topic": "Daily Articles",
            "current_level": 3
        }
    )

@router.get("/generate")
async def generate_daily_article(request: Request, level: int = 3):
    """Generate today's daily article at specified complexity level"""
    try:
        # Validate level
        if level < 1 or level > 5:
            raise HTTPException(status_code=400, detail="Level must be between 1 and 5")
        
        # Generate newscast using existing agent
        newscast = await news_agent.generate_full_newscast('american', 'general')
        
        # Prepare template context
        context = {
            "request": request,
            "date": datetime.now().strftime("%B %d, %Y"),
            "generated_time": datetime.now().strftime("%I:%M %p"),
            "level": level,
            "headlines_content": newscast['headlines'].content,
            "context_content": newscast['context'].content,
            "model_info": "AWS Bedrock Claude",
            "read_time": newscast['headlines'].duration_estimate // 60 + newscast['context'].duration_estimate // 60,
            "current_topic": f"Daily Brief - Level {level}",
            "current_level": level
        }
        
        return templates.TemplateResponse("daily/article.html", context)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Article generation failed: {str(e)}")

@router.get("/api/generate")
async def api_generate_article(level: int = 3):
    """API endpoint for programmatic access"""
    try:
        newscast = await news_agent.generate_full_newscast('american', 'general')
        
        return {
            "success": True,
            "data": {
                "date": datetime.now().isoformat(),
                "level": level,
                "headlines": {
                    "content": newscast['headlines'].content,
                    "stories_covered": newscast['headlines'].stories_covered,
                    "duration": newscast['headlines'].duration_estimate
                },
                "context": {
                    "content": newscast['context'].content,
                    "stories_covered": newscast['context'].stories_covered,
                    "duration": newscast['context'].duration_estimate
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }