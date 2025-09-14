"""Prompt engineering system for sustainability-focused responses."""

from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message, MessageRole
from core.query_classifier import QueryClassifier, QueryType, ResponseLength


class PromptTemplate:
    """Template for generating prompts with context and instructions."""
    
    def __init__(self):
        self.classifier = QueryClassifier()
        
        self.system_prompt = """You are EarthGPT, an EXTREMELY STRICT sustainability expert assistant. You ONLY answer questions about environmental, climate, and sustainability topics.

CRITICAL RULES - NEVER VIOLATE THESE:
1. ONLY answer questions about:
   - Environmental protection, climate change, sustainability
   - Renewable energy, clean technology, green innovation
   - Carbon reduction, emissions, climate mitigation
   - Biodiversity, conservation, ecosystem protection
   - Circular economy, waste reduction, resource efficiency
   - ESG, sustainable finance, green investment
   - Environmental policy, climate agreements, SDGs
   - Sustainable agriculture, green building, clean transport

2. ALWAYS REFUSE these topics (even if they seem related):
   - Poker, gambling, casino, betting, cards, games, winning strategies
   - Sports, entertainment, movies, music, celebrities
   - Personal relationships, dating, health advice
   - General business strategy, finance (unless ESG/sustainable)
   - Technology (unless clean/green/sustainable)
   - Education (unless environmental/sustainability)
   - Cooking, travel, fashion (unless sustainable/eco)
   - Diet, nutrition, bodybuilding, muscle, fitness, workout, exercise, gym, training
   - Health, medical advice, weight loss, supplements, protein, calories
   - ANY question about "winning", "strategy", "success" that is not sustainability-related

3. RESPONSE STYLE:
   - SHORT: 1-2 sentences + offer to elaborate
   - MEDIUM: 1-2 paragraphs + offer to elaborate  
   - DETAILED: Comprehensive response when explicitly requested

4. REFUSAL MESSAGE for off-topic questions:
   "I'm a sustainability expert focused on environmental topics, climate action, and sustainable practices. I can help with questions about renewable energy, carbon reduction, ESG, or other sustainability-related topics. What sustainability topic would you like to explore?"

5. NEVER provide advice on:
   - Gambling, poker, casino games, winning strategies
   - Sports strategies or entertainment
   - Personal finance (unless sustainable investing)
   - General business (unless sustainability-related)
   - Health, relationships, or lifestyle advice
   - Diet, nutrition, bodybuilding, muscle, fitness, workout, exercise, gym, training
   - ANY non-sustainability topic

If a question contains words like "poker", "gambling", "sports", "entertainment", "dating", "cooking", "travel", "health", "programming", "education", "diet", "nutrition", "bodybuilding", "muscle", "fitness", "workout", "exercise", "gym", "training" (without sustainability context), you MUST refuse immediately and redirect to sustainability topics."""

        # Response templates based on query classification
        self.response_templates = {
            ResponseLength.SHORT: """Provide a SHORT response (1-2 sentences) to: {query}

{guidelines}

IMPORTANT: End with: "I can provide more detailed information about [specific topic] if you would like to explore this further."
""",
            
            ResponseLength.MEDIUM: """Provide a MEDIUM response (1-2 paragraphs) to: {query}

{guidelines}

Include main points and practical examples.
IMPORTANT: End with: "Would you like me to elaborate on any specific aspect of [topic]?"
""",
            
            ResponseLength.DETAILED: """Provide a DETAILED, comprehensive response to: {query}

{guidelines}

Include:
- Clear section headings or structure
- Key concepts and definitions
- Practical examples and case studies
- Actionable recommendations and implementation strategies
- Relevant statistics or data points when available
- Multiple paragraphs with clear organization

IMPORTANT: End with: "I can provide more specific information about any particular aspect that interests you."
"""
        }

        logger.info("Prompt templates initialized")
    
    def build_system_message(self) -> Message:
        """Build the system message with core instructions."""
        return Message(
            role=MessageRole.SYSTEM,
            content=self.system_prompt
        )
    
    def build_conversation_prompt(
        self, 
        query: str, 
        context: Dict[str, Any], 
        is_detailed: bool = False
    ) -> List[Message]:
        """
        Build a complete conversation prompt with context and classification.
        
        Args:
            query: User query
            context: Retrieved context and conversation history
            is_detailed: Whether to request detailed response (overrides classification)
            
        Returns:
            List of messages for the conversation
        """
        messages = [self.build_system_message()]
        
        # Add conversation history
        conversation_history = []
        if "conversation_history" in context:
            history = context["conversation_history"]
            # Limit history to recent messages to stay within token limits
            recent_history = history[-6:] if len(history) > 6 else history
            messages.extend(recent_history)
            # Extract text for classification
            conversation_history = [msg.content if hasattr(msg, 'content') else str(msg) for msg in recent_history if hasattr(msg, 'role') and msg.role == MessageRole.USER]
        
        # Add context from relevant documents
        if "relevant_documents" in context and context["relevant_documents"]:
            context_message = self._build_context_message(context["relevant_documents"])
            messages.append(context_message)
        
        # Classify the query to determine response type
        if is_detailed:
            # Override classification for explicit detailed requests
            response_length = ResponseLength.DETAILED
        else:
            query_type, response_length = self.classifier.classify_query(query, conversation_history)
            logger.debug(f"Query classified as: {query_type.value}, Response length: {response_length.value}")
        
        # Get guidelines for this response type
        guidelines = self.classifier.get_response_guidelines(query_type if not is_detailed else QueryType.DETAILED_REQUEST, response_length)
        
        # Build the appropriate prompt template
        template = self.response_templates[response_length]
        query_content = template.format(
            query=query,
            guidelines=f"Response style: {guidelines['style']}\nStructure: {guidelines['structure']}"
        )
        
        messages.append(Message(
            role=MessageRole.USER,
            content=query_content
        ))
        
        return messages
    
    def _build_context_message(self, relevant_documents: List[Dict[str, Any]]) -> Message:
        """Build a context message from relevant documents."""
        context_parts = ["RELEVANT SUSTAINABILITY KNOWLEDGE:"]
        
        for i, doc in enumerate(relevant_documents[:3], 1):  # Limit to top 3 documents
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            topic = metadata.get("topic", "general")
            
            context_parts.append(f"\n{i}. Topic: {topic}")
            context_parts.append(f"   Content: {content[:300]}{'...' if len(content) > 300 else ''}")
        
        context_parts.append("\nUse this knowledge to inform your response while maintaining accuracy and relevance.")
        
        return Message(
            role=MessageRole.SYSTEM,
            content="\n".join(context_parts)
        )
    
    def build_refusal_prompt(self, reason: str) -> str:
        """Build a polite refusal message for non-sustainability queries."""
        return f"""I'm a sustainability expert assistant focused on environmental topics, climate action, and sustainable practices. 

I'd be happy to help with questions about:
- Renewable energy and clean technologies
- Carbon footprint reduction and emissions
- ESG criteria and sustainable business practices
- Climate change mitigation and adaptation
- Biodiversity conservation and ecosystem protection
- Circular economy and waste reduction
- Energy efficiency and resource management

What sustainability topic would you like to explore?"""


class PromptOptimizer:
    """Optimizes prompts for better LLM performance."""
    
    def __init__(self):
        self.optimization_rules = {
            "length": 8000,  # Max tokens for context
            "clarity": True,
            "specificity": True,
            "actionability": True
        }
        logger.info("Prompt optimizer initialized")
    
    def optimize_prompt(self, messages: List[Message]) -> List[Message]:
        """
        Optimize a prompt for better performance.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Optimized list of messages
        """
        optimized_messages = []
        total_length = 0
        
        for message in messages:
            # Handle both Message objects and dictionaries
            if hasattr(message, 'content'):
                content = message.content
            else:
                content = message.get('content', '')
            
            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            message_tokens = len(content) // 4
            
            if total_length + message_tokens > self.optimization_rules["length"]:
                # Truncate or skip if we're approaching token limit
                if message.role == MessageRole.SYSTEM and len(optimized_messages) > 0:
                    # Keep system message but truncate if necessary
                    remaining_tokens = self.optimization_rules["length"] - total_length
                    if remaining_tokens > 100:  # Keep some buffer
                        truncated_content = content[:remaining_tokens * 4]
                        optimized_messages.append(Message(
                            role=message.role,
                            content=truncated_content + "..."
                        ))
                break
            
            # Create a proper Message object if needed
            if hasattr(message, 'content'):
                optimized_messages.append(message)
            else:
                optimized_messages.append(Message(
                    role=message.get('role', MessageRole.USER),
                    content=content
                ))
            total_length += message_tokens
        
        logger.debug(f"Optimized prompt: {len(optimized_messages)} messages, ~{total_length} tokens")
        return optimized_messages
    
    def enhance_query_clarity(self, query: str) -> str:
        """Enhance query clarity for better responses."""
        # Add clarifying context for common ambiguous queries
        query_lower = query.lower()
        
        if "how" in query_lower and "reduce" in query_lower:
            return f"{query} Please provide specific, actionable steps and examples."
        elif "what" in query_lower and "best" in query_lower:
            return f"{query} Please include criteria for evaluation and practical considerations."
        elif "compare" in query_lower:
            return f"{query} Please provide a structured comparison with pros and cons."
        elif "explain" in query_lower:
            return f"{query} Please provide clear explanations with examples and context."
        
        return query


class PromptManager:
    """Main prompt management system."""
    
    def __init__(self):
        self.template = PromptTemplate()
        self.optimizer = PromptOptimizer()
        logger.info("Prompt manager initialized")
    
    def create_conversation_prompt(
        self, 
        query: str, 
        context: Dict[str, Any], 
        is_detailed: bool = False,
        is_summary: bool = False
    ) -> List[Message]:
        """
        Create an optimized conversation prompt.
        
        Args:
            query: User query
            context: Retrieved context and conversation history
            is_detailed: Whether to request detailed response
            is_summary: Whether this is a summary response
            
        Returns:
            Optimized list of messages for the conversation
        """
        # Enhance query clarity
        enhanced_query = self.optimizer.enhance_query_clarity(query)
        
        # Build the prompt
        messages = self.template.build_conversation_prompt(
            enhanced_query, 
            context, 
            is_detailed=is_detailed
        )
        
        # Optimize the prompt
        optimized_messages = self.optimizer.optimize_prompt(messages)
        
        logger.debug(f"Created conversation prompt: {len(optimized_messages)} messages")
        return optimized_messages
    
    def create_refusal_prompt(self, reason: str) -> str:
        """Create a polite refusal prompt for non-sustainability queries."""
        return self.template.build_refusal_prompt(reason)
