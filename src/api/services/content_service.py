from abc import ABC, abstractmethod
import asyncio
import json
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Import existing service contracts
from ..models import (
    ContentGenerationService, 
    GenerationRequest, 
    GenerationResponse,
    GeneratedComponent,
    ComponentType,
    LeanAxis,
    LeanLevel,
    AIProviderConfig,
    AIProviderResponse,
    PromptTemplate,
)

class BaseAIProvider(ABC):
    """Base class for AI providers"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.prompt_templates = self._load_prompt_templates()
    
    @abstractmethod
    async def _call_api(self, prompt_data: Dict[str, Any]) -> AIProviderResponse:
        """Call the provider's API"""
        pass
    
    @abstractmethod
    def _get_model_info(self) -> str:
        """Get model information string"""
        pass
    
    def _load_prompt_templates(self) -> PromptTemplate:
        """Load default prompt templates"""
        return PromptTemplate(
            system_prompt="""You are DR★NATE, an expert content generator that creates adaptive content based on lean levels. 

Your task is to generate {component_type} content at a specific lean level for the topic: {topic}

Lean Context:
- Axis: {lean_axis_name} ({lean_axis_label})
- Current Level: {lean_level_name} (Score: {lean_z_score})
- Description: {lean_level_description}

{lean_specific_instructions}

{component_specific_instructions}

Generate content that perfectly matches the requested lean level and component type. Return only the HTML content without explanations.""",
            
            user_prompt="Generate {component_type} content for: {topic}\n\nLean Level: {lean_level_name}\nContext: {context}",
            
            component_instructions={
                ComponentType.ARTICLE_CONTENT: """
Create an <article-content> web component with:
- Proper semantic HTML structure
- Content adapted to the exact lean level
- Appropriate data attributes for interactivity
- Professional styling classes
""",
                ComponentType.DATA_VISUALIZATION: """
Create a <data-visualization> web component with:
- Chart or graph appropriate for the complexity level
- Interactive controls if needed
- Data attributes for chart configuration
- Responsive design
""",
                ComponentType.INTERACTIVE_DEMO: """
Create an <interactive-demo> web component with:
- Hands-on examples matching the lean level
- JavaScript functionality for interactivity
- Progressive complexity based on lean level
- Clear instructions and feedback
""",
                ComponentType.CODE_EXAMPLE: """
Create a <code-example> web component with:
- Syntax-highlighted code blocks
- Explanatory comments appropriate for lean level
- Interactive elements if applicable
- Copy-to-clipboard functionality
"""
            },
            
            lean_instructions={
                "basic-expert": {
                    "basic": "Use simple language, fundamental concepts, step-by-step explanations. Avoid jargon.",
                    "intermediate": "Moderate complexity, some background assumed, practical examples.",
                    "advanced": "Professional level, technical depth, industry context.",
                    "expert": "Specialized knowledge, detailed analysis, advanced concepts.",
                    "master": "Cutting-edge research, theoretical frameworks, latest developments."
                },
                "liberal-conservative": {
                    "progressive": "Emphasize government solutions, social programs, collective action.",
                    "liberal": "Support regulated markets, institutional oversight, reform approaches.",
                    "centrist": "Balanced perspective, practical solutions, bipartisan approaches.",
                    "conservative": "Traditional values, market solutions, limited government role.",
                    "libertarian": "Maximum freedom, minimal regulation, individual responsibility."
                },
                "junior-senior": {
                    "intern": "Entry-level perspective, learning focus, basic concepts.",
                    "junior": "Growing experience, practical application, guided approach.",
                    "professional": "Competent execution, standard practices, reliable methods.",
                    "senior": "Strategic thinking, complex problem-solving, leadership perspective.",
                    "executive": "High-level strategy, business impact, organizational implications."
                }
            }
        )
    
    def _prepare_prompt(self, request: GenerationRequest) -> Dict[str, Any]:
        """Prepare prompt data for AI generation"""
        primary_axis = request.lean_axes[0]
        
        # Map level number to level name
        level_names = ["basic", "intermediate", "advanced", "expert", "master"]
        level_key = level_names[request.lean_level - 1]
        
        # Get level info (with fallback)
        if level_key in primary_axis.levels:
            level_info = primary_axis.levels[level_key]
        else:
            level_values = list(primary_axis.levels.values())
            level_info = level_values[request.lean_level - 1] if len(level_values) >= request.lean_level else level_values[0]
        
        # Calculate z-score
        z_score = (request.lean_level - 3)
        
        # Get component-specific instructions
        component_instructions = self.prompt_templates.component_instructions.get(
            request.component_type, 
            "Generate appropriate content for this component type."
        )
        
        # Get lean-specific instructions
        axis_instructions = self.prompt_templates.lean_instructions.get(primary_axis.axis_name, {})
        lean_specific_instructions = axis_instructions.get(level_key, "")
        
        return {
            "component_type": request.component_type.value,
            "topic": request.topic,
            "lean_axis_name": primary_axis.axis_name,
            "lean_axis_label": primary_axis.axis_label,
            "lean_level_name": level_info.name,
            "lean_z_score": z_score,
            "lean_level_description": level_info.description,
            "component_specific_instructions": component_instructions,
            "lean_specific_instructions": lean_specific_instructions,
            "context": json.dumps(request.context) if request.context else "{}"
        }
    
    def _parse_response(self, ai_response: AIProviderResponse, request: GenerationRequest) -> GeneratedComponent:
        """Parse AI response into GeneratedComponent"""
        z_score = (request.lean_level - 3)
        
        return GeneratedComponent(
            component_type=request.component_type,
            component_tag=f"{request.component_type.value.replace('_', '-')}",
            html_content=ai_response.content,
            component_data={
                "lean-level": request.lean_level,
                "z-score": z_score,
                "axis": request.lean_axes[0].axis_name,
                "article-id": request.article_id
            },
            lean_level_used=request.lean_level,
            estimated_read_time=self._estimate_read_time(ai_response.content),
            ai_model_info=ai_response.model_info,
            sources=[]  # Could be populated from RAG system
        )
    
    def _estimate_read_time(self, content: str) -> int:
        """Estimate reading time in minutes"""
        word_count = len(content.split())
        words_per_minute = 200  # Average reading speed
        return max(1, round(word_count / words_per_minute))

class AIContentService(ContentGenerationService):
    """Content service using pluggable AI providers"""
    
    def __init__(self, provider: BaseAIProvider):
        self.provider = provider
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content using the configured AI provider"""
        start_time = datetime.now()
        
        try:
            # Prepare prompt
            prompt_data = self.provider._prepare_prompt(request)
            
            # Call AI provider
            ai_response = await self.provider._call_api(prompt_data)
            
            # Parse response into component
            component = self.provider._parse_response(ai_response, request)
            
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return GenerationResponse(
                success=True,
                components=[component],
                lean_axes_used=request.lean_axes,
                article_metadata={
                    "model_used": ai_response.model_info,
                    "usage_stats": ai_response.usage_stats,
                    "provider_metadata": ai_response.metadata
                },
                generation_time_ms=int(generation_time)
            )
            
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return GenerationResponse(
                success=False,
                components=[],
                lean_axes_used=request.lean_axes,
                errors=[f"AI generation failed: {str(e)}"],
                generation_time_ms=int(generation_time)
            )
    
    async def get_available_axes(self) -> List[LeanAxis]:
        """Get all available lean axes"""
        return [
            LeanAxis(
                axis_name="basic-expert",
                axis_label="Complexity Level",
                axis_icon="🎯",
                default_level=3,
                levels={
                    "basic": LeanLevel(score=-2, name="Basic", description="Simple explanations, fundamental concepts", icon="📚"),
                    "intermediate": LeanLevel(score=-1, name="Intermediate", description="Some background assumed, practical focus", icon="📖"),
                    "advanced": LeanLevel(score=0, name="Advanced", description="Professional level, technical depth", icon="🔬"),
                    "expert": LeanLevel(score=1, name="Expert", description="Specialized knowledge, detailed analysis", icon="🎓"),
                    "master": LeanLevel(score=2, name="Master", description="Cutting-edge research, theoretical frameworks", icon="🏆")
                }
            ),
            LeanAxis(
                axis_name="liberal-conservative",
                axis_label="Political Perspective",
                axis_icon="🏛️",
                default_level=3,
                levels={
                    "progressive": LeanLevel(score=-2, name="Progressive", description="Strong government role, social change", icon="🌊"),
                    "liberal": LeanLevel(score=-1, name="Liberal", description="Government solutions, regulated markets", icon="🔵"),
                    "centrist": LeanLevel(score=0, name="Centrist", description="Balanced approach, pragmatic solutions", icon="⚖️"),
                    "conservative": LeanLevel(score=1, name="Conservative", description="Traditional values, limited government", icon="🔴"),
                    "libertarian": LeanLevel(score=2, name="Libertarian", description="Minimal government, maximum freedom", icon="🗽")
                }
            ),
            LeanAxis(
                axis_name="junior-senior",
                axis_label="Experience Level",
                axis_icon="💼",
                default_level=3,
                levels={
                    "intern": LeanLevel(score=-2, name="Intern", description="New to field, needs fundamentals", icon="🎓"),
                    "junior": LeanLevel(score=-1, name="Junior", description="Basic understanding, learning", icon="👨‍💻"),
                    "professional": LeanLevel(score=0, name="Professional", description="Solid foundation, practical focus", icon="💼"),
                    "senior": LeanLevel(score=1, name="Senior", description="Deep expertise, strategic thinking", icon="🎯"),
                    "executive": LeanLevel(score=2, name="Executive", description="Leadership perspective, big picture", icon="👔")
                }
            )
        ]
    
    async def preview_at_level(self, article_id: str, level: int) -> str:
        """Get a preview of content at specific level"""
        axes = await self.get_available_axes()
        
        request = GenerationRequest(
            article_id=article_id,
            component_type=ComponentType.ARTICLE_CONTENT,
            lean_level=level,
            lean_axes=[axes[0]],
            topic="Content Preview",
            max_length=500
        )
        
        response = await self.generate_content(request)
        if response.success and response.components:
            return response.components[0].html_content
        return "<p>Preview not available</p>"


# ===== USAGE EXAMPLES =====

async def example_bedrock_usage():
    """Example using Bedrock provider"""
    config = BedrockConfig(
        model_id=BedrockModel.CLAUDE_3_5_SONNET,
        temperature=0.7,
        max_tokens=3000
    )
    
    provider = BedrockProvider(config)
    service = AIContentService(provider)
    
    # Generate content
    axes = await service.get_available_axes()
    request = GenerationRequest(
        article_id="ai-ethics",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=4,
        lean_axes=[axes[0]],
        topic="AI Ethics in Healthcare"
    )
    
    response = await service.generate_content(request)
    
    if response.success:
        print(f"✅ Bedrock generation successful")
        print(f"Model: {response.article_metadata['model_used']}")
        print(f"Time: {response.generation_time_ms}ms")
        print(f"Content preview: {response.components[0].html_content[:200]}...")
    else:
        print(f"❌ Bedrock generation failed: {response.errors}")

async def example_gemini_usage():
    """Example using Gemini provider"""
    config = GeminiConfig(
        model_name=GeminiModel.GEMINI_1_5_PRO,
        api_key="your-google-ai-api-key",
        temperature=0.7,
        max_tokens=3000
    )
    
    provider = GeminiProvider(config)
    service = AIContentService(provider)
    
    # Generate content
    axes = await service.get_available_axes()
    request = GenerationRequest(
        article_id="climate-tech",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=2,
        lean_axes=[axes[1]],  # Political axis
        topic="Climate Technology Policy"
    )
    
    response = await service.generate_content(request)
    
    if response.success:
        print(f"✅ Gemini generation successful")
        print(f"Model: {response.article_metadata['model_used']}")
        print(f"Time: {response.generation_time_ms}ms")
        print(f"Content preview: {response.components[0].html_content[:200]}...")
    else:
        print(f"❌ Gemini generation failed: {response.errors}")

async def example_provider_switching():
    """Example of easily switching between providers"""
    
    # Factory function for provider creation
    async def create_service(provider_type: str) -> AIContentService:
        if provider_type == "bedrock":
            config = BedrockConfig(model_id=BedrockModel.CLAUDE_3_5_SONNET)
            provider = BedrockProvider(config)
        elif provider_type == "gemini":
            config = GeminiConfig(
                model_name=GeminiModel.GEMINI_1_5_PRO,
                api_key="your-api-key"
            )
            provider = GeminiProvider(config)
        else:
            raise ValueError(f"Unknown provider: {provider_type}")
        
        return AIContentService(provider)
    
    # Use the same request for both providers
    axes = await AIContentService(BedrockProvider(BedrockConfig())).get_available_axes()
    request = GenerationRequest(
        article_id="comparison-test",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=3,
        lean_axes=[axes[0]],
        topic="Cloud Security Fundamentals"
    )
    
    # Test both providers
    for provider_name in ["bedrock", "gemini"]:
        try:
            service = await create_service(provider_name)
            response = await service.generate_content(request)
            print(f"{provider_name.title()}: {'✅ Success' if response.success else '❌ Failed'}")
        except Exception as e:
            print(f"{provider_name.title()}: ❌ Error - {e}")

# FastAPI integration with provider selection
async def create_multi_provider_fastapi():
    """FastAPI app with multiple provider support"""
    from fastapi import FastAPI, Request, Query
    from fastapi.templating import Jinja2Templates
    
    app = FastAPI()
    templates = Jinja2Templates(directory="templates")
    
    # Initialize providers
    providers = {
        "bedrock": BedrockProvider(BedrockConfig()),
        "gemini": GeminiProvider(GeminiConfig(api_key="your-key"))
    }
    
    @app.get("/generate/{article_id}")
    async def generate_content(
        request: Request,
        article_id: str,
        level: int = 3,
        provider: str = Query(default="bedrock", description="AI provider to use")
    ):
        if provider not in providers:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
        service = AIContentService(providers[provider])
        axes = await service.get_available_axes()
        
        gen_request = GenerationRequest(
            article_id=article_id,
            component_type=ComponentType.ARTICLE_CONTENT,
            lean_level=level,
            lean_axes=[axes[0]],
            topic=article_id.replace("-", " ").title()
        )
        
        response = await service.generate_content(gen_request)
        
        return templates.TemplateResponse(request, "today.html", {
            "generated_components": response.components,
            "lean_axes": response.lean_axes_used,
            "current_level": level,
            "provider_used": provider,
            "generation_meta": response.article_metadata
        })
    
    return app

if __name__ == "__main__":
    import asyncio
    
    async def run_examples():
        print("=== Testing Bedrock Provider ===")
        await example_bedrock_usage()
        
        print("\n=== Testing Gemini Provider ===")
        await example_gemini_usage()
        
        print("\n=== Testing Provider Switching ===")
        await example_provider_switching()
    
    asyncio.run(run_examples())