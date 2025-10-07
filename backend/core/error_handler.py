"""Enhanced error handling for Claude API and tools."""

import re
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from config import settings


class ClaudeErrorHandler:
    """Enhanced error handler for Claude API and tool operations."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.error_patterns = {
            "rate_limit": [
                r"rate_limit_error",
                r"429",
                r"too many requests",
                r"rate limit exceeded"
            ],
            "quota_exceeded": [
                r"quota",
                r"billing",
                r"payment",
                r"credit",
                r"insufficient funds"
            ],
            "context_window": [
                r"context",
                r"token.*limit",
                r"maximum.*tokens",
                r"input.*too.*long"
            ],
            "authentication": [
                r"unauthorized",
                r"invalid.*key",
                r"authentication",
                r"401"
            ],
            "model_not_found": [
                r"model.*not.*found",
                r"invalid.*model",
                r"model.*unavailable"
            ],
            "tool_error": [
                r"tool.*error",
                r"tool.*not.*found",
                r"invalid.*tool"
            ],
            "network_error": [
                r"connection",
                r"timeout",
                r"network",
                r"dns"
            ]
        }
        
        self.user_friendly_messages = {
            "rate_limit": "I'm currently experiencing high demand. Please wait a moment and try again. The rate limit will reset shortly.",
            "quota_exceeded": "I'm sorry, the Claude API quota has been exceeded. Please check your API quota limits and try again later.",
            "context_window": "I'm sorry, this conversation has become too long for me to process. Please start a new conversation or ask a more focused question.",
            "authentication": "I'm sorry, there's an authentication issue with the Claude API. Please check your API key configuration.",
            "model_not_found": "I'm sorry, the requested model is not available. Please try again with a different model.",
            "tool_error": "I'm sorry, there was an error with one of the tools. Please try again.",
            "network_error": "I'm sorry, there's a network connectivity issue. Please check your internet connection and try again.",
            "unknown_error": "I'm sorry, I encountered an unexpected error. Please try again."
        }
        
        logger.info("Enhanced error handler initialized")
    
    def classify_error(self, error_message: str) -> str:
        """
        Classify an error message into a category.
        
        Args:
            error_message: The error message to classify
            
        Returns:
            Error category string
        """
        error_lower = error_message.lower()
        
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_lower):
                    logger.debug(f"Error classified as {category}: {error_message[:100]}...")
                    return category
        
        return "unknown_error"
    
    def get_user_friendly_message(self, error_message: str, error_category: str = None) -> str:
        """
        Get a user-friendly error message.
        
        Args:
            error_message: The original error message
            error_category: The classified error category (optional)
            
        Returns:
            User-friendly error message
        """
        if error_category is None:
            error_category = self.classify_error(error_message)
        
        return self.user_friendly_messages.get(error_category, self.user_friendly_messages["unknown_error"])
    
    def handle_claude_api_error(self, error: Exception) -> Dict[str, Any]:
        """
        Handle Claude API errors with proper classification and user-friendly messages.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Dictionary with error information
        """
        error_message = str(error)
        error_category = self.classify_error(error_message)
        user_message = self.get_user_friendly_message(error_message, error_category)
        
        # Log the error with appropriate level
        if error_category in ["rate_limit", "quota_exceeded"]:
            logger.warning(f"Claude API {error_category}: {error_message}")
        elif error_category in ["authentication", "model_not_found"]:
            logger.error(f"Claude API {error_category}: {error_message}")
        else:
            logger.error(f"Claude API {error_category}: {error_message}")
        
        return {
            "error": error_category,
            "message": user_message,
            "original_error": error_message,
            "retry_recommended": error_category in ["rate_limit", "network_error"],
            "retry_after_seconds": self._get_retry_delay(error_category)
        }
    
    def handle_tool_error(self, tool_name: str, error: Exception) -> Dict[str, Any]:
        """
        Handle tool-specific errors.
        
        Args:
            tool_name: Name of the tool that failed
            error: The exception that occurred
            
        Returns:
            Dictionary with error information
        """
        error_message = str(error)
        error_category = self.classify_error(error_message)
        
        # Tool-specific error messages
        tool_messages = {
            "memory": "I'm sorry, there was an error accessing my memory system. Please try again.",
            "web_fetch": "I'm sorry, there was an error fetching web content. Please check the URL and try again.",
            "web_search": "I'm sorry, there was an error performing the web search. Please try again.",
            "text_editor": "I'm sorry, there was an error with the text editor. Please try again."
        }
        
        user_message = tool_messages.get(tool_name, self.get_user_friendly_message(error_message, error_category))
        
        logger.error(f"Tool error in {tool_name}: {error_message}")
        
        return {
            "error": f"tool_{error_category}",
            "message": user_message,
            "tool_name": tool_name,
            "original_error": error_message,
            "retry_recommended": error_category in ["network_error", "rate_limit"]
        }
    
    def _get_retry_delay(self, error_category: str) -> int:
        """Get recommended retry delay in seconds for different error categories."""
        retry_delays = {
            "rate_limit": 60,  # 1 minute
            "quota_exceeded": 3600,  # 1 hour
            "network_error": 30,  # 30 seconds
            "context_window": 0,  # No retry
            "authentication": 0,  # No retry
            "model_not_found": 0,  # No retry
            "tool_error": 10,  # 10 seconds
            "unknown_error": 30  # 30 seconds
        }
        
        return retry_delays.get(error_category, 30)
    
    def should_retry(self, error_category: str, retry_count: int = 0) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error_category: The classified error category
            retry_count: Number of times already retried
            
        Returns:
            True if should retry, False otherwise
        """
        max_retries = {
            "rate_limit": 3,
            "network_error": 2,
            "tool_error": 2,
            "unknown_error": 1
        }
        
        if error_category not in max_retries:
            return False
        
        return retry_count < max_retries[error_category]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return {
            "error_patterns_count": sum(len(patterns) for patterns in self.error_patterns.values()),
            "user_friendly_messages_count": len(self.user_friendly_messages),
            "supported_error_categories": list(self.error_patterns.keys())
        }


# Global error handler instance
error_handler = ClaudeErrorHandler()

