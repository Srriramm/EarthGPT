"""Configuration settings for the Sustainability Assistant."""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Claude API Configuration
    claude_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    claude_model: str = "claude-sonnet-4-20250514"  # Latest Sonnet 4
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Specialized Claude Models
    claude_summarization_model: str = "claude-3-5-haiku-latest"  # Latest Haiku
    claude_classification_model: str = "claude-3-5-haiku-latest"  # Latest Haiku
    
    
    # API Version
    anthropic_version: str = "2023-06-01"
    
    # Database Configuration (MongoDB only)
    
    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")
    mongodb_database: str = Field(default="earthgpt", alias="MONGODB_DATABASE")
    
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Security
    secret_key: str = Field(default="", alias="SECRET_KEY")
    access_token_expire_minutes: int = 480  # 8 hours
    algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/sustainability_assistant.log"
    
    # Memory Configuration
    max_conversation_history: int = 6  # Reduced from 10 to save tokens
    max_context_tokens: int = 8000
    
    # Claude Memory Tool Configuration
    enable_claude_memory_tool: bool = True
    memories_directory: str = "./memories"
    max_memory_entries_per_session: int = 50
    memory_cleanup_days: int = 30
    
    # Web Fetch Tool Configuration
    enable_web_fetch_tool: bool = True
    web_fetch_max_uses: int = 5
    web_fetch_allowed_domains: List[str] = []  # Empty means all domains allowed
    web_fetch_max_content_length: int = 1000000  # 1MB limit
    
    # Web Search Tool Configuration
    enable_web_search_tool: bool = True
    web_search_max_uses: int = 5
    web_search_localization: str = "en-US"
    
    # Text Editor Tool Configuration
    enable_text_editor_tool: bool = True
    text_editor_max_characters: int = 10000
    text_editor_allowed_extensions: List[str] = [".py", ".js", ".ts", ".html", ".css", ".md", ".txt", ".json", ".yaml", ".yml"]
    
    # Streaming Configuration
    enable_streaming: bool = True
    streaming_chunk_size: int = 1024
    
    # Prompt Caching Configuration
    enable_prompt_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_entries: int = 1000
    
    # Batch Request Configuration
    enable_batch_requests: bool = True
    max_batch_size: int = 10
    max_concurrent_requests: int = 5
    
    
    # Guardrails Configuration
    enable_guardrails: bool = True
    
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate that secret key is provided and secure."""
        if not v:
            raise ValueError("SECRET_KEY must be provided in environment variables")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "protected_namespaces": (),
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
