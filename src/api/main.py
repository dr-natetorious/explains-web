from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

ROOT_PATH = Path(__file__).parent

app = FastAPI(
    title="Dr.Nate Explains API",
    description="API for gaining insights",
)

app.mount("/static", StaticFiles(directory= (ROOT_PATH/ "static").absolute()), name="static")

async def main():
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)