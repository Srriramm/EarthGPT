"""
LLM service specifically for classification tasks using Claude 3.5 Haiku.
"""

import os
from typing import List, Dict, Any
from loguru import logger
import anthropic
from config import settings


class ClassificationLLMService:
    """LLM service specifically for classification tasks."""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or settings.claude_api_key
        self.model_name = settings.claude_classification_model
        self.client = None
        self.is_loaded = False
        
        logger.info(f"Classification LLM Service initialized with Claude model: {self.model_name}")
    
    def load_model(self) -> bool:
        """Initialize the Claude API client."""
        try:
            if not self.api_key:
                logger.error("Claude API key not found. Please set ANTHROPIC_API_KEY in your .env file.")
                return False
            
            logger.info(f"Initializing Claude API client for classification with model: {self.model_name}")
            
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.is_loaded = True
            
            logger.info("Claude API client for classification initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client for classification: {e}")
            return False
    
    def classify_sustainability_relevance(self, query: str) -> bool:
        """
        Classify if a query is sustainability-related using Claude 3.5 Haiku.
        
        Args:
            query: User input query
            
        Returns:
            True if sustainability-related, False otherwise
        """
        if not self.is_loaded:
            if not self.load_model():
                logger.error("Classification LLM service not loaded")
                return False
        
        # Optimized classification prompt for Haiku
        classification_prompt = f"""You are a sustainability expert. Your task is to determine if a user query is related to sustainability or environmental topics.

Consider the following as sustainability-related:

CORE ENVIRONMENTAL TOPICS:
- Environmental protection, conservation, and restoration
- Climate change, global warming, and climate science
- Renewable energy, clean technology, and green innovation
- Carbon reduction, emissions, and carbon markets
- Biodiversity, ecosystems, and wildlife conservation
- Pollution control and environmental remediation
- Water resources and management
- Sustainable agriculture, forestry, and land use

SUSTAINABILITY FRAMEWORKS & STANDARDS:
- ESG (Environmental, Social, Governance) investing and reporting
- Sustainability certifications and standards (FSC, LEED, B-Corp, etc.)
- Carbon credit systems and verification bodies (Verra, Gold Standard, etc.)
- Environmental impact assessments and life cycle analysis
- Sustainability reporting frameworks (GRI, SASB, TCFD, etc.)
- Green bonds, sustainable finance, and impact investing

SUSTAINABLE PRACTICES & SYSTEMS:
- Circular economy, waste reduction, and recycling
- Energy efficiency and sustainable design
- Green building and sustainable infrastructure
- Sustainable supply chains and procurement
- Corporate sustainability and CSR initiatives
- Sustainable transportation and mobility
- Eco-friendly products and services

POLICY & GOVERNANCE:
- Environmental policy and regulation
- Climate agreements and international cooperation
- Environmental law and compliance
- Sustainability governance and risk management
- Green taxonomy and sustainable finance regulations

ORGANIZATIONS & ENTITIES:
- Environmental NGOs, certification bodies, and standards organizations
- Sustainability-focused companies and initiatives
- Climate research institutions and environmental agencies
- Carbon offset providers and verification bodies

FOLLOW-UP QUERIES:
- Any follow-up requests about previously discussed sustainability topics
- Requests for clarification, examples, or more details on sustainability matters

Consider the following as NOT sustainability-related:
- General personal health and fitness (unless discussing environmental health impacts)
- Entertainment, sports, gaming (unless discussing environmental impact of these industries)
- General business advice (unless specifically about sustainability integration)
- General technology and programming (unless green tech or environmental applications)
- General education topics (unless environmental science or sustainability studies)
- Personal relationships and lifestyle (unless discussing sustainable living)
- General cooking and recipes (unless about sustainable food practices)
- General travel and tourism (unless about sustainable or eco-tourism)

User Query: "{query}"

Is this question related to sustainability or environmental topics in any way? Consider both direct and indirect connections to sustainability.

IMPORTANT: Answer with ONLY the word "YES" or "NO". Do not provide any explanation or additional text."""

        try:
            # Use Haiku for fast, cost-effective classification
            api_params = {
                "model": self.model_name,
                "max_tokens": 5,  # Very short response
                "temperature": 0.0,  # Deterministic classification
                "messages": [
                    {
                        "role": "user",
                        "content": classification_prompt
                    }
                ]
            }
            
            response = self.client.messages.create(**api_params)
            result = response.content[0].text.strip() if response.content else "NO"
            
            # Parse response aggressively
            response_clean = result.strip().upper()
            if response_clean.startswith("YES") or response_clean == "YES":
                return True
            elif response_clean.startswith("NO") or response_clean == "NO":
                return False
            else:
                # Handle unclear responses
                logger.warning(f"Unclear LLM classification response: '{result}', defaulting to NO")
                return False
                
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            return False


# Global instance
classification_llm_service = ClassificationLLMService()
