"""LLM service for handling Claude API integration."""

import os
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from loguru import logger
from models.schemas import Message, MessageRole
from config import settings


class LLMService:
    """Service for handling LLM inference with Claude API."""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or settings.claude_api_key
        self.model_name = settings.claude_model
        self.client = None
        self.is_loaded = False
        
        logger.info(f"LLM Service initialized with Claude model: {self.model_name}")
    
    def load_model(self) -> bool:
        """Initialize the Claude API client."""
        try:
            if not self.api_key:
                logger.error("Claude API key not found. Please set ANTHROPIC_API_KEY in your .env file.")
                return False
            
            logger.info(f"Initializing Claude API client with model: {self.model_name}")
            
            # Initialize Claude client
            self.client = Anthropic(api_key=self.api_key)
            
            self.is_loaded = True
            logger.info("Claude API client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client: {e}")
            return False
    
    def generate_response(
        self, 
        messages: List[Message], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        is_detailed: bool = False
    ) -> str:
        """
        Generate a response from Claude API.
        
        Args:
            messages: List of conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            is_detailed: Whether to generate a detailed response
            
        Returns:
            Generated response text
        """
        if not self.is_loaded:
            logger.error("Claude API client not initialized, attempting to initialize...")
            if not self.load_model():
                logger.error("Failed to initialize Claude API client")
                return "I'm sorry, the Claude API is not currently available. Please check your API key and try again later."
        
        try:
            # Format messages for Claude API
            formatted_messages = self._format_messages_for_claude(messages)
            
            # Set generation parameters
            response_tokens = max_tokens or settings.max_tokens
            if is_detailed:
                response_tokens = min(response_tokens * 2, 4096)  # Cap at 4096 for detailed responses
            
            # Generate response
            logger.debug(f"Generating response with {len(formatted_messages)} messages")
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=response_tokens,
                temperature=temperature or settings.temperature,
                messages=formatted_messages
            )
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text.strip()
            else:
                logger.warning("No content in Claude response")
                response_text = "I apologize, but I couldn't generate a response. Please try again."
            
            logger.debug(f"Generated response length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response from Claude: {e}")
            if "quota" in str(e).lower() or "429" in str(e):
                return "I'm sorry, the Claude API quota has been exceeded. Please check your API quota limits and try again later."
            return "I'm sorry, I encountered an error while generating a response. Please try again."
    
    def _format_messages_for_claude(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Format messages for Claude messages API with sustainability focus."""
        formatted_messages = []
        
        # Add sustainability-focused system prompt if not present
        has_system_prompt = any(msg.role == MessageRole.SYSTEM for msg in messages)
        if not has_system_prompt:
            system_prompt = """You are EarthGPT, an expert sustainability assistant focused on environmental topics, climate action, and sustainable practices. 

Your expertise includes:
- Renewable energy and clean technology
- Carbon reduction and climate mitigation
- Circular economy and waste management
- Environmental protection and conservation
- Sustainable business practices and ESG
- Green building and sustainable design
- Climate adaptation and resilience

Provide detailed, practical, and varied responses that help users understand and implement sustainable solutions. Use specific examples, data, and actionable recommendations. Each response should be unique and tailored to the specific question asked.

When users ask for more details or explanations, provide comprehensive, in-depth responses with specific implementation strategies, examples, and actionable steps."""
            
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Convert messages to Claude format
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                # Skip system messages as they're handled above
                continue
            elif message.role == MessageRole.USER:
                formatted_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif message.role == MessageRole.ASSISTANT:
                formatted_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
        
        return formatted_messages
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the Claude API configuration."""
        return {
            "model_name": self.model_name,
            "api_provider": "Anthropic Claude",
            "is_loaded": self.is_loaded,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "has_api_key": bool(self.api_key)
        }


# Global LLM service instance
llm_service = LLMService()
logger.info("Using Claude API LLM service")