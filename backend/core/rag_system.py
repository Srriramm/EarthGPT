"""Simple RAG system for sustainability knowledge base."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
from loguru import logger
from config import settings


class SustainabilityRAG:
    """Simple RAG system for sustainability knowledge base using ChromaDB."""
    
    def __init__(self):
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
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
                    "content": "Sustainable development goals (SDGs) are 17 interconnected goals adopted by the United Nations in 2015 to address global challenges including poverty, inequality, climate change, environmental degradation, peace, and justice. They provide a shared blueprint for peace and prosperity for people and the planet.",
                    "metadata": {"topic": "sdgs", "source": "un_goals"}
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
    
    def retrieve_relevant_context(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            relevant_docs = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    relevant_docs.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                        "score": 1 - results["distances"][0][i] if results["distances"] and results["distances"][0] else 0
                    })
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error retrieving relevant context: {e}")
            return []

