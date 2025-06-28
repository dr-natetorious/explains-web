# Pydantic models for API
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    repo_filter: Optional[List[str]] = Field(default=None, description="Filter by repository names")
    file_type_filter: Optional[List[str]] = Field(default=None, description="Filter by file types (.pdf, .docx, .md)")


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    source_file: str
    repo_name: str
    file_type: str
    similarity_score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: float
    timestamp: str


class DatabaseStats(BaseModel):
    total_chunks: int
    total_files: int
    total_repos: int
    last_updated: Optional[str]
    repos: Dict[str, Dict[str, int]]


class HealthResponse(BaseModel):
    status: str
    database_loaded: bool
    model_loaded: bool
    stats: DatabaseStats
