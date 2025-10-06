"""
Intelligent Output Validator using semantic similarity and context awareness.
This provides a more robust long-term solution for output validation.
"""

import re
from typing import Tuple, Optional, Dict, Any
from loguru import logger
from sentence_transformers import SentenceTransformer

class IntelligentOutputValidator:
    """Advanced output validator using semantic analysis and context awareness."""
    
    def __init__(self):
        """Initialize the intelligent validator."""
        # Lazy loading - don't load model at startup
        self.model = None
        self._model_loaded = False
        
        # Define sustainability themes (embeddings will be computed lazily)
        self.sustainability_themes = [
                "environmental protection and conservation",
                "climate change and global warming",
                "renewable energy and clean technology", 
                "carbon emissions and climate action",
                "sustainable business practices",
                "ESG reporting and compliance",
                "circular economy and waste reduction",
                "biodiversity and ecosystem protection",
                "sustainable development goals",
                "green finance and sustainable investing",
                "corporate sustainability reporting",
                "environmental policy and governance"
            ]
        
        # Embeddings will be computed lazily when first needed
        self.theme_embeddings = None
        
        logger.info("Intelligent output validator initialized (lazy loading enabled)")
    
    def _ensure_model_loaded(self):
        """Lazy load the embedding model and compute embeddings if not already loaded."""
        if not self._model_loaded:
            try:
                logger.info("Loading embedding model for intelligent output validator...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.theme_embeddings = self.model.encode(self.sustainability_themes)
                self._model_loaded = True
                logger.info("Intelligent output validator model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load intelligent validator model: {e}")
                self.model = None
    
    def validate_output_intelligent(
        self, 
        response: str, 
        input_query: str = None,
        input_classification_score: float = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Intelligently validate output using semantic analysis and context.
        
        Args:
            response: The generated response text
            input_query: Original user query for context
            input_classification_score: Score from input classification
            
        Returns:
            Tuple of (is_valid, rejection_reason, validation_metadata)
        """
        
        validation_metadata = {
            "method": "intelligent_semantic",
            "input_score": input_classification_score,
            "response_length": len(response)
        }
        
        
        # Step 1: Basic inappropriate content check
        if self._contains_inappropriate_content(response):
            return False, "Response contains inappropriate content", validation_metadata
        
        # Step 2: If embeddings are not available, fall back to enhanced keyword approach
        if self.model is None:
            return self._fallback_validation(response, input_query, validation_metadata)
        
        # Step 3: Semantic similarity analysis
        semantic_score = self._calculate_semantic_sustainability_score(response)
        validation_metadata["semantic_score"] = semantic_score
        
        # Step 4: Context-aware thresholds
        threshold = self._get_adaptive_threshold(input_classification_score, len(response))
        validation_metadata["threshold_used"] = threshold
        
        # Step 5: Make validation decision
        if semantic_score >= threshold:
            validation_metadata["decision_reason"] = "semantic_similarity_passed"
            return True, None, validation_metadata
        
        # Step 6: Secondary checks for edge cases
        if input_classification_score and input_classification_score > 0.7:
            # High confidence input classification - be VERY lenient
            if semantic_score >= (threshold * 0.5):  # 50% more lenient
                validation_metadata["decision_reason"] = "high_input_confidence_override"
                logger.info(f"Validation override: High input confidence ({input_classification_score:.3f}) with semantic score {semantic_score:.3f}")
                return True, None, validation_metadata
            
            # For VERY high confidence (>0.73), be even more lenient
            if input_classification_score > 0.73 and semantic_score >= 0.1:
                validation_metadata["decision_reason"] = "very_high_input_confidence_override"
                logger.info(f"Validation override: VERY high input confidence ({input_classification_score:.3f}) with minimal semantic score {semantic_score:.3f}")
                return True, None, validation_metadata
        
        # Step 7: Check for technical sustainability terms that might not have high semantic similarity
        if self._contains_technical_sustainability_terms(response):
            validation_metadata["decision_reason"] = "technical_terms_detected"
            return True, None, validation_metadata
        
        # Final rejection
        validation_metadata["decision_reason"] = "semantic_similarity_failed"
        return False, f"Response semantic score ({semantic_score:.3f}) below threshold ({threshold:.3f})", validation_metadata
    
    def _calculate_semantic_sustainability_score(self, response: str) -> float:
        """Calculate semantic similarity to sustainability themes."""
        try:
            # Ensure model is loaded (lazy loading)
            self._ensure_model_loaded()
            
            if not self.model:
                return 0.0  # Return neutral score if model failed to load
                
            response_embedding = self.model.encode([response])
            
            # Calculate cosine similarity manually without sklearn
            import numpy as np
            
            # Normalize embeddings
            response_norm = response_embedding / np.linalg.norm(response_embedding)
            theme_norms = self.theme_embeddings / np.linalg.norm(self.theme_embeddings, axis=1, keepdims=True)
            
            # Calculate cosine similarities
            similarities = np.dot(response_norm, theme_norms.T)[0]
            
            # Return the maximum similarity (best match)
            max_similarity = float(max(similarities))
            logger.debug(f"Response semantic sustainability score: {max_similarity:.3f}")
            return max_similarity
            
        except Exception as e:
            logger.error(f"Error calculating semantic score: {e}")
            return 0.0
    
    def _get_adaptive_threshold(self, input_score: float = None, response_length: int = 0) -> float:
        """Get adaptive threshold based on context."""
        base_threshold = 0.3  # Conservative baseline
        
        # Adjust based on input classification confidence
        if input_score:
            if input_score > 0.8:
                base_threshold -= 0.1  # More lenient for high-confidence inputs
            elif input_score > 0.6:
                base_threshold -= 0.05  # Slightly more lenient
        
        # Adjust based on response length (longer responses might be more diluted)
        if response_length > 1000:
            base_threshold -= 0.05
        elif response_length < 100:
            base_threshold += 0.1  # Stricter for very short responses
        
        return max(0.1, min(0.6, base_threshold))  # Keep within reasonable bounds
    
    def _contains_inappropriate_content(self, response: str) -> bool:
        """Check for clearly inappropriate content patterns."""
        response_lower = response.lower()
        
        inappropriate_patterns = [
            r'\b(?:i cannot|i can\'t|i\'m not able to)\s+(?:help|assist)',
            r'\b(?:sorry, i don\'t|i don\'t know about)',
            r'\b(?:that\'s not my area|outside my expertise)',
            r'\b(?:i\'m not qualified|i don\'t have expertise)',
            r'\b(?:i can\'t answer|i cannot answer)',
            r'\b(?:i\'m only|only sustainability|only environmental)',
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, response_lower):
                return True
        return False
    
    def _contains_technical_sustainability_terms(self, response: str) -> bool:
        """Check for technical sustainability terms that might not have high semantic similarity."""
        response_lower = response.lower()
        
        technical_terms = [
            'scope 1', 'scope 2', 'scope 3', 'ghg protocol', 'sbti', 'science based targets',
            'tcfd', 'task force', 'cdp', 'carbon disclosure', 'gri', 'sasb', 'issb',
            'eu taxonomy', 'sfdr', 'article 8', 'article 9', 'dnsh', 'pai',
            'life cycle assessment', 'lca', 'carbon footprint', 'water footprint',
            'material topics', 'double materiality', 'impact materiality',
            'green bonds', 'sustainability-linked', 'transition finance',
            'nature-based solutions', 'biodiversity credits', 'natural capital'
        ]
        
        return any(term in response_lower for term in technical_terms)
    
    def _fallback_validation(
        self, 
        response: str, 
        input_query: str = None, 
        validation_metadata: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Enhanced fallback validation when embeddings are not available."""
        response_lower = response.lower()
        
        # Enhanced keyword list
        sustainability_keywords = [
            'sustainability', 'sustainable', 'environment', 'environmental', 'climate', 'green',
            'renewable', 'carbon', 'emission', 'esg', 'clean energy', 'solar', 'wind',
            'biodiversity', 'conservation', 'circular economy', 'waste reduction', 'reporting',
            'disclosure', 'policy', 'policies', 'framework', 'standard', 'compliance',
            'governance', 'social', 'impact', 'footprint', 'assessment', 'certification'
        ]
        
        keyword_count = sum(1 for keyword in sustainability_keywords if keyword in response_lower)
        validation_metadata["method"] = "enhanced_keyword_fallback"
        validation_metadata["keyword_count"] = keyword_count
        
        # More nuanced keyword-based validation
        if len(response) > 200:
            min_keywords = 2
        elif len(response) > 100:
            min_keywords = 1
        else:
            min_keywords = 1
        
        if keyword_count >= min_keywords:
            return True, None, validation_metadata
        
        # Check for technical terms as last resort
        if self._contains_technical_sustainability_terms(response):
            validation_metadata["technical_terms_found"] = True
            return True, None, validation_metadata
        
        return False, f"Response lacks sufficient sustainability context (keywords: {keyword_count}, required: {min_keywords})", validation_metadata
