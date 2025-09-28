"""LLM service for handling Claude API integration with token management."""

import os
from typing import List, Dict, Any, Optional, Tuple
from anthropic import Anthropic
from loguru import logger
from models.schemas import Message, MessageRole
from config import settings
from core.token_manager import ContextWindowManager, TokenCounter


class LLMService:
    """Service for handling LLM inference with Claude API."""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or settings.claude_api_key
        self.model_name = settings.claude_model
        self.client = None
        self.is_loaded = False
        
        # Initialize token management
        self.context_manager = ContextWindowManager()
        self.token_counter = TokenCounter()
        
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
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude API with token management.
        
        Args:
            messages: List of conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            is_detailed: Whether to generate a detailed response
            
        Returns:
            Dictionary with response text and metadata
        """
        if not self.is_loaded:
            logger.error("Claude API client not initialized, attempting to initialize...")
            if not self.load_model():
                logger.error("Failed to initialize Claude API client")
                return {
                    "response": "I'm sorry, the Claude API is not currently available. Please check your API key and try again later.",
                    "error": "api_not_available",
                    "usage_info": {}
                }
        
        try:
            # Format messages for Claude API
            formatted_messages, system_prompt = self._format_messages_for_claude(messages)
            
            # Calculate token usage and validate request
            expected_output_tokens = max_tokens or settings.max_tokens
            if is_detailed:
                expected_output_tokens = min(expected_output_tokens * 2, 4096)
            
            # Validate context window
            validation = self.context_manager.validate_request(formatted_messages, expected_output_tokens)
            
            if not validation["valid"]:
                logger.warning(f"Request exceeds context window: {validation['usage_info']}")
                return {
                    "response": "I'm sorry, this conversation has become too long for me to process effectively. Please start a new conversation or ask a more focused question.",
                    "error": "context_window_exceeded",
                    "usage_info": validation["usage_info"],
                    "recommendations": validation["recommendations"]
                }
            
            # Truncate if needed
            if self.context_manager.should_truncate(formatted_messages, expected_output_tokens):
                logger.info("Truncating conversation to fit context window")
                formatted_messages, truncation_info = self.context_manager.truncate_conversation(
                    formatted_messages, expected_output_tokens
                )
                logger.info(f"Truncation info: {truncation_info}")
            
            # Get optimal output tokens
            optimal_tokens = self.context_manager.get_optimal_output_tokens(formatted_messages)
            response_tokens = min(expected_output_tokens, optimal_tokens)
            
            # Generate response
            logger.debug(f"Generating response with {len(formatted_messages)} messages, max_tokens: {response_tokens}")
            
            # Debug: Log the first message to see if system prompt is present
            if formatted_messages:
                first_msg = formatted_messages[0]
                logger.info(f"LLM Service: First message role: {first_msg.get('role', 'unknown')}")
                if system_prompt:
                    logger.info(f"LLM Service: System prompt present, length: {len(system_prompt)}")
                else:
                    logger.warning(f"LLM Service: No system prompt found!")
            
            # Prepare API parameters
            api_params = {
                "model": self.model_name,
                "max_tokens": response_tokens,
                "temperature": temperature or settings.temperature,
                "messages": formatted_messages
            }
            
            # Add system prompt if available
            if system_prompt:
                api_params["system"] = system_prompt
            
            response = self.client.messages.create(**api_params)
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                response_text = response.content[0].text.strip()
            else:
                logger.warning("No content in Claude response")
                response_text = "I apologize, but I couldn't generate a response. Please try again."
            
            # Calculate final usage
            final_usage = self.context_manager.calculate_usage(formatted_messages, response_tokens)
            
            logger.debug(f"Generated response length: {len(response_text)}")
            return {
                "response": response_text,
                "error": None,
                "usage_info": final_usage,
                "tokens_used": response_tokens
            }
            
        except Exception as e:
            logger.error(f"Error generating response from Claude: {e}")
            
            # Handle specific error types
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg:
                return {
                    "response": "I'm sorry, the Claude API quota has been exceeded. Please check your API quota limits and try again later.",
                    "error": "quota_exceeded",
                    "usage_info": {}
                }
            elif "context" in error_msg or "token" in error_msg:
                return {
                    "response": "I'm sorry, this conversation has become too long for me to process. Please start a new conversation or ask a more focused question.",
                    "error": "context_window_exceeded",
                    "usage_info": {}
                }
            else:
                return {
                    "response": "I'm sorry, I encountered an error while generating a response. Please try again.",
                    "error": "unknown_error",
                    "usage_info": {}
                }
    
    def _format_messages_for_claude(self, messages: List[Message]) -> Tuple[List[Dict[str, str]], str]:
        """Format messages for Claude messages API with sustainability focus."""
        formatted_messages = []
        system_prompt = None
        
        # Extract system prompt from messages
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                system_prompt = message.content
                break
        
        # Add default system prompt if none found
        if not system_prompt:
            system_prompt = """You are EarthGPT, a sustainability and environmental expert assistant. You provide accurate information on sustainability, environmental protection, climate action, and related topics.

IMPORTANT: Questions reaching you have already been validated as sustainability-related by an advanced classification system. Trust this validation and provide helpful answers.

CORE FUNCTION
Answer questions about environmental science, climate solutions, sustainable practices, green technology, renewable energy, conservation, sustainability policy, ESG reporting, environmental frameworks, standards, certifications, and all related topics.

Include technical topics like:
- Sustainability reporting frameworks (GRI, SASB, TCFD, CDP, etc.)
- Environmental policies and regulations
- Carbon accounting and emissions management
- ESG investing and sustainable finance
- Corporate sustainability practices
- Environmental compliance and standards

RESPONSE PROTOCOL
For All Questions (pre-validated as sustainability-related):
Provide direct, accurate answers using natural conversational language. If you're unfamiliar with a specific term or policy, acknowledge this but still attempt to provide context within the sustainability domain.

QUALITY STANDARDS
- Accuracy: Base responses on current scientific consensus
- Precision: Answer exactly what was asked
- Clarity: Use natural, conversational language
- Completeness: Provide sufficient detail for the question's complexity

RESPONSE LENGTH
- Simple questions: Direct 1-2 sentence answers
- Complex questions: Comprehensive paragraphs as needed
Always prioritize precision over length"""
        
        # Convert messages to Claude format, properly handling system messages
        for message in messages:
            if message.role == MessageRole.USER:
                formatted_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif message.role == MessageRole.ASSISTANT:
                formatted_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
            # Skip system messages as they're handled separately
        
        return formatted_messages, system_prompt
    
    def generate_response_simple(
        self, 
        messages: List[Message], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        is_detailed: bool = False
    ) -> str:
        """
        Generate a response from Claude API (backward-compatible method).
        
        Returns just the response text for existing code compatibility.
        """
        result = self.generate_response(messages, max_tokens, temperature, is_detailed)
        return result.get("response", "I'm sorry, I couldn't generate a response.")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the Claude API configuration."""
        return {
            "model_name": self.model_name,
            "api_provider": "Anthropic Claude",
            "is_loaded": self.is_loaded,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "has_api_key": bool(self.api_key),
            "context_window": self.context_manager.config.max_context_tokens,
            "max_output_tokens": self.context_manager.config.max_output_tokens
        }


# Global LLM service instance
llm_service = LLMService()
logger.info("Using Claude API LLM service")