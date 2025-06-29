import fastapi
#from .content import router as content_router
from .daily import router as daily_router

def include_routes(app:"fastapi.FastAPI"):
    """Include all routes in the FastAPI app"""
    #app.include_router(content_router, prefix="/content", tags=["Content"])
    app.include_router(daily_router, prefix="/daily", tags=["Daily Articles"])

__all__ = [
    "include_routes",
]