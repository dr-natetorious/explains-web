#!/usr/bin/env python3
"""
FastAPI service for searching the vector database.
Provides REST API endpoints for document search functionality.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import uvicorn

# Add current directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from pipeline import VectorStore



# Initialize FastAPI app
app = FastAPI(
    title="Document Vector Search API",
    description="Search through document collections using semantic similarity",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# Global variables for loaded components
vector_store: Optional[VectorStore] = None
search_model: Optional[SentenceTransformer] = None
logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_components():
    """Load vector store and search model"""
    global vector_store, search_model
    
    try:
        logger.info("Loading vector store...")
        vector_store = VectorStore()
        
        logger.info("Loading sentence transformer model...")
        model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
        search_model = SentenceTransformer(model_name)
        
        stats = vector_store.get_stats()
        logger.info(f"Loaded vector store with {stats['total_chunks']} chunks")
        
    except Exception as e:
        logger.error(f"Error loading components: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    setup_logging()
    load_components()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    database_loaded = vector_store is not None and vector_store.index is not None
    model_loaded = search_model is not None
    
    stats = DatabaseStats(
        total_chunks=0,
        total_files=0,
        total_repos=0,
        last_updated=None,
        repos={}
    )
    
    if database_loaded:
        vector_stats = vector_store.get_stats()
        stats = DatabaseStats(**vector_stats)
    
    return HealthResponse(
        status="healthy" if database_loaded and model_loaded else "unhealthy",
        database_loaded=database_loaded,
        model_loaded=model_loaded,
        stats=stats
    )


@app.get("/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Get database statistics"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not loaded")
    
    stats = vector_store.get_stats()
    return DatabaseStats(**stats)


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search for documents using semantic similarity"""
    if not vector_store or not search_model:
        raise HTTPException(status_code=503, detail="Search components not loaded")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    start_time = datetime.now()
    
    try:
        # Generate query embedding
        query_embedding = search_model.encode(request.query)
        
        # Search vector store
        raw_results = vector_store.search(query_embedding, k=request.limit * 2)  # Get extra for filtering
        
        # Filter and format results
        filtered_results = []
        for chunk, score in raw_results:
            # Apply score filter
            if score < request.min_score:
                continue
            
            # Apply repo filter
            if request.repo_filter and chunk.repo_name not in request.repo_filter:
                continue
            
            # Apply file type filter
            file_ext = Path(chunk.source_file).suffix.lower()
            if request.file_type_filter and file_ext not in request.file_type_filter:
                continue
            
            result = SearchResult(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                source_file=chunk.source_file,
                repo_name=chunk.repo_name,
                file_type=file_ext,
                similarity_score=score,
                metadata=chunk.metadata
            )
            filtered_results.append(result)
            
            # Stop when we have enough results
            if len(filtered_results) >= request.limit:
                break
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=request.query,
            results=filtered_results,
            total_results=len(filtered_results),
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search", response_model=SearchResponse)
async def search_documents_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score"),
    repo: Optional[str] = Query(None, description="Repository filter (comma-separated)"),
    file_type: Optional[str] = Query(None, description="File type filter (comma-separated)")
):
    """GET endpoint for search (for easy testing)"""
    repo_filter = repo.split(',') if repo else None
    file_type_filter = file_type.split(',') if file_type else None
    
    request = SearchRequest(
        query=q,
        limit=limit,
        min_score=min_score,
        repo_filter=repo_filter,
        file_type_filter=file_type_filter
    )
    
    return await search_documents(request)


@app.get("/repositories")
async def list_repositories():
    """List all available repositories"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not loaded")
    
    stats = vector_store.get_stats()
    return {
        "repositories": list(stats.get("repos", {}).keys()),
        "total_repos": len(stats.get("repos", {}))
    }


@app.get("/repositories/{repo_name}")
async def get_repository_info(repo_name: str):
    """Get information about a specific repository"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not loaded")
    
    stats = vector_store.get_stats()
    repos = stats.get("repos", {})
    
    if repo_name not in repos:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo_info = repos[repo_name]
    
    # Get files for this repo
    repo_files = []
    for file_key, file_info in vector_store.metadata.get("files", {}).items():
        if file_key.startswith(f"{repo_name}/"):
            file_path = file_key[len(f"{repo_name}/"):]
            repo_files.append({
                "path": file_path,
                "hash": file_info.get("file_hash"),
                "processed_at": file_info.get("processed_at"),
                "chunk_count": file_info.get("chunk_count", 0)
            })
    
    return {
        "name": repo_name,
        "files": repo_files,
        "total_files": len(repo_files),
        "total_chunks": repo_info.get("chunks", 0)
    }


@app.post("/reload")
async def reload_database(background_tasks: BackgroundTasks):
    """Reload the vector database (useful after updates)"""
    def reload_components():
        global vector_store, search_model
        try:
            logger.info("Reloading vector store...")
            vector_store = VectorStore()
            logger.info("Vector store reloaded successfully")
        except Exception as e:
            logger.error(f"Error reloading vector store: {e}")
    
    background_tasks.add_task(reload_components)
    return {"message": "Database reload initiated"}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Document Vector Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search",
            "health": "/health",
            "stats": "/stats",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Document Vector Search API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "search_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1
    )