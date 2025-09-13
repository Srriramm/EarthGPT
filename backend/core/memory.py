"""Conversational memory and RAG system implementation."""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from models.schemas import Message, MemoryContext
from config import settings


class ConversationMemory:
    """Manages conversation history and session state."""
    
    def __init__(self):
        self.sessions: Dict[str, List[Message]] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.max_history = settings.max_conversation_history
        
        logger.info("Conversation memory initialized")
    
    def create_session(self) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        self.session_metadata[session_id] = {
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_count": 0
        }
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to the conversation history."""
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found, creating new one")
            # Create a new session and use the provided session_id
            self.sessions[session_id] = []
            self.session_metadata[session_id] = {
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "message_count": 0
            }
        
        self.sessions[session_id].append(message)
        self.session_metadata[session_id]["last_activity"] = datetime.utcnow()
        self.session_metadata[session_id]["message_count"] += 1
        
        # Trim history if it exceeds max length
        if len(self.sessions[session_id]) > self.max_history * 2:  # *2 for user+assistant pairs
            self.sessions[session_id] = self.sessions[session_id][-self.max_history * 2:]
        
        logger.debug(f"Added message to session {session_id}")
    
    def get_conversation_history(self, session_id: str) -> List[Message]:
        """Get conversation history for a session."""
        return self.sessions.get(session_id, [])
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata."""
        return self.session_metadata.get(session_id)
    
    def cleanup_old_sessions(self, hours: int = 24) -> None:
        """Clean up sessions older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        sessions_to_remove = []
        
        for session_id, metadata in self.session_metadata.items():
            if metadata["last_activity"] < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            del self.session_metadata[session_id]
            logger.info(f"Cleaned up old session: {session_id}")


class SustainabilityRAG:
    """Retrieval-Augmented Generation system for sustainability knowledge."""
    
    def __init__(self):
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="sustainability_knowledge",
            metadata={"description": "Sustainability and environmental knowledge base"}
        )
        
        # Initialize with sample sustainability documents
        self._initialize_knowledge_base()
        
        logger.info("RAG system initialized")
    
    def _initialize_knowledge_base(self) -> None:
        """Initialize the knowledge base with sample sustainability documents."""
        if self.collection.count() == 0:
            sample_documents = [
                {
                    "content": "Renewable energy sources like solar, wind, and hydroelectric power are essential for reducing carbon emissions and combating climate change. These technologies are becoming increasingly cost-effective and can provide clean, sustainable energy for the future.",
                    "metadata": {"topic": "renewable_energy", "source": "sustainability_guide"}
                },
                {
                    "content": "Carbon footprint refers to the total amount of greenhouse gases, particularly carbon dioxide, emitted directly or indirectly by human activities. Reducing carbon footprint through energy efficiency, sustainable transportation, and waste reduction is crucial for environmental protection.",
                    "metadata": {"topic": "carbon_footprint", "source": "environmental_science"}
                },
                {
                    "content": "ESG (Environmental, Social, and Governance) criteria are used to evaluate companies' sustainability performance. Environmental factors include climate change, resource depletion, and pollution. Social factors consider human rights, labor practices, and community impact. Governance focuses on corporate ethics and transparency.",
                    "metadata": {"topic": "esg", "source": "sustainable_investing"}
                },
                {
                    "content": "The circular economy is an economic system aimed at eliminating waste and the continual use of resources. It involves designing products for longevity, reusing materials, and recycling components to create a closed-loop system that minimizes environmental impact.",
                    "metadata": {"topic": "circular_economy", "source": "sustainable_design"}
                },
                {
                    "content": "Biodiversity conservation is essential for maintaining ecosystem health and resilience. Protecting natural habitats, reducing pollution, and implementing sustainable land-use practices help preserve species diversity and ecosystem services.",
                    "metadata": {"topic": "biodiversity", "source": "conservation_biology"}
                },
                {
                    "content": "Climate change mitigation involves reducing greenhouse gas emissions through renewable energy adoption, energy efficiency improvements, sustainable transportation, and carbon capture technologies. Adaptation strategies help communities prepare for climate impacts.",
                    "metadata": {"topic": "climate_change", "source": "climate_science"}
                }
            ]
            
            # Add documents to collection
            for i, doc in enumerate(sample_documents):
                self.collection.add(
                    documents=[doc["content"]],
                    metadatas=[doc["metadata"]],
                    ids=[f"doc_{i}"]
                )
            
            logger.info(f"Initialized knowledge base with {len(sample_documents)} documents")
    
    def retrieve_relevant_context(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context documents for a query.
        
        Args:
            query: User query
            n_results: Number of relevant documents to retrieve
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            relevant_docs = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    relevant_docs.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            logger.debug(f"Retrieved {len(relevant_docs)} relevant documents for query")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add a new document to the knowledge base."""
        doc_id = str(uuid.uuid4())
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        logger.info(f"Added document {doc_id} to knowledge base")
        return doc_id


class MemoryManager:
    """Main memory management system combining conversation memory and RAG."""
    
    def __init__(self):
        self.conversation_memory = ConversationMemory()
        self.rag_system = SustainabilityRAG()
        logger.info("Memory manager initialized")
    
    def get_context_for_query(self, session_id: str, query: str) -> MemoryContext:
        """
        Get comprehensive context for a query including conversation history and relevant documents.
        
        Args:
            session_id: Session identifier
            query: User query
            
        Returns:
            MemoryContext with conversation history and relevant documents
        """
        # Get conversation history
        conversation_history = self.conversation_memory.get_conversation_history(session_id)
        
        # Retrieve relevant documents
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
                    # Handle both Message objects and dictionaries
                    if hasattr(msg, 'content'):
                        content = msg.content
                    else:
                        content = msg.get('content', '')
                    recent_topics.append(content[:50] + "..." if len(content) > 50 else content)
            
            if recent_topics:
                summary_parts.append(f"Recent conversation topics: {', '.join(recent_topics)}")
        
        if documents:
            doc_topics = [doc["metadata"].get("topic", "general") for doc in documents]
            summary_parts.append(f"Relevant knowledge areas: {', '.join(set(doc_topics))}")
        
        return "; ".join(summary_parts) if summary_parts else "No specific context available"
    
    def create_session(self) -> str:
        """Create a new conversation session."""
        return self.conversation_memory.create_session()
    
    def add_message(self, session_id: str, message: Message) -> None:
        """Add a message to conversation history."""
        self.conversation_memory.add_message(session_id, message)
    
    def cleanup_old_sessions(self, hours: int = 24) -> None:
        """Clean up old sessions."""
        self.conversation_memory.cleanup_old_sessions(hours)
