"""Authentication routes for user registration, login, and session management."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import (
    User, UserCreate, UserLogin, Token, ChatSession, ChatSessionCreate, 
    ConversationRequestWithUser, ConversationResponseWithUser
)
from models.user import user_model, chat_session_model
from auth.dependencies import get_current_active_user
from config import settings
from loguru import logger
from core.smart_memory import smart_memory_manager

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Register a new user."""
    try:
        new_user = await user_model.create_user(user)
        logger.info(f"New user registered: {new_user.email}")
        return new_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Login user and return access token."""
    try:
        user = await user_model.authenticate_user(user_credentials.email, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = user_model.create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """Refresh access token for current user."""
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = user_model.create_access_token(
            data={"sub": current_user.id}, expires_delta=access_token_expires
        )
        
        logger.info(f"Token refreshed for user: {current_user.email}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.post("/sessions", response_model=ChatSession, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session."""
    try:
        new_session = await chat_session_model.create_session(
            user_id=current_user.id,
            title=session_data.title
        )
        logger.info(f"New chat session created for user {current_user.id}: {new_session.id}")
        return new_session
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.get("/sessions", response_model=List[ChatSession])
async def get_user_sessions(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
):
    """Get all chat sessions for the current user."""
    try:
        # First restore user sessions from database to memory
        restored_count = await smart_memory_manager.restore_user_sessions_from_database(current_user.id)
        logger.info(f"Restored {restored_count} sessions for user {current_user.id} when fetching session list")
        
        sessions = await chat_session_model.get_user_sessions(
            user_id=current_user.id,
            limit=limit
        )
        return sessions
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat sessions"
        )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session."""
    try:
        # First try to find the session for the authenticated user
        session = await chat_session_model.get_session_by_id(session_id, current_user.id)
        
        # If not found, try to find it for the "default" user (anonymous session)
        if not session:
            logger.info(f"Session {session_id} not found for user {current_user.id}, checking for anonymous session")
            session = await chat_session_model.get_session_by_id(session_id, "default")
            if session:
                logger.info(f"Found anonymous session {session_id}, transferring ownership to user {current_user.id}")
                # Transfer ownership of the session to the authenticated user
                await _transfer_session_ownership(session_id, "default", current_user.id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat session"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session."""
    try:
        # First try to delete the session for the authenticated user
        success = await chat_session_model.delete_session(session_id, current_user.id)
        
        # If not found, try to delete it for the "default" user (anonymous session)
        if not success:
            logger.info(f"Session {session_id} not found for user {current_user.id}, checking for anonymous session")
            success = await chat_session_model.delete_session(session_id, "default")
            if success:
                logger.info(f"Deleted anonymous session {session_id} for user {current_user.id}")
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        logger.info(f"Chat session deleted: {session_id}")
        return {"message": "Chat session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )


@router.get("/sessions/{session_id}/history")
async def get_chat_session_history(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get conversation history for a chat session."""
    try:
        # First try to find the session for the authenticated user
        session = await chat_session_model.get_session_by_id(session_id, current_user.id)
        user_id_for_conversation = current_user.id
        
        # If not found, try to find it for the "default" user (anonymous session)
        if not session:
            logger.info(f"Session {session_id} not found for user {current_user.id}, checking for anonymous session")
            session = await chat_session_model.get_session_by_id(session_id, "default")
            if session:
                logger.info(f"Found anonymous session {session_id}, transferring ownership to user {current_user.id}")
                # Transfer ownership of the session to the authenticated user
                await _transfer_session_ownership(session_id, "default", current_user.id)
                user_id_for_conversation = "default"  # Still load from original location
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found"
                )
        
        # Get conversation from smart memory
        session = smart_memory_manager.get_session(session_id)
        if session:
            messages = []
            for role, content in session.history:
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": session.last_activity.isoformat()
                })
        else:
            # Try to restore session from database
            logger.info(f"Session {session_id} not in memory, attempting to restore from database")
            restored = await smart_memory_manager.restore_session_from_database(session_id, user_id_for_conversation)
            if restored:
                session = smart_memory_manager.get_session(session_id)
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
            else:
                messages = []
        
        if messages:
            # Convert to the expected format
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", "")
                })
            return {"session_id": session_id, "messages": formatted_messages}
        else:
            return {"session_id": session_id, "messages": []}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session history"
        )


async def _transfer_session_ownership(session_id: str, from_user_id: str, to_user_id: str):
    """Transfer ownership of a session from one user to another."""
    try:
        from database.mongodb import get_database
        
        # Update session ownership in chat_sessions collection
        db = await get_database()
        sessions_collection = db["chat_sessions"]
        
        # Update session ownership
        result = await sessions_collection.update_one(
            {"session_id": session_id, "user_id": from_user_id},
            {"$set": {"user_id": to_user_id}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Transferred session {session_id} ownership from {from_user_id} to {to_user_id}")
        
        # Update conversation ownership in conversation_history collection
        history_collection = db["conversation_history"]
        
        # Update conversation ownership
        result = await history_collection.update_one(
            {"session_id": session_id, "user_id": from_user_id},
            {"$set": {"user_id": to_user_id}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Transferred conversation {session_id} ownership from {from_user_id} to {to_user_id}")
            
    except Exception as e:
        logger.error(f"Error transferring session ownership: {e}")
        # Don't raise the exception as this is not critical for the main operation

