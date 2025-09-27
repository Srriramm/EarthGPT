"""FastAPI routes for the Sustainability Assistant."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from loguru import logger

from models.schemas import (
    ConversationRequest, ConversationResponse, SessionInfo, 
    HealthResponse, ErrorResponse, Message, MessageRole,
    ConversationRequestWithUser, ConversationResponseWithUser
)
from guardrails import TwoLevelGuardrails
from core.smart_memory import smart_memory_manager
from core.hybrid_memory import get_hybrid_memory_manager
from core.prompt_engineering import PromptManager
from core.title_generator import TitleGenerator
from services.llm_service import llm_service
from core.summarization_llm import summarization_llm_service
from auth.dependencies import get_current_active_user, get_optional_current_user
from models.schemas import User
from models.user import chat_session_model
from config import settings

# Initialize components
guardrails = TwoLevelGuardrails()
smart_memory = smart_memory_manager
prompt_manager = PromptManager()
title_generator = TitleGenerator()

# Set LLM services for memory managers
smart_memory.set_llm_service(llm_service)
smart_memory.set_summarization_llm(summarization_llm_service)

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
            # Create MongoDB session first, then use its ID for smart memory
            try:
                mongo_session = await chat_session_model.create_session("default", "New Chat")
                session_id = mongo_session.id  # Use the session_id from MongoDB
                # Create corresponding smart memory session
                smart_memory.create_session("default", session_id)
            except Exception as e:
                logger.error(f"Failed to create MongoDB session for anonymous user: {e}")
                # Fallback to smart memory only
                session_id = smart_memory.create_session("default")
        else:
            session_id = request.session_id
            # Try to use existing session, but be more lenient
            try:
                # First check if session exists in smart memory
                if smart_memory.get_session_info(session_id):
                    logger.info(f"Using existing session {session_id} from smart memory")
                else:
                    # Try to restore from MongoDB
                    mongo_session = await chat_session_model.get_session_by_id(session_id, "default")
                    if mongo_session:
                        # Restore session to smart memory
                        smart_memory.create_session("default", session_id)
                        logger.info(f"Restored session {session_id} from MongoDB to smart memory")
                    else:
                        # Create new session only if absolutely necessary
                        logger.warning(f"Session {session_id} not found, creating new session")
                        mongo_session = await chat_session_model.create_session("default", "New Chat")
                        session_id = mongo_session.id
                        smart_memory.create_session("default", session_id)
            except Exception as e:
                logger.warning(f"Failed to verify session {session_id}: {e}")
                # Only create new session as last resort
                try:
                    mongo_session = await chat_session_model.create_session("default", "New Chat")
                    session_id = mongo_session.id
                    smart_memory.create_session("default", session_id)
                    logger.info(f"Created fallback session {session_id}")
                except Exception as fallback_error:
                    logger.error(f"Failed to create fallback session: {fallback_error}")
                    session_id = smart_memory.create_session("default")
        
        logger.info(f"Processing chat request for session: {session_id}")
        
        # Step 1: Get conversation context for guardrail check
        context = smart_memory.get_optimized_context(session_id, request.message, "default")
        conversation_context = ""
        if context.get('conversation_history'):
            # Extract recent conversation for context
            recent_messages = context['conversation_history'][-4:]  # Last 4 messages
            conversation_context = " ".join([msg.get('content', '') for msg in recent_messages])
        
        # Step 2: STRICT Guardrail check with context
        guardrail_result = guardrails.check_sustainability_relevance(request.message, conversation_context)
        
        if not guardrail_result.is_sustainability_related:
            # Get the refusal message
            refusal_message = guardrails.get_polite_refusal_message(guardrail_result.rejection_reason)
            
            # Store the out-of-domain interaction in memory
            try:
                hybrid_memory = get_hybrid_memory_manager()
                user_msg_id = await hybrid_memory.store_message("default", session_id, "user", request.message)
                assistant_msg_id = await hybrid_memory.store_message("default", session_id, "assistant", refusal_message)
                logger.info(f"Stored out-of-domain messages in hybrid memory - User: {user_msg_id}, Assistant: {assistant_msg_id}")
            except Exception as e:
                logger.error(f"Failed to store out-of-domain messages in hybrid memory: {e}")
            
            # Update MongoDB session activity
            try:
                await chat_session_model.update_session_activity(session_id, "default")
                # Sync message count from smart memory to MongoDB
                session = smart_memory.get_session(session_id)
                if session:
                    await chat_session_model.sync_message_count(session_id, "default", session.message_count)
            except Exception as e:
                logger.warning(f"Failed to update MongoDB session activity for out-of-domain: {e}")
            
            # Log the rejection
            background_tasks.add_task(
                log_interaction,
                session_id=session_id,
                query=request.message,
                response=refusal_message,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
            
            return ConversationResponse(
                response=refusal_message,
                session_id=session_id,
                is_summary=False,
                can_request_detailed=False,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
        
        
        # Step 3: Get optimized context from smart memory system (already retrieved above)
        
        # Step 4: Generate response using LLM (let LLM decide response length naturally)
        messages = prompt_manager.create_conversation_prompt(
            request.message, 
            context, 
            is_detailed=request.request_detailed,  # Only use explicit user request
            is_summary=False
        )
        
        # Generate response from LLM with token management
        llm_result = llm_service.generate_response(messages, is_detailed=request.request_detailed)
        
        # Handle token management results
        if llm_result.get("error"):
            logger.warning(f"LLM error: {llm_result['error']}")
            if llm_result["error"] == "context_window_exceeded":
                # Try to get a more focused response
                context = smart_memory.get_optimized_context(session_id, request.message, "default", max_output_tokens=1000)
                messages = prompt_manager.create_conversation_prompt(
                    request.message, 
                    context, 
                    is_detailed=False,  # Force shorter response
                    is_summary=False
                )
                llm_result = llm_service.generate_response(messages, is_detailed=False)
        
        response_text = llm_result.get("response", "I'm sorry, I couldn't generate a response.")
        
        # Step 6: Validate output with guardrails
        is_valid, rejection_reason = guardrails.validate_output(response_text)
        
        if not is_valid:
            logger.warning(f"Output validation failed: {rejection_reason}")
            response_text = "I apologize, but I need to provide a more focused response on sustainability topics. Could you please rephrase your question with more specific sustainability context?"
        
        # Step 7: Check if this is the first user message for title generation
        should_generate_title = False
        try:
            session_info = smart_memory.get_session_info(session_id)
            logger.info(f"Session info for title generation: {session_info}")
            if session_info and session_info.get("message_count", 0) == 0:
                should_generate_title = True
                logger.info(f"Will generate title for session {session_id} - first message")
            else:
                logger.info(f"Will NOT generate title for session {session_id} - message_count: {session_info.get('message_count', 'unknown') if session_info else 'no session info'}")
        except Exception as e:
            logger.warning(f"Failed to check session info for title generation: {e}")
        
        # Step 7.1: Add messages to conversation history with token tracking
        smart_memory.add_message_with_token_tracking(session_id, "user", request.message, "default")
        smart_memory.add_message_with_token_tracking(session_id, "assistant", response_text, "default")
        
        # Step 7.2: Auto-generate title if this was the first user message
        if should_generate_title:
            try:
                new_title = title_generator.generate_title(request.message)
                logger.info(f"Generated title: '{new_title}' for message: '{request.message[:50]}...'")
                if new_title and new_title != "New Chat":
                    await chat_session_model.update_session_title(session_id, "default", new_title)
                    logger.info(f"Auto-generated title for session {session_id}: {new_title}")
                else:
                    logger.info(f"Title generation returned '{new_title}' - not updating")
            except Exception as e:
                logger.warning(f"Failed to auto-generate title: {e}")
        
        # Step 8: Store messages in hybrid memory system (MongoDB + Pinecone)
        try:
            hybrid_memory = get_hybrid_memory_manager()
            logger.info(f"Hybrid memory manager type: {type(hybrid_memory)}")
            user_msg_id = await hybrid_memory.store_message("default", session_id, "user", request.message)
            assistant_msg_id = await hybrid_memory.store_message("default", session_id, "assistant", response_text)
            logger.info(f"Stored messages in hybrid memory - User: {user_msg_id}, Assistant: {assistant_msg_id}")
        except Exception as e:
            logger.error(f"Failed to store messages in hybrid memory: {e}")
            logger.error(f"Hybrid memory error details: {type(e).__name__}: {str(e)}")
            # Fallback to hybrid memory only
            logger.warning("Hybrid memory storage failed, messages stored in smart memory only")
        
        # Step 8.1: Update MongoDB session last_activity and sync message count
        try:
            await chat_session_model.update_session_activity(session_id, "default")
            # Sync message count from smart memory to MongoDB
            session = smart_memory.get_session(session_id)
            if session:
                await chat_session_model.sync_message_count(session_id, "default", session.message_count)
        except Exception as e:
            logger.warning(f"Failed to update MongoDB session activity: {e}")
        
        # Conversation saved in smart memory and hybrid memory
        
        # Step 8: Log the interaction
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
        # Step 0: Restore user sessions from database first to avoid duplicates
        if request.session_id:
            # Only restore if we have a specific session_id to look for
            if not smart_memory.get_session_info(request.session_id):
                logger.info(f"Session {request.session_id} not in memory, attempting to restore from database")
                restored_count = await smart_memory.restore_user_sessions_from_database(current_user.id)
                logger.info(f"Restored {restored_count} sessions for user {current_user.id}")
        
        # Generate session ID if not provided
        if not request.session_id:
            # Create new session only when no session_id is provided
            try:
                mongo_session = await chat_session_model.create_session(current_user.id, "New Chat")
                session_id = mongo_session.id  # Use the session_id from MongoDB
                # Create corresponding smart memory session
                smart_memory.create_session(current_user.id, session_id)
                logger.info(f"Created new authenticated session {session_id} for user {current_user.id}")
            except Exception as e:
                logger.error(f"Failed to create MongoDB session for user {current_user.id}: {e}")
                # Fallback to smart memory only
                session_id = smart_memory.create_session(current_user.id)
        else:
            session_id = request.session_id
            # Try to use existing session, but be more lenient
            try:
                # First check if session exists in smart memory
                if smart_memory.get_session_info(session_id):
                    logger.info(f"Using existing authenticated session {session_id} from smart memory")
                    # Update session activity
                    await chat_session_model.update_session_activity(session_id, current_user.id)
                else:
                    # Try to restore from MongoDB
                    mongo_session = await chat_session_model.get_session_by_id(session_id, current_user.id)
                    if mongo_session:
                        # Restore session to smart memory
                        smart_memory.create_session(current_user.id, session_id)
                        await chat_session_model.update_session_activity(session_id, current_user.id)
                        logger.info(f"Restored authenticated session {session_id} from MongoDB to smart memory")
                    else:
                        # Create new session only if absolutely necessary
                        logger.warning(f"Authenticated session {session_id} not found, creating new session")
                        mongo_session = await chat_session_model.create_session(current_user.id, "New Chat")
                        session_id = mongo_session.id
                        smart_memory.create_session(current_user.id, session_id)
            except Exception as e:
                logger.warning(f"Failed to verify authenticated session {session_id}: {e}")
                # Only create new session as last resort
                try:
                    mongo_session = await chat_session_model.create_session(current_user.id, "New Chat")
                    session_id = mongo_session.id
                    smart_memory.create_session(current_user.id, session_id)
                    logger.info(f"Created fallback authenticated session {session_id}")
                except Exception as fallback_error:
                    logger.error(f"Failed to create fallback authenticated session: {fallback_error}")
                    session_id = smart_memory.create_session(current_user.id)
        
        logger.info(f"Processing authenticated chat request for user {current_user.id}, session: {session_id}")
        
        # Step 0.1: Check if session exists but has wrong user_id (from anonymous usage)
        session_info = smart_memory.get_session_info(session_id)
        if session_info and session_info.get("user_id") == "default":
            logger.info(f"Session {session_id} has default user_id, updating to authenticated user {current_user.id}")
            # Update the session's user_id
            session = smart_memory.get_session(session_id)
            if session:
                session.user_id = current_user.id
                logger.info(f"Updated session {session_id} user_id from 'default' to {current_user.id}")
        
        # Step 1: Get conversation context for guardrail check
        context = smart_memory.get_optimized_context(session_id, request.message, current_user.id)
        conversation_context = ""
        if context.get('conversation_history'):
            # Extract recent conversation for context
            recent_messages = context['conversation_history'][-4:]  # Last 4 messages
            conversation_context = " ".join([msg.get('content', '') for msg in recent_messages])
        
        # Step 2: STRICT Guardrail check with context
        guardrail_result = guardrails.check_sustainability_relevance(request.message, conversation_context)
        
        if not guardrail_result.is_sustainability_related:
            # Get the refusal message
            refusal_message = guardrails.get_polite_refusal_message(guardrail_result.rejection_reason)
            
            # Store the out-of-domain interaction in memory
            try:
                hybrid_memory = get_hybrid_memory_manager()
                user_msg_id = await hybrid_memory.store_message(current_user.id, session_id, "user", request.message)
                assistant_msg_id = await hybrid_memory.store_message(current_user.id, session_id, "assistant", refusal_message)
                logger.info(f"Stored authenticated out-of-domain messages in hybrid memory - User: {user_msg_id}, Assistant: {assistant_msg_id}")
            except Exception as e:
                logger.error(f"Failed to store authenticated out-of-domain messages in hybrid memory: {e}")
            
            # Update MongoDB session activity
            try:
                await chat_session_model.update_session_activity(session_id, current_user.id)
                # Sync message count from smart memory to MongoDB
                session = smart_memory.get_session(session_id)
                if session:
                    await chat_session_model.sync_message_count(session_id, current_user.id, session.message_count)
            except Exception as e:
                logger.warning(f"Failed to update MongoDB session activity for authenticated out-of-domain: {e}")
            
            # Log the rejection
            background_tasks.add_task(
                log_interaction_authenticated,
                user_id=current_user.id,
                session_id=session_id,
                query=request.message,
                response=refusal_message,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason
            )
            
            # Get current message count from session
            current_message_count = 0
            session = smart_memory.get_session(session_id)
            if session:
                current_message_count = session.message_count

            return ConversationResponseWithUser(
                response=refusal_message,
                session_id=session_id,
                user_id=current_user.id,
                is_summary=False,
                can_request_detailed=False,
                guardrail_triggered=True,
                guardrail_reason=guardrail_result.rejection_reason,
                message_count=current_message_count,
                summarization_triggered=False  # No summarization for blocked queries
            )
        
        # Step 3: Memory retrieval (already retrieved above)
        
        # Step 4: Generate response using LLM (let LLM decide response length naturally)
        messages = prompt_manager.create_conversation_prompt(
            request.message, 
            context, 
            is_detailed=request.request_detailed,  # Only use explicit user request
            is_summary=False
        )
        
        # Generate response from LLM with token management
        llm_result = llm_service.generate_response(messages, is_detailed=request.request_detailed)
        
        # Handle token management results
        if llm_result.get("error"):
            logger.warning(f"LLM error: {llm_result['error']}")
            if llm_result["error"] == "context_window_exceeded":
                # Try to get a more focused response
                context = smart_memory.get_optimized_context(session_id, request.message, current_user.id, max_output_tokens=1000)
                messages = prompt_manager.create_conversation_prompt(
                    request.message, 
                    context, 
                    is_detailed=False,  # Force shorter response
                    is_summary=False
                )
                llm_result = llm_service.generate_response(messages, is_detailed=False)
        
        response_text = llm_result.get("response", "I'm sorry, I couldn't generate a response.")
        
        # Step 6: Validate output with guardrails
        is_valid, rejection_reason = guardrails.validate_output(response_text)
        if not is_valid:
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
        
        # Step 7: Check if this is the first user message for title generation
        should_generate_title = False
        try:
            session_info = smart_memory.get_session_info(session_id)
            logger.info(f"Authenticated session info for title generation: {session_info}")
            if session_info and session_info.get("message_count", 0) == 0:
                should_generate_title = True
                logger.info(f"Will generate title for authenticated session {session_id} - first message")
            else:
                logger.info(f"Will NOT generate title for authenticated session {session_id} - message_count: {session_info.get('message_count', 'unknown') if session_info else 'no session info'}")
        except Exception as e:
            logger.warning(f"Failed to check session info for title generation: {e}")
        
        # Step 7.1: Add messages to conversation history with token tracking
        user_memory_result = smart_memory.add_message_with_token_tracking(session_id, "user", request.message, current_user.id)
        assistant_memory_result = smart_memory.add_message_with_token_tracking(session_id, "assistant", response_text, current_user.id)
        
        # Check if summarization was triggered
        summarization_triggered = assistant_memory_result.get("summarization_triggered", False)
        
        # Step 7.2: Auto-generate title if this was the first user message
        if should_generate_title:
            try:
                new_title = title_generator.generate_title(request.message)
                logger.info(f"Generated title for authenticated user: '{new_title}' for message: '{request.message[:50]}...'")
                if new_title and new_title != "New Chat":
                    await chat_session_model.update_session_title(session_id, current_user.id, new_title)
                    logger.info(f"Auto-generated title for authenticated session {session_id}: {new_title}")
                else:
                    logger.info(f"Title generation returned '{new_title}' - not updating")
            except Exception as e:
                logger.warning(f"Failed to auto-generate title: {e}")
        
        # Step 8: Store messages in hybrid memory system (MongoDB + Pinecone)
        try:
            hybrid_memory = get_hybrid_memory_manager()
            logger.info(f"Authenticated hybrid memory manager type: {type(hybrid_memory)}")
            user_msg_id = await hybrid_memory.store_message(current_user.id, session_id, "user", request.message)
            assistant_msg_id = await hybrid_memory.store_message(current_user.id, session_id, "assistant", response_text)
            logger.info(f"Stored authenticated messages in hybrid memory - User: {user_msg_id}, Assistant: {assistant_msg_id}")
        except Exception as e:
            logger.error(f"Failed to store authenticated messages in hybrid memory: {e}")
            logger.error(f"Authenticated hybrid memory error details: {type(e).__name__}: {str(e)}")
            # Fallback to hybrid memory only
            logger.warning("Hybrid memory storage failed, messages stored in smart memory only")
        
        # Step 8.1: Update MongoDB session last_activity and sync message count
        try:
            await chat_session_model.update_session_activity(session_id, current_user.id)
            # Sync message count from smart memory to MongoDB
            session = smart_memory.get_session(session_id)
            if session:
                await chat_session_model.sync_message_count(session_id, current_user.id, session.message_count)
        except Exception as e:
            logger.warning(f"Failed to update MongoDB session activity: {e}")
        
        # Conversation saved in smart memory and hybrid memory
        
        # Step 8: Log the interaction
        background_tasks.add_task(
            log_interaction_authenticated,
            user_id=current_user.id,
            session_id=session_id,
            query=request.message,
            response=response_text,
            guardrail_triggered=False
        )
        
        # Get current message count from session
        current_message_count = 0
        session = smart_memory.get_session(session_id)
        if session:
            current_message_count = session.message_count

        return ConversationResponseWithUser(
            response=response_text,
            session_id=session_id,
            user_id=current_user.id,
            is_summary=False,  # Let LLM decide response style naturally
            can_request_detailed=False,  # No artificial restrictions
            guardrail_triggered=False,
            message_count=current_message_count,
            summarization_triggered=summarization_triggered
        )
        
    except Exception as e:
        logger.error(f"Error in authenticated chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get information about a specific session."""
    session_info = smart_memory.get_session_info(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(
        session_id=session_id,
        created_at=session_info["created_at"],
        last_activity=session_info["last_activity"],
        message_count=session_info["message_count"],
        is_active=session_info.get("is_active", True)
    )


@router.get("/sessions/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session (anonymous users)."""
    # First check if session exists in memory manager
    session_info = smart_memory.get_session_info(session_id)
    if not session_info:
        # For anonymous sessions, this is normal behavior - just return empty
        # No need to attempt restoration since anonymous sessions are temporary
        logger.debug(f"Anonymous session {session_id} not found in memory - this is normal")
        return {"session_id": session_id, "messages": []}
    
    # Get conversation history from smart memory
    history = smart_memory.get_conversation_history(session_id)
    
    return {"session_id": session_id, "messages": history}


@router.get("/sessions")
async def get_user_sessions(user_id: str = "default"):
    """Get all sessions for a user."""
    try:
        # Get sessions from MongoDB
        mongo_sessions = await chat_session_model.get_user_sessions(user_id)
        sessions = []
        for session in mongo_sessions:
            sessions.append({
                "session_id": session.id,
                "title": session.title,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "message_count": session.message_count,
                "is_active": session.is_active
            })
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error fetching sessions for user {user_id}: {e}")
        # Fallback to memory manager
        sessions = smart_memory.get_user_sessions(user_id)
        return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    logger.info(f"Attempting to delete session: {session_id}")
    
    try:
        # Delete from MongoDB first
        mongo_success = await chat_session_model.delete_session(session_id, "default")
        
        # Delete from memory manager
        memory_success = smart_memory.delete_session(session_id)
        
        # Session deleted from smart memory and MongoDB
        
        if mongo_success or memory_success:
            logger.info(f"Successfully deleted session: {session_id}")
            return {"message": "Session deleted successfully"}
        else:
            logger.warning(f"Session {session_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@router.post("/sessions")
async def create_session(user_id: str = "default"):
    """Create a new conversation session."""
    try:
        # Create MongoDB session
        mongo_session = await chat_session_model.create_session(user_id, "New Chat")
        session_id = mongo_session.id
        
        # Create corresponding memory manager session
        smart_memory.create_session(user_id, session_id)
        
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as e:
        logger.error(f"Error creating session for user {user_id}: {e}")
        # Fallback to memory manager only
        session_id = smart_memory.create_session(user_id)
        return {"session_id": session_id, "message": "Session created successfully"}


@router.get("/model/info")
async def get_model_info():
    """Get information about the loaded model."""
    return llm_service.get_model_info()


@router.post("/admin/cleanup")
async def cleanup_old_sessions():
    """Clean up old sessions (admin endpoint)."""
    smart_memory.cleanup_old_sessions(hours=24)
    return {"message": "Old sessions cleaned up successfully"}


@router.get("/search/messages")
async def search_similar_messages(
    query: str,
    user_id: str = "default",
    limit: int = 10,
    session_id: Optional[str] = None,
    role_filter: Optional[str] = None
):
    """Search for semantically similar messages in chat history."""
    try:
        try:
            hybrid_memory = get_hybrid_memory_manager()
            similar_messages = await hybrid_memory.search_similar_messages(
                query=query,
                user_id=user_id,
                limit=limit,
                session_id=session_id,
                role_filter=role_filter
            )
        except Exception as e:
            logger.warning(f"Hybrid memory search failed: {e}")
            # Fallback: return empty results
            similar_messages = []
        
        return {
            "query": query,
            "results": similar_messages,
            "total_found": len(similar_messages)
        }
        
    except Exception as e:
        logger.error(f"Error searching similar messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to search messages")


@router.get("/messages/stats")
async def get_user_message_stats(user_id: str = "default"):
    """Get statistics about user's messages."""
    try:
        try:
            hybrid_memory = get_hybrid_memory_manager()
            stats = await hybrid_memory.get_user_message_stats(user_id)
        except Exception as e:
            logger.warning(f"Hybrid memory stats failed: {e}")
            # Fallback to smart memory stats
            user_sessions = smart_memory.get_user_sessions(user_id)
            total_messages = sum(session.get("message_count", 0) for session in user_sessions)
            stats = {
                "total_messages": total_messages,
                "total_sessions": len(user_sessions),
                "user_id": user_id
            }
        return stats
        
    except Exception as e:
        logger.error(f"Error getting message stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get message stats")


@router.get("/messages/session/{session_id}")
async def get_session_messages(
    session_id: str,
    user_id: str = "default",
    limit: int = 100
):
    """Get all messages for a specific session."""
    try:
        try:
            hybrid_memory = get_hybrid_memory_manager()
            messages = await hybrid_memory.get_session_messages(
                session_id=session_id,
                user_id=user_id,
                limit=limit
            )
        except Exception as e:
            logger.warning(f"Hybrid memory session messages failed: {e}")
            # Fallback to smart memory
            session = smart_memory.get_session(session_id)
            if session:
                messages = []
                for role, content in session.history:
                    messages.append({
                        "role": role,
                        "content": content,
                        "timestamp": session.last_activity.isoformat()
                    })
            else:
                messages = []
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session messages")


@router.get("/admin/stats")
async def get_system_stats():
    """Get system statistics (admin endpoint)."""
    return {
        "total_sessions": len(smart_memory.sessions),
        "memory_system_active": True,
        "model_loaded": llm_service.is_loaded,
        "guardrails_enabled": settings.enable_guardrails
    }


@router.get("/admin/sessions")
async def get_all_sessions():
    """Get all sessions (admin endpoint for debugging)."""
    sessions = []
    for session_id, session in smart_memory.sessions.items():
        sessions.append({
            "session_id": session_id,
            "user_id": session.user_id,
            "message_count": session.message_count,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "summary": session.summary[:100] + "..." if len(session.summary) > 100 else session.summary
        })
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
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
