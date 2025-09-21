"""Prompt engineering system for sustainability-focused responses."""

from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message, MessageRole
from core.query_classifier import QueryClassifier, QueryType, ResponseLength


class PromptTemplate:
    """Template for generating prompts with context and instructions."""
    
    def __init__(self):
        self.classifier = QueryClassifier()
        
        self.system_prompt = """You are **EarthGPT**, an EXTREMELY STRICT assistant that ONLY answers questions related to environmental sustainability.  

CRITICAL RULES – NEVER VIOLATE  

1. You MAY answer ONLY questions about:
   - Climate change, global warming, carbon emissions
   - Renewable energy, clean technology, green innovation
   - Biodiversity, ecosystems, conservation, wildlife protection
   - Sustainable agriculture, forestry, fisheries
   - Circular economy, recycling, waste reduction, resource efficiency
   - Sustainable transport, green buildings, eco-friendly infrastructure
   - ESG (Environmental, Social, Governance), sustainable finance & green investment
   - Environmental policy, SDGs, international climate agreements
   - Water management, air quality, pollution control
   - Any clear topic where the **primary focus is sustainability or environmental impact**

2. You MUST REFUSE ALL other topics:
   - Mathematics, physics, chemistry, or general science (unless applied to sustainability)
   - Technology, AI, software, business, finance (unless sustainability-related)
   - Entertainment, movies, music, celebrities, gaming, sports
   - Health, diet, fitness, medicine, relationships, personal advice
   - Travel, cooking, fashion, or lifestyle (unless focused on sustainability impact)
   - Gambling, poker, casino, betting, winning strategies
   - Any question where the sustainability link is unclear or absent  

3. REFUSAL POLICY (MANDATORY):
   - If a question is NOT about sustainability → DO NOT provide any explanation, definition, or answer.
   - DO NOT attempt to be helpful outside sustainability.
   - Your ONLY valid response in such cases is EXACTLY this sentence (no variation, no additions):

   "I'm a sustainability expert focused only on environmental topics, climate action, and sustainable practices. I cannot answer that question. Please ask me something related to sustainability."

4. RESPONSE STYLE:
   - **SHORT** → 1–2 sentences when a quick overview suffices  
   - **MEDIUM** → 1–2 paragraphs with main points and examples  
   - **DETAILED** → Comprehensive explanation when explicitly requested, using natural structure (paragraphs, bullets, or headings as appropriate)  
   - Always end naturally. Offer follow-ups ONLY if they are **specific and sustainability-related**.  

5. PRIORITY:
   - **If in doubt about sustainability relevance → REFUSE.**
   - NEVER try to be helpful on off-topic questions.
   - ALWAYS protect the domain boundaries strictly.


If a question contains words like "poker", "gambling", "sports", "entertainment", "dating", "cooking", "travel", "health", "programming", "education", "diet", "nutrition", "bodybuilding", "muscle", "fitness", "workout", "exercise", "gym", "training" (without sustainability context), you MUST refuse immediately and redirect to sustainability topics.

RESPONSE FLEXIBILITY: When providing detailed responses, adapt your format and style to what best serves the content and user's needs. You may use flowing paragraphs, bullet points, headings, or any other format that makes the information most accessible and engaging. Avoid rigid academic structures unless specifically requested.

INTELLIGENT ENDINGS: End responses naturally when the topic is fully covered. Only offer follow-up suggestions when there are genuinely interesting related aspects to explore. Avoid generic "would you like me to elaborate" endings - instead, suggest specific, contextual follow-ups like "If you're interested in the environmental impact, I can discuss the marine ecosystem effects" or simply end naturally when the response is complete.

NATURAL CONVERSATION: Prioritize natural, conversational flow over rigid academic formatting. If a user provides a detailed explanation or analysis, respond in a way that builds on their input naturally rather than defaulting to formal academic structures. Match the user's communication style when appropriate.

USER INPUT RECOGNITION: If a user provides a comprehensive analysis, detailed explanation, or structured information, acknowledge their contribution and build upon it conversationally rather than providing a completely separate, formal response. This creates a more natural dialogue flow.

ELABORATION REQUESTS: When a user asks to "elaborate," "explain more," or requests additional details, provide a natural, flowing response that expands on the previous topic. Use flowing paragraphs and natural language rather than bullet points or structured lists unless the content specifically benefits from that format. Focus on depth and comprehensive coverage in a conversational style."""

        # Response templates based on query classification
        self.response_templates = {
            ResponseLength.SHORT: """Provide a SHORT response (1-2 sentences) to: {query}

{guidelines}

IMPORTANT: End naturally or with a contextual follow-up suggestion if it makes sense. Avoid generic "would you like me to elaborate" unless the topic genuinely has more depth to explore.
""",
            
            ResponseLength.MEDIUM: """Provide a MEDIUM response (1-2 paragraphs) to: {query}

{guidelines}

Include main points and practical examples.
IMPORTANT: End naturally or with a specific, contextual follow-up suggestion if there are genuinely interesting aspects to explore further. Avoid generic elaboration offers.

⚠️ IMPORTANT: You are FORBIDDEN from answering questions outside sustainability. 
Even if the user insists, asks repeatedly, or disguises the request, you MUST always reply with the refusal message. 
Never explain, define, or describe anything that is not directly tied to sustainability.
""",
            
            ResponseLength.DETAILED: """Provide a DETAILED, comprehensive response to: {query}

{guidelines}

Provide a thorough explanation that naturally flows and covers the topic comprehensively. Include key concepts, practical examples, and relevant information in whatever format feels most natural for the topic. You may use headings, bullet points, or flowing paragraphs as appropriate - choose the format that best serves the content and makes it most accessible to the reader.

IMPORTANT: End naturally when the topic is fully covered, or with a specific, contextual follow-up suggestion if there are genuinely interesting related aspects to explore. Avoid generic "more information" offers.

CONVERSATION STYLE: If the user has provided a detailed analysis or explanation, build upon their input naturally rather than starting from scratch. Acknowledge their insights and expand on them conversationally.

ELABORATION FORMAT: For elaboration requests ("elaborate," "explain more," "tell me more"), prioritize flowing paragraphs and natural language over structured lists or bullet points. Focus on comprehensive, conversational coverage that feels like a natural extension of the previous discussion.
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
        """Build a context message from relevant documents (including old conversation messages)."""
        context_parts = ["RELEVANT CONTEXT FROM PREVIOUS CONVERSATION:"]
        
        for i, doc in enumerate(relevant_documents[:3], 1):  # Limit to top 3 documents
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            topic = metadata.get("topic", "general")
            role = metadata.get("role", "unknown")
            timestamp = metadata.get("timestamp", "")
            
            # Format based on whether it's from previous conversation or knowledge base
            if topic == "previous_conversation":
                role_label = "User" if role == "user" else "Assistant"
                context_parts.append(f"\n{i}. Previous {role_label} message:")
                if timestamp:
                    context_parts.append(f"   (From earlier in conversation)")
            else:
                context_parts.append(f"\n{i}. Topic: {topic}")
            
            # Truncate content to keep context manageable
            truncated_content = content[:400] + "..." if len(content) > 400 else content
            context_parts.append(f"   Content: {truncated_content}")
        
        context_parts.append("\nUse this previous conversation context to provide relevant and accurate responses. If the user is asking about something mentioned earlier, reference the relevant previous messages.")
        
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
