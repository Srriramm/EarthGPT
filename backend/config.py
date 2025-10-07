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
    claude_model: str = "claude-sonnet-4-5-20250929"  # Latest Sonnet 4.5
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # Specialized Claude Models
    claude_summarization_model: str = "claude-3-5-haiku-latest"  # Latest Haiku
    claude_classification_model: str = "claude-3-5-haiku-latest"  # Latest Haiku
    
    # Additional Model Options
    claude_opus_model: str = "claude-opus-4-1-20250805"  # Latest Opus 4.1
    claude_sonnet_3_7_model: str = "claude-3-7-sonnet-20250219"  # Latest Sonnet 3.7
    
    # API Version
    anthropic_version: str = "2023-06-01"
    
    # Database Configuration (MongoDB only)
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "earthgpt"
    
    
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
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "protected_namespaces": (),
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
