"""
MongoDB Memory Manager - Pure MongoDB-based session and memory storage.

This module replaces the file-based memory system with a clean MongoDB-only approach
that integrates with the existing ChatSessionModel and adds memory management capabilities.
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger

from models.schemas import Message, MessageRole, MemoryContext
from models.user import chat_session_model
from database.mongodb import get_database


class MongoDBSessionManager:
    """
    MongoDB-based session and memory manager.
    
    This class provides all session and memory management functionality
    using MongoDB as the single source of truth.
    """
    
    def __init__(self):
        """Initialize the MongoDB session manager."""
        self.session_model = chat_session_model
        logger.info("MongoDB Session Manager initialized")
    
    async def create_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Create a new session in MongoDB.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID, generates new one if not provided
            
        Returns:
            str: Session ID
        """
        try:
            if session_id:
                # Use existing session ID, just create metadata
                await self._store_session_metadata(session_id, user_id, {
                    "messages": [],
                    "context_summary": "",
                    "memory_references": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Created metadata for existing MongoDB session {session_id} for user {user_id}")
                return session_id
            else:
                # Create new session in MongoDB
                mongo_session = await self.session_model.create_session(
                    user_id=user_id,
                    title="New Chat"
                )
                
                # Store session metadata in MongoDB
                await self._store_session_metadata(mongo_session.id, user_id, {
                    "messages": [],
                    "context_summary": "",
                    "memory_references": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Created new MongoDB session {mongo_session.id} for user {user_id}")
                return mongo_session.id
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB session: {e}")
            raise
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information from MongoDB."""
        try:
            # Get basic session info from ChatSessionModel
            # We need to find the session without knowing the user_id first
            db = await get_database()
            sessions_collection = db.chat_sessions
            
            # Find session by session_id only
            session_doc = await sessions_collection.find_one({"session_id": session_id})
            
            if not session_doc:
                return None
            
            # Convert to ChatSession object
            from models.schemas import ChatSession
            session = ChatSession(
                id=session_doc["session_id"],
                user_id=session_doc["user_id"],
                title=session_doc["title"],
                created_at=session_doc["created_at"],
                last_activity=session_doc["last_activity"],
                message_count=session_doc["message_count"],
                is_active=session_doc["is_active"]
            )
            
            # Get additional metadata from our custom collection
            metadata = await self._get_session_metadata(session_id)
            
            # Combine session data with metadata
            session_info = {
                "session_id": session.id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "message_count": session.message_count,
                "is_active": session.is_active,
                "title": session.title,
                "messages": metadata.get("messages", []),
                "context_summary": metadata.get("context_summary", ""),
                "memory_references": metadata.get("memory_references", [])
            }
            
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get full session data."""
        session_info = await self.get_session_info(session_id)
        if not session_info:
            return {
                "session_id": session_id,
                "message_count": 0,
                "messages": [],
                "is_active": False
            }
        return session_info
    
    async def update_session_activity(self, session_id: str, user_id: str) -> bool:
        """Update session activity timestamp."""
        try:
            # Update in ChatSessionModel
            success = await self.session_model.update_session_activity(session_id, user_id)
            
            # Update metadata timestamp
            await self._update_session_metadata_timestamp(session_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update session activity for {session_id}: {e}")
            return False
    
    async def add_message_to_session(self, session_id: str, role: MessageRole, content: str) -> bool:
        """Add a message to the session."""
        try:
            # Add message to metadata
            message = {
                "role": role.value,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self._add_message_to_metadata(session_id, message)
            
            # Update message count in ChatSessionModel after message is added
            session_info = await self.get_session_info(session_id)
            if session_info:
                message_count = len(session_info.get("messages", []))
                await self.session_model.sync_message_count(session_id, session_info["user_id"], message_count)
                logger.info(f"Updated message count for session {session_id}: {message_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            return False
    
    async def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages from a session."""
        try:
            session_info = await self.get_session_info(session_id)
            if not session_info:
                return []
            
            messages_data = session_info.get("messages", [])
            if limit:
                messages_data = messages_data[-limit:]  # Get last N messages
            
            # Convert to Message objects
            messages = []
            for msg_data in messages_data:
                message = Message(
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"])
                )
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        try:
            sessions = await self.session_model.get_user_sessions(user_id)
            
            # Convert to our format
            session_list = []
            for session in sessions:
                session_info = {
                    "session_id": session.id,
                    "user_id": session.user_id,
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "message_count": session.message_count,
                    "is_active": session.is_active
                }
                session_list.append(session_info)
            
            return session_list
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            # Get session info first to get user_id
            session_info = await self.get_session_info(session_id)
            if not session_info:
                return False
            
            user_id = session_info["user_id"]
            
            # Soft delete in ChatSessionModel
            success = await self.session_model.delete_session(session_id, user_id)
            
            # Remove metadata
            await self._delete_session_metadata(session_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def create_memory(self, session_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new memory entry."""
        try:
            memory_id = str(uuid.uuid4())
            
            # Store memory in MongoDB
            db = await get_database()
            memories_collection = db.chat_memories
            
            memory_doc = {
                "memory_id": memory_id,
                "session_id": session_id,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow()
            }
            
            await memories_collection.insert_one(memory_doc)
            
            # Add reference to session metadata
            await self._add_memory_reference(session_id, memory_id)
            
            logger.info(f"Created memory {memory_id} for session {session_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to create memory for session {session_id}: {e}")
            raise
    
    async def search_memories(self, query: str, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories."""
        try:
            db = await get_database()
            memories_collection = db.chat_memories
            
            # Build search query
            search_query = {}
            if session_id:
                search_query["session_id"] = session_id
            
            # Simple text search (can be enhanced with MongoDB text indexes)
            if query:
                search_query["content"] = {"$regex": query, "$options": "i"}
            
            # Find memories
            cursor = memories_collection.find(search_query).sort("last_accessed", -1).limit(limit)
            memories = []
            
            async for memory_doc in cursor:
                memory = {
                    "memory_id": memory_doc["memory_id"],
                    "session_id": memory_doc["session_id"],
                    "content": memory_doc["content"],
                    "metadata": memory_doc["metadata"],
                    "created_at": memory_doc["created_at"].isoformat(),
                    "last_accessed": memory_doc["last_accessed"].isoformat()
                }
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def build_context(self, session_id: str, max_tokens: int = 8000) -> MemoryContext:
        """Build optimized context for the session."""
        try:
            session_info = await self.get_session_info(session_id)
            if not session_info:
                return MemoryContext(
                    relevant_documents=[],
                    conversation_history=[],
                    context_summary=""
                )
            
            # Get recent messages
            messages = await self.get_session_messages(session_id, limit=20)
            
            # Get relevant memories
            memories = await self.search_memories("", session_id, limit=5)
            
            # Calculate approximate tokens (rough estimation)
            total_tokens = sum(len(msg.content.split()) for msg in messages) * 1.3  # Rough estimation
            
            return MemoryContext(
                relevant_documents=memories,
                conversation_history=messages,
                context_summary=session_info.get("context_summary", "")
            )
            
        except Exception as e:
            logger.error(f"Failed to build context for session {session_id}: {e}")
            return MemoryContext(
                relevant_documents=[],
                conversation_history=[],
                context_summary=""
            )
    
    # Private helper methods for metadata management
    
    async def _store_session_metadata(self, session_id: str, user_id: str, metadata: Dict[str, Any]):
        """Store session metadata in MongoDB."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        metadata_doc = {
            "session_id": session_id,
            "user_id": user_id,
            **metadata
        }
        
        await metadata_collection.replace_one(
            {"session_id": session_id},
            metadata_doc,
            upsert=True
        )
    
    async def _get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get session metadata from MongoDB."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        metadata_doc = await metadata_collection.find_one({"session_id": session_id})
        if metadata_doc:
            # Remove MongoDB-specific fields
            metadata_doc.pop("_id", None)
            metadata_doc.pop("session_id", None)
            metadata_doc.pop("user_id", None)
            return metadata_doc
        
        return {}
    
    async def _update_session_metadata_timestamp(self, session_id: str):
        """Update the last activity timestamp in metadata."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        await metadata_collection.update_one(
            {"session_id": session_id},
            {"$set": {"last_activity": datetime.utcnow().isoformat()}}
        )
    
    async def _add_message_to_metadata(self, session_id: str, message: Dict[str, Any]):
        """Add a message to session metadata."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        await metadata_collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message},
                "$set": {"last_activity": datetime.utcnow().isoformat()}
            }
        )
    
    async def _add_memory_reference(self, session_id: str, memory_id: str):
        """Add a memory reference to session metadata."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        await metadata_collection.update_one(
            {"session_id": session_id},
            {"$push": {"memory_references": memory_id}}
        )
    
    async def _delete_session_metadata(self, session_id: str):
        """Delete session metadata."""
        db = await get_database()
        metadata_collection = db.session_metadata
        
        await metadata_collection.delete_one({"session_id": session_id})
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        try:
            db = await get_database()
            
            # Count sessions
            sessions_count = await db.chat_sessions.count_documents({"is_active": True})
            
            # Count memories
            memories_count = await db.chat_memories.count_documents({})
            
            # Count metadata entries
            metadata_count = await db.session_metadata.count_documents({})
            
            return {
                "total_sessions": sessions_count,
                "total_memories": memories_count,
                "total_metadata_entries": metadata_count,
                "storage_type": "MongoDB"
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                "total_sessions": 0,
                "total_memories": 0,
                "total_metadata_entries": 0,
                "storage_type": "MongoDB",
                "error": str(e)
            }


# Global instance
mongodb_session_manager = MongoDBSessionManager()
