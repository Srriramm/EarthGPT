"""Pydantic models for API request/response schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Individual message in conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationRequest(BaseModel):
    """Request model for chat conversation."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    request_detailed: bool = False  # For progressive summarization


class ConversationResponse(BaseModel):
    """Response model for chat conversation."""
    response: str
    session_id: str
    is_summary: bool = False
    can_request_detailed: bool = False
    guardrail_triggered: bool = False
    guardrail_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    model_loaded: bool
    guardrails_enabled: bool
    memory_system_active: bool


class GuardrailCheck(BaseModel):
    """Guardrail validation result."""
    is_sustainability_related: bool
    confidence_score: float
    detected_keywords: List[str]
    rejection_reason: Optional[str] = None


class MemoryContext(BaseModel):
    """Retrieved context from memory system."""
    relevant_documents: List[Dict[str, Any]]
    conversation_history: List[Message]
    context_summary: str


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Authentication Schemas
class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class User(UserBase):
    """User model for responses."""
    id: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[str] = None


# Session Management Schemas
class ChatSession(BaseModel):
    """Chat session model."""
    id: str
    user_id: str
    title: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    is_active: bool = True


class ChatSessionCreate(BaseModel):
    """Chat session creation model."""
    title: str = Field(..., min_length=1, max_length=100)


class ChatSessionUpdate(BaseModel):
    """Chat session update model."""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


# Updated conversation schemas with user context
class ConversationRequestWithUser(BaseModel):
    """Request model for chat conversation with user context."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    request_detailed: bool = False
    user_id: str  # Added user context


class ConversationResponseWithUser(BaseModel):
    """Response model for chat conversation with user context."""
    response: str
    session_id: str
    user_id: str
    is_summary: bool = False
    can_request_detailed: bool = False
    guardrail_triggered: bool = False
    guardrail_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
