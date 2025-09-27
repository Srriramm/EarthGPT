"""Pydantic models for guardrails functionality."""

from typing import List, Optional
from pydantic import BaseModel


class GuardrailCheck(BaseModel):
    """Guardrail validation result."""
    is_sustainability_related: bool
    confidence_score: float
    detected_keywords: List[str]
    rejection_reason: Optional[str] = None

