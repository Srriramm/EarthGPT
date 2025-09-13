"""Pinecone-based conversation memory and session management."""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from models.schemas import Message, MemoryContext
from config import settings


class PineconeConversationMemory:
    """Manages conversation history and session state using Pinecone."""
    
    def __init__(self):
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create conversation index
        self.index_name = "earthgpt-conversations"
        
        # Check if index exists and create if not
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=384,  # all-MiniLM-L6-v2 embedding dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                ),
                metadata_config={
                    "indexed": ["session_id", "message_type", "timestamp", "user_id"]
                }
            )
        
        self.index = self.pc.Index(self.index_name)
        
        # In-memory session metadata (could be moved to a database)
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.max_history = settings.max_conversation_history
        
        logger.info("Pinecone conversation memory initialized")
    
    def create_session(self, user_id: str = "default") -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        self.session_metadata[session_id] = {
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_count": 0,
            "user_id": user_id
        }
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def add_message(self, session_id: str, message: Message, user_id: str = "default") -> None:
        """Add a message to the conversation history in Pinecone."""
        if session_id not in self.session_metadata:
            logger.warning(f"Session {session_id} not found, creating new one")
            self.session_metadata[session_id] = {
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "message_count": 0,
                "user_id": user_id
            }
        
        # Generate embedding for the message
        message_embedding = self.embedding_model.encode(message.content).tolist()
        
        # Create unique ID for this message using the message timestamp
        try:
            # message.timestamp is a datetime object, so we can use it directly
            message_id = f"{session_id}_{message.role}_{message.timestamp.timestamp()}"
        except (AttributeError, TypeError) as e:
            # Fallback to current timestamp if parsing fails
            logger.warning(f"Failed to use message timestamp '{message.timestamp}': {e}")
            message_id = f"{session_id}_{message.role}_{datetime.utcnow().timestamp()}"
        
        # Prepare metadata (Pinecone only accepts specific types)
        timestamp_str = message.timestamp.isoformat()
        metadata = {
            "session_id": session_id,
            "message_type": message.role,
            "content": message.content,
            "timestamp": timestamp_str,  # Convert datetime to ISO string
            "user_id": user_id
        }
        
        logger.info(f"Storing message: {message.role} at {timestamp_str}")
        
        # Upsert to Pinecone
        self.index.upsert(
            vectors=[(message_id, message_embedding, metadata)]
        )
        
        # Update session metadata
        self.session_metadata[session_id]["last_activity"] = datetime.utcnow()
        self.session_metadata[session_id]["message_count"] += 1
        
        logger.debug(f"Added message to session {session_id} in Pinecone")
    
    def get_conversation_history(self, session_id: str, limit: int = 100) -> List[Message]:
        """Get conversation history for a session from Pinecone."""
        try:
            logger.info(f"Getting conversation history for session: {session_id}")
            
            # Query Pinecone for messages in this session
            results = self.index.query(
                vector=[0] * 384,  # Dummy vector since we're filtering by metadata
                filter={"session_id": {"$eq": session_id}},
                top_k=limit,
                include_metadata=True
            )
            
            logger.info(f"Retrieved {len(results.matches)} messages for session {session_id}")
            
            messages = []
            for match in results.matches:
                metadata = match.metadata
                message = Message(
                    role=metadata["message_type"],
                    content=metadata["content"],
                    timestamp=metadata["timestamp"]  # Already a string from Pinecone
                )
                logger.info(f"Retrieved message: {message.role} at {message.timestamp}")
                messages.append(message)
            
            # Sort by timestamp (convert to datetime for proper sorting)
            def get_timestamp_for_sorting(msg):
                try:
                    # msg.timestamp is a string from Pinecone metadata
                    if isinstance(msg.timestamp, str):
                        if msg.timestamp.endswith('Z'):
                            return datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00'))
                        else:
                            return datetime.fromisoformat(msg.timestamp)
                    else:
                        # If it's already a datetime object, use it directly
                        return msg.timestamp
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Failed to parse timestamp '{msg.timestamp}' for sorting: {e}")
                    return datetime.min  # Use minimum datetime as fallback
            
            messages.sort(key=get_timestamp_for_sorting)
            
            logger.info(f"Sorted messages for session {session_id}: {[f'{msg.role}: {msg.timestamp}' for msg in messages]}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata."""
        return self.session_metadata.get(session_id)
    
    def get_user_sessions(self, user_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        logger.info(f"Getting sessions for user: {user_id}")
        user_sessions = []
        for session_id, metadata in self.session_metadata.items():
            if metadata.get("user_id") == user_id:
                # Get recent messages to create a preview (with error handling)
                preview = ""
                try:
                    recent_messages = self.get_conversation_history(session_id, limit=5)
                    if recent_messages:
                        first_user_message = next(
                            (msg for msg in recent_messages if msg.role == "user"), 
                            None
                        )
                        if first_user_message:
                            preview = first_user_message.content[:100] + "..." if len(first_user_message.content) > 100 else first_user_message.content
                except Exception as e:
                    logger.warning(f"Failed to get preview for session {session_id}: {e}")
                    preview = "Session with messages"
                
                user_sessions.append({
                    "session_id": session_id,
                    "created_at": metadata["created_at"],
                    "last_activity": metadata["last_activity"],
                    "message_count": metadata["message_count"],
                    "preview": preview,
                    "is_active": True
                })
        
        # Sort by last activity
        user_sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return user_sessions[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session and all its messages."""
        try:
            # Delete all messages for this session from Pinecone
            results = self.index.query(
                vector=[0] * 384,
                filter={"session_id": {"$eq": session_id}},
                top_k=10000,  # Large number to get all messages
                include_metadata=True
            )
            
            message_ids = [match.id for match in results.matches]
            if message_ids:
                self.index.delete(ids=message_ids)
            
            # Remove session metadata
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            
            logger.info(f"Deleted session {session_id} and {len(message_ids)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, hours: int = 24) -> None:
        """Clean up sessions older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        sessions_to_remove = []
        
        for session_id, metadata in self.session_metadata.items():
            if metadata["last_activity"] < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.delete_session(session_id)
            logger.info(f"Cleaned up old session: {session_id}")
    
    def search_conversations(self, query: str, user_id: str = "default", limit: int = 10) -> List[Dict[str, Any]]:
        """Search through conversation history using semantic search."""
        try:
            # Generate embedding for the search query
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embedding,
                filter={"user_id": {"$eq": user_id}},
                top_k=limit,
                include_metadata=True
            )
            
            search_results = []
            for match in results.matches:
                metadata = match.metadata
                search_results.append({
                    "session_id": metadata["session_id"],
                    "content": metadata["content"],
                    "message_type": metadata["message_type"],
                    "timestamp": metadata["timestamp"],
                    "score": match.score
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []


class PineconeMemoryManager:
    """Main memory management system using Pinecone for conversations and ChromaDB for knowledge."""
    
    def __init__(self):
        self.conversation_memory = PineconeConversationMemory()
        # Keep the existing RAG system for knowledge base
        from core.memory import SustainabilityRAG
        self.rag_system = SustainabilityRAG()
        logger.info("Pinecone memory manager initialized")
    
    def get_context_for_query(self, session_id: str, query: str, user_id: str = "default") -> MemoryContext:
        """
        Get comprehensive context for a query including conversation history and relevant documents.
        """
        # Get conversation history from Pinecone
        conversation_history = self.conversation_memory.get_conversation_history(session_id)
        
        # Retrieve relevant documents from ChromaDB
        relevant_documents = self.rag_system.retrieve_relevant_context(query)
        
        # Create context summary
        context_summary = self._create_context_summary(conversation_history, relevant_documents)
        
        return MemoryContext(
            relevant_documents=relevant_documents,
            conversation_history=conversation_history,
            context_summary=context_summary
        )
    
    def _create_context_summary(self, history: List[Message], documents: List[Dict[str, Any]]) -> str:
        """Create a summary of the available context."""
        summary_parts = []
        
        if history:
            recent_topics = []
            for msg in history[-4:]:  # Last 4 messages
                if msg.role == "user":
                    content = msg.content
                    recent_topics.append(content[:50] + "..." if len(content) > 50 else content)
            
            if recent_topics:
                summary_parts.append(f"Recent conversation topics: {', '.join(recent_topics)}")
        
        if documents:
            doc_topics = [doc["metadata"].get("topic", "general") for doc in documents]
            summary_parts.append(f"Relevant knowledge areas: {', '.join(set(doc_topics))}")
        
        return "; ".join(summary_parts) if summary_parts else "No specific context available"
    
    def create_session(self, user_id: str = "default") -> str:
        """Create a new conversation session."""
        return self.conversation_memory.create_session(user_id)
    
    def add_message(self, session_id: str, message: Message, user_id: str = "default") -> None:
        """Add a message to conversation history."""
        self.conversation_memory.add_message(session_id, message, user_id)
    
    def get_user_sessions(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        return self.conversation_memory.get_user_sessions(user_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        return self.conversation_memory.delete_session(session_id)
    
    def cleanup_old_sessions(self, hours: int = 24) -> None:
        """Clean up old sessions."""
        self.conversation_memory.cleanup_old_sessions(hours)
    
    def search_conversations(self, query: str, user_id: str = "default") -> List[Dict[str, Any]]:
        """Search through conversation history."""
        return self.conversation_memory.search_conversations(query, user_id)
