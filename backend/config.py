"""Configuration settings for the Sustainability Assistant."""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Claude API Configuration
    claude_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = "claude-3-7-sonnet-latest"
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Database Configuration (MongoDB only)
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "earthgpt"
    
    # Vector Database Configuration
    chroma_persist_directory: str = "./chroma_db"
    
    # Pinecone Configuration
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 480  # 8 hours
    algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/sustainability_assistant.log"
    
    # Memory Configuration
    max_conversation_history: int = 10
    max_context_tokens: int = 8000
    
    # Guardrails Configuration
    enable_guardrails: bool = True
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "protected_namespaces": (),
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
