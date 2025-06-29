
from pydantic import BaseModel, Field
from typing import Dict, Any
from .lean import ComponentType

# ===== BASE AI PROVIDER =====

class AIProviderConfig(BaseModel):
    """Base configuration for AI providers"""
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Generation temperature")
    max_tokens: int = Field(default=4000, description="Maximum tokens to generate")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    timeout_seconds: int = Field(default=30, description="Request timeout")

class AIProviderResponse(BaseModel):
    """Standardized AI provider response"""
    content: str = Field(..., description="Generated content")
    model_info: str = Field(..., description="Model used for generation")
    usage_stats: Dict[str, Any] = Field(default_factory=dict, description="Token usage and costs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")

class PromptTemplate(BaseModel):
    """Template for generating prompts based on lean level"""
    system_prompt: str = Field(..., description="System prompt template")
    user_prompt: str = Field(..., description="User prompt template")
    component_instructions: Dict[ComponentType, str] = Field(
        default_factory=dict, 
        description="Component-specific instructions"
    )
    lean_instructions: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Lean-specific prompt modifications by axis"
    )