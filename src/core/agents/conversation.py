import asyncio
import json
from typing import List, Dict, AsyncIterator, Optional
import aioboto3
from enum import StrEnum


# Global default client - lazy initialized
_default_client = None


async def get_default_client(region: str = "us-east-1"):
    """Get or create the global default Bedrock client."""
    global _default_client
    if _default_client is None:
        session = aioboto3.Session()
        _default_client = await session.client('bedrock-runtime', region_name=region).__aenter__()
    return _default_client


async def close_default_client():
    """Close the global default client."""
    global _default_client
    if _default_client:
        await _default_client.__aexit__(None, None, None)
        _default_client = None


class ModelNames(StrEnum):
    SONNET_35 = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    SONNET_37 = "us.anthropic.claude-3-7-sonnet-20250601-v1:0"
    SONNET_40 = "us.anthropic.claude-sonnet-4-20250514-v1:0"


class AgentConversation:
    """Simple async streaming conversation with Claude using boto3."""
    
    def __init__(self, 
                 client=None, 
                 model_id: str = ModelNames.SONNET_35, 
                 region: str = "us-east-1"):
        self.model_id = model_id
        self.region = region
        self.messages: List[Dict[str, str]] = []
        self._client = client
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self._client is None:
            self._client = await get_default_client(self.region)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Don't close clients - either it's user-provided or it's the shared global client
        pass
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": content})
    
    async def send_message(self, content: str, max_tokens: int = 4096) -> AsyncIterator[str]:
        """Send a message and stream the response."""
        # Add user message to history
        self.add_message("user", content)
        
        # Prepare request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": self.messages
        }
        
        # Stream the response
        response = await self._client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        
        assistant_response = ""
        
        async for event in response['body']:
            chunk = json.loads(event['chunk']['bytes'])
            
            if chunk['type'] == 'content_block_delta':
                delta_text = chunk['delta'].get('text', '')
                assistant_response += delta_text
                yield delta_text
            elif chunk['type'] == 'message_stop':
                break
        
        # Add complete assistant response to history
        if assistant_response:
            self.add_message("assistant", assistant_response)
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages.clear()
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get a copy of the conversation history."""
        return self.messages.copy()


# Example usage
async def main():
    # Option 1: Use global default client (recommended for most cases)
    async with AgentConversation() as claude:
        print("User: Hello, how are you?")
        print("Claude: ", end="", flush=True)
        
        async for chunk in claude.send_message("Hello, how are you?"):
            print(chunk, end="", flush=True)
        print("\n")
    
    # Option 2: Multiple conversations with same global client (very efficient)
    async with AgentConversation() as claude1:
        async for chunk in claude1.send_message("What's 2+2?"):
            print(chunk, end="", flush=True)
        print("\n")
    
    async with AgentConversation() as claude2:
        async for chunk in claude2.send_message("What's the capital of France?"):
            print(chunk, end="", flush=True)
        print("\n")
    
    # Option 3: Provide your own client for custom configuration
    session = aioboto3.Session()
    custom_client = await session.client('bedrock-runtime', region_name='us-west-2').__aenter__()
    
    try:
        async with AgentConversation(client=custom_client) as claude:
            async for chunk in claude.send_message("Hello from custom client!"):
                print(chunk, end="", flush=True)
            print("\n")
    finally:
        await custom_client.__aexit__(None, None, None)
    
    # Clean up global client when app shuts down
    await close_default_client()


if __name__ == "__main__":
    asyncio.run(main())