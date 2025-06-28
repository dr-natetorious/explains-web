# src/shared/config.py
import yaml
import os
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AIProviderConfig:
    model_id: str
    region: str = "us-east-1"
    temperature: float = 0.7
    max_tokens: int = 4000

class ConfigurationSettings:
    """Simple configuration management reading from config/application.yml"""
    
    def __init__(self, config_path: str = "config/application.yml"):
        self.config_path = Path(config_path)
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    @property
    def ai_providers(self) -> Dict[str, AIProviderConfig]:
        """Get AI provider configurations"""
        providers = {}
        for name, config in self._config.get('ai_providers', {}).items():
            providers[name] = AIProviderConfig(**config)
        return providers
    
    @property
    def aws_region(self) -> str:
        """Get AWS region with environment override"""
        return os.getenv('AWS_DEFAULT_REGION', 
                        self._config.get('aws', {}).get('region', 'us-east-1'))
    
    @property
    def aws_profile(self) -> str:
        """Get AWS profile with environment override"""
        return os.getenv('AWS_PROFILE', 
                        self._config.get('aws', {}).get('profile', 'default'))
    
    @property
    def thenewsapi_key(self) -> str:
        """Get TheNewsAPI key from environment"""
        key = os.getenv('THENEWSAPI_KEY')
        if not key:
            raise ValueError("THENEWSAPI_KEY environment variable required")
        return key
    
    @property
    def pipeline_settings(self) -> Dict[str, Any]:
        """Get pipeline configuration"""
        return self._config.get('pipeline', {
            'max_workers': 4,
            'max_concurrent_repos': 3,
            'chunk_size': 512,
            'overlap': 50
        })
    
    @property
    def server_settings(self) -> Dict[str, Any]:
        """Get server configuration"""
        return self._config.get('server', {
            'host': '127.0.0.1',
            'port': 8000,
            'debug': False
        })

# Global configuration instance
settings = ConfigurationSettings()