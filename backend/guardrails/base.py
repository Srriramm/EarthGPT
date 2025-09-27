"""Base guardrails class with common functionality."""

from abc import ABC, abstractmethod
from typing import Tuple, Optional
from loguru import logger

from .models import GuardrailCheck


class BaseGuardrails(ABC):
    """Base class for all guardrails implementations."""
    
    def __init__(self):
        """Initialize base guardrails."""
        logger.info("Base guardrails initialized")
    
    @abstractmethod
    def check_sustainability_relevance(self, query: str, conversation_context: str = None) -> GuardrailCheck:
        """
        Check if the query is sustainability-related.
        
        Args:
            query: User input query
            conversation_context: Previous conversation context for follow-up detection
            
        Returns:
            GuardrailCheck with validation results
        """
        pass
    
    @abstractmethod
    def validate_output(self, response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the response is appropriate and sustainability-focused.
        
        Args:
            response: Generated response text
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        pass
    
    @abstractmethod
    def get_polite_refusal_message(self, reason: str) -> str:
        """
        Generate a polite refusal message for non-sustainability queries.
        
        Args:
            reason: Reason for rejection
            
        Returns:
            Polite refusal message
        """
        pass

