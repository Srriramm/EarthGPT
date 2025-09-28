"""Hybrid classifier guardrails using embeddings + LLM for sustainability relevance detection."""

import numpy as np
from typing import List, Tuple, Optional, Dict
from loguru import logger
from sentence_transformers import SentenceTransformer

from .base import BaseGuardrails
from .models import GuardrailCheck
from .intelligent_output_validator import IntelligentOutputValidator
from services.llm_service import llm_service
from core.classification_llm import classification_llm_service
from models.schemas import Message, MessageRole


class HybridClassifierGuardrails(BaseGuardrails):
    """Hybrid guardrails system using semantic embeddings + LLM classification."""
    
    def __init__(self):
        """Initialize hybrid classifier guardrails."""
        super().__init__()
        
        # Initialize embedding model
        logger.info("Loading embedding model for hybrid classifier...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
        
        # Define broad sustainability category labels for embedding comparison
        self.sustainability_categories = [
            # Core environmental topics
            "environmental protection and conservation",
            "climate change and global warming mitigation",
            "renewable energy and clean technology",
            "carbon emissions reduction and net zero",
            "sustainable development and practices",
            "circular economy and waste reduction",
            "biodiversity and ecosystem conservation",
            "green energy transition and efficiency",
            
            # Business and finance sustainability
            "ESG environmental social governance investing",
            "sustainable finance and green bonds",
            "corporate sustainability reporting",
            "sustainable business practices and models",
            "green technology innovation and development",
            
            # Policy and governance
            "environmental policy and regulation",
            "climate agreements and international cooperation",
            "sustainable urban planning and development",
            "green infrastructure and buildings",
            
            # Lifestyle and consumer
            "sustainable agriculture and food systems",
            "eco-friendly products and consumption",
            "sustainable transportation and mobility",
            "environmental awareness and education"
        ]
        
        # Non-sustainability category labels for contrast
        self.non_sustainability_categories = [
            "personal health and medical advice",
            "entertainment movies music and celebrities",
            "sports and gaming activities",
            "personal relationships and dating advice", 
            "cooking recipes and restaurant recommendations",
            "fashion trends and clothing styles",
            "general travel and vacation planning",
            "programming and software development",
            "mathematics and academic subjects",
            "financial investments and trading",
            "general business and marketing advice"
        ]
        
        # Pre-compute embeddings for category labels
        logger.info("Computing embeddings for sustainability categories...")
        self.sustainability_embeddings = self.embedding_model.encode(self.sustainability_categories)
        self.non_sustainability_embeddings = self.embedding_model.encode(self.non_sustainability_categories)
        
        # Initialize intelligent output validator for long-term robustness
        try:
            self.output_validator = IntelligentOutputValidator()
            logger.info("Intelligent output validator initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize intelligent output validator: {e}")
            self.output_validator = None
        logger.info(f"Computed embeddings for {len(self.sustainability_categories)} sustainability and {len(self.non_sustainability_categories)} non-sustainability categories")
        
        # Thresholds for decision making
        self.high_confidence_threshold = 0.7  # Clearly sustainability-related
        self.low_confidence_threshold = 0.3   # Clearly not sustainability-related
        # Between these thresholds -> uncertain -> LLM decides
        
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
        
        logger.info("Hybrid classifier guardrails initialized successfully")
    
    def check_sustainability_relevance(self, query: str, conversation_context: str = None) -> GuardrailCheck:
        """
        Check if the query is sustainability-related using hybrid classification.
        
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
        
        # ENHANCED FOLLOW-UP DETECTION
        is_follow_up = self._two_layer_follow_up_detection(query_lower, conversation_context)
        
        if is_follow_up:
            # If we have conversation context and it contains sustainability content, allow the follow-up
            if conversation_context:
                context_lower = conversation_context.lower()
                context_sustainability_score = self._calculate_context_sustainability_score(context_lower)
                
                # If the conversation context is sustainability-related, allow the follow-up
                if context_sustainability_score >= 0.3:
                    logger.info(f"Follow-up allowed based on sustainability context (score: {context_sustainability_score:.2f})")
                    return GuardrailCheck(
                        is_sustainability_related=True,
                        confidence_score=0.95,
                        detected_keywords=["follow-up", "context-aware", "sustainability-context"],
                        rejection_reason=None
                    )
            
            # For very short follow-ups without clear context, still allow but with lower confidence
            if len(query.strip()) <= 10:
                logger.info("Follow-up allowed based on query length heuristic")
                return GuardrailCheck(
                    is_sustainability_related=True,
                    confidence_score=0.8,
                    detected_keywords=["follow-up", "short-query"],
                    rejection_reason=None
                )
        
        # HYBRID CLASSIFICATION
        logger.info(f"Applying hybrid classification for query: '{query[:50]}...'")
        
        try:
            # Step 1: Embedding-based classification
            embedding_result = self._classify_with_embeddings(query)
            sustainability_score, confidence_level = embedding_result
            
            logger.info(f"Embedding classification: score={sustainability_score:.3f}, confidence={confidence_level}")
            
            # Step 2: Decision logic based on embedding confidence
            if confidence_level == "high_sustainability":
                # High confidence it's sustainability-related
                return GuardrailCheck(
                    is_sustainability_related=True,
                    confidence_score=sustainability_score,
                    detected_keywords=["embedding-classified", "high-confidence"],
                    rejection_reason=None
                )
            
            elif confidence_level == "high_non_sustainability":
                # High confidence it's NOT sustainability-related
                return GuardrailCheck(
                    is_sustainability_related=False,
                    confidence_score=1.0 - sustainability_score,
                    detected_keywords=["embedding-classified", "clearly-off-topic"],
                    rejection_reason="Query is not related to sustainability topics"
                )
            
            else:  # confidence_level == "uncertain"
                # Uncertain -> use LLM for final decision
                logger.info(f"Embedding uncertain (score={sustainability_score:.3f}), consulting LLM...")
                llm_result = self._classify_with_llm(query)
                
                if llm_result:
                    logger.info(f"LLM classification: ALLOWED - '{query[:50]}...'")
                    return GuardrailCheck(
                        is_sustainability_related=True,
                        confidence_score=0.8,  # Good confidence from LLM
                        detected_keywords=["hybrid-classified", "llm-decided"],
                        rejection_reason=None
                    )
                else:
                    logger.info(f"LLM classification: BLOCKED - '{query[:50]}...'")
                    return GuardrailCheck(
                        is_sustainability_related=False,
                        confidence_score=0.8,
                        detected_keywords=["hybrid-classified", "llm-rejected"],
                        rejection_reason="Query is not related to sustainability topics"
                    )
                    
        except Exception as e:
            logger.error(f"Hybrid classification failed: {e}")
            # Fallback: if classification fails, be conservative and block the query
            logger.warning("Hybrid classification failed, blocking query as fallback")
            return GuardrailCheck(
                is_sustainability_related=False,
                confidence_score=0.0,
                detected_keywords=[],
                rejection_reason="Classification system error"
            )
    
    def _classify_with_embeddings(self, query: str) -> Tuple[float, str]:
        """
        Classify query using semantic embeddings against sustainability categories.
        
        Args:
            query: User input query
            
        Returns:
            Tuple of (sustainability_score, confidence_level)
            confidence_level: "high_sustainability", "high_non_sustainability", or "uncertain"
        """
        # Get query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Calculate similarities with sustainability categories
        sustainability_similarities = np.dot(query_embedding, self.sustainability_embeddings.T)[0]
        max_sustainability_sim = np.max(sustainability_similarities)
        
        # Calculate similarities with non-sustainability categories  
        non_sustainability_similarities = np.dot(query_embedding, self.non_sustainability_embeddings.T)[0]
        max_non_sustainability_sim = np.max(non_sustainability_similarities)
        
        # Calculate sustainability score (relative preference for sustainability categories)
        if max_sustainability_sim + max_non_sustainability_sim > 0:
            sustainability_score = max_sustainability_sim / (max_sustainability_sim + max_non_sustainability_sim)
        else:
            sustainability_score = 0.5  # Neutral if no similarity
        
        # Determine confidence level
        if sustainability_score >= self.high_confidence_threshold:
            confidence_level = "high_sustainability"
        elif sustainability_score <= self.low_confidence_threshold:
            confidence_level = "high_non_sustainability"
        else:
            confidence_level = "uncertain"
        
        logger.debug(f"Embedding scores - Sustainability: {max_sustainability_sim:.3f}, Non-sustainability: {max_non_sustainability_sim:.3f}, Final score: {sustainability_score:.3f}")
        
        return sustainability_score, confidence_level
    
    def _classify_with_llm(self, query: str) -> bool:
        """
        Use LLM to classify uncertain queries for sustainability relevance.
        
        Args:
            query: User input query
            
        Returns:
            True if sustainability-related, False otherwise
        """
        try:
            # Use the dedicated classification service with Claude 3.5 Haiku
            return classification_llm_service.classify_sustainability_relevance(query)
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            return False
    
    def _smart_follow_up_detection(self, query_lower: str, conversation_context: str = None) -> bool:
        """
        Enhanced follow-up detection using linguistic patterns and context analysis.
        No LLM needed - uses smart pattern matching + context awareness.
        """
        # 1. EXPLICIT FOLLOW-UP PATTERNS (Enhanced)
        explicit_patterns = [
            # Direct continuation requests
            "explain more", "tell me more", "elaborate", "can you elaborate",
            "more details", "more information", "continue", "go on", "keep going",
            
            # Affirmative + request
            "yes please", "yeah tell me more", "sure elaborate", "ok explain",
            "yes explain", "yeah elaborate", "ok continue",
            
            # Simple affirmatives (context-dependent)
            "yes", "yeah", "yep", "sure", "ok", "okay", "right", "exactly",
            
            # Clarification requests  
            "what do you mean", "can you clarify", "could you explain",
            "how so", "why is that", "what about", "such as", "like what",
            
            # Extension and expansion
            "what else", "anything else", "other examples", "more examples",
            "other ways", "alternatives", "what other", "also tell me",
            
            # Specific requests
            "for example", "give me an example", "show me", "demonstrate",
            
            # Length/format requests (common follow-ups)
            "in short", "briefly", "summarize", "can you explain it in short",
            "explain it briefly", "tell me in short", "give me a summary",
            "make it shorter", "condense it", "in simple terms",
            
            # Context-dependent pronouns and references
            "explain it", "tell me about it", "how does it work", "what is it",
            "show me how", "demonstrate it", "prove it", "verify it"
        ]
        
        # Check explicit patterns
        for pattern in explicit_patterns:
            if pattern in query_lower:
                logger.debug(f"Follow-up detected: explicit pattern '{pattern}'")
                return True
        
        # 2. CONTEXTUAL HEURISTICS
        if conversation_context:
            word_count = len(query_lower.split())
            
            # Short queries with pronouns (likely referring to previous context)
            pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them', 'which']
            has_pronouns = any(pronoun in query_lower.split() for pronoun in pronouns)
            
            if has_pronouns and word_count <= 20:
                logger.debug("Follow-up detected: pronouns + short query")
                return True
            
            # Very short queries with context (likely follow-ups)
            if word_count <= 5 and len(conversation_context) > 50:
                logger.debug("Follow-up detected: very short query with substantial context")
                return True
        
        # 3. QUESTION PATTERNS THAT BUILD ON CONTEXT
        continuation_patterns = [
            "how about", "what if", "could you", "would you", "can you also",
            "do you think", "is it possible", "what would happen", "how would"
        ]
        
        for pattern in continuation_patterns:
            if pattern in query_lower:
                logger.debug(f"Follow-up detected: continuation pattern '{pattern}'")
                return True
        
        return False
    
    def _two_layer_follow_up_detection(self, query_lower: str, conversation_context: str = None) -> bool:
        """
        Two-layer follow-up detection system:
        1. Layer 1: Fast pattern-based detection (existing logic)
        2. Layer 2: LLM-based detection using Claude 3.5 Haiku for uncertain cases
        """
        # LAYER 1: Fast pattern-based detection
        layer1_result = self._smart_follow_up_detection(query_lower, conversation_context)
        
        if layer1_result:
            logger.debug("Follow-up detected by Layer 1 (pattern-based)")
            return True
        
        # LAYER 2: LLM-based detection for uncertain cases
        # Only use LLM if we have conversation context and the query is ambiguous
        if conversation_context and len(conversation_context) > 50:
            # Check if query is ambiguous (short, contains pronouns, or unclear)
            word_count = len(query_lower.split())
            pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them', 'which', 'what', 'how']
            has_pronouns = any(pronoun in query_lower.split() for pronoun in pronouns)
            
            # Use LLM for ambiguous cases
            if (word_count <= 10) or has_pronouns or any(word in query_lower for word in ['explain', 'tell', 'show', 'clarify']):
                logger.debug("Query is ambiguous, using LLM for follow-up detection")
                return self._llm_follow_up_detection(query_lower, conversation_context)
        
        return False
    
    def _llm_follow_up_detection(self, query_lower: str, conversation_context: str) -> bool:
        """
        Use Claude 3.5 Haiku to detect if a query is a follow-up to the conversation context.
        """
        try:
            from core.classification_llm import classification_llm_service
            
            # Ensure the classification service is loaded
            if not classification_llm_service.is_loaded:
                classification_llm_service.load_model()
            
            # Create a specialized prompt for follow-up detection
            followup_prompt = f"""You are analyzing whether a user query is a follow-up question to a previous conversation about sustainability topics.

CONVERSATION CONTEXT:
{conversation_context[:1000]}...

CURRENT USER QUERY:
"{query_lower}"

TASK: Determine if the current query is a follow-up question that refers to, builds upon, or asks for clarification about the previous conversation context.

A follow-up question typically:
- References something mentioned in the context (using "it", "this", "that", etc.)
- Asks for more details, examples, or clarification
- Requests explanation of a specific aspect
- Asks "how", "what", "why" about topics from the context
- Is a short question that only makes sense with the previous context

Examples of follow-up questions:
- "Can you explain it in short?" (after a detailed explanation)
- "What about renewable energy?" (after discussing sustainability)
- "How does that work?" (after mentioning a process)
- "Tell me more about that" (after introducing a topic)

Examples of NEW questions (not follow-ups):
- "What is climate change?" (standalone question)
- "How do solar panels work?" (standalone question)
- "Tell me about ESG" (standalone question)

Answer with ONLY "YES" if it's a follow-up question, or "NO" if it's a new standalone question."""

            # Use the classification LLM service
            response = classification_llm_service.client.messages.create(
                model=classification_llm_service.model_name,
                max_tokens=5,
                temperature=0.0,
                messages=[{"role": "user", "content": followup_prompt}]
            )
            
            response_text = response.content[0].text.strip().upper()
            
            # Parse response
            if "YES" in response_text:
                logger.debug(f"LLM follow-up detection: YES - '{query_lower[:30]}...'")
                return True
            elif "NO" in response_text:
                logger.debug(f"LLM follow-up detection: NO - '{query_lower[:30]}...'")
                return False
            else:
                logger.warning(f"Unclear LLM follow-up response: '{response_text}', defaulting to NO")
                return False
                
        except Exception as e:
            logger.error(f"LLM follow-up detection failed: {e}, defaulting to NO")
            return False
    
    def _calculate_context_sustainability_score(self, context_lower: str) -> float:
        """Calculate a comprehensive sustainability score for conversation context."""
        sustainability_terms = [
            # Core environmental terms
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'green',
            'renewable', 'carbon', 'emission', 'esg', 'clean energy', 'solar', 'wind',
            'biodiversity', 'conservation', 'circular economy', 'waste reduction',
            
            # Extended sustainability vocabulary
            'eco-friendly', 'carbon neutral', 'net zero', 'decarbonization', 'greenhouse gas',
            'clean technology', 'green building', 'leed', 'sustainable development',
            'environmental impact', 'life cycle', 'carbon footprint', 'energy efficiency',
            'pollution', 'recycling', 'organic', 'renewable energy', 'climate change'
        ]
        
        score = 0.0
        term_matches = 0
        
        for term in sustainability_terms:
            if term in context_lower:
                score += 0.05  # Reduced individual weight
                term_matches += 1
        
        # Bonus for multiple term matches (indicates deeper sustainability focus)
        if term_matches >= 3:
            score += 0.1
        elif term_matches >= 2:
            score += 0.05
        
        return min(score, 1.0)
    
    def validate_output(self, response: str, input_query: str = None, input_classification_score: float = None) -> Tuple[bool, Optional[str]]:
        """
        Validate that the response is appropriate and sustainability-focused.
        
        Args:
            response: Generated response text
            input_query: Original user query for context (optional)
            input_classification_score: Score from input classification (optional)
            
        Returns:
            Tuple of (is_valid, rejection_reason)
        """
        # Use intelligent validator if available
        if self.output_validator:
            try:
                is_valid, rejection_reason, metadata = self.output_validator.validate_output_intelligent(
                    response, input_query, input_classification_score
                )
                logger.info(f"Intelligent validation: {metadata}")
                return is_valid, rejection_reason
            except Exception as e:
                logger.error(f"Intelligent validator failed: {e}, falling back to basic validation")
        
        # Fallback to enhanced basic validation
        return self._basic_output_validation(response, input_query, input_classification_score)
    
    def _basic_output_validation(self, response: str, input_query: str = None, input_classification_score: float = None) -> Tuple[bool, Optional[str]]:
        """Enhanced basic validation as fallback."""
        response_lower = response.lower()
        
        # CRITICAL FIX: For very high confidence inputs (like 0.734), be extremely lenient
        if input_classification_score and input_classification_score > 0.73:
            return True, None
        
        # Check for inappropriate content
        inappropriate_patterns = [
            r'\b(?:i cannot|i can\'t|i\'m not able to)\s+(?:help|assist)',
            r'\b(?:sorry, i don\'t|i don\'t know about)',
            r'\b(?:that\'s not my area|outside my expertise)',
            r'\b(?:i\'m not qualified|i don\'t have expertise)',
            r'\b(?:i can\'t answer|i cannot answer)',
        ]
        
        import re
        for pattern in inappropriate_patterns:
            if re.search(pattern, response_lower):
                logger.info(f"BASIC VALIDATOR: Rejecting due to inappropriate pattern: {pattern}")
                return False, "Response contains inappropriate refusal patterns"
        
        # Enhanced sustainability terms
        sustainability_terms = [
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'green',
            'renewable', 'carbon', 'emission', 'esg', 'clean energy', 'solar', 'wind',
            'biodiversity', 'conservation', 'circular economy', 'waste reduction', 'reporting',
            'disclosure', 'policy', 'policies', 'framework', 'standard', 'compliance',
            'governance', 'social', 'impact', 'footprint', 'assessment', 'certification'
        ]
        
        sustainability_mentions = sum(1 for term in sustainability_terms if term in response_lower)
        
        # Very lenient thresholds for high confidence inputs
        if input_classification_score and input_classification_score > 0.7:
            # High confidence input - extremely lenient
            min_terms_required = 0
        elif input_classification_score and input_classification_score > 0.6:
            # Medium confidence - very lenient
            min_terms_required = 0 if len(response) < 300 else 1
        else:
            # Standard validation
            min_terms_required = 1 if len(response) > 100 else 0
        
        if sustainability_mentions >= min_terms_required:
            return True, None
        
        # Check for technical sustainability terms
        technical_terms = [
            'scope 1', 'scope 2', 'scope 3', 'ghg protocol', 'sbti', 'tcfd', 'cdp', 'gri', 'sasb',
            'eu taxonomy', 'sfdr', 'life cycle assessment', 'carbon footprint', 'green bonds',
            'va00', 'policies', 'regulation', 'compliance', 'disclosure', 'framework'
        ]
        
        technical_found = [term for term in technical_terms if term in response_lower]
        if technical_found:
            return True, None
        
        # Absolute final decision - be very lenient for any decent confidence
        if input_classification_score and input_classification_score > 0.5:
            return True, None
        
        return False, f"Response lacks sustainability context (terms: {sustainability_mentions}, required: {min_terms_required})"
    
    def get_polite_refusal_message(self, reason: str) -> str:
        """Generate a polite refusal message for non-sustainability queries."""
        return "I'm a sustainability expert focused on environmental topics, climate action, and sustainable practices. I can help with questions about renewable energy, carbon reduction, ESG, circular economy, or other sustainability-related topics. What sustainability question can I help you with?"
