"""Query classification system for determining response type and length."""

import re
from typing import Dict, List, Tuple
from enum import Enum
from loguru import logger


class QueryType(Enum):
    """Types of queries that determine response strategy."""
    SIMPLE_DEFINITION = "simple_definition"
    COMPLEX_EXPLANATION = "complex_explanation"
    DETAILED_REQUEST = "detailed_request"
    FOLLOW_UP = "follow_up"
    COMPARISON = "comparison"
    HOW_TO = "how_to"
    LIST_REQUEST = "list_request"


class ResponseLength(Enum):
    """Expected response lengths."""
    SHORT = "short"  # 1-2 sentences + offer for more
    MEDIUM = "medium"  # 1-2 paragraphs + offer for more
    DETAILED = "detailed"  # Comprehensive explanation
    EXTENDED = "extended"  # Very detailed, multi-section response


class QueryClassifier:
    """Classifies queries to determine appropriate response type and length."""
    
    def __init__(self):
        # Patterns for detailed request detection
        self.detailed_request_patterns = [
            r'\b(?:explain|elaborate|detail|comprehensive|thorough|in-depth|extensive)\b.*\b(?:detail|depth)\b',
            r'\bexplain\s+(?:me\s+)?(?:that\s+)?in\s+detail\b',
            r'\bcan\s+you\s+elaborate\b',
            r'\btell\s+me\s+more\s+about\b',
            r'\bprovide\s+(?:a\s+)?(?:detailed|comprehensive|thorough)\b',
            r'\bgive\s+me\s+(?:a\s+)?(?:detailed|comprehensive|full)\b',
            r'\bbreak\s+down\b',
            r'\bcomprehensive\s+(?:analysis|explanation|overview)\b',
            r'\byes\s+explain\s+(?:that\s+)?(?:in\s+)?detail',
            r'\belaborate\s+(?:on\s+)?(?:that|it)\b',
            r'\bmore\s+detailed?\s+(?:information|explanation)\b',
            r'\bgo\s+into\s+(?:more\s+)?detail\b'
        ]
        
        # Patterns for simple definitions
        self.simple_definition_patterns = [
            r'^\s*what\s+is\s+\w+\s*\??\s*$',
            r'^\s*define\s+\w+\s*\??\s*$',
            r'^\s*meaning\s+of\s+\w+\s*\??\s*$',
            r'^\s*\w+\s+definition\s*\??\s*$'
        ]
        
        # Patterns for how-to questions
        self.how_to_patterns = [
            r'\bhow\s+to\s+',
            r'\bhow\s+can\s+(?:i|we|one)\s+',
            r'\bwhat\s+are\s+the\s+steps\s+to\s+',
            r'\bhow\s+do\s+(?:i|you|we)\s+'
        ]
        
        # Patterns for comparison questions
        self.comparison_patterns = [
            r'\b(?:difference|differences)\s+between\b',
            r'\bcompare\s+(?:and\s+contrast\s+)?\b',
            r'\bversus\b|\bvs\b',
            r'\brather\s+than\b',
            r'\binstead\s+of\b'
        ]
        
        # Patterns for list requests
        self.list_patterns = [
            r'\blist\s+(?:of\s+)?\w+',
            r'\bwhat\s+are\s+(?:the\s+)?(?:main\s+|key\s+|different\s+|various\s+)?\w+',
            r'\btypes\s+of\b',
            r'\bkinds\s+of\b',
            r'\bexamples\s+of\b'
        ]
        
        # Complex topics that usually need detailed responses
        self.complex_topics = [
            'carbon emission', 'climate change', 'sustainable development', 'circular economy',
            'renewable energy', 'biodiversity', 'ecosystem', 'greenhouse gas', 'carbon footprint',
            'sustainability framework', 'esg criteria', 'environmental impact', 'carbon neutral',
            'green infrastructure', 'waste management', 'energy efficiency', 'conservation',
            'pollution control', 'environmental policy'
        ]
        
        # Follow-up indicators
        self.follow_up_patterns = [
            r'\bmore\s+(?:about|on|regarding)\b',
            r'\bfurther\s+(?:information|details)\b',
            r'\bgo\s+deeper\b',
            r'\bexpand\s+on\b',
            r'\belaborate\s+further\b',
            r'^\s*yes\s+',
            r'^\s*yeah\s+',
            r'^\s*sure\s+',
            r'\bthat\s+in\s+detail\b',
            r'\bit\s+in\s+detail\b',
            r'\belaborate\s+(?:on\s+)?(?:that|it)\s*$'
        ]

    def classify_query(self, query: str, conversation_history: List[str] = None) -> Tuple[QueryType, ResponseLength]:
        """
        Classify a query to determine the appropriate response type and length.
        
        Args:
            query: The user's query
            conversation_history: Previous messages in the conversation
            
        Returns:
            Tuple of (QueryType, ResponseLength)
        """
        query_lower = query.lower().strip()
        conversation_context = ' '.join(conversation_history or []).lower()
        
        logger.debug(f"Classifying query: {query[:50]}...")
        
        # Check for explicit detailed requests
        if self._is_detailed_request(query_lower):
            logger.debug("Classified as detailed request")
            return QueryType.DETAILED_REQUEST, ResponseLength.DETAILED
        
        # Check for follow-up questions
        if conversation_history and self._is_follow_up(query_lower):
            # Check if follow-up is asking for details
            if self._is_detailed_request(query_lower):
                logger.debug("Classified as detailed follow-up")
                return QueryType.DETAILED_REQUEST, ResponseLength.DETAILED
            logger.debug("Classified as follow-up question")
            return QueryType.FOLLOW_UP, ResponseLength.MEDIUM
        
        # Check for simple definitions
        if self._is_simple_definition(query_lower):
            logger.debug("Classified as simple definition")
            return QueryType.SIMPLE_DEFINITION, ResponseLength.SHORT
        
        # Check for comparisons
        if self._is_comparison(query_lower):
            logger.debug("Classified as comparison")
            return QueryType.COMPARISON, ResponseLength.MEDIUM
        
        # Check for how-to questions
        if self._is_how_to(query_lower):
            logger.debug("Classified as how-to question")
            return QueryType.HOW_TO, ResponseLength.MEDIUM
        
        # Check for list requests
        if self._is_list_request(query_lower):
            logger.debug("Classified as list request")
            return QueryType.LIST_REQUEST, ResponseLength.MEDIUM
        
        # Check if topic is inherently complex
        if self._is_complex_topic(query_lower):
            logger.debug("Classified as complex explanation")
            return QueryType.COMPLEX_EXPLANATION, ResponseLength.MEDIUM
        
        # Default to simple explanation
        logger.debug("Classified as simple explanation")
        return QueryType.SIMPLE_DEFINITION, ResponseLength.SHORT

    def _is_detailed_request(self, query: str) -> bool:
        """Check if query explicitly requests detailed information."""
        for pattern in self.detailed_request_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_simple_definition(self, query: str) -> bool:
        """Check if query is asking for a simple definition."""
        for pattern in self.simple_definition_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_how_to(self, query: str) -> bool:
        """Check if query is a how-to question."""
        for pattern in self.how_to_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_comparison(self, query: str) -> bool:
        """Check if query is asking for a comparison."""
        for pattern in self.comparison_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_list_request(self, query: str) -> bool:
        """Check if query is requesting a list."""
        for pattern in self.list_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _is_complex_topic(self, query: str) -> bool:
        """Check if query involves inherently complex topics."""
        for topic in self.complex_topics:
            if topic in query:
                return True
        return False

    def _is_follow_up(self, query: str) -> bool:
        """Check if query is a follow-up question."""
        for pattern in self.follow_up_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        # Check for generic follow-up phrases
        follow_up_phrases = [
            'more about', 'tell me more', 'can you elaborate', 'go deeper',
            'explain further', 'more details', 'expand on', 'elaborate',
            'that in detail', 'it in detail'
        ]
        
        for phrase in follow_up_phrases:
            if phrase in query:
                return True
        
        # Check for simple affirmative responses that might be follow-ups
        simple_affirmatives = ['yes', 'yeah', 'sure', 'ok', 'okay', 'yep']
        words = query.strip().split()
        if len(words) >= 2 and words[0].lower() in simple_affirmatives:
            return True
                
        return False

    def get_response_guidelines(self, query_type: QueryType, response_length: ResponseLength) -> Dict[str, str]:
        """Get response guidelines based on classification."""
        guidelines = {
            "length": response_length.value,
            "style": "",
            "structure": "",
            "ending": ""
        }
        
        if response_length == ResponseLength.SHORT:
            guidelines.update({
                "style": "concise and direct",
                "structure": "1-2 sentences with key definition or concept",
                "ending": "I can provide more detailed information about [topic] if you would like to explore this further."
            })
        
        elif response_length == ResponseLength.MEDIUM:
            guidelines.update({
                "style": "informative but accessible",
                "structure": "1-2 paragraphs with main points and examples",
                "ending": "Would you like me to elaborate on any specific aspect of [topic]?"
            })
        
        elif response_length == ResponseLength.DETAILED:
            guidelines.update({
                "style": "comprehensive and educational",
                "structure": "Multiple paragraphs with sections, examples, and implementation details",
                "ending": "I can provide more specific information about any particular aspect that interests you."
            })
        
        return guidelines
