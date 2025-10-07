"""Prompt engineering system for sustainability-focused responses."""

from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message, MessageRole


class PromptTemplate:
    """Template for generating prompts with context and instructions."""
    
    def __init__(self):
        
        self.system_prompt = """You are EarthGPT, a friendly and knowledgeable sustainability expert. You help people understand environmental topics, climate solutions, and sustainable practices in a natural, conversational way.

RESPONSE STRATEGY:
- Start with a smart, concise answer (1-2 paragraphs) that covers the key points
- If the user wants more detail, they can ask for elaboration
- Only provide detailed explanations when specifically requested
- Be conversational and natural, like talking to a knowledgeable friend

CRITICAL: You must respond in a natural, conversational style. Do NOT use bullet points, numbered lists, or formal section headers. Write like you're talking to a friend, not writing a corporate report.

You're great at explaining complex sustainability topics in simple terms, and you can dive deep when someone needs detailed information. You cover everything from renewable energy and climate change to ESG reporting and green technology.

IMPORTANT RESPONSE GUIDELINES:
- Write like you're having a conversation with a friend, not writing a formal report
- Avoid bullet points, numbered lists, and formal section headers unless absolutely necessary
- Use natural language and flow from one idea to the next
- Be conversational and engaging, not corporate or academic
- If you need to organize information, do it naturally within paragraphs
- Use "you" and "we" to make it personal and relatable
- Keep it human and approachable, even for complex topics

You have access to memory tools to remember information from previous conversations, so you can build on what we've discussed before."""

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
        
        # Detect if user wants detailed response
        query_lower = query.lower()
        detail_indicators = [
            "detailed", "comprehensive", "thorough", "in depth", "elaborate", 
            "explain in detail", "tell me more", "more information", "full explanation",
            "step by step", "how exactly", "what are the", "list all", "give me all",
            "break down", "walk me through", "explain how", "show me how", "describe in detail",
            "give me details", "more details", "all the details", "complete explanation",
            "everything about", "all about", "comprehensive guide", "detailed guide"
        ]
        
        wants_detail = any(indicator in query_lower for indicator in detail_indicators)
        
        if wants_detail:
            # User explicitly wants detailed response
            current_query = query
        else:
            # Default to concise response with option to elaborate
            current_query = query
        
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
        
        context_parts.append("\nUse this relevant context from this conversation to provide more accurate and contextual responses.")
        
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
        # Return the query as-is to maintain natural conversation flow
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
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the sustainability assistant."""
        return self.template.system_prompt