from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# ===== LEAN SYSTEM =====

class LeanLevel(BaseModel):
    """Single level definition for a lean axis"""
    score: int = Field(..., ge=-2, le=2, description="Z-score from -2 to +2")
    name: str = Field(..., description="Human readable name for this level")
    description: str = Field(..., description="What this level means for content")
    icon: Optional[str] = Field(None, description="Optional emoji or icon")

class LeanAxis(BaseModel):
    """Defines the lean axis for an article type"""
    axis_name: str = Field(..., description="Internal name like 'junior-senior'")
    axis_label: str = Field(..., description="Display name like 'Experience Level'")
    axis_icon: str = Field(..., description="Icon representing this axis like '💼'")
    default_level: int = Field(3, ge=1, le=5, description="Default level (1-5)")
    levels: Dict[str, LeanLevel] = Field(..., description="Named levels (e.g. 'basic', 'expert')")

# ===== CONTENT GENERATION =====

class ComponentType(str, Enum):
    """Types of web components that can be generated"""
    ARTICLE_CONTENT = "article-content"
    DATA_VISUALIZATION = "data-visualization" 
    INTERACTIVE_DEMO = "interactive-demo"
    COMPARISON_TABLE = "comparison-table"
    TIMELINE_WIDGET = "timeline-widget"
    QUIZ_COMPONENT = "quiz-component"
    CODE_EXAMPLE = "code-example"
    CONCEPT_MAP = "concept-map"

class GenerationRequest(BaseModel):
    """Request to generate content at specific lean level"""
    article_id: str = Field(..., description="Unique identifier for the article")
    component_type: ComponentType = Field(..., description="Type of component to generate")
    lean_level: int = Field(..., ge=1, le=5, description="Requested lean level (1-5)")
    lean_axes: List[LeanAxis] = Field(..., description="Available lean axes for this article")
    
    # Context for AI generation
    topic: str = Field(..., description="Main topic/title")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User personalization")
    
    # Output preferences  
    max_length: Optional[int] = Field(None, description="Maximum content length")
    include_sources: bool = Field(True, description="Whether to include source citations")
    interactive_features: bool = Field(True, description="Enable interactive elements")

class GeneratedComponent(BaseModel):
    """Generated web component with content"""
    component_type: ComponentType = Field(..., description="Type of component generated")
    component_tag: str = Field(..., description="HTML tag name for the component")
    
    # Core content
    html_content: str = Field(..., description="Generated HTML content")
    component_data: Dict[str, Any] = Field(default_factory=dict, description="Data attributes for component")
    
    # Metadata
    lean_level_used: int = Field(..., description="Actual lean level used")
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    estimated_read_time: Optional[int] = Field(None, description="Estimated read time in minutes")
    
    # Dependencies
    required_css: List[str] = Field(default_factory=list, description="Additional CSS files needed")
    required_js: List[str] = Field(default_factory=list, description="Additional JS files needed")
    
    # Sources and attribution
    sources: List[str] = Field(default_factory=list, description="Source citations")
    ai_model_info: Optional[str] = Field(None, description="Model used for generation")

class GenerationResponse(BaseModel):
    """Complete response from content generation service"""
    success: bool = Field(..., description="Whether generation succeeded")
    components: List[GeneratedComponent] = Field(default_factory=list, description="Generated components")
    
    # Article-level data
    article_metadata: Dict[str, Any] = Field(default_factory=dict, description="Article metadata")
    lean_axes_used: List[LeanAxis] = Field(..., description="Lean axes configurations used")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Any warnings")
    
    # Performance
    generation_time_ms: Optional[int] = Field(None, description="Time taken to generate")

# ===== SERVICE INTERFACE =====

class ContentGenerationService:
    """Abstract interface for content generation service"""
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        """Generate content based on request parameters"""
        raise NotImplementedError
    
    async def get_available_axes(self) -> List[LeanAxis]:
        """Get all available lean axes"""
        raise NotImplementedError
    
    async def preview_at_level(self, article_id: str, level: int) -> str:
        """Get a preview of content at specific level"""
        raise NotImplementedError

# ===== EXAMPLE IMPLEMENTATION =====

class MockContentService(ContentGenerationService):
    """Mock implementation for development"""
    
    async def generate_content(self, request: GenerationRequest) -> GenerationResponse:
        # Mock lean level calculation
        z_score = (request.lean_level - 3)  # Convert 1-5 to -2 to +2
        
        # Use first axis for simplicity in mock
        primary_axis = request.lean_axes[0]
        level_names = ["basic", "intermediate", "advanced", "expert", "master"]
        level_key = level_names[request.lean_level - 1]
        
        # Get the level info from the named levels
        if level_key in primary_axis.levels:
            level_info = primary_axis.levels[level_key]
        else:
            # Fallback if exact key doesn't exist
            level_values = list(primary_axis.levels.values())
            level_info = level_values[request.lean_level - 1] if len(level_values) >= request.lean_level else level_values[0]
        
        # Generate mock HTML based on component type
        if request.component_type == ComponentType.ARTICLE_CONTENT:
            html_content = self._generate_article_content(request, level_info, z_score, primary_axis)
        elif request.component_type == ComponentType.DATA_VISUALIZATION:
            html_content = self._generate_data_viz(request, level_info)
        else:
            html_content = f"<div>Mock {request.component_type} at level {level_info.name}</div>"
        
        component = GeneratedComponent(
            component_type=request.component_type,
            component_tag=f"{request.component_type.value.replace('_', '-')}",
            html_content=html_content,
            component_data={
                "lean-level": request.lean_level,
                "z-score": z_score,
                "axis": primary_axis.axis_name
            },
            lean_level_used=request.lean_level,
            estimated_read_time=3 + request.lean_level  # Mock: higher levels take longer
        )
        
        return GenerationResponse(
            success=True,
            components=[component],
            lean_axes_used=request.lean_axes,
            generation_time_ms=150
        )
    
    def _generate_article_content(self, request: GenerationRequest, level_info: LeanLevel, z_score: float, axis: LeanAxis) -> str:
        """Generate article content HTML"""
        return f"""
        <article-content 
            data-lean-level="{request.lean_level}"
            data-z-score="{z_score}"
            data-axis="{axis.axis_name}">
            
            <div class="content-header">
                <h2>{request.topic}</h2>
                <span class="lean-indicator">
                    {axis.axis_icon} {level_info.name}
                </span>
            </div>
            
            <div class="content-body">
                <p>Content adapted for <strong>{level_info.name}</strong> perspective:</p>
                <p>{level_info.description}</p>
                
                <!-- Mock content that would come from AI -->
                <div class="generated-content">
                    <p>This is where the AI-generated content would appear, 
                    tailored to the {level_info.name} level with a z-score of {z_score}.</p>
                </div>
            </div>
            
            <div class="content-footer">
                <small>Generated at {level_info.name} level</small>
            </div>
        </article-content>
        """
    
    def _generate_data_viz(self, request: GenerationRequest, level_info: LeanLevel) -> str:
        """Generate data visualization HTML"""
        return f"""
        <data-visualization 
            data-complexity="{request.lean_level}"
            data-type="chart">
            
            <div class="viz-header">
                <h3>Data Visualization - {level_info.name}</h3>
            </div>
            
            <div class="viz-container">
                <!-- Visualization complexity varies by level -->
                <canvas id="chart-{request.article_id}" width="400" height="200"></canvas>
            </div>
            
            <div class="viz-controls">
                <button onclick="updateChart({request.lean_level})">Update View</button>
            </div>
        </data-visualization>
        """
    
    async def get_available_axes(self) -> List[LeanAxis]:
        """Return sample lean axes"""
        return [
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
            )
        ]
    
    async def preview_at_level(self, article_id: str, level: int) -> str:
        """Get a preview of content at specific level"""
        axes = await self.get_available_axes()
        request = GenerationRequest(
            article_id=article_id,
            component_type=ComponentType.ARTICLE_CONTENT,
            lean_level=level,
            lean_axes=[axes[0]],  # Use first axis for preview
            topic="Preview Content"
        )
        
        response = await self.generate_content(request)
        if response.success and response.components:
            return response.components[0].html_content
        return "<p>Preview not available</p>"

# ===== USAGE EXAMPLES =====

async def example_single_axis():
    """Example with single lean axis"""
    service = MockContentService()
    
    # Get available lean axes
    axes = await service.get_available_axes()
    tech_axis = next(axis for axis in axes if axis.axis_name == "basic-expert")
    
    # Create generation request
    request = GenerationRequest(
        article_id="cloud-security-basics",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=4,  # Expert level
        lean_axes=[tech_axis],
        topic="Cloud Security Fundamentals",
        context={
            "industry": "technology",
            "use_case": "enterprise_security"
        }
    )
    
    # Generate content
    response = await service.generate_content(request)
    
    if response.success:
        for component in response.components:
            print(f"Generated {component.component_tag}:")
            print(component.html_content[:200] + "...")
    else:
        print("Generation failed:", response.errors)

async def example_multi_axis():
    """Example with multiple lean axes"""
    service = MockContentService()
    
    # Get available lean axes
    axes = await service.get_available_axes()
    
    # Political article with both political lean and complexity
    political_axis = next(axis for axis in axes if axis.axis_name == "liberal-conservative")
    complexity_axis = next(axis for axis in axes if axis.axis_name == "basic-expert")
    
    request = GenerationRequest(
        article_id="healthcare-policy-analysis",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=3,  # Centrist + Advanced
        lean_axes=[political_axis, complexity_axis],
        topic="Healthcare Policy Reform",
        context={
            "domain": "healthcare",
            "policy_focus": "universal_coverage"
        }
    )
    
    response = await service.generate_content(request)
    
    if response.success:
        component = response.components[0]
        print(f"Multi-axis content generated:")
        print(f"Political: {political_axis.levels['centrist'].name}")
        print(f"Complexity: {complexity_axis.levels['advanced'].name}")
        print(component.html_content[:200] + "...")

async def example_business_content():
    """Example of business content with experience-based lean"""
    service = MockContentService()
    
    axes = await service.get_available_axes()
    business_axis = next(axis for axis in axes if axis.axis_name == "junior-senior")
    
    # Generate executive-level business content
    request = GenerationRequest(
        article_id="q4-strategy-update",
        component_type=ComponentType.ARTICLE_CONTENT,
        lean_level=5,  # Executive level
        lean_axes=[business_axis],
        topic="Q4 Strategic Initiatives",
        context={
            "audience": "c_suite",
            "quarter": "Q4_2025",
            "focus": "growth_strategy"
        }
    )
    
    response = await service.generate_content(request)
    
    if response.success:
        component = response.components[0]
        print(f"Business content for: {business_axis.levels['executive'].name}")
        print(f"Description: {business_axis.levels['executive'].description}")
        print(component.html_content[:200] + "...")

# FastAPI Integration Example
async def fastapi_integration_example():
    """Example of how to integrate with FastAPI"""
    from fastapi import FastAPI, Request
    from fastapi.templating import Jinja2Templates
    
    app = FastAPI()
    templates = Jinja2Templates(directory="templates")
    service = MockContentService()
    
    @app.get("/article/{article_id}")
    async def get_article(request: Request, article_id: str, level: int = 3):
        # Get appropriate axes for this article
        axes = await service.get_available_axes()
        
        # Determine axes based on article type/content
        if "policy" in article_id:
            selected_axes = [axis for axis in axes if axis.axis_name == "liberal-conservative"]
        elif "tech" in article_id:
            selected_axes = [axis for axis in axes if axis.axis_name == "basic-expert"]
        else:
            selected_axes = [axes[0]]  # Default to first axis
        
        # Generate content
        gen_request = GenerationRequest(
            article_id=article_id,
            component_type=ComponentType.ARTICLE_CONTENT,
            lean_level=level,
            lean_axes=selected_axes,
            topic=article_id.replace("-", " ").title()
        )
        
        response = await service.generate_content(gen_request)
        
        return templates.TemplateResponse(request, "article.html", {
            "article_id": article_id,
            "generated_components": response.components,
            "lean_axes": response.lean_axes_used,
            "current_level": level
        })
    
    return app

# Run examples
if __name__ == "__main__":
    import asyncio
    
    async def run_examples():
        print("=== Single Axis Example ===")
        await example_single_axis()
        
        print("\n=== Multi Axis Example ===")
        await example_multi_axis()
        
        print("\n=== Business Content Example ===")
        await example_business_content()
    
    asyncio.run(run_examples())