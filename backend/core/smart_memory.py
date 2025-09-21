"""Smart memory system with token-aware context management."""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from loguru import logger

from .token_manager import ContextWindowManager, TokenCounter, ContextWindowConfig


@dataclass
class SessionMemory:
    """Basic session memory for storing conversation history."""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    history: List[Tuple[str, str]] = field(default_factory=list)  # (role, content)
    message_count: int = 0
    
    def add(self, role: str, content: str):
        """Add a message to the session history."""
        self.history.append((role, content))
        self.message_count += 1
        self.last_activity = datetime.utcnow()
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history in API format."""
        return [
            {
                "role": role,
                "content": content,
                "timestamp": self.last_activity.isoformat()
            }
            for role, content in self.history
        ]
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session metadata."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count,
            "is_active": True
        }


@dataclass
class SmartSessionMemory(SessionMemory):
    """Enhanced session memory with token tracking."""
    token_usage_history: List[Dict[str, Any]] = field(default_factory=list)
    last_token_count: int = 0
    summarization_triggered: bool = False
    summary: str = ""
    turns_since_summary: int = 0
    
    def add_token_usage(self, usage_info: Dict[str, Any]):
        """Track token usage for this session."""
        self.token_usage_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "usage_info": usage_info
        })
        self.last_token_count = usage_info.get("total_used", 0)
        
        # Keep only recent usage history (last 10 entries)
        if len(self.token_usage_history) > 10:
            self.token_usage_history = self.token_usage_history[-10:]
    
    def recent_messages(self, limit: int = 4) -> List[Tuple[str, str]]:
        """Get recent messages from the session history."""
        return self.history[-limit:] if self.history else []
    
    def recent_plain(self, k: int = 10) -> str:
        """Get recent messages as plain text for summarization."""
        if not self.history:
            return ""
        
        recent = self.history[-k:] if len(self.history) > k else self.history
        formatted_messages = []
        
        for role, content in recent:
            formatted_messages.append(f"{role.title()}: {content}")
        
        return "\n".join(formatted_messages)
    
    def trim(self, max_pairs: int = 8):
        """Trim conversation history to keep only recent message pairs."""
        if not self.history:
            return
        
        # Keep only the last max_pairs * 2 messages (pairs of user/assistant)
        max_messages = max_pairs * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
            self.message_count = len(self.history)


class MemoryManager:
    """Base memory manager for session management."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionMemory] = {}
        self._answer_llm = None
        self._summ_llm = None
        logger.info("Memory manager initialized")
    
    def set_llm_service(self, llm_service):
        """Set the LLM service for normal responses."""
        self._answer_llm = llm_service
    
    def set_summarization_llm(self, summ_llm):
        """Set a separate LLM service for summarization."""
        self._summ_llm = summ_llm
    
    def create_session(self, user_id: str = "default", session_id: str = None) -> str:
        """Create a new conversation session."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = SessionMemory(
            session_id=session_id,
            user_id=user_id
        )
        logger.info(f"Created new session for user {user_id}: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionMemory]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, user_id: str = "default") -> bool:
        """Add a message to a session."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found, creating new one")
            session = SessionMemory(session_id=session_id, user_id=user_id)
            self.sessions[session_id] = session
        
        session.add(role, content)
        return True
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return []
        
        return session.get_conversation_history()
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get_session_info()
    
    def get_user_sessions(self, user_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        user_sessions = []
        for session in self.sessions.values():
            if session.user_id == user_id:
                session_info = session.get_session_info()
                session_info["session_id"] = session.session_id
                
                # Add a preview of the conversation
                if session.history:
                    first_user_msg = next((content for role, content in session.history if role == "user"), "")
                    session_info["preview"] = first_user_msg[:100] + "..." if len(first_user_msg) > 100 else first_user_msg
                else:
                    session_info["preview"] = "New session"
                
                user_sessions.append(session_info)
        
        # Sort by last activity (most recent first)
        user_sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return user_sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False
    
    async def restore_session_from_database(self, session_id: str, user_id: str) -> bool:
        """Restore a session from the database into memory."""
        try:
            # Skip restoration for anonymous users (user_id = "default")
            if user_id == "default":
                logger.debug(f"Skipping restoration for anonymous session {session_id}")
                return False
            
            # Import here to avoid circular imports
            from core.hybrid_memory import get_hybrid_memory_manager
            
            # Get hybrid memory manager
            hybrid_memory = get_hybrid_memory_manager()
            
            # Get messages from database
            messages = await hybrid_memory.get_session_messages(session_id, user_id)
            
            if not messages:
                logger.debug(f"No messages found for session {session_id} in database")
                return False
            
            # Create session in memory
            session = SmartSessionMemory(session_id=session_id, user_id=user_id)
            
            # Restore messages to session
            for msg in messages:
                session.add(msg["role"], msg["content"])
            
            # Store in memory
            self.sessions[session_id] = session
            
            logger.info(f"Restored session {session_id} with {len(messages)} messages from database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore session {session_id} from database: {e}")
            return False
    
    async def restore_user_sessions_from_database(self, user_id: str) -> int:
        """Restore all active sessions for a user from the database."""
        try:
            # Skip restoration for anonymous users (user_id = "default")
            if user_id == "default":
                logger.debug(f"Skipping session restoration for anonymous user")
                return 0
            
            # Import here to avoid circular imports
            from models.user import chat_session_model
            
            # Get user's sessions from MongoDB
            mongo_sessions = await chat_session_model.get_user_sessions(user_id, limit=50)
            
            restored_count = 0
            for mongo_session in mongo_sessions:
                session_id = mongo_session.id
                
                # Skip if session already exists in memory
                if session_id in self.sessions:
                    continue
                
                # Restore session from database
                success = await self.restore_session_from_database(session_id, user_id)
                if success:
                    restored_count += 1
            
            logger.info(f"Restored {restored_count} sessions for user {user_id} from database")
            return restored_count
            
        except Exception as e:
            logger.error(f"Failed to restore sessions for user {user_id} from database: {e}")
            return 0
    
    def cleanup_old_sessions(self, hours: int = 24) -> None:
        """Clean up old sessions."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        sessions_to_delete = []
        
        for session_id, session in self.sessions.items():
            if session.last_activity < cutoff_time:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            del self.sessions[session_id]
            logger.info(f"Cleaned up old session {session_id}")
        
        if sessions_to_delete:
            logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")


class SmartMemoryManager(MemoryManager):
    """Smart memory manager with token-aware context management."""
    
    def __init__(self, context_config: Optional[ContextWindowConfig] = None):
        super().__init__()
        self.context_manager = ContextWindowManager(context_config)
        self.token_counter = TokenCounter()
        logger.info("Smart memory manager initialized with token management")
    
    def create_session(self, user_id: str = "default", session_id: str = None) -> str:
        """Create a new smart session."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = SmartSessionMemory(
            session_id=session_id,
            user_id=user_id
        )
        logger.info(f"Created new smart session for user {user_id}: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SmartSessionMemory]:
        """Get a smart session by ID."""
        return self.sessions.get(session_id)
    
    def add_message_with_token_tracking(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        user_id: str = "default",
        expected_output_tokens: int = 0
    ) -> Dict[str, Any]:
        """Add message with token usage tracking and smart context management."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found, creating new one")
            session = SmartSessionMemory(session_id=session_id, user_id=user_id)
            self.sessions[session_id] = session
        
        # Add the message
        session.add(role, content)
        
        # Calculate token usage
        messages = self._session_to_messages(session)
        usage_info = self.context_manager.calculate_usage(messages, expected_output_tokens)
        session.add_token_usage(usage_info)
        
        # Check if we need smart summarization based on token usage
        should_summarize = self._should_trigger_smart_summarization(session, usage_info)
        
        result = {
            "success": True,
            "session_id": session_id,
            "usage_info": usage_info,
            "should_summarize": should_summarize,
            "messages_count": len(session.history)
        }
        
        if should_summarize and role == "assistant":
            logger.info(f"Triggering smart summarization for session {session_id}")
            self._smart_summarize_session(session)
            result["summarized"] = True
        
        return result
    
    def _should_trigger_smart_summarization(self, session: SmartSessionMemory, usage_info: Dict[str, Any]) -> bool:
        """Determine if smart summarization should be triggered based on token usage."""
        # Trigger if approaching context limits
        if usage_info["is_critical"] or usage_info["is_overflow"]:
            return True
        
        # Trigger if we've had several high-usage interactions
        recent_high_usage = sum(
            1 for entry in session.token_usage_history[-5:] 
            if entry["usage_info"].get("is_warning", False)
        )
        
        if recent_high_usage >= 3:
            return True
        
        # Trigger based on traditional turn count if token usage is moderate
        if session.turns_since_summary >= 3 and not usage_info["is_warning"]:
            return True
        
        return False
    
    def _smart_summarize_session(self, session: SmartSessionMemory):
        """Enhanced summarization with token awareness."""
        if not self._summ_llm or not session.history:
            return
        
        try:
            # Get more context for summarization if we have token room
            recent_block = session.recent_plain(k=15)  # Increased from 10
            
            # Enhanced summarization prompt with token awareness
            summarization_prompt = f"""You are a concise session summarizer for a sustainability expert assistant. Your job is to MAINTAIN and UPDATE a running summary of the conversation so far.

Instructions:
- Keep the important context that is already in the Current summary.
- Add any new facts, topics, or sustainability insights from the Recent dialogue.
- Remove or update items only if they are clearly corrected or contradicted.
- Keep the summary short and factual (≤ 6 bullet points or short lines).
- Focus on sustainability topics, environmental concerns, and actionable insights.

Current summary:
{session.summary}

Recent dialogue (oldest to newest):
{recent_block}

Return ONLY the updated summary."""

            # Use the summarization LLM service
            new_summary = self._summ_llm.generate_response(
                [{"role": "user", "content": summarization_prompt}],
                is_detailed=False
            )
            
            # Update session with new summary
            if new_summary and new_summary.strip():
                session.summary = new_summary.strip()
                
                # Smart trimming based on token usage
                self._smart_trim_session(session)
                session.turns_since_summary = 0
                session.summarization_triggered = True
                
                logger.info(f"Smart summarized session {session.session_id}")
                logger.debug(f"New summary: {session.summary}")
            else:
                logger.warning(f"Empty summary generated for session {session.session_id}")
                session.turns_since_summary = 0
            
        except Exception as e:
            logger.error(f"Error in smart summarization for session {session.session_id}: {e}")
            session.turns_since_summary = 0
    
    def _smart_trim_session(self, session: SmartSessionMemory):
        """Smart trimming based on token usage and conversation importance."""
        if not session.history:
            return
        
        # Calculate current token usage
        messages = self._session_to_messages(session)
        usage_info = self.context_manager.calculate_usage(messages)
        
        # If we're in critical territory, be more aggressive with trimming
        if usage_info["is_critical"]:
            # Keep only last 3 exchanges (6 messages)
            session.trim(max_pairs=3)
        elif usage_info["is_warning"]:
            # Keep last 5 exchanges (10 messages)
            session.trim(max_pairs=5)
        else:
            # Standard trimming
            session.trim(max_pairs=8)
    
    def get_optimized_context(
        self, 
        session_id: str, 
        query: str, 
        user_id: str = "default",
        max_output_tokens: int = 0
    ) -> Dict[str, Any]:
        """Get context optimized for token usage with semantic search for relevant old messages."""
        session = self.get_session(session_id)
        if not session:
            return {
                "conversation_history": [],
                "summary": "",
                "context_summary": "No session context available",
                "usage_info": {},
                "optimized": False,
                "relevant_documents": []
            }
        
        # Get conversation messages
        messages = self._session_to_messages(session)
        
        # Calculate usage and determine if truncation is needed
        usage_info = self.context_manager.calculate_usage(messages, max_output_tokens)
        
        # If we need to truncate, do it
        if self.context_manager.should_truncate(messages, max_output_tokens):
            truncated_messages, truncation_info = self.context_manager.truncate_conversation(
                messages, max_output_tokens
            )
            
            # Update session with truncated history
            self._update_session_from_messages(session, truncated_messages)
            
            logger.info(f"Truncated context for session {session_id}: {truncation_info}")
        else:
            truncated_messages = messages
            truncation_info = {"truncated": False}
        
        # Get recent messages for context
        recent_messages = session.recent_messages()
        
        # NEW: Search for relevant old messages using semantic search
        relevant_documents = []
        try:
            # Import here to avoid circular imports
            from core.hybrid_memory import get_hybrid_memory_manager
            
            # Get hybrid memory manager
            hybrid_memory = get_hybrid_memory_manager()
            
            # Check if we have a real hybrid memory manager (not mock)
            if hasattr(hybrid_memory, 'search_similar_messages'):
                # Use thread pool to run async code in sync context
                try:
                    import concurrent.futures
                    import asyncio
                    
                    def run_async_search():
                        try:
                            # Create new event loop in thread
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(
                                    hybrid_memory.search_similar_messages(
                                        query=query,
                                        user_id=user_id,
                                        session_id=session_id,
                                        limit=5  # Limit to top 5 most relevant
                                    )
                                )
                            finally:
                                loop.close()
                        except Exception as e:
                            logger.warning(f"Async search failed: {e}")
                            return []
                    
                    # Run in thread pool to avoid event loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_search)
                        similar_messages = future.result(timeout=10)  # Increased to 10 second timeout
                    
                    logger.debug(f"Retrieved {len(similar_messages)} similar messages from hybrid memory")
                    
                    # Convert to relevant documents format
                    for i, msg in enumerate(similar_messages):
                        try:
                            # Only include messages that are NOT in recent history
                            msg_content = msg.get('content', '')
                            msg_role = msg.get('role', '')
                            msg_timestamp = msg.get('timestamp', '')
                            
                            logger.debug(f"Processing message {i+1}: role={msg_role}, content_length={len(msg_content)}")
                            
                            # Check if this message is already in recent history
                            is_recent = False
                            try:
                                is_recent = any(
                                    content == msg_content and role == msg_role 
                                    for role, content in recent_messages
                                )
                            except Exception as comparison_error:
                                logger.warning(f"Error comparing messages: {comparison_error}")
                                is_recent = False
                            
                            if not is_recent and msg_content:
                                relevant_documents.append({
                                    "content": msg_content,
                                    "metadata": {
                                        "role": msg_role,
                                        "timestamp": msg_timestamp,
                                        "session_id": session_id,
                                        "topic": "previous_conversation"
                                    }
                                })
                                logger.debug(f"Added message {i+1} to relevant documents")
                        except Exception as msg_error:
                            logger.warning(f"Error processing message {i+1}: {msg_error}")
                            continue
                    
                    logger.info(f"Found {len(relevant_documents)} relevant old messages for query: {query[:50]}...")
                    
                except concurrent.futures.TimeoutError:
                    logger.warning("Semantic search timed out after 10 seconds")
                    relevant_documents = []
                except Exception as e:
                    logger.warning(f"Semantic search failed: {type(e).__name__}: {e}")
                    relevant_documents = []
            else:
                logger.debug("Hybrid memory not available, skipping semantic search")
                
        except Exception as e:
            logger.warning(f"Failed to perform semantic search: {type(e).__name__}: {e}")
            relevant_documents = []
        
        # Create context summary
        context_parts = []
        if session.summary:
            context_parts.append(f"Session summary: {session.summary}")
        if recent_messages:
            recent_topics = [content[:50] + "..." if len(content) > 50 else content 
                           for role, content in recent_messages if role == "user"]
            if recent_topics:
                context_parts.append(f"Recent topics: {', '.join(recent_topics)}")
        if relevant_documents:
            context_parts.append(f"Found {len(relevant_documents)} relevant previous messages")
        
        context_summary = "; ".join(context_parts) if context_parts else "No specific context available"
        
        return {
            "conversation_history": truncated_messages,
            "summary": session.summary,
            "context_summary": context_summary,
            "recent_messages": recent_messages,
            "usage_info": usage_info,
            "truncation_info": truncation_info,
            "relevant_documents": relevant_documents,
            "optimized": True
        }
    
    def _session_to_messages(self, session: SmartSessionMemory) -> List[Dict[str, str]]:
        """Convert session history to message format."""
        messages = []
        for role, content in session.history:
            messages.append({
                "role": role,
                "content": content
            })
        return messages
    
    def _update_session_from_messages(self, session: SmartSessionMemory, messages: List[Dict[str, str]]):
        """Update session history from message format."""
        session.history = []
        for msg in messages:
            session.history.append((msg["role"], msg["content"]))
    


# Global smart memory manager instance
smart_memory_manager = SmartMemoryManager()
