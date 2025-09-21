"""Separate LLM service for summarization that can handle different message formats."""

import os
from typing import List, Dict, Any
from anthropic import Anthropic
from loguru import logger
from config import settings


class SummarizationLLMService:
    """LLM service specifically for summarization tasks."""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or settings.claude_api_key
        self.model_name = settings.claude_model
        self.client = None
        self.is_loaded = False
        
        logger.info(f"Summarization LLM Service initialized with Claude model: {self.model_name}")
    
    def load_model(self) -> bool:
        """Initialize the Claude API client."""
        try:
            if not self.api_key:
                logger.error("Claude API key not found. Please set ANTHROPIC_API_KEY in your .env file.")
                return False
            
            logger.info(f"Initializing Claude API client for summarization with model: {self.model_name}")
            
            # Initialize Claude client
            self.client = Anthropic(api_key=self.api_key)
            
            self.is_loaded = True
            logger.info("Claude API client for summarization initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client for summarization: {e}")
            return False
    
    def generate_response(self, messages: List[Dict[str, str]], is_detailed: bool = False) -> str:
        """
        Generate a response from Claude API for summarization.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            is_detailed: Whether to generate a detailed response (ignored for summarization)
            
        Returns:
            Generated response text
        """
        if not self.is_loaded:
            logger.error("Summarization LLM service not loaded")
            return ""
        
        try:
            # Convert dictionary format to Claude's expected format
            claude_messages = []
            system_prompt = None
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_prompt = content
                elif role == "user":
                    claude_messages.append({"role": "user", "content": content})
                elif role == "assistant":
                    claude_messages.append({"role": "assistant", "content": content})
            
            # Prepare the API call
            api_params = {
                "model": self.model_name,
                "max_tokens": 1000,  # Shorter for summaries
                "temperature": 0.1,  # Lower temperature for more consistent summaries
                "messages": claude_messages
            }
            
            # Add system prompt if provided
            if system_prompt:
                api_params["system"] = system_prompt
            
            # Call Claude API
            response = self.client.messages.create(**api_params)
            
            # Extract the response content
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                logger.warning("Empty response from Claude API for summarization")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating summarization response from Claude: {e}")
            return ""


# Global summarization LLM service instance
summarization_llm_service = SummarizationLLMService()
