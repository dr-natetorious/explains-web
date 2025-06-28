# ===== GCP GEMINI PROVIDER =====

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from api.models import AIProviderConfig, AIProviderResponse, PromptTemplate,
from ..content_service import BaseAIProvider

class GeminiModel(str, Enum):
    """Available Gemini models"""
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_0_PRO = "gemini-1.0-pro"

class GeminiConfig(AIProviderConfig):
    """Google Gemini specific configuration"""
    model_name: GeminiModel = Field(default=GeminiModel.GEMINI_1_5_PRO, description="Gemini model to use")
    api_key: str = Field(..., description="Google AI API key")
    top_k: Optional[int] = Field(default=40, description="Top-k sampling")
    candidate_count: int = Field(default=1, description="Number of response candidates")
    
    # Safety settings
    safety_settings: Dict[str, str] = Field(
        default={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        description="Safety filter settings"
    )

class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider implementation"""
    
    def __init__(self, config: GeminiConfig):
        super().__init__(config)
        self.gemini_config = config
        self._configure_client()
    
    def _configure_client(self):
        """Configure Gemini client"""
        genai.configure(api_key=self.gemini_config.api_key)
        
        generation_config = genai.GenerationConfig(
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.gemini_config.top_k,
            max_output_tokens=self.config.max_tokens,
            candidate_count=self.gemini_config.candidate_count
        )
        
        self.model = genai.GenerativeModel(
            model_name=self.gemini_config.model_name.value,
            generation_config=generation_config,
            safety_settings=self.gemini_config.safety_settings
        )
    
    def _get_model_info(self) -> str:
        return f"Google Gemini - {self.gemini_config.model_name.value}"
    
    async def _call_api(self, prompt_data: Dict[str, Any]) -> AIProviderResponse:
        """Call Gemini API"""
        system_prompt = self.prompt_templates.system_prompt.format(**prompt_data)
        user_prompt = self.prompt_templates.user_prompt.format(**prompt_data)
        
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        loop = asyncio.get_event_loop()
        
        def _call_sync():
            try:
                response = self.model.generate_content(full_prompt)
                
                if not response.candidates:
                    raise Exception("No candidates returned from Gemini")
                
                candidate = response.candidates[0]
                
                if candidate.finish_reason.name != "STOP":
                    raise Exception(f"Generation stopped due to: {candidate.finish_reason.name}")
                
                content = candidate.content.parts[0].text if candidate.content.parts else ""
                
                usage_stats = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0
                }
                
                return AIProviderResponse(
                    content=content,
                    model_info=self._get_model_info(),
                    usage_stats=usage_stats,
                    metadata={
                        "finish_reason": candidate.finish_reason.name,
                        "safety_ratings": [
                            {"category": rating.category.name, "probability": rating.probability.name}
                            for rating in candidate.safety_ratings
                        ] if candidate.safety_ratings else []
                    }
                )
                
            except Exception as e:
                raise Exception(f"Gemini API error: {e}")
        
        return await loop.run_in_executor(None, _call_sync)