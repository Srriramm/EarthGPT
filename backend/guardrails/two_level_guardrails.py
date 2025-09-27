"""Two-level guardrails system with regex filtering and LLM classification."""

import re
from typing import List, Tuple, Optional, Dict
from loguru import logger

from .base import BaseGuardrails
from .models import GuardrailCheck
from .config import GuardrailsConfig
from services.llm_service import llm_service
from models.schemas import Message, MessageRole


class TwoLevelGuardrails(BaseGuardrails):
    """Two-level guardrails system: regex filtering + LLM classification."""
    
    def __init__(self, config: GuardrailsConfig = None):
        """Initialize two-level guardrails."""
        super().__init__()
        self.config = config or GuardrailsConfig()
        
        # Regex patterns for first-level filtering (obvious non-sustainability)
        self.regex_block_patterns = [
            # Gaming and gambling
            r'\b(?:poker|gambling|casino|betting|cards)\b.*\b(?:strategy|winning|success|profit|long run|long-term)\b',
            r'\b(?:chess|checkers|bridge|monopoly|scrabble|board game|card game)\b.*\b(?:best|player|champion|strategy|tips|winning)\b',
            r'\b(?:gaming|video game|playstation|xbox|nintendo)\b.*\b(?:strategy|tips|winning)\b',
            
            # Sports and entertainment
            r'\b(?:sports|football|basketball|soccer|tennis|golf|baseball|cricket)\b.*\b(?:strategy|winning|success|improve)\b',
            r'\b(?:movie|film|music|celebrity|entertainment)\b.*\b(?:best|recommend|review)\b',
            
            # Personal topics
            r'\b(?:dating|relationship|love|marriage|romance)\b.*\b(?:advice|tips|how to)\b',
            r'\b(?:cooking|recipe|restaurant|chef)\b.*\b(?:best|how to|tips)\b(?!\s+(?:sustainable|organic|local))',
            r'\b(?:fashion|clothing|shopping)\b.*\b(?:best|style|trends)\b(?!\s+(?:sustainable|eco|green))',
            r'\b(?:travel|vacation|tourism)\b.*\b(?:best|recommend|guide)\b(?!\s+(?:sustainable|eco|green))',
            
            # Health and fitness (non-environmental)
            r'\b(?:diet|nutrition|bodybuilding|muscle|fitness|workout|exercise|gym|training)\b.*\b(?:plan|strategy|tips|advice|how to)\b(?!\s+(?:sustainable|environmental|eco))',
            r'\b(?:health|medical|doctor|medicine|hospital)\b.*\b(?:advice|tips|treatment)\b(?!\s+(?:environmental|sustainability))',
            
            # Technology and programming (non-sustainability)
            r'\b(?:programming|coding|software|computer|tech)\b.*\b(?:tips|tutorial|learn)\b(?!\s+(?:sustainable|green|clean))',
            r'\b(?:stock market|trading|cryptocurrency|bitcoin|ethereum|blockchain)\b.*\b(?:strategy|investment|tips|explain|difference|what is|how does)\b(?!\s+(?:sustainable|esg|green))',
            # Block cryptocurrency queries unless they contain sustainability context
            r'\b(?:cryptocurrency|bitcoin|ethereum|blockchain|fiat money|digital currency)\b(?!.*\b(?:sustainable|green|environmental|carbon|emission|mining|energy|renewable|climate|esg)\b)',
            
            # Education (non-environmental)
            r'\b(?:education|school|university|student|college)\b.*\b(?:advice|tips|study)\b(?!\s+(?:environmental|sustainability|green))',
            
            # Academic subjects (non-sustainability)
            r'\b(?:mathematics|math|mathematical|philosophy|philosophical|paradox|achilles|tortoise|zeno)\b',
            r'\b(?:cantor|diagonal|argument|set theory|infinity|infinite|cardinality)\b',
            r'\b(?:geometry|algebra|calculus|statistics|probability|theorem|proof)\b',
            r'\b(?:logic|logical|reasoning|deduction|induction|syllogism)\b',
            r'\b(?:physics|physical|motion|velocity|acceleration|momentum|kinetic|potential)\b(?!\s+(?:sustainable|renewable|clean|green|environmental|efficiency|transition|storage|security))',
            r'\b(?:force|tangential|linear|rotational|oscillatory|harmonic|wave|frequency|amplitude)\b(?!\s+(?:economy|business|model|approach|design|thinking|supply|chain|waste|reuse|recycle))',
            r'\b(?:mechanics|thermodynamics|electromagnetism|quantum|relativity|particle|atom|molecule)\b',
            r'\b(?:newton|einstein|maxwell|schrodinger|heisenberg|planck|bohr|rutherford)\b',
        ]
        
        # Follow-up phrases that should be allowed with context
        self.follow_up_phrases = [
            "explain more", "more details", "tell me more", "elaborate",
            "can you tell more", "can you explain more", "can you elaborate",
            "yes", "y", "yeah", "yep", "sure", "ok", "okay",
            "what else", "anything else", "more information", "continue",
            "go on", "keep going", "more", "please", "summarize", "summary",
            "can you", "could you", "would you", "please elaborate", "please explain",
            "tell me", "show me", "give me", "provide", "expand", "detail"
        ]
        
        logger.info(f"Two-level guardrails initialized with {len(self.regex_block_patterns)} regex patterns")
    
    def check_sustainability_relevance(self, query: str, conversation_context: str = None) -> GuardrailCheck:
        """
        Check if the query is sustainability-related using two-level filtering.
        
        Args:
            query: User input query
            conversation_context: Previous conversation context for follow-up detection
            
        Returns:
            GuardrailCheck with validation results
        """
        query_lower = query.lower().strip()
        
        # Handle empty queries
        if not query_lower:
            return GuardrailCheck(
                is_sustainability_related=False,
                confidence_score=0.0,
                detected_keywords=[],
                rejection_reason="Empty query"
            )
        
        # Check for follow-up responses with context awareness
        is_follow_up = any(phrase in query_lower for phrase in self.follow_up_phrases)
        
        if is_follow_up:
            # If we have conversation context and it contains sustainability content, allow the follow-up
            if conversation_context:
                context_lower = conversation_context.lower()
                context_sustainability_score = self._calculate_context_sustainability_score(context_lower)
                
                # If the conversation context is sustainability-related, allow the follow-up
                if context_sustainability_score >= 0.3:
                    return GuardrailCheck(
                        is_sustainability_related=True,
                        confidence_score=0.9,
                        detected_keywords=["follow-up", "context-aware"],
                        rejection_reason=None
                    )
            
            # For very short follow-ups without context, allow them
            if len(query.strip()) <= 10:
                return GuardrailCheck(
                    is_sustainability_related=True,
                    confidence_score=0.8,
                    detected_keywords=["follow-up"],
                    rejection_reason=None
                )
        
        # Count sentences to determine processing path
        sentence_count = self._count_sentences(query)
        
        # FIRST LEVEL: Regex check for single sentences
        if sentence_count <= 1:
            logger.info(f"Single sentence query detected, applying regex filter")
            
            # Apply regex patterns for obvious non-sustainability queries
            for pattern in self.regex_block_patterns:
                if re.search(pattern, query_lower):
                    logger.info(f"Regex BLOCKED query '{query[:50]}...' - matched pattern: {pattern}")
                    return GuardrailCheck(
                        is_sustainability_related=False,
                        confidence_score=0.0,
                        detected_keywords=[],
                        rejection_reason="Query is out of domain"
                    )
            
            # If regex doesn't block, proceed to LLM classification
            logger.info(f"Regex passed, proceeding to LLM classification")
        
        # SECOND LEVEL: LLM Classification (Claude Haiku 3)
        logger.info(f"Applying LLM classification for query: '{query[:50]}...'")
        
        try:
            llm_result = self._classify_with_llm(query)
            
            if llm_result:
                logger.info(f"LLM classification: ALLOWED - '{query[:50]}...'")
                return GuardrailCheck(
                    is_sustainability_related=True,
                    confidence_score=0.9,
                    detected_keywords=["llm-classified"],
                    rejection_reason=None
                )
            else:
                logger.info(f"LLM classification: BLOCKED - '{query[:50]}...'")
                return GuardrailCheck(
                    is_sustainability_related=False,
                    confidence_score=0.0,
                    detected_keywords=[],
                    rejection_reason="Query is out of domain"
                )
                
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fallback: if LLM fails, be conservative and block the query
            logger.warning("LLM classification failed, blocking query as fallback")
            return GuardrailCheck(
                is_sustainability_related=False,
                confidence_score=0.0,
                detected_keywords=[],
                rejection_reason="Query is out of domain"
            )
    
    def _count_sentences(self, text: str) -> int:
        """Count the number of sentences in the text."""
        # Simple sentence counting based on punctuation
        sentences = re.split(r'[.!?]+', text.strip())
        # Filter out empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)
    
    def _classify_with_llm(self, query: str) -> bool:
        """
        Use Claude Haiku 3 to classify if the query is sustainability-related.
        
        Args:
            query: User input query
            
        Returns:
            True if sustainability-related, False otherwise
        """
        # Ensure LLM service is loaded
        if not llm_service.is_loaded:
            if not llm_service.load_model():
                raise Exception("Failed to load LLM service")
        
        # Create classification prompt
        classification_prompt = f"""You are a sustainability expert. Your task is to determine if a user query is related to sustainability or environmental topics.

Consider the following as sustainability-related:
- Environmental protection and conservation
- Climate change and global warming
- Renewable energy and clean technology
- Carbon reduction and emissions
- ESG (Environmental, Social, Governance)
- Sustainable development and practices
- Green finance and sustainable investing
- Circular economy and waste reduction
- Biodiversity and ecosystem protection
- Energy efficiency and transition
- Sustainable agriculture and food systems
- Green building and infrastructure
- Environmental policy and governance
- Climate agreements and international cooperation
- Follow-up requests about sustainability topics (e.g., "explain more", "give it in points", "summarize", "what else")

Consider the following as NOT sustainability-related:
- Personal health and fitness (unless environmental impact)
- Entertainment, sports, gaming
- General business advice (unless sustainability-focused)
- Technology and programming (unless green tech)
- Education and academic subjects (unless environmental)
- Personal relationships and lifestyle
- Cooking and recipes (unless sustainable practices)
- Travel and tourism (unless sustainable travel)

User Query: "{query}"

Is this question related to sustainability or a sustainability context? 

IMPORTANT: Answer with ONLY the word "YES" or "NO". Do not provide any explanation or additional text."""

        try:
            # Create message for LLM
            messages = [
                Message(
                    role=MessageRole.USER,
                    content=classification_prompt
                )
            ]
            
            # Get response from Claude Haiku 3
            result = llm_service.generate_response_simple(
                messages=messages,
                max_tokens=10,  # Very short response expected
                temperature=0.0  # Deterministic response
            )
            
            # Parse the response
            response_lower = result.strip().lower()
            
            # Check for yes/no in the response
            if "yes" in response_lower and "no" not in response_lower:
                return True
            elif "no" in response_lower and "yes" not in response_lower:
                return False
            else:
                # If response is unclear, log and default to False
                logger.warning(f"Unclear LLM classification response: '{result}'")
                return False
                
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            raise
    
    def _calculate_context_sustainability_score(self, context_lower: str) -> float:
        """Calculate a simple sustainability score for conversation context."""
        sustainability_terms = [
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'green',
            'renewable', 'carbon', 'emission', 'esg', 'clean energy', 'solar', 'wind',
            'biodiversity', 'conservation', 'circular economy', 'waste reduction'
        ]
        
        score = 0.0
        for term in sustainability_terms:
            if term in context_lower:
                score += 0.1
        
        return min(score, 1.0)
    
    def validate_output(self, response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the response is appropriate and sustainability-focused.
        
        Args:
            response: Generated response text
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        response_lower = response.lower()
        
        # Check for inappropriate content
        inappropriate_patterns = [
            r'\b(?:i cannot|i can\'t|i\'m not able to)\s+(?:help|assist)',
            r'\b(?:sorry, i don\'t|i don\'t know about)',
            r'\b(?:that\'s not my area|outside my expertise)',
            r'\b(?:i\'m not qualified|i don\'t have expertise)',
            r'\b(?:i can\'t answer|i cannot answer)',
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, response_lower):
                return False, "Response contains inappropriate refusal patterns"
        
        # Check for sustainability relevance in response
        sustainability_terms = [
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'green',
            'renewable', 'carbon', 'emission', 'esg', 'clean energy', 'solar', 'wind',
            'biodiversity', 'conservation', 'circular economy', 'waste reduction'
        ]
        
        sustainability_mentions = sum(1 for term in sustainability_terms if term in response_lower)
        
        # For longer responses, require sustainability context
        if len(response) > 100 and sustainability_mentions == 0:
            return False, "Response lacks sustainability context"
        
        return True, None
    
    def get_polite_refusal_message(self, reason: str) -> str:
        """Generate a polite refusal message for non-sustainability queries."""
        return "I'm a sustainability expert focused on environmental topics, climate action, and sustainable practices. I can help with questions about renewable energy, carbon reduction, ESG, or other sustainability-related topics. What sustainability topic would you like to explore?"
