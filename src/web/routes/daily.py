from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

# Add path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.agents import NewsAgent

router = APIRouter()

# Initialize templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Initialize services
news_agent = NewsAgent()

class DailyArticleRequest(BaseModel):
    lean: int = Field(0, ge=-2, le=2, description="Personalization lean: -2 (liberal) to 2 (conservative)")

class DailyArticleResponse(BaseModel):
    date: str
    lean: int
    headlines: dict
    context: dict
    model_info: Optional[str] = None
    read_time: Optional[int] = None

@router.get("/")
async def daily_home(request: Request, lean: int = 0):
    """Daily articles home page and generator (default lean=0)"""
    try:
        req = DailyArticleRequest(lean=lean)
        newscast = await news_agent.generate_full_newscast('american', 'general')
        response = DailyArticleResponse(
            date=datetime.now().strftime("%B %d, %Y"),
            lean=req.lean,
            headlines={
                "content": newscast['headlines'].content,
                "stories_covered": newscast['headlines'].stories_covered,
                "duration": newscast['headlines'].duration_estimate
            },
            context={
                "content": newscast['context'].content,
                "stories_covered": newscast['context'].stories_covered,
                "duration": newscast['context'].duration_estimate
            },
            model_info="AWS Bedrock Claude",
            read_time=newscast['headlines'].duration_estimate // 60 + newscast['context'].duration_estimate // 60
        )
        accept = request.headers.get("accept", "text/html")
        if "application/json" in accept:
            return response
        # For HTML, build context for template
        context = response.model_dump()
        context["current_topic"] = f"Daily Brief - Lean {req.lean}"
        context["current_lean"] = req.lean
        context["headlines_content"] = response.headlines["content"]
        context["context_content"] = response.context["content"]
        return templates.TemplateResponse(request, "daily/home.html", context)
    except Exception as e:
        accept = request.headers.get("accept", "text/html")
        if "application/json" in accept:
            return {"success": False, "error": str(e)}
        raise HTTPException(status_code=500, detail=f"Article generation failed: {str(e)}")