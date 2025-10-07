"""FastAPI routes for authenticated users only."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from models.schemas import (
    ConversationRequestWithUser, ConversationResponseWithUser, SessionInfo, 
    HealthResponse, ErrorResponse, Message, MessageRole
)
from guardrails import HybridClassifierGuardrails
from core.mongodb_memory import mongodb_session_manager
from core.prompt_engineering import PromptManager
from core.title_generator import TitleGenerator
from services.llm_service import llm_service
from auth.dependencies import get_current_active_user
from models.schemas import User
from models.user import chat_session_model
from config import settings

# Initialize components
guardrails = HybridClassifierGuardrails()
mongodb_memory = mongodb_session_manager
prompt_manager = PromptManager()
title_generator = TitleGenerator()

# Create router
router = APIRouter(prefix=settings.api_prefix)


@router.post("/chat", response_model=ConversationResponseWithUser)
async def chat(
    request: ConversationRequestWithUser, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Main chat endpoint for authenticated users using Claude's native memory.
    """
    try:
        # Generate session ID if not provided
        if not request.session_id:
            try:
                session_id = await mongodb_memory.create_session(current_user.id)
                logger.info(f"Created new session {session_id} for user {current_user.id}")
            except Exception as e:
                logger.error(f"Failed to create session for user {current_user.id}: {e}")
                raise HTTPException(status_code=500, detail="Failed to create session")
        else:
            session_id = request.session_id
            
            # Check if session exists and belongs to user
            session_info = await mongodb_memory.get_session_info(session_id)
            if not session_info:
                logger.warning(f"Session {session_id} not found for user {current_user.id}")
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Verify session ownership
            if session_info.get("user_id") != current_user.id:
                logger.warning(f"Session {session_id} does not belong to user {current_user.id}")
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Step 1: Fast guardrail check for obvious non-sustainability queries
        guardrail_result = None
        if settings.enable_guardrails:
            try:
                # Fast path: Check for obvious non-sustainability keywords first
                query_lower = request.message.lower()
                obvious_non_sustainability = [
                    "portfolio", "investment", "trading", "stock", "market", "finance",
                    "cooking", "recipe", "food", "restaurant", "travel", "vacation",
                    "health", "fitness", "exercise", "medical", "doctor", "medicine",
                    "entertainment", "movie", "music", "game", "sports", "football",
                    "programming", "code", "software", "app", "website", "database",
                    "relationship", "dating", "marriage", "family", "personal"
                ]
                
                # Check if this is a memory-related question first
                memory_indicators = [
                    "remember", "recall", "do you remember", "did we discuss", "you mentioned", 
                    "you said", "earlier you", "previously", "before you", "in our conversation",
                    "what did you", "you told me", "you explained", "you suggested"
                ]
                is_memory_question = any(indicator in query_lower for indicator in memory_indicators)
                
                # If query contains obvious non-sustainability terms, block immediately
                # UNLESS it's a memory question or has sustainability indicators
                if any(term in query_lower for term in obvious_non_sustainability):
                    # Check if it's actually about sustainability (e.g., "sustainable finance")
                    sustainability_indicators = ["sustainable", "green", "eco", "environmental", "climate", "carbon", "renewable", "esg"]
                    if not any(indicator in query_lower for indicator in sustainability_indicators) and not is_memory_question:
                        logger.warning(f"Fast path: Non-sustainability query blocked: {request.message[:100]}...")
                        return ConversationResponseWithUser(
                            response="I'm specialized in sustainability topics. Please ask me about environmental issues, climate change, renewable energy, sustainable practices, or related topics.",
                            session_id=session_id,
                            user_id=current_user.id,
                            is_sustainability_related=False,
                            confidence_score=0.9,
                            guardrail_triggered=True,
                            guardrail_reason="Query appears to be about non-sustainability topics",
                            memory_used=False,
                            claude_memory_enabled=True,
                            web_search_enabled=False,
                            user=current_user
                        )
                
                # Full guardrail check for uncertain cases
                guardrail_result = guardrails.check_sustainability_relevance(request.message)
                if not guardrail_result.is_sustainability_related:
                    logger.warning(f"Non-sustainability query blocked: {request.message[:100]}...")
                    return ConversationResponseWithUser(
                        response="I'm specialized in sustainability topics. Please ask me about environmental issues, climate change, renewable energy, sustainable practices, or related topics.",
                        session_id=session_id,
                        user_id=current_user.id,
                        is_sustainability_related=False,
                        confidence_score=guardrail_result.confidence_score,
                        guardrail_triggered=True,
                        guardrail_reason=guardrail_result.rejection_reason,
                        memory_used=False,
                        claude_memory_enabled=True,
                        web_search_enabled=False,
                        user=current_user
                    )
            except Exception as e:
                logger.error(f"Guardrail validation error: {e}")
        
        # Step 2: Store user message in memory
        await mongodb_memory.add_message_to_session(session_id, MessageRole.USER, request.message)
        
        # Step 3: Prepare messages for Claude with enhanced context
        messages = []
        
        # Add system prompt
        system_prompt = prompt_manager.get_system_prompt()
        messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        
        # Add context summary if available
        memory_context = await mongodb_memory.build_context(session_id)
        if memory_context.context_summary:
            context_message = f"Previous conversation context: {memory_context.context_summary}"
            messages.append(Message(role=MessageRole.SYSTEM, content=context_message))
        
        # Add recent conversation history
        recent_messages = memory_context.conversation_history[-settings.max_conversation_history:]
        messages.extend(recent_messages)
        
        # Add current user message
        messages.append(Message(role=MessageRole.USER, content=request.message))
        
        # Step 4: Generate response using Claude with memory tool
        result = await llm_service.generate_response(
            messages=messages,
            session_id=session_id
        )
        
        if result.get("error"):
            logger.error(f"LLM service error: {result['error']}")
            raise HTTPException(status_code=500, detail="Failed to generate response")
        
        response_text = result["response"]
        
        # Step 5: Store assistant response in memory
        await mongodb_memory.add_message_to_session(session_id, MessageRole.ASSISTANT, response_text)
        
        # Step 6: Generate title if this is the first exchange
        session_data = await mongodb_memory.get_session_info(session_id)
        if session_data and session_data.get("message_count", 0) == 2:  # One user message + one assistant message
            try:
                title = title_generator.generate_title(request.message)
                if title and title != "New Chat":
                    await mongodb_memory.update_session_title(session_id, title)
                    logger.info(f"Generated title for session {session_id}: {title}")
            except Exception as e:
                logger.error(f"Failed to generate title for session {session_id}: {e}")
        
        # Step 7: Update session activity
        await mongodb_memory.update_session_activity(session_id, current_user.id)
        
        logger.info(f"Successfully processed authenticated chat request for user {current_user.id}, session {session_id}")
        
        return ConversationResponseWithUser(
            response=response_text,
            session_id=session_id,
            user_id=current_user.id,
            is_sustainability_related=True,
            confidence_score=guardrail_result.confidence_score if guardrail_result else 0.95,
            memory_used=result.get("memory_used", False),
            claude_memory_enabled=True,
            web_search_enabled=False,
            user=current_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in authenticated chat endpoint: {e}")
        return ConversationResponseWithUser(
            response="I'm sorry, I encountered an unexpected error. Please try again.",
            session_id=request.session_id or "unknown",
            user_id=current_user.id,
            is_sustainability_related=True,
            confidence_score=0.0,
            memory_used=False,
            claude_memory_enabled=True,
            web_search_enabled=False,
            user=current_user,
            error=str(e)
        )


@router.get("/sessions", response_model=List[SessionInfo])
async def get_sessions(current_user: User = Depends(get_current_active_user)):
    """Get all sessions for the authenticated user."""
    try:
        sessions = await mongodb_memory.get_user_sessions(current_user.id)
        
        # Convert to SessionInfo format
        session_list = []
        for session in sessions:
            session_info = SessionInfo(
                session_id=session["session_id"],
                title=session.get("title", "New Chat"),
                created_at=session.get("created_at", ""),
                last_activity=session.get("last_activity", ""),
                message_count=session.get("message_count", 0),
                is_active=session.get("is_active", True)
            )
            session_list.append(session_info)
        
        return session_list
        
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str, 
    current_user: User = Depends(get_current_active_user)
):
    """Get conversation history for a session."""
    try:
        # Get session info first
        session_info = await mongodb_memory.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session ownership
        if session_info.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get messages from the session
        messages = await mongodb_memory.get_session_messages(session_id)
        
        # Convert to the expected format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        return {"session_id": session_id, "messages": formatted_messages}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch session history")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, 
    current_user: User = Depends(get_current_active_user)
):
    """Delete a specific session."""
    try:
        # Get session info first to verify ownership
        session_info = await mongodb_memory.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify session ownership
        if session_info.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete the session
        success = await mongodb_memory.delete_session(session_id)
        if success:
            logger.info(f"Successfully deleted session {session_id} for user {current_user.id}")
            return {"message": "Session deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=llm_service.is_loaded,
        guardrails_enabled=settings.enable_guardrails,
        memory_system_active=True,
        claude_memory_enabled=settings.enable_claude_memory_tool,
        web_search_enabled=False,
        web_fetch_enabled=False,
        memory_stats=await mongodb_memory.get_memory_stats()
    )
