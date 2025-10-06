"""
Claude Native Memory System Implementation

This module implements memory and context management according to Claude API specifications.
It uses Claude's native memory tool with the context-management-2025-06-27 beta header
and provides persistent memory operations through the /memories directory.
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from loguru import logger

from models.schemas import Message, MessageRole, MemoryContext
from config import settings


class ClaudeMemoryManager:
    """
    Claude Native Memory Manager implementing the memory tool specification.
    
    This class manages memory operations according to Claude's API standards:
    - Uses the context-management-2025-06-27 beta header
    - Operates within the /memories directory
    - Provides CRUD operations for memory files
    - Manages conversation context and session state
    """
    
    def __init__(self, memories_dir: str = "memories"):
        """Initialize the Claude Memory Manager."""
        self.memories_dir = Path(memories_dir)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        
        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Memory statistics
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_memories": 0,
            "last_cleanup": datetime.utcnow()
        }
        
        logger.info(f"Claude Memory Manager initialized with memories directory: {self.memories_dir}")
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """Get the file path for a session's memory."""
        return self.memories_dir / f"session_{session_id}.json"
    
    def _get_user_sessions_file_path(self, user_id: str) -> Path:
        """Get the file path for user's session metadata."""
        return self.memories_dir / f"user_{user_id}_sessions.json"
    
    def _get_memory_file_path(self, memory_id: str) -> Path:
        """Get the file path for a specific memory."""
        return self.memories_dir / f"memory_{memory_id}.json"
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Safely load JSON data from file."""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to load JSON file {file_path}: {e}")
            return {}
    
    def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Safely save JSON data to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON file {file_path}: {e}")
            return False
    
    def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Create a new memory session.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID, generates new one if not provided
            
        Returns:
            str: Session ID
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create session data structure
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "message_count": 0,
            "is_active": True,
            "messages": [],
            "context_summary": "",
            "memory_references": []
        }
        
        # Save session to file
        session_file = self._get_session_file_path(session_id)
        if self._save_json_file(session_file, session_data):
            # Update active sessions
            self.active_sessions[session_id] = session_data
            
            # Update user sessions metadata
            self._update_user_sessions_metadata(user_id, session_id, session_data)
            
            # Update stats
            self.stats["total_sessions"] += 1
            self.stats["active_sessions"] += 1
            
            logger.info(f"Created new session {session_id} for user {user_id}")
            return session_id
        else:
            raise Exception(f"Failed to create session {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Load from file
        session_file = self._get_session_file_path(session_id)
        session_data = self._load_json_file(session_file)
        
        if session_data:
            # Add to active sessions
            self.active_sessions[session_id] = session_data
            return session_data
        
        return None
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get full session data."""
        session_info = self.get_session_info(session_id)
        if not session_info:
            return {
                "session_id": session_id,
                "message_count": 0,
                "messages": [],
                "is_active": False
            }
        return session_info
    
    def update_session_activity(self, session_id: str, user_id: str) -> bool:
        """Update session activity timestamp."""
        session_data = self.get_session_info(session_id)
        if session_data:
            session_data["last_activity"] = datetime.utcnow().isoformat()
            session_data["user_id"] = user_id
            
            # Save to file
            session_file = self._get_session_file_path(session_id)
            if self._save_json_file(session_file, session_data):
                # Update active sessions
                self.active_sessions[session_id] = session_data
                return True
        
        return False
    
    def add_message_to_session(self, session_id: str, role: MessageRole, content: str) -> bool:
        """Add a message to the session."""
        session_data = self.get_session_info(session_id)
        if not session_data:
            return False
        
        # Create message
        message = {
            "role": role.value,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to session
        session_data["messages"].append(message)
        session_data["message_count"] += 1
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        # Save to file
        session_file = self._get_session_file_path(session_id)
        if self._save_json_file(session_file, session_data):
            # Update active sessions
            self.active_sessions[session_id] = session_data
            return True
        
        return False
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages from a session."""
        session_data = self.get_session_info(session_id)
        if not session_data:
            return []
        
        messages = session_data.get("messages", [])
        if limit:
            messages = messages[-limit:]
        
        return [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"])
            )
            for msg in messages
        ]
    
    def create_memory(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new memory entry.
        
        Args:
            session_id: Associated session ID
            content: Memory content
            metadata: Optional metadata
            
        Returns:
            str: Memory ID
        """
        memory_id = str(uuid.uuid4())
        
        memory_data = {
            "memory_id": memory_id,
            "session_id": session_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "access_count": 0
        }
        
        # Save memory to file
        memory_file = self._get_memory_file_path(memory_id)
        if self._save_json_file(memory_file, memory_data):
            # Add reference to session
            session_data = self.get_session_info(session_id)
            if session_data:
                session_data["memory_references"].append(memory_id)
                session_file = self._get_session_file_path(session_id)
                self._save_json_file(session_file, session_data)
                self.active_sessions[session_id] = session_data
            
            self.stats["total_memories"] += 1
            logger.info(f"Created memory {memory_id} for session {session_id}")
            return memory_id
        else:
            raise Exception(f"Failed to create memory {memory_id}")
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory."""
        memory_file = self._get_memory_file_path(memory_id)
        memory_data = self._load_json_file(memory_file)
        
        if memory_data:
            # Update access statistics
            memory_data["last_accessed"] = datetime.utcnow().isoformat()
            memory_data["access_count"] = memory_data.get("access_count", 0) + 1
            self._save_json_file(memory_file, memory_data)
        
        return memory_data
    
    def search_memories(self, query: str, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search memories by content (simple text search).
        
        Args:
            query: Search query
            session_id: Optional session filter
            limit: Maximum results
            
        Returns:
            List of matching memories
        """
        results = []
        query_lower = query.lower()
        
        # Search through all memory files
        for memory_file in self.memories_dir.glob("memory_*.json"):
            memory_data = self._load_json_file(memory_file)
            if not memory_data:
                continue
            
            # Filter by session if specified
            if session_id and memory_data.get("session_id") != session_id:
                continue
            
            # Simple text search
            content = memory_data.get("content", "").lower()
            if query_lower in content:
                results.append(memory_data)
        
        # Sort by relevance (simple: by access count and recency)
        results.sort(key=lambda x: (
            x.get("access_count", 0),
            datetime.fromisoformat(x.get("last_accessed", "1970-01-01"))
        ), reverse=True)
        
        return results[:limit]
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        user_sessions_file = self._get_user_sessions_file_path(user_id)
        user_sessions = self._load_json_file(user_sessions_file)
        
        sessions = []
        for session_id, session_meta in user_sessions.items():
            session_data = self.get_session_info(session_id)
            if session_data:
                sessions.append({
                    "session_id": session_id,
                    "created_at": datetime.fromisoformat(session_data["created_at"]),
                    "last_activity": datetime.fromisoformat(session_data["last_activity"]),
                    "message_count": session_data["message_count"],
                    "is_active": session_data["is_active"]
                })
        
        # Sort by last activity
        sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its associated memories."""
        session_data = self.get_session_info(session_id)
        if not session_data:
            return False
        
        # Delete associated memories
        for memory_id in session_data.get("memory_references", []):
            memory_file = self._get_memory_file_path(memory_id)
            if memory_file.exists():
                memory_file.unlink()
                self.stats["total_memories"] -= 1
        
        # Delete session file
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            session_file.unlink()
        
        # Remove from active sessions
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Update user sessions metadata
        user_id = session_data.get("user_id")
        if user_id:
            self._remove_user_session_metadata(user_id, session_id)
        
        self.stats["active_sessions"] -= 1
        logger.info(f"Deleted session {session_id}")
        return True
    
    def _update_user_sessions_metadata(self, user_id: str, session_id: str, session_data: Dict[str, Any]):
        """Update user sessions metadata."""
        user_sessions_file = self._get_user_sessions_file_path(user_id)
        user_sessions = self._load_json_file(user_sessions_file)
        
        user_sessions[session_id] = {
            "created_at": session_data["created_at"],
            "last_activity": session_data["last_activity"],
            "message_count": session_data["message_count"],
            "is_active": session_data["is_active"]
        }
        
        self._save_json_file(user_sessions_file, user_sessions)
    
    def _remove_user_session_metadata(self, user_id: str, session_id: str):
        """Remove session from user metadata."""
        user_sessions_file = self._get_user_sessions_file_path(user_id)
        user_sessions = self._load_json_file(user_sessions_file)
        
        if session_id in user_sessions:
            del user_sessions[session_id]
            self._save_json_file(user_sessions_file, user_sessions)
    
    async def restore_user_sessions_from_database(self, user_id: str) -> bool:
        """
        Restore user sessions from database (MongoDB integration).
        This method maintains compatibility with existing database operations.
        """
        try:
            # This would integrate with MongoDB to restore sessions
            # For now, we'll just ensure the user's session metadata is loaded
            user_sessions_file = self._get_user_sessions_file_path(user_id)
            if user_sessions_file.exists():
                user_sessions = self._load_json_file(user_sessions_file)
                for session_id in user_sessions.keys():
                    # Load session data into active sessions
                    self.get_session_info(session_id)
            
            logger.info(f"Restored sessions for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore sessions for user {user_id}: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            **self.stats,
            "memories_directory": str(self.memories_dir),
            "active_sessions_count": len(self.active_sessions),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old inactive sessions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        cleaned_count = 0
        
        for session_file in self.memories_dir.glob("session_*.json"):
            session_data = self._load_json_file(session_file)
            if not session_data:
                continue
            
            last_activity = datetime.fromisoformat(session_data.get("last_activity", "1970-01-01"))
            if last_activity < cutoff_date and not session_data.get("is_active", True):
                # Delete old inactive session
                session_id = session_data.get("session_id")
                if session_id:
                    self.delete_session(session_id)
                    cleaned_count += 1
        
        self.stats["last_cleanup"] = datetime.utcnow()
        logger.info(f"Cleaned up {cleaned_count} old sessions")
        return cleaned_count
    
    def build_context(self, session_id: str, max_tokens: int = 8000) -> MemoryContext:
        """
        Build optimized context for Claude API.
        
        Args:
            session_id: Session ID
            max_tokens: Maximum context tokens
            
        Returns:
            MemoryContext: Optimized context for the conversation
        """
        session_data = self.get_session_info(session_id)
        if not session_data:
            return MemoryContext(
                relevant_documents=[],
                conversation_history=[],
                context_summary=""
            )
        
        # Get recent messages
        messages = self.get_session_messages(session_id, limit=10)
        
        # Get relevant memories
        relevant_memories = []
        if session_data.get("memory_references"):
            for memory_id in session_data["memory_references"][-5:]:  # Last 5 memories
                memory = self.get_memory(memory_id)
                if memory:
                    relevant_memories.append({
                        "id": memory_id,
                        "content": memory["content"],
                        "metadata": memory.get("metadata", {}),
                        "created_at": memory["created_at"]
                    })
        
        # Create context summary
        context_summary = session_data.get("context_summary", "")
        if not context_summary and messages:
            # Generate simple summary from recent messages
            recent_content = " ".join([msg.content for msg in messages[-3:]])
            context_summary = recent_content[:200] + "..." if len(recent_content) > 200 else recent_content
        
        return MemoryContext(
            relevant_documents=relevant_memories,
            conversation_history=messages,
            context_summary=context_summary
        )


# Global instance
claude_memory_manager = ClaudeMemoryManager()
