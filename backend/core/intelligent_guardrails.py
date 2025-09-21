"""Intelligent guardrails system using semantic understanding."""

import re
from typing import List, Tuple, Optional, Dict
from loguru import logger
from models.schemas import GuardrailCheck
from config import settings


class IntelligentGuardrails:
    """Intelligent guardrails system that understands sustainability context semantically."""
    
    def __init__(self):
        self.sustainability_keywords = set(
            keyword.lower() for keyword in settings.sustainability_keywords
        )
        
        # Core sustainability concepts with weights
        self.sustainability_concepts = {
            # High-weight core concepts
            'environment': 0.8, 'environmental': 0.8, 'climate': 0.8, 'sustainability': 0.9, 'sustainable': 0.9,
            'green': 0.7, 'eco': 0.7, 'carbon': 0.8, 'emission': 0.8, 'renewable': 0.9, 'clean energy': 0.9,
            'biodiversity': 0.8, 'conservation': 0.8, 'pollution': 0.7, 'waste': 0.7, 'recycling': 0.7,
            'esg': 0.8, 'circular economy': 0.8, 'circular': 0.6, 'net zero': 0.8, 'carbon neutral': 0.8,
            # Energy and power systems
            'solar': 0.8, 'wind': 0.8, 'hydro': 0.8, 'geothermal': 0.8, 'fossil fuel': 0.6, 'coal': 0.6, 'oil': 0.6,
            'energy security': 0.7, 'energy efficiency': 0.8, 'energy transition': 0.8, 'energy storage': 0.7,
            'power': 0.5, 'electricity': 0.5, 'grid': 0.5,
            # Finance and investment
            'green finance': 0.8, 'green bonds': 0.8, 'sustainable finance': 0.8, 'climate finance': 0.8,
            # Infrastructure and technology
            'green infrastructure': 0.8, 'sustainable agriculture': 0.8, 'green building': 0.8,
            'sustainable transport': 0.8, 'clean technology': 0.8, 'green technology': 0.8,
            # Environmental protection
            'air pollution': 0.8, 'greenhouse gas': 0.8, 'global warming': 0.8, 'climate change': 0.9,
            'public health': 0.6, 'health': 0.4, 'quality of life': 0.5,
            
            # Medium-weight concepts
            'impact': 0.6, 'effect': 0.6, 'consequence': 0.6, 'footprint': 0.7, 'reduction': 0.6,
            'mitigation': 0.7, 'adaptation': 0.7, 'resilience': 0.6, 'protection': 0.6,
            'preservation': 0.6, 'restoration': 0.6, 'efficiency': 0.5, 'optimization': 0.5,
            # Economic sustainability
            'economic growth': 0.5, 'green jobs': 0.7, 'innovation': 0.5, 'entrepreneurship': 0.4,
            'developing countries': 0.5, 'rural areas': 0.4, 'microgrids': 0.6, 'decentralized': 0.5,
            'technology': 0.3, 'cost': 0.3, 'investment': 0.4, 'infrastructure': 0.4,
            # Policy and governance
            'policy': 0.5, 'regulation': 0.5, 'incentive': 0.5, 'subsidy': 0.5, 'carbon pricing': 0.8,
            'government': 0.3, 'industry': 0.3, 'business': 0.3, 'household': 0.3,
            
            # Action-oriented terms
            'reduce': 0.5, 'minimize': 0.5, 'optimize': 0.5, 'improve': 0.4, 'enhance': 0.4,
            'implement': 0.4, 'develop': 0.4, 'create': 0.3, 'build': 0.3, 'design': 0.3,
            'manage': 0.3, 'monitor': 0.3, 'track': 0.3, 'measure': 0.3
        }
        
        # Non-sustainability topics with EXTREME negative weights
        self.non_sustainability_topics = {
            'poker': -1.5, 'gambling': -1.5, 'casino': -1.5, 'betting': -1.5, 'cards': -1.2,
            'sports': -1.2, 'football': -1.2, 'basketball': -1.2, 'soccer': -1.2, 'tennis': -1.2,
            'golf': -1.2, 'baseball': -1.2, 'cricket': -1.2, 'movie': -1.2, 'film': -1.2,
            'music': -1.0, 'celebrity': -1.2, 'actor': -1.0, 'actress': -1.0, 'entertainment': -1.2,
            'cooking': -1.0, 'recipe': -1.0, 'restaurant': -1.0, 'chef': -1.0, 'food': -0.8,
            'dating': -1.2, 'relationship': -1.0, 'love': -1.2, 'marriage': -1.0, 'romance': -1.2,
            'gaming': -1.2, 'video game': -1.2, 'playstation': -1.2, 'xbox': -1.2, 'nintendo': -1.2,
            'chess': -1.2, 'checkers': -1.2, 'bridge': -1.2, 'monopoly': -1.2, 'scrabble': -1.2,
            'board game': -1.2, 'card game': -1.2, 'player': -0.8, 'champion': -0.8, 'tournament': -0.8,
            'fashion': -1.0, 'clothing': -0.8, 'shopping': -0.8, 'retail': -0.8, 'style': -0.8,
            'travel': -1.0, 'vacation': -1.0, 'tourism': -1.0, 'hotel': -1.0, 'trip': -1.0,
            'health': -1.0, 'medical': -1.0, 'doctor': -1.0, 'medicine': -1.0, 'hospital': -1.0,
            'stock market': -1.0, 'trading': -1.0, 'cryptocurrency': -1.0, 'bitcoin': -1.0,
            'programming': -1.0, 'coding': -1.0, 'software': -0.8, 'computer': -0.8, 'tech': -0.8,
            'education': -0.8, 'school': -0.8, 'university': -0.8, 'student': -0.8, 'college': -0.8,
            'weather': -0.8, 'forecast': -0.8, 'temperature': -0.6, 'news': -0.8, 'current events': -0.8,
            'winning': -0.8, 'strategy': -0.6, 'success': -0.6, 'profit': -0.6, 'business': -0.6,
            'diet': -1.0, 'nutrition': -1.0, 'bodybuilding': -1.2, 'muscle': -1.0, 'fitness': -1.0,
            'workout': -1.0, 'exercise': -1.0, 'gym': -1.0, 'training': -1.0, 'weight': -0.8,
            'protein': -0.8, 'calories': -0.8, 'macros': -0.8, 'supplements': -0.8,
            # Physics and motion-related terms
            'physics': -1.2, 'physical': -0.8, 'motion': -1.0, 'velocity': -1.0, 'acceleration': -1.0,
            'force': -0.8, 'momentum': -1.0, 'kinetic': -1.0, 'potential': -0.8,
            'tangential': -1.2, 'linear': -1.0, 'rotational': -1.0, 'oscillatory': -1.0,
            'harmonic': -1.0, 'wave': -0.8, 'frequency': -0.8, 'amplitude': -0.8, 'mechanics': -1.0,
            'thermodynamics': -1.0, 'electromagnetism': -1.0, 'quantum': -1.0, 'relativity': -1.0,
            'particle': -0.8, 'atom': -0.8, 'molecule': -0.8, 'newton': -1.0, 'einstein': -1.0,
            'maxwell': -1.0, 'schrodinger': -1.0, 'heisenberg': -1.0, 'planck': -1.0, 'bohr': -1.0,
            # Mathematical and philosophical topics
            'mathematics': -1.2, 'math': -1.2, 'mathematical': -1.2, 'philosophy': -1.2, 'philosophical': -1.2,
            'paradox': -1.2, 'achilles': -1.2, 'tortoise': -1.2, 'zeno': -1.2, 'cantor': -1.2,
            'diagonal': -1.2, 'argument': -1.0, 'set theory': -1.2, 'infinity': -1.0, 'infinite': -1.0,
            'cardinality': -1.2, 'geometry': -1.0, 'algebra': -1.0, 'calculus': -1.0, 'statistics': -1.0,
            'probability': -1.0, 'theorem': -1.0, 'proof': -1.0, 'logic': -1.0, 'logical': -1.0,
            'reasoning': -1.0, 'deduction': -1.0, 'induction': -1.0, 'syllogism': -1.0
        }
        
        # Business/finance context (neutral unless sustainability-related)
        self.business_terms = {
            'business': 0.0, 'strategy': 0.0, 'profit': 0.0, 'success': 0.0, 'winning': 0.0,
            'investment': 0.0, 'finance': 0.0, 'market': 0.0, 'company': 0.0, 'corporate': 0.0,
            'management': 0.0, 'leadership': 0.0, 'growth': 0.0, 'development': 0.0
        }
        
        logger.info(f"Intelligent guardrails initialized with {len(self.sustainability_concepts)} sustainability concepts")
    
    def check_sustainability_relevance(self, query: str, conversation_context: str = None) -> GuardrailCheck:
        """
        Check if the query is sustainability-related using intelligent semantic analysis.
        
        Args:
            query: User input query
            conversation_context: Previous conversation context for follow-up detection
            
        Returns:
            GuardrailCheck with validation results
        """
        query_lower = query.lower()
        
        # IMMEDIATE BLOCK for obvious non-sustainability questions
        immediate_block_patterns = [
            r'\b(?:poker|gambling|casino|betting|cards)\b.*\b(?:strategy|winning|success|profit|long run|long-term)\b',
            r'\b(?:sports|football|basketball|soccer|tennis|golf)\b.*\b(?:strategy|winning|success|improve)\b',
            r'\b(?:movie|film|music|celebrity|entertainment)\b.*\b(?:best|recommend|review)\b',
            r'\b(?:cooking|recipe|restaurant|chef)\b.*\b(?:best|how to|tips)\b(?!\s+(?:sustainable|organic|local))',
            r'\b(?:dating|relationship|love|marriage)\b.*\b(?:advice|tips|how to)\b',
            r'\b(?:gaming|video game|playstation|xbox)\b.*\b(?:strategy|tips|winning)\b',
            r'\b(?:chess|checkers|poker|bridge|monopoly|scrabble|board game|card game)\b.*\b(?:best|player|champion|strategy|tips|winning)\b',
            r'\b(?:chess|checkers|poker|bridge|monopoly|scrabble|board game|card game)\b',
            r'\b(?:best|top|greatest|world|champion|player)\b.*\b(?:chess|checkers|poker|bridge|monopoly|scrabble|board game|card game)\b',
            r'\b(?:fashion|clothing|shopping)\b.*\b(?:best|style|trends)\b(?!\s+(?:sustainable|eco|green))',
            r'\b(?:travel|vacation|tourism)\b.*\b(?:best|recommend|guide)\b(?!\s+(?:sustainable|eco|green))',
            r'\b(?:health|medical|doctor|medicine)\b.*\b(?:advice|tips|treatment)\b(?!\s+(?:environmental|sustainability))',
            r'\b(?:stock market|trading|cryptocurrency|bitcoin)\b.*\b(?:strategy|investment|tips)\b(?!\s+(?:sustainable|esg|green))',
            r'\b(?:programming|coding|software|computer)\b.*\b(?:tips|tutorial|learn)\b(?!\s+(?:sustainable|green|clean))',
            r'\b(?:education|school|university|student)\b.*\b(?:advice|tips|study)\b(?!\s+(?:environmental|sustainability|green))',
            # NEW: Block bodybuilding, fitness, diet questions
            r'\b(?:diet|nutrition|bodybuilding|muscle|fitness|workout|exercise|gym|training)\b.*\b(?:plan|strategy|tips|advice|how to)\b(?!\s+(?:sustainable|environmental|eco))',
            # Block mathematical, philosophical, and physics topics
            r'\b(?:mathematics|math|mathematical|philosophy|philosophical|paradox|achilles|tortoise|zeno)\b',
            r'\b(?:cantor|diagonal|argument|set theory|infinity|infinite|cardinality)\b',
            r'\b(?:geometry|algebra|calculus|statistics|probability|theorem|proof)\b',
            r'\b(?:logic|logical|reasoning|deduction|induction|syllogism)\b',
            # Block physics and motion-related topics
            r'\b(?:physics|physical|motion|velocity|acceleration|force|momentum|kinetic|potential)\b(?!\s+(?:sustainable|renewable|clean|green|environmental|efficiency|transition|storage|security))',
            r'\b(?:tangential|circular|linear|rotational|oscillatory|harmonic|wave|frequency|amplitude)\b',
            r'\b(?:mechanics|thermodynamics|electromagnetism|quantum|relativity|particle|atom|molecule)\b',
            r'\b(?:newton|einstein|maxwell|schrodinger|heisenberg|planck|bohr|rutherford)\b',
            r'\b(?:bodybuilding|muscle|fitness|workout|exercise|gym|training)\b.*\b(?:sustainable|diet|nutrition)\b(?!\s+(?:environmental|eco|green))',
            r'\b(?:sustainable|diet|nutrition)\b.*\b(?:bodybuilding|muscle|fitness|workout|exercise|gym|training)\b(?!\s+(?:environmental|eco|green))',
        ]
        
        for pattern in immediate_block_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Guardrails: BLOCKED query '{query[:50]}...' - matched pattern: {pattern}")
                logger.info(f"Guardrails: Query lower: '{query_lower}'")
                return GuardrailCheck(
                    is_sustainability_related=False,
                    confidence_score=0.0,
                    detected_keywords=[],
                    rejection_reason="Query is about non-sustainability topics"
                )
        
        # Allow follow-up phrases and content requests
        follow_up_phrases = [
            "explain more", "more details", "tell me more", "elaborate",
            "can you tell more", "can you explain more", "can you elaborate",
            "yes", "y", "yeah", "yep", "sure", "ok", "okay",
            "what else", "anything else", "more information", "continue",
            "go on", "keep going", "more", "please", "summarize", "summary",
            "can you", "could you", "would you", "please elaborate", "please explain",
            "tell me", "show me", "give me", "provide", "expand", "detail"
        ]
        
        # Check for follow-up responses with context awareness
        is_follow_up = any(phrase in query_lower for phrase in follow_up_phrases)
        
        if is_follow_up:
            # If we have conversation context and it contains sustainability content, allow the follow-up
            if conversation_context:
                context_lower = conversation_context.lower()
                context_sustainability_score = self._calculate_semantic_sustainability_score(context_lower)
                
                # If the conversation context is sustainability-related, allow the follow-up
                if context_sustainability_score >= 0.3:
                    return GuardrailCheck(
                        is_sustainability_related=True,
                        confidence_score=0.9,
                        detected_keywords=["follow-up", "context-aware"],
                        rejection_reason=None
                    )
            
            # For follow-ups (short or medium length), allow them ONLY if conversation context is sustainability-related
            # This handles cases like "Can you elaborate" (17 chars) which should be allowed
            if conversation_context and len(query.strip()) <= 30:
                context_lower = conversation_context.lower()
                context_sustainability_score = self._calculate_semantic_sustainability_score(context_lower)
                
                # Only allow if the conversation context is actually sustainability-related
                if context_sustainability_score >= 0.2:  # Lower threshold for follow-ups
                    return GuardrailCheck(
                        is_sustainability_related=True,
                        confidence_score=0.8,
                        detected_keywords=["follow-up", "context-aware"],
                        rejection_reason=None
                    )
            
            # For very short follow-ups without context, allow them (original behavior)
            if len(query.strip()) <= 10:
                return GuardrailCheck(
                    is_sustainability_related=True,
                    confidence_score=0.8,
                    detected_keywords=["follow-up"],
                    rejection_reason=None
                )
        
        # Check for content requests with substantial content (likely legitimate sustainability content)
        content_request_phrases = ["summarize", "summary", "explain", "tell me about", "what is", "how does"]
        if any(phrase in query_lower for phrase in content_request_phrases) and len(query_lower) > 50:
            # If it's a content request with substantial text, allow it to proceed to semantic analysis
            pass
        
        # Calculate semantic sustainability score
        sustainability_score = self._calculate_semantic_sustainability_score(query_lower)
        
        # Check for explicit sustainability keywords
        detected_keywords = []
        keyword_matches = 0
        
        for keyword in self.sustainability_keywords:
            if keyword in query_lower:
                detected_keywords.append(keyword)
                keyword_matches += 1
        
        # Calculate confidence score based on both semantic analysis and keywords
        confidence_score = max(sustainability_score, min(keyword_matches / 2.0, 1.0))
        
        # Debug logging
        logger.info(f"Guardrails: Query '{query[:50]}...' - sustainability_score: {sustainability_score:.2f}, keyword_matches: {keyword_matches}, confidence_score: {confidence_score:.2f}")
        
        # INTELLIGENT: Allow if we have clear sustainability indicators - be more lenient
        is_sustainability_related = (
            sustainability_score >= 0.2 or  # Lower semantic sustainability score threshold
            (keyword_matches >= 1) or  # At least ONE sustainability keyword
            (keyword_matches >= 1 and sustainability_score >= 0.1) or  # One keyword + low semantic score
            (keyword_matches >= 1 and len(query_lower) > 50) or  # One keyword + moderate content
            (sustainability_score >= 0.1 and len(query_lower) > 100)  # Low semantic score + substantial content
        )
        
        if not is_sustainability_related:
            logger.info(f"Guardrails: BLOCKED query '{query[:50]}...' - semantic score: {confidence_score:.2f}")
            return GuardrailCheck(
                is_sustainability_related=False,
                confidence_score=confidence_score,
                detected_keywords=detected_keywords,
                rejection_reason="Query does not appear to be related to sustainability topics"
            )
        
        logger.info(f"Guardrails: ALLOWED query '{query[:50]}...' - semantic score: {confidence_score:.2f}")
        return GuardrailCheck(
            is_sustainability_related=True,
            confidence_score=confidence_score,
            detected_keywords=detected_keywords,
            rejection_reason=None
        )
    
    def _calculate_semantic_sustainability_score(self, query_lower: str) -> float:
        """
        Calculate a semantic sustainability score based on the query content.
        Returns a score between -1.0 (strongly non-sustainability) and 1.0 (strongly sustainability-related).
        """
        score = 0.0
        
        # Check for sustainability concepts
        for concept, weight in self.sustainability_concepts.items():
            if concept in query_lower:
                score += weight
        
        # Check for non-sustainability topics
        for topic, weight in self.non_sustainability_topics.items():
            if topic in query_lower:
                score += weight  # weight is already negative
        
        # Check for business context
        has_business_context = False
        for term in self.business_terms:
            if term in query_lower:
                has_business_context = True
                break
        
        # If there's business context but no sustainability indicators, penalize lightly
        if has_business_context and not any(sust_term in query_lower for sust_term in ['sustainable', 'green', 'esg', 'environmental', 'climate', 'carbon', 'renewable', 'clean energy', 'solar', 'wind', 'hydro', 'geothermal']):
            score -= 0.2  # Reduced penalty
        
        # Special check: if "sustainable" is used with non-sustainability topics, heavily penalize
        if 'sustainable' in query_lower:
            non_sust_with_sustainable = [
                'diet', 'nutrition', 'bodybuilding', 'muscle', 'fitness', 'workout', 'exercise', 'gym', 'training',
                'poker', 'gambling', 'sports', 'entertainment', 'dating', 'cooking', 'travel', 'health',
                'programming', 'education', 'business', 'finance', 'investment'
            ]
            if any(term in query_lower for term in non_sust_with_sustainable):
                score -= 1.0  # Heavy penalty for misusing "sustainable"
        
        # Check for contextual sustainability indicators
        if self._check_contextual_sustainability(query_lower):
            score += 0.3
        
        # Normalize score to -1 to 1 range, then convert to 0-1 for final score
        normalized_score = max(-1.0, min(1.0, score))
        final_score = (normalized_score + 1.0) / 2.0  # Convert to 0-1 range
        
        return final_score
    
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
            r'\b(?:i\'m not qualified|i don\'t have expertise)',
            r'\b(?:i can\'t answer|i cannot answer)',
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, response_lower):
                return False, "Response contains inappropriate refusal patterns"
        
        # Check for off-topic content in response using semantic analysis
        response_sustainability_score = self._calculate_semantic_sustainability_score(response_lower)
        
        # If response has negative sustainability score, it's likely off-topic
        if response_sustainability_score < 0.2:
            return False, "Response contains off-topic content"
        
        # Check for sustainability relevance in response
        sustainability_mentions = sum(
            1 for keyword in self.sustainability_keywords 
            if keyword in response_lower
        )
        
        # For longer responses, require sustainability context
        if len(response) > 100 and sustainability_mentions == 0 and response_sustainability_score < 0.3:
            return False, "Response lacks sustainability context"
        
        return True, None
    
    def get_polite_refusal_message(self, reason: str) -> str:
        """Generate a polite refusal message for non-sustainability queries."""
        return "I'm a sustainability expert focused on environmental topics, climate action, and sustainable practices. I can help with questions about renewable energy, carbon reduction, ESG, or other sustainability-related topics. What sustainability topic would you like to explore?"
