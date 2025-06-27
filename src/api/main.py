from pathlib import Path
from fastapi import APIRouter, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT_PATH = Path(__file__).parent
templates_dir = ROOT_PATH / "templates"
if not templates_dir.exists():
    raise FileNotFoundError(f"Templates directory not found at {templates_dir}")

templates = Jinja2Templates(directory=templates_dir)

app = FastAPI(
    title="Dr.Nate Explains API",
    description="API for gaining insights",
)

app.mount("/static", StaticFiles(directory= (ROOT_PATH/ "static").absolute()), name="static")

@app.get("/")
def root(request:Request):
    class Stats:
        def __init__(self):
            self.levels = "1"
    return templates.TemplateResponse(request, "base.html",{
        "stats": Stats(),
    })

async def main():
    import uvicorn
    uvicorn.run("api.main:app", 
                host="127.0.0.1", 
                port=8000,
                reload_includes=["*.py", "*.html", "*.css", "*.js"],
                reload=True)