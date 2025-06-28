# ===== AWS BEDROCK PROVIDER =====

import boto3
from botocore.exceptions import ClientError
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from api.models import AIProviderConfig, AIProviderResponse, PromptTemplate,
from ..content_service import BaseAIProvider

class BedrockModel(str, Enum):
    """Available Bedrock models"""
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0"
    CLAUDE_3_OPUS = "anthropic.claude-3-opus-20240229-v1:0"
    CLAUDE_3_5_SONNET = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    TITAN_TEXT_EXPRESS = "amazon.titan-text-express-v1"
    JURASSIC_2_ULTRA = "ai21.j2-ultra-v1"

class BedrockConfig(AIProviderConfig):
    """AWS Bedrock specific configuration"""
    region_name: str = Field(default="us-east-1", description="AWS region")
    model_id: BedrockModel = Field(default=BedrockModel.CLAUDE_3_5_SONNET, description="Model to use")
    top_k: int = Field(default=250, ge=0, description="Top-k sampling")
    stop_sequences: List[str] = Field(default_factory=list, description="Stop sequences")
    
    # AWS credentials (optional - can use IAM roles)
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret key")
    aws_session_token: Optional[str] = Field(None, description="AWS session token")

class BedrockProvider(BaseAIProvider):
    """AWS Bedrock AI provider implementation"""
    
    def __init__(self, config: BedrockConfig):
        super().__init__(config)
        self.bedrock_config = config
        self.client = self._create_client()
    
    def _create_client(self):
        """Create Bedrock client"""
        session_kwargs = {
            "region_name": self.bedrock_config.region_name
        }
        
        if self.bedrock_config.aws_access_key_id:
            session_kwargs.update({
                "aws_access_key_id": self.bedrock_config.aws_access_key_id,
                "aws_secret_access_key": self.bedrock_config.aws_secret_access_key,
                "aws_session_token": self.bedrock_config.aws_session_token
            })
        
        session = boto3.Session(**session_kwargs)
        return session.client("bedrock-runtime")
    
    def _get_model_info(self) -> str:
        return f"AWS Bedrock - {self.bedrock_config.model_id.value}"
    
    async def _call_api(self, prompt_data: Dict[str, Any]) -> AIProviderResponse:
        """Call Bedrock API"""
        system_prompt = self.prompt_templates.system_prompt.format(**prompt_data)
        user_prompt = self.prompt_templates.user_prompt.format(**prompt_data)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "top_k": self.bedrock_config.top_k,
            "stop_sequences": self.bedrock_config.stop_sequences,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }
        
        loop = asyncio.get_event_loop()
        
        def _call_sync():
            try:
                response = self.client.invoke_model(
                    body=json.dumps(request_body),
                    modelId=self.bedrock_config.model_id.value,
                    accept="application/json",
                    contentType="application/json"
                )
                
                response_body = json.loads(response.get("body").read())
                
                content = ""
                if response_body.get("content") and len(response_body["content"]) > 0:
                    content = response_body["content"][0].get("text", "")
                
                usage_stats = response_body.get("usage", {})
                
                return AIProviderResponse(
                    content=content,
                    model_info=self._get_model_info(),
                    usage_stats=usage_stats,
                    metadata={
                        "stop_reason": response_body.get("stop_reason"),
                        "response_id": response_body.get("id")
                    }
                )
                
            except ClientError as e:
                raise Exception(f"Bedrock API error: {e}")
            except Exception as e:
                raise Exception(f"Bedrock error: {e}")
        
        return await loop.run_in_executor(None, _call_sync)
