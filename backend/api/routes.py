"""FastAPI routes for the Sustainability Assistant."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from datetime import datetime
import uuid
from loguru import logger

from models.schemas import (
    ConversationRequest, ConversationResponse, SessionInfo, 
    HealthResponse, ErrorResponse, Message, MessageRole
)
from core.guardrails import SustainabilityGuardrails
from core.pinecone_memory import PineconeMemoryManager
from core.complex_questions import ComplexQuestionHandler
from core.prompt_engineering import PromptManager
from services.llm_service import llm_service
from config import settings

# Initialize components
guardrails = SustainabilityGuardrails()
memory_manager = PineconeMemoryManager()
complex_handler = ComplexQuestionHandler()
prompt_manager = PromptManager()

# Create router
router = APIRouter(prefix=settings.api_prefix)


@router.post("/chat", response_model=ConversationResponse)
async def chat(request: ConversationRequest, background_tasks: BackgroundTasks):
    """
    Main chat endpoint for sustainability conversations.
    """
    try:
        # Generate session ID if not provided
        if not request.session_id:
            session_id = memory_manager.create_session()
        else:
            session_id = request.session_id
            # Ensure session exists by checking if we can get session info
            session_info = memory_manager.conversation_memory.get_session_info(session_id)
            if not session_info:
                # Create session metadata if it doesn't exist
                memory_manager.conversation_memory.session_metadata[session_id] = {
                    "created_at": datetime.utcnow(),
                    "last_activity": datetime.utcnow(),
                    "message_count": 0,
                    "user_id": "default"
                }
        
        logger.info(f"Processing chat request for session: {session_id}")
        
        # Step 1: Guardrail check
        guardrail_result = guardrails.check_sustainability_relevance(request.message)
        
        if not guardrail_result.is_sustainability_related:
            # Log the rejection
            background_tasks.add_task(
                log_interaction,
                session_id=session_id,
                query=request.message,
                response="",
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
            
            return ConversationResponse(
                response=guardrails.get_polite_refusal_message(guardrail_result.rejection_reason),
                session_id=session_id,
                is_summary=False,
                can_request_detailed=False,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
        
        # Step 2: Get context from memory system
        context = memory_manager.get_context_for_query(session_id, request.message)
        
        # Step 3: Use query classifier to determine if detailed response is needed
        # Get conversation history for classification
        conversation_history = []
        if hasattr(context, 'conversation_history') and context.conversation_history:
            conversation_history = [msg.content for msg in context.conversation_history if hasattr(msg, 'role') and msg.role == MessageRole.USER]
        
        # Import and use the query classifier
        from core.query_classifier import QueryClassifier, ResponseLength
        classifier = QueryClassifier()
        query_type, response_length = classifier.classify_query(request.message, conversation_history)
        
        # Check if this should be a detailed response
        is_detailed_request = (
            request.request_detailed or 
            response_length == ResponseLength.DETAILED or
            ("explain" in request.message.lower()) or  # Any "explain" query should be detailed
            ("elaborate" in request.message.lower() and len(conversation_history) > 0) or
            ("example" in request.message.lower())  # Queries asking for examples should be detailed
        )
        
        # Only use old simple question detection for very basic definitions
        is_simple_question = (
            "which of the following" in request.message.lower() or
            ("what is" in request.message.lower() and len(request.message.split()) <= 5) or
            ("define" in request.message.lower() and len(request.message.split()) <= 4) or
            ("what does" in request.message.lower() and "mean" in request.message.lower() and len(request.message.split()) <= 6)
        )
        
        # Always use LLM service for full responses - disable complex_handler summary generation
        is_summary = False
        can_request_detailed = False
        
        # Step 4: Generate full response using LLM
        is_detailed = is_detailed_request
        messages = prompt_manager.create_conversation_prompt(
            request.message, 
            context.dict() if hasattr(context, 'dict') else context, 
            is_detailed=is_detailed,
            is_summary=False
        )
        
        # Generate response from LLM
        response_text = llm_service.generate_response(messages, is_detailed=is_detailed)
        
        # Step 5: Validate output with guardrails
        is_valid, rejection_reason = guardrails.validate_output(response_text)
        
        if not is_valid:
            logger.warning(f"Output validation failed: {rejection_reason}")
            response_text = "I apologize, but I need to provide a more focused response on sustainability topics. Could you please rephrase your question with more specific sustainability context?"
        
        # Step 6: Add messages to conversation history
        from datetime import datetime, timedelta
        
        # Create user message with current timestamp
        user_timestamp = datetime.utcnow()
        user_message = Message(role=MessageRole.USER, content=request.message, timestamp=user_timestamp)
        
        # Create assistant message with slightly later timestamp
        assistant_timestamp = user_timestamp + timedelta(milliseconds=1)
        assistant_message = Message(role=MessageRole.ASSISTANT, content=response_text, timestamp=assistant_timestamp)
        
        logger.info(f"User message timestamp: {user_timestamp.isoformat()}")
        logger.info(f"Assistant message timestamp: {assistant_timestamp.isoformat()}")
        
        memory_manager.add_message(session_id, user_message)
        memory_manager.add_message(session_id, assistant_message)
        
        # Step 7: Log the interaction
        background_tasks.add_task(
            log_interaction,
            session_id=session_id,
            query=request.message,
            response=response_text,
            guardrail_triggered=False,
            guardrail_reason=None
        )
        
        return ConversationResponse(
            response=response_text,
            session_id=session_id,
            is_summary=False,
            can_request_detailed=False,
            guardrail_triggered=False
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=llm_service.is_loaded,
        guardrails_enabled=settings.enable_guardrails,
        memory_system_active=True
    )


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a specific session."""
    session_info = memory_manager.conversation_memory.get_session_info(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(
        session_id=session_id,
        created_at=session_info["created_at"],
        last_activity=session_info["last_activity"],
        message_count=session_info["message_count"],
        is_active=True
    )


@router.get("/sessions/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session."""
    history = memory_manager.conversation_memory.get_conversation_history(session_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or no history")
    
    return {"session_id": session_id, "messages": history}


@router.get("/sessions")
async def get_user_sessions(user_id: str = "default"):
    """Get all sessions for a user."""
    sessions = memory_manager.get_user_sessions(user_id)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    success = memory_manager.delete_session(session_id)
    if success:
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/sessions")
async def create_session(user_id: str = "default"):
    """Create a new conversation session."""
    session_id = memory_manager.create_session(user_id)
    return {"session_id": session_id, "message": "Session created successfully"}


@router.get("/model/info")
async def get_model_info():
    """Get information about the loaded model."""
    return llm_service.get_model_info()


@router.post("/admin/cleanup")
async def cleanup_old_sessions():
    """Clean up old sessions (admin endpoint)."""
    memory_manager.cleanup_old_sessions(hours=24)
    return {"message": "Old sessions cleaned up successfully"}


@router.get("/admin/stats")
async def get_system_stats():
    """Get system statistics (admin endpoint)."""
    active_sessions = len(memory_manager.conversation_memory.session_metadata)
    total_documents = memory_manager.rag_system.collection.count()
    
    return {
        "active_sessions": active_sessions,
        "total_documents": total_documents,
        "guardrails_enabled": settings.enable_guardrails,
        "model_loaded": llm_service.is_loaded,
        "uptime": "N/A"  # Could implement proper uptime tracking
    }


async def log_interaction(
    session_id: str,
    query: str,
    response: str,
    guardrail_triggered: bool,
    guardrail_reason: str = None
):
    """Background task to log interactions."""
    try:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "query": query,
            "response": response,
            "guardrail_triggered": guardrail_triggered,
            "guardrail_reason": guardrail_reason,
            "query_length": len(query),
            "response_length": len(response)
        }
        
        logger.info(f"Interaction logged: {log_data}")
        
        # In a production system, you would save this to a database
        # For now, we'll just log it
        
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")


# Error handlers will be added to the main FastAPI app in main.py
