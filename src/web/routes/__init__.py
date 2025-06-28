import fastapi
from .content import router as content_router

def include_routes(app:"fastapi.FastAPI"):
    """Include all routes in the FastAPI app"""
    app.include_router(content_router, prefix="/content", tags=["Content"]) 

__all__ = [
    "include_routes",
]