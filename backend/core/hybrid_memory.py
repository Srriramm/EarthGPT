"""Hybrid MongoDB + Pinecone memory system for semantic search in chat history."""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from sentence_transformers import SentenceTransformer
try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    # Fallback for older versions
    from pinecone import Pinecone
    ServerlessSpec = None
from database.mongodb import get_database
from config import settings


class HybridMemoryManager:
    """Hybrid memory system combining MongoDB for storage and Pinecone for semantic search."""
    
    def __init__(self):
        logger.info("Starting hybrid memory manager initialization...")
        
        # Initialize MongoDB
        self.mongodb_collection_name = "chat_messages"
        self.is_available = True
        logger.info(f"MongoDB collection name set to: {self.mongodb_collection_name}")
        
        # Initialize Pinecone
        logger.info("Initializing Pinecone...")
        if not settings.pinecone_api_key:
            logger.warning("Pinecone API key not found, using mock implementation")
            self.pc = None
            self.index = None
            self.index_name = "earthgpt-chat-messages"
        else:
            self.pc = Pinecone(api_key=settings.pinecone_api_key)
            self.index_name = "earthgpt-chat-messages"
            logger.info(f"Pinecone initialized with index: {self.index_name}")
        
        # Initialize embedding model
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
        
        # Setup Pinecone index
        logger.info("Setting up Pinecone index...")
        self._setup_pinecone_index()
        logger.info("Pinecone index setup completed")
        
        logger.info("Hybrid memory manager initialized successfully")
    
    def _setup_pinecone_index(self):
        """Setup Pinecone index for chat messages."""
        if not self.pc:
            logger.warning("Pinecone not available, skipping index setup")
            return
            
        try:
            if self.index_name not in self.pc.list_indexes().names():
                if ServerlessSpec:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=384,  # all-MiniLM-L6-v2 embedding dimension
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud='aws',
                            region='us-east-1'
                        )
                    )
                else:
                    # Fallback for older Pinecone versions
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=384,
                        metric="cosine"
                    )
                logger.info(f"Created Pinecone index: {self.index_name}")
            
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup Pinecone index: {e}")
            self.pc = None
            self.index = None
    
    async def get_mongodb_collection(self):
        """Get MongoDB collection for chat messages."""
        db = await get_database()
        return db[self.mongodb_collection_name]
    
    async def store_message(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Store a message in both MongoDB and Pinecone.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            timestamp: Message timestamp (defaults to now)
            
        Returns:
            MongoDB document ID
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        try:
            # 1. Store in MongoDB first
            mongodb_id = await self._store_in_mongodb(
                user_id, session_id, role, content, timestamp
            )
            
            # 2. Create embedding and store in Pinecone
            await self._store_in_pinecone(
                mongodb_id, user_id, session_id, role, content, timestamp
            )
            
            logger.info(f"Stored message {mongodb_id} in hybrid system")
            return mongodb_id
            
        except Exception as e:
            logger.error(f"Failed to store message in hybrid system: {e}")
            raise
    
    async def _store_in_mongodb(
        self, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str, 
        timestamp: datetime
    ) -> str:
        """Store message in MongoDB."""
        try:
            collection = await self.get_mongodb_collection()
            
            message_doc = {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "created_at": datetime.utcnow(),
                "message_length": len(content),
                "word_count": len(content.split())
            }
            
            result = await collection.insert_one(message_doc)
            logger.info(f"Stored message in MongoDB: {str(result.inserted_id)}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to store message in MongoDB: {e}")
            raise
    
    async def _store_in_pinecone(
        self, 
        mongodb_id: str, 
        user_id: str, 
        session_id: str, 
        role: str, 
        content: str, 
        timestamp: datetime
    ):
        """Store message embedding in Pinecone with MongoDB reference."""
        if not self.index:
            logger.debug("Pinecone not available, skipping embedding storage")
            return
            
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Create unique Pinecone ID
            pinecone_id = f"{mongodb_id}_{role}_{timestamp.timestamp()}"
            
            # Prepare metadata with more complete information
            metadata = {
                "mongodb_id": mongodb_id,
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content[:2000],  # Store more content in metadata
                "timestamp": timestamp.isoformat(),
                "message_length": len(content),
                "word_count": len(content.split())  # Add word count to metadata
            }
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[{
                    "id": pinecone_id,
                    "values": embedding,
                    "metadata": metadata
                }]
            )
            
            logger.info(f"Stored embedding for message {mongodb_id} in Pinecone")
            
        except Exception as e:
            logger.error(f"Failed to store in Pinecone: {e}")
            # Don't raise - MongoDB storage succeeded
    
    async def search_similar_messages(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 10,
        session_id: Optional[str] = None,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar messages.
        
        Args:
            query: Search query
            user_id: User to search within
            limit: Maximum number of results
            session_id: Optional session filter
            role_filter: Optional role filter (user/assistant)
            
        Returns:
            List of similar messages with MongoDB details
        """
        if not self.index:
            logger.debug("Pinecone not available, returning empty search results")
            return []
            
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build Pinecone filter
            filter_dict = {"user_id": {"$eq": user_id}}
            if session_id:
                filter_dict["session_id"] = {"$eq": session_id}
            if role_filter:
                filter_dict["role"] = {"$eq": role_filter}
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embedding,
                filter=filter_dict,
                top_k=limit,
                include_metadata=True
            )
            
            # Fetch full details from MongoDB
            similar_messages = []
            
            # Import ObjectId here to avoid circular imports
            from bson import ObjectId
            
            # For now, use only Pinecone metadata to avoid asyncio conflicts
            # This provides the essential information without MongoDB dependency
            for match in results.matches:
                similar_messages.append({
                    "mongodb_id": match.metadata.get("mongodb_id", ""),
                    "session_id": match.metadata.get("session_id", ""),
                    "role": match.metadata.get("role", ""),
                    "content": match.metadata.get("content", ""),
                    "timestamp": match.metadata.get("timestamp", ""),
                    "similarity_score": match.score,
                    "message_length": match.metadata.get("message_length", 0),
                    "word_count": match.metadata.get("word_count", 0)
                })
            
            # TODO: Implement async-safe MongoDB operations in a future version
            # The current implementation uses Pinecone metadata which contains
            # the essential message content and context information
            
            logger.info(f"Found {len(similar_messages)} similar messages for query")
            return similar_messages
            
        except Exception as e:
            logger.error(f"Failed to search similar messages: {e}")
            logger.error(f"Search error details: {type(e).__name__}: {str(e)}")
            return []
    
    async def get_session_messages(
        self, 
        session_id: str, 
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all messages for a session from MongoDB."""
        try:
            collection = await self.get_mongodb_collection()
            
            cursor = collection.find(
                {"session_id": session_id, "user_id": user_id}
            ).sort("timestamp", 1).limit(limit)
            
            messages = []
            async for doc in cursor:
                try:
                    messages.append({
                        "mongodb_id": str(doc["_id"]),
                        "session_id": doc["session_id"],
                        "role": doc["role"],
                        "content": doc["content"],
                        "timestamp": doc["timestamp"],
                        "message_length": doc.get("message_length", 0),
                        "word_count": doc.get("word_count", 0)
                    })
                except Exception as doc_error:
                    logger.warning(f"Failed to process document: {doc_error}")
                    continue
            
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get session messages: {e}")
            logger.error(f"Session messages error details: {type(e).__name__}: {str(e)}")
            return []
    
    async def delete_session_messages(self, session_id: str, user_id: str) -> bool:
        """Delete all messages for a session from both MongoDB and Pinecone."""
        try:
            collection = await self.get_mongodb_collection()
            
            # Get all message IDs for the session
            cursor = collection.find(
                {"session_id": session_id, "user_id": user_id},
                {"_id": 1}
            )
            
            message_ids = []
            async for doc in cursor:
                message_ids.append(str(doc["_id"]))
            
            # Delete from MongoDB
            mongo_result = await collection.delete_many({
                "session_id": session_id, 
                "user_id": user_id
            })
            
            # Delete from Pinecone
            if self.index:
                pinecone_ids = [f"{msg_id}_user_" for msg_id in message_ids] + \
                              [f"{msg_id}_assistant_" for msg_id in message_ids] + \
                              [f"{msg_id}_system_" for msg_id in message_ids]
                
                if pinecone_ids:
                    self.index.delete(ids=pinecone_ids)
            
            logger.info(f"Deleted {mongo_result.deleted_count} messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session messages: {e}")
            return False
    
    async def get_user_message_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's messages."""
        try:
            collection = await self.get_mongodb_collection()
            
            # Get total message count
            total_messages = await collection.count_documents({"user_id": user_id})
            
            # Get message count by role
            user_messages = await collection.count_documents({
                "user_id": user_id, 
                "role": "user"
            })
            assistant_messages = await collection.count_documents({
                "user_id": user_id, 
                "role": "assistant"
            })
            
            # Get total word count
            total_words = 0
            try:
                pipeline = [
                    {"$match": {"user_id": user_id}},
                    {"$group": {"_id": None, "total_words": {"$sum": "$word_count"}}}
                ]
                result = await collection.aggregate(pipeline).to_list(1)
                total_words = result[0]["total_words"] if result else 0
            except Exception as agg_error:
                logger.warning(f"Failed to aggregate word count: {agg_error}")
                # Fallback: count words manually
                try:
                    cursor = collection.find({"user_id": user_id}, {"word_count": 1})
                    async for doc in cursor:
                        total_words += doc.get("word_count", 0)
                except Exception as fallback_error:
                    logger.warning(f"Failed to count words manually: {fallback_error}")
            
            stats = {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "total_words": total_words,
                "average_words_per_message": total_words / total_messages if total_messages > 0 else 0
            }
            
            logger.info(f"Retrieved stats for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user message stats: {e}")
            logger.error(f"Stats error details: {type(e).__name__}: {str(e)}")
            return {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "total_words": 0,
                "average_words_per_message": 0
            }


# Global instance - lazy initialization
hybrid_memory_manager = None

def get_hybrid_memory_manager():
    """Get or create the hybrid memory manager instance."""
    global hybrid_memory_manager
    if hybrid_memory_manager is None:
        try:
            logger.info("Initializing hybrid memory manager...")
            hybrid_memory_manager = HybridMemoryManager()
            logger.info("Hybrid memory manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize hybrid memory manager: {e}")
            logger.error(f"Hybrid memory initialization error details: {type(e).__name__}: {str(e)}")
            # Return a mock object that fails gracefully
            class MockHybridMemoryManager:
                def __init__(self):
                    self.is_available = False
                
                async def store_message(self, *args, **kwargs):
                    logger.warning("Hybrid memory manager not available - message not stored")
                    return "mock_id"
                
                async def search_similar_messages(self, *args, **kwargs):
                    logger.warning("Hybrid memory manager not available - returning empty results")
                    return []
                
                async def get_session_messages(self, *args, **kwargs):
                    logger.warning("Hybrid memory manager not available - returning empty results")
                    return []
                
                async def get_user_message_stats(self, *args, **kwargs):
                    logger.warning("Hybrid memory manager not available - returning empty stats")
                    return {}
                
                async def delete_session_messages(self, *args, **kwargs):
                    logger.warning("Hybrid memory manager not available - deletion skipped")
                    return False
                
                async def get_mongodb_collection(self):
                    logger.warning("Hybrid memory manager not available - MongoDB collection not accessible")
                    return None
            
            hybrid_memory_manager = MockHybridMemoryManager()
    
    return hybrid_memory_manager


def is_hybrid_memory_available():
    """Check if hybrid memory manager is properly initialized and available."""
    global hybrid_memory_manager
    if hybrid_memory_manager is None:
        return False
    
    # Check if it's a mock object
    if hasattr(hybrid_memory_manager, 'is_available') and not hybrid_memory_manager.is_available:
        return False
    
    return True
