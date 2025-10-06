"""
Smart Memory Manager - Session-based memory management

This module provides session-based memory management and context optimization
using the Claude Memory System as the underlying implementation.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from loguru import logger

from .claude_memory import claude_memory_manager
from models.schemas import Message, MessageRole, MemoryContext


class SmartMemoryManager:
    """
    Smart Memory Manager for session-based memory and context optimization.
    
    This class provides intelligent memory management features:
    - Session-based context optimization
    - Message history management
    - Context summarization
    - Memory relevance scoring
    """
    
    def __init__(self):
        """Initialize the smart memory manager."""
        self.claude_memory = claude_memory_manager
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        self.summary_cache: Dict[str, str] = {}
        
        logger.info("Smart Memory Manager initialized")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data with enhanced context information."""
        session_data = self.claude_memory.get_session_info(session_id)
        if not session_data:
            return None
        
        # Enhance with smart memory features
        enhanced_session = {
            **session_data,
            "context_optimized": True,
            "memory_relevance_score": self._calculate_relevance_score(session_data),
            "context_summary": self._get_or_generate_summary(session_id, session_data)
        }
        
        return enhanced_session
    
    def get_session_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get session messages with smart filtering."""
        messages = self.claude_memory.get_session_messages(session_id, limit)
        
        # Apply smart filtering if needed
        if limit and len(messages) > limit:
            # Keep most recent messages and most relevant ones
            recent_messages = messages[-limit//2:]
            relevant_messages = self._get_most_relevant_messages(messages, limit//2)
            
            # Combine and deduplicate
            all_messages = recent_messages + relevant_messages
            seen_content = set()
            filtered_messages = []
            
            for msg in all_messages:
                if msg.content not in seen_content:
                    filtered_messages.append(msg)
                    seen_content.add(msg.content)
            
            messages = filtered_messages[:limit]
        
        return messages
    
    def add_message(self, session_id: str, role: MessageRole, content: str) -> bool:
        """Add a message to the session with smart processing."""
        success = self.claude_memory.add_message_to_session(session_id, role, content)
        
        if success:
            # Clear cached context for this session
            if session_id in self.context_cache:
                del self.context_cache[session_id]
            if session_id in self.summary_cache:
                del self.summary_cache[session_id]
            
            # Auto-create memory for important messages
            if self._should_create_memory(role, content):
                try:
                    self.claude_memory.create_memory(
                        session_id=session_id,
                        content=content,
                        metadata={
                            "role": role.value,
                            "auto_created": True,
                            "importance_score": self._calculate_importance_score(content)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to auto-create memory: {e}")
        
        return success
    
    def build_context(self, session_id: str, max_tokens: int = 8000) -> MemoryContext:
        """Build optimized context for the session."""
        # Check cache first
        cache_key = f"{session_id}_{max_tokens}"
        if cache_key in self.context_cache:
            cached_data = self.context_cache[cache_key]
            if datetime.fromisoformat(cached_data["timestamp"]) > datetime.utcnow() - timedelta(minutes=5):
                return cached_data["context"]
        
        # Build new context
        context = self.claude_memory.build_context(session_id, max_tokens)
        
        # Enhance with smart features
        enhanced_context = self._enhance_context(context, session_id)
        
        # Cache the result
        self.context_cache[cache_key] = {
            "context": enhanced_context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return enhanced_context
    
    def get_relevant_memories(self, session_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant memories for a query."""
        # Search memories
        memories = self.claude_memory.search_memories(query, session_id, limit * 2)
        
        # Score and rank memories
        scored_memories = []
        for memory in memories:
            score = self._calculate_memory_relevance_score(memory, query)
            scored_memories.append((score, memory))
        
        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for score, memory in scored_memories[:limit]]
    
    def summarize_conversation(self, session_id: str, max_length: int = 200) -> str:
        """Generate a conversation summary."""
        # Check cache
        if session_id in self.summary_cache:
            return self.summary_cache[session_id]
        
        session_data = self.claude_memory.get_session_info(session_id)
        if not session_data:
            return ""
        
        messages = session_data.get("messages", [])
        if not messages:
            return ""
        
        # Simple summarization logic
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        
        if len(user_messages) == 0:
            return ""
        
        # Create summary from first and last user messages
        first_message = user_messages[0]["content"]
        last_message = user_messages[-1]["content"] if len(user_messages) > 1 else ""
        
        if last_message and last_message != first_message:
            summary = f"Started with: {first_message[:100]}... Ended with: {last_message[:100]}"
        else:
            summary = first_message[:max_length]
        
        # Cache the summary
        self.summary_cache[session_id] = summary
        return summary
    
    def _calculate_relevance_score(self, session_data: Dict[str, Any]) -> float:
        """Calculate relevance score for session data."""
        score = 0.0
        
        # Factor in message count
        message_count = session_data.get("message_count", 0)
        score += min(message_count * 0.1, 1.0)
        
        # Factor in recency
        last_activity = datetime.fromisoformat(session_data.get("last_activity", "1970-01-01"))
        hours_ago = (datetime.utcnow() - last_activity).total_seconds() / 3600
        recency_score = max(0, 1 - (hours_ago / 24))  # Decay over 24 hours
        score += recency_score * 0.5
        
        # Factor in memory references
        memory_count = len(session_data.get("memory_references", []))
        score += min(memory_count * 0.2, 0.5)
        
        return min(score, 1.0)
    
    def _get_or_generate_summary(self, session_id: str, session_data: Dict[str, Any]) -> str:
        """Get or generate context summary."""
        existing_summary = session_data.get("context_summary", "")
        if existing_summary:
            return existing_summary
        
        return self.summarize_conversation(session_id)
    
    def _get_most_relevant_messages(self, messages: List[Message], limit: int) -> List[Message]:
        """Get most relevant messages based on content analysis."""
        if len(messages) <= limit:
            return messages
        
        # Simple relevance scoring based on message length and content
        scored_messages = []
        for msg in messages:
            score = len(msg.content) * 0.1  # Longer messages might be more important
            if "?" in msg.content:  # Questions are often important
                score += 0.5
            if msg.role == MessageRole.USER:  # User messages are generally more important
                score += 0.3
            
            scored_messages.append((score, msg))
        
        # Sort by score and return top messages
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        return [msg for score, msg in scored_messages[:limit]]
    
    def _should_create_memory(self, role: MessageRole, content: str) -> bool:
        """Determine if a message should be stored as a memory."""
        # Don't create memories for system messages
        if role == MessageRole.SYSTEM:
            return False
        
        # Create memories for longer, substantive messages
        if len(content) < 50:
            return False
        
        # Create memories for questions or important statements
        if "?" in content or len(content) > 200:
            return True
        
        # Create memories for messages with specific keywords
        important_keywords = ["remember", "important", "note", "save", "store"]
        if any(keyword in content.lower() for keyword in important_keywords):
            return True
        
        return False
    
    def _calculate_importance_score(self, content: str) -> float:
        """Calculate importance score for content."""
        score = 0.0
        
        # Length factor
        score += min(len(content) / 1000, 0.5)
        
        # Question factor
        if "?" in content:
            score += 0.3
        
        # Keyword factors
        important_keywords = ["important", "remember", "note", "save", "store", "key", "critical"]
        for keyword in important_keywords:
            if keyword in content.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    def _enhance_context(self, context: MemoryContext, session_id: str) -> MemoryContext:
        """Enhance context with smart features."""
        # Add conversation summary if not present
        if not context.context_summary:
            context.context_summary = self.summarize_conversation(session_id)
        
        # Enhance relevant documents with relevance scores
        enhanced_documents = []
        for doc in context.relevant_documents:
            enhanced_doc = {
                **doc,
                "relevance_score": self._calculate_memory_relevance_score(doc, context.context_summary)
            }
            enhanced_documents.append(enhanced_doc)
        
        # Sort by relevance
        enhanced_documents.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return MemoryContext(
            relevant_documents=enhanced_documents,
            conversation_history=context.conversation_history,
            context_summary=context.context_summary
        )
    
    def _calculate_memory_relevance_score(self, memory: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for a memory against a query."""
        content = memory.get("content", "").lower()
        query_lower = query.lower()
        
        # Simple text matching score
        if query_lower in content:
            return 1.0
        
        # Partial matching
        query_words = query_lower.split()
        content_words = content.split()
        
        matches = sum(1 for word in query_words if word in content_words)
        if matches > 0:
            return matches / len(query_words)
        
        return 0.0
    
    def cleanup_cache(self):
        """Clean up expired cache entries."""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, data in self.context_cache.items():
            timestamp = datetime.fromisoformat(data["timestamp"])
            if now - timestamp > timedelta(minutes=10):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.context_cache[key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global instance
smart_memory_manager = SmartMemoryManager()





