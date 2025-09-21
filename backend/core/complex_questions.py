"""Progressive summarization system for handling complex questions."""

import re
from typing import Tuple, List, Dict, Any
from loguru import logger
from models.schemas import Message, MessageRole


class ComplexQuestionDetector:
    """Detects complex questions that require progressive summarization."""
    
    def __init__(self):
        # Keywords that indicate complex questions
        self.complex_keywords = [
            "explain", "analyze", "describe", "detail", "comprehensive",
            "thorough", "in-depth", "elaborate", "break down", "compare",
            "contrast", "evaluate", "assess", "investigate", "examine"
        ]
        
        # Question patterns that suggest complexity
        self.complex_patterns = [
            r'\b(?:how\s+does|how\s+do|how\s+can|how\s+to)\b.*\b(?:work|function|operate|implement)\b',
            r'\b(?:what\s+are\s+the\s+)(?:benefits|advantages|disadvantages|impacts|effects)\b',
            r'\b(?:compare\s+and\s+contrast|differences\s+between|similarities\s+between)\b',
            r'\b(?:step\s+by\s+step|process|methodology|approach)\b',
            r'\b(?:best\s+practices|recommendations|strategies|solutions)\b',
            r'\b(?:pros\s+and\s+cons|advantages\s+and\s+disadvantages)\b',
            r'\b(?:comprehensive|detailed|thorough|in-depth)\b',
            r'\b(?:multiple|various|different|several)\b.*\b(?:ways|methods|approaches|options|strategies)\b'
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.complex_patterns]
        
        logger.info("Complex question detector initialized")
    
    def is_complex_question(self, query: str) -> Tuple[bool, float, List[str]]:
        """
        Determine if a question is complex and requires progressive summarization.
        
        Args:
            query: User query text
            
        Returns:
            Tuple of (is_complex, complexity_score, detected_indicators)
        """
        query_lower = query.lower()
        detected_indicators = []
        complexity_score = 0.0
        
        # Check for complex keywords
        keyword_matches = 0
        for keyword in self.complex_keywords:
            if keyword in query_lower:
                detected_indicators.append(f"keyword: {keyword}")
                keyword_matches += 1
        
        # Check for complex patterns
        pattern_matches = 0
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(query_lower):
                detected_indicators.append(f"pattern: {self.complex_patterns[i]}")
                pattern_matches += 1
        
        # Check query length (longer queries tend to be more complex)
        length_score = min(len(query.split()) / 20.0, 1.0)  # Normalize to 0-1
        if length_score > 0.5:
            detected_indicators.append("length: long query")
        
        # Calculate overall complexity score
        complexity_score = (
            (keyword_matches * 0.3) +
            (pattern_matches * 0.4) +
            (length_score * 0.3)
        )
        
        # Determine if question is complex
        is_complex = (
            keyword_matches > 0 or 
            pattern_matches > 0 or 
            length_score > 0.7 or
            complexity_score > 0.4
        )
        
        logger.debug(f"Complexity analysis: score={complexity_score:.2f}, complex={is_complex}")
        return is_complex, complexity_score, detected_indicators


class ProgressiveSummarizer:
    """Handles progressive summarization for complex questions."""
    
    def __init__(self):
        self.summary_templates = {
            "renewable_energy": "Renewable energy sources like solar, wind, and hydro provide clean alternatives to fossil fuels, reducing carbon emissions and environmental impact.",
            "carbon_footprint": "Carbon footprint measures total greenhouse gas emissions from activities, and can be reduced through energy efficiency, sustainable transportation, and waste reduction.",
            "esg": "ESG (Environmental, Social, Governance) criteria evaluate sustainability performance across environmental impact, social responsibility, and corporate governance practices.",
            "circular_economy": "The circular economy eliminates waste by designing products for longevity, reusing materials, and recycling components in closed-loop systems.",
            "biodiversity": "Biodiversity conservation protects ecosystem health through habitat preservation, pollution reduction, and sustainable land-use practices.",
            "climate_change": "Climate change mitigation reduces emissions through renewable energy and efficiency, while adaptation prepares communities for climate impacts."
        }
        
        logger.info("Progressive summarizer initialized")
    
    def generate_summary(self, query: str, context: Dict[str, Any]) -> str:
        """
        Generate a concise summary for a complex question.
        
        Args:
            query: User query
            context: Retrieved context and conversation history
            
        Returns:
            Concise summary response
        """
        # Extract key topics from context
        topics = self._extract_topics_from_context(context)
        
        # Generate topic-specific summary
        if topics:
            primary_topic = topics[0]
            if primary_topic in self.summary_templates:
                base_summary = self.summary_templates[primary_topic]
            else:
                base_summary = self._generate_generic_summary(query, context)
        else:
            base_summary = self._generate_generic_summary(query, context)
        
        # Add context from conversation if available (only if relevant)
        conversation_context = self._extract_conversation_context(context)
        if conversation_context and conversation_context != "about":
            base_summary += f" Building on our previous discussion about {conversation_context}."
        
        # Only add detailed explanation offer for truly complex questions
        if len(query.split()) > 15 or any(word in query.lower() for word in ["comprehensive", "detailed", "thorough", "in-depth"]):
            base_summary += " Would you like me to provide a more detailed explanation with specific examples and implementation strategies?"
        
        return base_summary
    
    def _extract_topics_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Extract relevant topics from the context."""
        topics = []
        
        # Extract from relevant documents
        if "relevant_documents" in context:
            for doc in context["relevant_documents"]:
                if "metadata" in doc and "topic" in doc["metadata"]:
                    topics.append(doc["metadata"]["topic"])
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_conversation_context(self, context: Dict[str, Any]) -> str:
        """Extract relevant context from conversation history."""
        if "conversation_history" in context:
            history = context["conversation_history"]
            if len(history) >= 2:
                # Get the last user question
                for msg in reversed(history):
                    # Handle both Message objects and dictionaries
                    if hasattr(msg, 'role'):
                        role = msg.role
                        content = msg.content
                    else:
                        role = msg.get('role')
                        content = msg.get('content')
                    
                    if role == MessageRole.USER:
                        # Extract meaningful sustainability terms, not generic words
                        words = content.lower().split()
                        sustainability_terms = [
                            word for word in words 
                            if len(word) > 4 and word.isalpha() and 
                            word in ['sustainability', 'renewable', 'carbon', 'climate', 'environment', 
                                   'sustainable', 'energy', 'emissions', 'biodiversity', 'conservation',
                                   'circular', 'economy', 'waste', 'recycling', 'green', 'esg']
                        ]
                        if sustainability_terms:
                            return sustainability_terms[0]  # Return first sustainability term
        return ""
    
    def _generate_generic_summary(self, query: str, context: Dict[str, Any]) -> str:
        """Generate a generic summary when no specific template matches."""
        # Extract key concepts from the query
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["renewable", "solar", "wind", "hydro"]):
            return "Renewable energy technologies like solar, wind, and hydroelectric power provide clean alternatives to fossil fuels, reducing carbon emissions and environmental impact."
        elif any(word in query_lower for word in ["carbon", "emission", "footprint"]):
            return "Carbon emissions are greenhouse gases released into the atmosphere, primarily from burning fossil fuels. Carbon footprint measures total emissions from activities and can be reduced through energy efficiency and sustainable practices."
        elif any(word in query_lower for word in ["esg", "sustainable", "governance"]):
            return "ESG (Environmental, Social, and Governance) criteria evaluate companies' sustainability performance, focusing on environmental impact, social responsibility, and corporate governance practices."
        elif any(word in query_lower for word in ["circular", "waste", "recycle"]):
            return "The circular economy aims to eliminate waste through designing products for longevity, reusing materials, and recycling components to create closed-loop systems."
        elif any(word in query_lower for word in ["biodiversity", "conservation", "ecosystem"]):
            return "Biodiversity conservation focuses on protecting ecosystems, species diversity, and natural habitats to maintain ecological balance and environmental health."
        elif any(word in query_lower for word in ["climate", "warming", "mitigation"]):
            return "Climate change refers to long-term shifts in global temperatures caused by human activities. Mitigation strategies include reducing emissions through renewable energy and sustainable practices."
        elif any(word in query_lower for word in ["sustainability", "sustainable"]):
            return "Sustainability refers to meeting present needs without compromising future generations' ability to meet their own needs, encompassing environmental, social, and economic dimensions."
        else:
            return "This is a sustainability-related topic that requires detailed explanation."
    
    def should_offer_detailed_explanation(self, query: str, complexity_score: float) -> bool:
        """Determine if a detailed explanation should be offered."""
        return complexity_score > 0.3 or len(query.split()) > 10


class ComplexQuestionHandler:
    """Main handler for complex question processing."""
    
    def __init__(self):
        self.detector = ComplexQuestionDetector()
        self.summarizer = ProgressiveSummarizer()
        logger.info("Complex question handler initialized")
    
    def process_query(self, query: str, context: Dict[str, Any]) -> Tuple[str, bool, bool]:
        """
        Process a query and determine if it needs progressive summarization.
        
        Args:
            query: User query
            context: Retrieved context and conversation history
            
        Returns:
            Tuple of (response, is_summary, can_request_detailed)
        """
        # Detect if question is complex
        is_complex, complexity_score, indicators = self.detector.is_complex_question(query)
        
        if is_complex:
            # Generate summary response
            summary_response = self.summarizer.generate_summary(query, context)
            can_request_detailed = self.summarizer.should_offer_detailed_explanation(query, complexity_score)
            
            logger.info(f"Generated summary for complex question (complexity: {complexity_score:.2f})")
            return summary_response, True, can_request_detailed
        else:
            # Regular response (will be handled by main LLM)
            return "", False, False
    
    def handle_complex_question(self, query: str, context: Dict[str, Any], classification: Tuple = None) -> str:
        """
        Handle complex questions with progressive summarization.
        
        Args:
            query: User query
            context: Retrieved context and conversation history
            classification: Query classification tuple (for compatibility)
            
        Returns:
            Response string or None if not a complex question
        """
        # Detect if question is complex
        is_complex, complexity_score, indicators = self.detector.is_complex_question(query)
        
        if is_complex:
            # Generate summary response
            summary_response = self.summarizer.generate_summary(query, context)
            logger.info(f"Generated summary for complex question (complexity: {complexity_score:.2f})")
            return summary_response
        else:
            # Not a complex question, return None to let main LLM handle it
            return None