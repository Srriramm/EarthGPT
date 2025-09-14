"""FastAPI routes for the Sustainability Assistant."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from datetime import datetime
import re
from loguru import logger

from models.schemas import (
    ConversationRequest, ConversationResponse, SessionInfo, 
    HealthResponse, ErrorResponse, Message, MessageRole,
    ConversationRequestWithUser, ConversationResponseWithUser
)
from core.intelligent_guardrails import IntelligentGuardrails
from core.pinecone_memory import PineconeMemoryManager
from core.complex_questions import ComplexQuestionHandler
from core.prompt_engineering import PromptManager
from services.llm_service import llm_service
from auth.dependencies import get_current_active_user, get_optional_current_user
from models.schemas import User
from models.user import chat_session_model
from config import settings

# Initialize components
guardrails = IntelligentGuardrails()
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
            session_id = memory_manager.create_session("default")
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
        
        # Step 1: STRICT Guardrail check
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
        
        # Step 3: Use query classifier to determine response length
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
            _is_elaboration_request(request.message, conversation_history)
        )
        
        # Step 4: Generate response using LLM with appropriate length
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
        from datetime import timedelta
        
        # Create user message with current timestamp
        user_timestamp = datetime.utcnow()
        user_message = Message(role=MessageRole.USER, content=request.message, timestamp=user_timestamp)
        
        # Create assistant message with slightly later timestamp
        assistant_timestamp = user_timestamp + timedelta(milliseconds=1)
        assistant_message = Message(role=MessageRole.ASSISTANT, content=response_text, timestamp=assistant_timestamp)
        
        logger.info(f"User message timestamp: {user_timestamp.isoformat()}")
        logger.info(f"Assistant message timestamp: {assistant_timestamp.isoformat()}")
        
        memory_manager.add_message(session_id, user_message, "default")
        memory_manager.add_message(session_id, assistant_message, "default")
        
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


@router.post("/chat/authenticated", response_model=ConversationResponseWithUser)
async def chat_authenticated(
    request: ConversationRequestWithUser, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Authenticated chat endpoint for sustainability conversations with user context.
    """
    try:
        # Generate session ID if not provided
        if not request.session_id:
            session_id = memory_manager.create_session(current_user.id)
        else:
            session_id = request.session_id
            # Verify session belongs to user
            session = await chat_session_model.get_session_by_id(session_id, current_user.id)
            if not session:
                # Create new session if it doesn't exist or doesn't belong to user
                session_id = memory_manager.create_session(current_user.id)
            else:
                # Update session activity
                await chat_session_model.update_session_activity(session_id, current_user.id)
        
        logger.info(f"Processing authenticated chat request for user {current_user.id}, session: {session_id}")
        
        # Step 1: STRICT Guardrail check
        guardrail_result = guardrails.check_sustainability_relevance(request.message)
        
        if not guardrail_result.is_sustainability_related:
            # Log the rejection
            background_tasks.add_task(
                log_interaction_authenticated,
                user_id=current_user.id,
                session_id=session_id,
                query=request.message,
                response="",
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
            
            return ConversationResponseWithUser(
                response=guardrails.get_polite_refusal_message(guardrail_result.rejection_reason),
                session_id=session_id,
                user_id=current_user.id,
                is_summary=False,
                can_request_detailed=False,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
        
        # Step 2: Query classification and response length determination
        from core.query_classifier import QueryClassifier
        classifier = QueryClassifier()
        classification = classifier.classify_query(request.message)
        
        # Check for elaboration requests
        is_detailed_request = classification.response_length.value == "detailed"
        if not is_detailed_request and _is_elaboration_request(request.message):
            is_detailed_request = True
        
        # Step 3: Memory retrieval
        memory_context = memory_manager.get_context_for_query(
            session_id=session_id,
            query=request.message,
            user_id=current_user.id
        )
        
        # Step 4: Complex question handling
        if classification.is_complex:
            complex_response = complex_handler.handle_complex_question(
                query=request.message,
                context=memory_context,
                classification=classification
            )
            
            if complex_response:
                # Store the interaction
                user_message = Message(role=MessageRole.USER, content=request.message)
                assistant_message = Message(role=MessageRole.ASSISTANT, content=complex_response)
                
                memory_manager.add_message(session_id, user_message, current_user.id)
                memory_manager.add_message(session_id, assistant_message, current_user.id)
                
                # Log the interaction
                background_tasks.add_task(
                    log_interaction_authenticated,
                    user_id=current_user.id,
                    session_id=session_id,
                    query=request.message,
                    response=complex_response,
                    guardrail_triggered=False
                )
                
                return ConversationResponseWithUser(
                    response=complex_response,
                    session_id=session_id,
                    user_id=current_user.id,
                    is_summary=classification.response_length.value == "short",
                    can_request_detailed=classification.response_length.value == "short",
                    guardrail_triggered=False
                )
        
        # Step 5: LLM generation
        response_guidelines = classifier.get_response_guidelines(classification)
        
        # Generate response using LLM service
        llm_response = await llm_service.generate_response(
            query=request.message,
            context=memory_context,
            is_detailed=is_detailed_request,
            response_guidelines=response_guidelines,
            conversation_history=memory_context.conversation_history
        )
        
        # Step 6: Output validation
        if not guardrails.validate_output(llm_response, request.message):
            # Return generic refusal if output validation fails
            refusal_message = "I apologize, but I can only provide information related to sustainability topics. How can I help you with environmental, climate, or sustainability questions?"
            
            background_tasks.add_task(
                log_interaction_authenticated,
                user_id=current_user.id,
                session_id=session_id,
                query=request.message,
                response=refusal_message,
                guardrail_triggered=True,
                guardrail_reason="Output validation failed"
            )
            
            return ConversationResponseWithUser(
                response=refusal_message,
                session_id=session_id,
                user_id=current_user.id,
                is_summary=False,
                can_request_detailed=False,
                guardrail_triggered=True,
                guardrail_reason="Output validation failed"
            )
        
        # Step 7: Store interaction in memory
        user_message = Message(role=MessageRole.USER, content=request.message)
        assistant_message = Message(role=MessageRole.ASSISTANT, content=llm_response)
        
        memory_manager.add_message(session_id, user_message, current_user.id)
        memory_manager.add_message(session_id, assistant_message, current_user.id)
        
        # Step 8: Log interaction
        background_tasks.add_task(
            log_interaction_authenticated,
            user_id=current_user.id,
            session_id=session_id,
            query=request.message,
            response=llm_response,
            guardrail_triggered=False
        )
        
        return ConversationResponseWithUser(
            response=llm_response,
            session_id=session_id,
            user_id=current_user.id,
            is_summary=classification.response_length.value == "short",
            can_request_detailed=classification.response_length.value == "short",
            guardrail_triggered=False
        )
        
    except Exception as e:
        logger.error(f"Error in authenticated chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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


def _is_elaboration_request(query: str, conversation_history: List[str]) -> bool:
    """Check if the query is asking for elaboration on a previous topic."""
    query_lower = query.lower().strip()
    
    # Direct elaboration requests
    elaboration_patterns = [
        r'\b(?:explain|elaborate|detail|comprehensive|thorough|in-depth|extensive)\b.*\b(?:detail|depth|more)\b',
        r'\bexplain\s+(?:me\s+)?(?:that\s+)?in\s+detail\b',
        r'\bcan\s+you\s+elaborate\b',
        r'\btell\s+me\s+more\s+about\b',
        r'\bprovide\s+(?:a\s+)?(?:detailed|comprehensive|thorough)\b',
        r'\bgive\s+me\s+(?:a\s+)?(?:detailed|comprehensive|full)\b',
        r'\bbreak\s+down\b',
        r'\bcomprehensive\s+(?:analysis|explanation|overview)\b',
        r'\byes\s+explain\s+(?:that\s+)?(?:in\s+)?detail',
        r'\belaborate\s+(?:on\s+)?(?:that|it)\b',
        r'\bmore\s+detailed?\s+(?:information|explanation)\b',
        r'\bgo\s+into\s+(?:more\s+)?detail\b'
    ]
    
    for pattern in elaboration_patterns:
        if re.search(pattern, query_lower):
            return True
    
    # Simple affirmative responses that might be follow-ups
    simple_affirmatives = ['yes', 'yeah', 'sure', 'ok', 'okay', 'yep']
    words = query_lower.strip().split()
    if len(words) <= 2 and words[0].lower() in simple_affirmatives and conversation_history:
        return True
    
    return False


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


async def log_interaction_authenticated(
    user_id: str,
    session_id: str,
    query: str,
    response: str,
    guardrail_triggered: bool,
    guardrail_reason: str = None
):
    """Background task to log authenticated interactions."""
    try:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "query": query,
            "response": response,
            "guardrail_triggered": guardrail_triggered,
            "guardrail_reason": guardrail_reason,
            "query_length": len(query),
            "response_length": len(response)
        }
        
        logger.info(f"Authenticated interaction logged: {log_data}")
        
    except Exception as e:
        logger.error(f"Failed to log authenticated interaction: {e}")


# Error handlers will be added to the main FastAPI app in main.py
