"""Factory for creating guardrails instances."""

from typing import Optional
from loguru import logger

from .config import GuardrailsConfig
from .sustainability_guardrails import SustainabilityGuardrails
from .intelligent_guardrails import IntelligentGuardrails
from .base import BaseGuardrails


class GuardrailsFactory:
    """Factory class for creating guardrails instances."""
    
    @staticmethod
    def create_guardrails(
        guardrails_type: str = "intelligent",
        config: Optional[GuardrailsConfig] = None
    ) -> BaseGuardrails:
        """
        Create a guardrails instance.
        
        Args:
            guardrails_type: Type of guardrails to create ("basic", "intelligent")
            config: Optional configuration object
            
        Returns:
            Guardrails instance
        """
        if config is None:
            config = GuardrailsConfig()
        
        if guardrails_type == "basic":
            logger.info("Creating basic sustainability guardrails")
            return SustainabilityGuardrails(config)
        elif guardrails_type == "intelligent":
            logger.info("Creating intelligent guardrails")
            return IntelligentGuardrails(config)
        else:
            raise ValueError(f"Unknown guardrails type: {guardrails_type}")
    
    @staticmethod
    def create_default_guardrails() -> BaseGuardrails:
        """
        Create the default guardrails instance (intelligent).
        
        Returns:
            Default guardrails instance
        """
        return GuardrailsFactory.create_guardrails("intelligent")


# Global instance for easy access
default_guardrails = GuardrailsFactory.create_default_guardrails()




