"""Prompt engineering system for sustainability-focused responses."""

from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message, MessageRole


class PromptTemplate:
    """Template for generating prompts with context and instructions."""
    
    def __init__(self):
        
        self.system_prompt = """You are EarthGPT, a sustainability expert assistant. You provide accurate information on sustainability, environmental protection, climate action, and related topics.

IMPORTANT: Questions reaching you have already been validated as sustainability-related by an advanced classification system. Trust this validation and provide helpful answers.

CORE FUNCTION
Answer questions about environmental science, climate solutions, sustainable practices, green technology, renewable energy, conservation, sustainability policy, ESG reporting, environmental frameworks, standards, certifications, and all related topics.

Include technical topics like:
- Sustainability reporting frameworks (GRI, SASB, TCFD, CDP, etc.)
- Environmental policies and regulations
- Carbon accounting and emissions management
- ESG investing and sustainable finance
- Corporate sustainability practices
- Environmental compliance and standards

RESPONSE PROTOCOL
For All Questions (pre-validated as sustainability-related):
Provide direct, accurate answers using natural conversational language. If you're unfamiliar with a specific term or policy, acknowledge this but still attempt to provide context within the sustainability domain.

QUALITY STANDARDS
- Accuracy: Base responses on current scientific consensus
- Precision: Answer exactly what was asked
- Clarity: Use natural, conversational language
- Completeness: Provide sufficient detail for the question's complexity

RESPONSE LENGTH
- Simple questions: Direct 1-2 sentence answers
- Complex questions: Comprehensive paragraphs as needed
Always prioritize precision over length"""

        logger.info("Prompt manager initialized")
    
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
            
            # CRITICAL FIX: Limit conversation history to prevent context pollution
            # Keep only the most recent conversation turns to avoid old topics influencing responses
            max_history_items = 6  # Last 3 exchanges (user+assistant pairs)
            if len(history) > max_history_items:
                # Keep only the most recent exchanges
                recent_history = history[-max_history_items:]
                logger.info(f"Limited conversation history to {len(recent_history)} recent messages to prevent context pollution")
            else:
                recent_history = history
            
            # Convert new memory system format to Message objects
            for msg in recent_history:
                if isinstance(msg, dict):
                    # New memory system format: {"role": "user", "content": "...", "timestamp": "..."}
                    role = MessageRole.USER if msg.get("role") == "user" else MessageRole.ASSISTANT
                    content = msg.get("content", "")
                    messages.append(Message(role=role, content=content))
                else:
                    # Old format: Message objects
                    messages.append(msg)
            
            # Extract text for classification
            conversation_history = [msg.get("content", "") if isinstance(msg, dict) else (msg.content if hasattr(msg, 'content') else str(msg)) 
                                 for msg in recent_history 
                                 if (isinstance(msg, dict) and msg.get("role") == "user") or 
                                    (hasattr(msg, 'role') and msg.role == MessageRole.USER)]
        
        # Add session summary if available
        if "summary" in context and context["summary"]:
            summary_message = Message(
                role=MessageRole.SYSTEM,
                content=f"CONVERSATION SUMMARY: {context['summary']}\n\nUse this summary to maintain context and continuity in your response."
            )
            messages.append(summary_message)
        
        # Add context from relevant documents
        if "relevant_documents" in context and context["relevant_documents"]:
            context_message = self._build_context_message(context["relevant_documents"])
            messages.append(context_message)
        
        # CRITICAL: Current user query MUST be the last message for highest priority
        # Parse user intent for response length and add clear instructions
        query_lower = query.lower()
        
        # Detect user preference for response length
        length_instruction = ""
        if any(phrase in query_lower for phrase in ["in short", "briefly", "quick", "summary", "concise", "short"]):
            length_instruction = "IMPORTANT: Provide a BRIEF, concise response (2-3 sentences maximum). "
        elif any(phrase in query_lower for phrase in ["detailed", "comprehensive", "thorough", "in depth", "elaborate"]):
            length_instruction = "IMPORTANT: Provide a detailed, comprehensive response. "
        
        # Add clear instruction and current query
        current_query = f"{length_instruction}Current question: {query}"
        
        messages.append(Message(
            role=MessageRole.USER,
            content=current_query
        ))
        
        return messages
    
    def _build_context_message(self, relevant_documents: List[Dict[str, Any]]) -> Message:
        """Build a context message from relevant documents (including old conversation messages)."""
        context_parts = ["RELEVANT CONTEXT FROM THIS CONVERSATION:"]
        
        for i, doc in enumerate(relevant_documents[:5], 1):  # Top 5 most relevant old messages
            content = doc.get("content", "")
            timestamp = doc.get("timestamp", "")
            relevance_score = doc.get("relevance_score", 0.0)
            
            # Format for old conversation messages from semantic search
            context_parts.append(f"\n{i}. Previous Assistant Response (relevance: {relevance_score:.2f}):")
            if timestamp:
                context_parts.append(f"   (From earlier in this conversation)")
            
            # Truncate content to keep context manageable
            truncated_content = content[:400] + "..." if len(content) > 400 else content
            context_parts.append(f"   {truncated_content}")
        
        context_parts.append("\nUse this relevant context from this conversation to provide more accurate and contextual responses. Reference the relevant previous messages when appropriate.")
        
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
