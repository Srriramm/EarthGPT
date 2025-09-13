"""Sustainability-focused guardrails implementation."""

import re
from typing import List, Tuple, Optional
from loguru import logger
from models.schemas import GuardrailCheck
from config import settings


class SustainabilityGuardrails:
    """Guardrails system to ensure only sustainability-related queries are processed."""
    
    def __init__(self):
        self.sustainability_keywords = set(
            keyword.lower() for keyword in settings.sustainability_keywords
        )
        self.negative_patterns = [
            r'\b(?:politics|political)\b',
            r'\b(?:sports|football|basketball|soccer)\b',
            r'\b(?:entertainment|movie|music|celebrity)\b',
            r'\b(?:cooking|recipe|food)\b',
            r'\b(?:dating|relationship|love)\b',
            r'\b(?:gaming|video game|playstation|xbox)\b',
            r'\b(?:fashion|clothing|shopping)\b',
            r'\b(?:travel|vacation|tourism)\b',
            r'\b(?:health|medical|doctor|medicine)\b',
            # More specific finance patterns that exclude sustainability-related finance
            r'\b(?:stock market|day trading|forex|cryptocurrency|bitcoin|ethereum)\b',
            r'\b(?:personal finance|retirement planning|tax advice|insurance)\b',
            r'\b(?:technology|programming|coding|software)\b',
            r'\b(?:education|school|university|student)\b',
        ]
        
        # Compile regex patterns for efficiency
        self.negative_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.negative_patterns
        ]
        
        logger.info(f"Guardrails initialized with {len(self.sustainability_keywords)} sustainability keywords")
    
    def check_sustainability_relevance(self, query: str) -> GuardrailCheck:
        """
        Check if the query is sustainability-related.
        
        Args:
            query: User input query
            
        Returns:
            GuardrailCheck with validation results
        """
        query_lower = query.lower()
        
        # Allow follow-up phrases that are context-dependent
        follow_up_phrases = [
            "explain more", "more details", "tell me more", "elaborate",
            "can you tell more", "can you explain more", "can you elaborate",
            "yes", "y", "yeah", "yep", "sure", "ok", "okay",
            "what else", "anything else", "more information"
        ]
        
        if any(phrase in query_lower for phrase in follow_up_phrases):
            return GuardrailCheck(
                is_sustainability_related=True,
                confidence_score=0.8,
                detected_keywords=["follow-up"],
                rejection_reason=None
            )
        
        # Check for negative patterns first
        for pattern in self.negative_regex:
            if pattern.search(query):
                return GuardrailCheck(
                    is_sustainability_related=False,
                    confidence_score=0.0,
                    detected_keywords=[],
                    rejection_reason=f"Query appears to be about non-sustainability topics"
                )
        
        # Check for sustainability keywords
        detected_keywords = []
        keyword_matches = 0
        
        for keyword in self.sustainability_keywords:
            if keyword in query_lower:
                detected_keywords.append(keyword)
                keyword_matches += 1
        
        # Calculate confidence score
        confidence_score = min(keyword_matches / 3.0, 1.0)  # Normalize to 0-1
        
        # Determine if query is sustainability-related
        is_sustainability_related = (
            keyword_matches > 0 or 
            self._check_contextual_sustainability(query_lower)
        )
        
        if not is_sustainability_related:
            return GuardrailCheck(
                is_sustainability_related=False,
                confidence_score=confidence_score,
                detected_keywords=detected_keywords,
                rejection_reason="Query does not appear to be related to sustainability topics"
            )
        
        return GuardrailCheck(
            is_sustainability_related=True,
            confidence_score=confidence_score,
            detected_keywords=detected_keywords,
            rejection_reason=None
        )
    
    def _check_contextual_sustainability(self, query_lower: str) -> bool:
        """Check for contextual sustainability indicators with advanced semantic understanding."""
        
        # Climate agreements and international frameworks
        climate_agreement_patterns = [
            r'\b(?:paris\s+agreement|paris\s+accord|paris\s+climate\s+agreement)\b',
            r'\b(?:kyoto\s+protocol|kyoto\s+agreement)\b',
            r'\b(?:cop\s*\d+|cop\s+\d+|conference\s+of\s+parties)\b',
            r'\b(?:unfccc|united\s+nations\s+framework\s+convention)\b',
            r'\b(?:ipcc|intergovernmental\s+panel)\b',
            r'\b(?:climate\s+(?:summit|conference|treaty|accord|agreement|negotiation|diplomacy))\b',
            r'\b(?:international\s+climate|global\s+climate)\s+(?:agreement|accord|treaty|policy)\b',
            r'\b(?:montreal\s+protocol|rio\s+declaration|agenda\s+2030)\b',
            r'\b(?:sustainable\s+development\s+goals|sdgs)\b',
        ]
        
        # Environmental governance and policy
        governance_patterns = [
            r'\b(?:environmental|climate)\s+(?:policy|law|regulation|governance|treaty)\b',
            r'\b(?:green\s+new\s+deal|green\s+recovery|green\s+transition)\b',
            r'\b(?:carbon\s+(?:pricing|tax|trading|market|offset|credit))\b',
            r'\b(?:emissions?\s+(?:trading|reduction|targets?))\b',
            r'\b(?:net\s+zero|carbon\s+neutral|decarboni[sz]ation)\b',
        ]
        
        # Environmental topics without obvious keywords
        environmental_topic_patterns = [
            r'\b(?:significance|importance|impact|role)\s+of.*(?:2015|agreement|accord|protocol|treaty)\b',
            r'\b(?:explain|describe|discuss).*(?:2015|agreement|accord|international)\b',
            r'\b(?:how|why|what).*(?:countries|nations|global|international).*(?:cooperat|collaborat|work\s+together)\b',
            r'\b(?:global|international|worldwide)\s+(?:cooperation|collaboration|effort|initiative)\b',
            r'\b(?:temperature|warming|degrees?|1\.5|2\.0|celsius|fahrenheit)\s+(?:limit|target|goal|threshold)\b',
            r'\b(?:fossil\s+fuel|oil|coal|gas|petroleum)\s+(?:reduction|phase\s+out|transition)\b',
        ]
        
        # Scientific and technical sustainability terms
        technical_patterns = [
            r'\b(?:greenhouse\s+gas|ghg|co2|methane|nitrous\s+oxide)\b',
            r'\b(?:renewable\s+energy|clean\s+energy|solar|wind|hydro|geothermal)\b',
            r'\b(?:energy\s+(?:efficiency|transition|storage|security))\b',
            r'\b(?:smart\s+grid|microgrid|electric\s+vehicle|ev)\b',
            r'\b(?:organic|regenerative|sustainable)\s+(?:farming|agriculture)\b',
            r'\b(?:green\s+(?:building|infrastructure|technology|finance))\b',
            r'\b(?:circular\s+economy|waste\s+(?:reduction|management|recycling))\b',
            r'\b(?:biodiversity|ecosystem|conservation|deforestation|reforestation)\b',
        ]
        
        # Questions about sustainability without explicit keywords
        implicit_sustainability_patterns = [
            r'\b(?:how|why|what).*(?:reduce|minimize|decrease|lower).*(?:impact|footprint|consumption|usage)\b',
            r'\b(?:alternative|solution|way|method|approach).*(?:protect|save|preserve|conserve)\b',
            r'\b(?:future|next\s+generation|long[- ]?term|sustainable)\s+(?:development|growth|progress)\b',
            r'\b(?:responsible|ethical|conscious)\s+(?:business|investment|consumption|production)\b',
            r'\b(?:earth|planet|world|global|environment)\s+(?:protection|preservation|conservation|health)\b',
        ]
        
        # Organizations, people, and events (sustainability context)
        entity_patterns = [
            r'\b(?:greta\s+thunberg|al\s+gore|ban\s+ki[- ]?moon)\b',
            r'\b(?:wwf|greenpeace|unep|iea|irena|world\s+bank)\b',
            r'\b(?:green\s+climate\s+fund|global\s+environment\s+facility)\b',
            r'\b(?:earth\s+day|world\s+environment\s+day|climate\s+week)\b',
            r'\b(?:extinction\s+rebellion|fridays\s+for\s+future|climate\s+strike)\b',
        ]
        
        # Combine all pattern groups
        all_patterns = (
            climate_agreement_patterns + governance_patterns + 
            environmental_topic_patterns + technical_patterns + 
            implicit_sustainability_patterns + entity_patterns
        )
        
        # Check for any pattern match
        for pattern in all_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Contextual sustainability match found: {pattern}")
                return True
        
        # Additional semantic checks
        return self._check_semantic_sustainability(query_lower)
    
    def _check_semantic_sustainability(self, query_lower: str) -> bool:
        """Advanced semantic checking for sustainability relevance."""
        
        # Check for questions about agreements, policies, or frameworks with dates
        if re.search(r'\b(?:agreement|accord|treaty|protocol|framework|policy).*(?:20\d{2}|19\d{2})\b', query_lower):
            # If it mentions an agreement with a year, likely environmental/climate related
            return True
        
        # Check for environmental impact questions
        environmental_impact_words = ['impact', 'effect', 'consequence', 'result', 'outcome', 'influence']
        environmental_context_words = ['environment', 'planet', 'earth', 'global', 'world', 'nature', 'ecosystem']
        
        if (any(word in query_lower for word in environmental_impact_words) and 
            any(word in query_lower for word in environmental_context_words)):
            return True
        
        # Check for action/solution oriented questions about global issues
        action_words = ['how to', 'ways to', 'methods to', 'solution', 'approach', 'strategy', 'plan']
        global_issue_words = ['global', 'worldwide', 'international', 'universal', 'planetary']
        
        if (any(phrase in query_lower for phrase in action_words) and 
            any(word in query_lower for word in global_issue_words)):
            return True
            
        # Check for questions about cooperation, collaboration on global issues
        cooperation_words = ['cooperation', 'collaboration', 'partnership', 'alliance', 'joint', 'collective']
        if any(word in query_lower for word in cooperation_words):
            return True
        
        return False
    
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
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, response_lower):
                return False, "Response contains inappropriate refusal patterns"
        
        # Check for sustainability relevance in response
        sustainability_mentions = sum(
            1 for keyword in self.sustainability_keywords 
            if keyword in response_lower
        )
        
        if sustainability_mentions == 0 and len(response) > 100:
            return False, "Response lacks sustainability context"
        
        return True, None
    
    def get_polite_refusal_message(self, reason: str) -> str:
        """Generate a polite refusal message for non-sustainability queries."""
        refusal_messages = [
            "I'm a sustainability expert assistant focused on environmental topics, climate action, and sustainable practices. I'd be happy to help with questions about renewable energy, carbon reduction, ESG, or other sustainability-related topics!",
            "I specialize in sustainability and environmental topics. Please ask me about climate change, renewable energy, sustainable development, or other environmental subjects, and I'll be glad to help!",
            "As a sustainability-focused assistant, I can help with questions about environmental protection, clean energy, carbon footprints, and sustainable practices. What sustainability topic would you like to explore?"
        ]
        
        # Return a random polite message (in production, you might want to rotate these)
        return refusal_messages[0]
