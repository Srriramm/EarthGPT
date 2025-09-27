"""Prompt engineering system for sustainability-focused responses."""

from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message, MessageRole


class PromptTemplate:
    """Template for generating prompts with context and instructions."""
    
    def __init__(self):
        
        self.system_prompt = """You are EarthGPT, a sustainability expert focused on environmental topics, climate action, and sustainable practices.

You ONLY answer questions related to environmental sustainability, including climate change, global warming, carbon emissions, renewable energy, clean technology, green innovation, biodiversity, ecosystems, conservation, wildlife protection, sustainable agriculture, forestry, fisheries, circular economy, recycling, waste reduction, resource efficiency, sustainable transport, green buildings, eco-friendly infrastructure, ESG (Environmental, Social, Governance), sustainable finance and green investment, environmental policy, SDGs, international climate agreements, water management, air quality, and pollution control.

If a question is NOT about sustainability, respond with: "I'm a sustainability expert focused only on environmental topics, climate action, and sustainable practices. I cannot answer that question. Please ask me something related to sustainability."

For sustainability questions, provide natural, conversational responses that feel like you're having a friendly discussion. Use flowing paragraphs and natural language. Only use structured formatting (like bullet points or headings) when the user specifically asks for lists, components, or structured information. Otherwise, respond in a natural, conversational style that matches how people actually talk about these topics."""

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
            # Include full conversation history - token management will handle limits
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
        
        # Let the LLM decide the appropriate response style naturally
        query_content = query
        
        messages.append(Message(
            role=MessageRole.USER,
            content=query_content
        ))
        
        return messages
    
    def _build_context_message(self, relevant_documents: List[Dict[str, Any]]) -> Message:
        """Build a context message from relevant documents (including old conversation messages)."""
        context_parts = ["RELEVANT CONTEXT FROM THIS CONVERSATION:"]
        
        for i, doc in enumerate(relevant_documents[:5], 1):  # Increased to top 5 documents
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            topic = metadata.get("topic", "general")
            role = metadata.get("role", "unknown")
            timestamp = metadata.get("timestamp", "")
            similarity_score = metadata.get("similarity_score", 0)
            
            # Format based on whether it's from previous conversation or knowledge base
            if topic == "previous_conversation":
                role_label = "User" if role == "user" else "Assistant"
                context_parts.append(f"\n{i}. Previous {role_label} message (relevance: {similarity_score:.2f}):")
                if timestamp:
                    context_parts.append(f"   (From earlier in this conversation)")
            else:
                context_parts.append(f"\n{i}. Topic: {topic} (relevance: {similarity_score:.2f})")
            
            # Truncate content to keep context manageable
            truncated_content = content[:400] + "..." if len(content) > 400 else content
            context_parts.append(f"   Content: {truncated_content}")
        
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
