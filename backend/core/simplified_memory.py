"""
Simplified Memory Manager - Compatibility Layer

This module provides a compatibility layer for the existing simplified_memory_manager
interface while using the new Claude Memory System underneath.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from .claude_memory import claude_memory_manager
from models.schemas import Message, MessageRole


class SimplifiedMemoryManager:
    """
    Simplified Memory Manager - Compatibility layer for existing code.
    
    This class provides the same interface as the old simplified_memory_manager
    while using the new Claude Memory System implementation.
    """
    
    def __init__(self):
        """Initialize the simplified memory manager."""
        self.claude_memory = claude_memory_manager
        logger.info("Simplified Memory Manager initialized with Claude Memory System")
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Create a new session.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID
            
        Returns:
            str: Session ID
        """
        return self.claude_memory.create_session(user_id, session_id)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self.claude_memory.get_session_info(session_id)
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get full session data."""
        return self.claude_memory.get_session(session_id)
    
    def update_session_activity(self, session_id: str, user_id: str) -> bool:
        """Update session activity."""
        return self.claude_memory.update_session_activity(session_id, user_id)
    
    def add_message_to_session(self, session_id: str, role: MessageRole, content: str) -> bool:
        """Add a message to the session."""
        return self.claude_memory.add_message_to_session(session_id, role, content)
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages from a session."""
        return self.claude_memory.get_session_messages(session_id, limit)
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        return self.claude_memory.get_user_sessions(user_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.claude_memory.delete_session(session_id)
    
    async def restore_user_sessions_from_database(self, user_id: str) -> bool:
        """Restore user sessions from database."""
        return await self.claude_memory.restore_user_sessions_from_database(user_id)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return self.claude_memory.get_memory_stats()
    
    def create_memory(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new memory entry."""
        return self.claude_memory.create_memory(session_id, content, metadata)
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory."""
        return self.claude_memory.get_memory(memory_id)
    
    def search_memories(self, query: str, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories."""
        return self.claude_memory.search_memories(query, session_id, limit)
    
    def build_context(self, session_id: str, max_tokens: int = 8000) -> Any:
        """Build optimized context."""
        return self.claude_memory.build_context(session_id, max_tokens)
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old sessions."""
        return self.claude_memory.cleanup_old_sessions(days_old)


# Global instance for backward compatibility
simplified_memory_manager = SimplifiedMemoryManager()





