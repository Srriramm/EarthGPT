"""Token management system for Claude API context window monitoring."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from config import settings


@dataclass
class TokenUsage:
    """Token usage statistics for a message or conversation."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated: bool = True  # Whether this is an estimate or exact count


class TokenCounter:
    """Token counter compatible with Claude's tokenization."""
    
    def __init__(self):
        # Claude uses a similar tokenization to GPT-4, roughly 4 characters per token
        # This is an approximation - for exact counts, you'd need tiktoken or similar
        self.chars_per_token = 4.0
        self.overhead_per_message = 4  # Formatting overhead per message
        
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text using character-based approximation.
        
        This is a rough estimate. For production use with exact counts,
        consider using tiktoken or similar tokenizer.
        """
        if not text:
            return 0
            
        # Basic character count with some adjustments for common patterns
        char_count = len(text)
        
        # Adjust for common tokenization patterns
        # URLs, code, and special characters tend to use more tokens
        url_pattern = r'https?://[^\s]+'
        code_pattern = r'```[\s\S]*?```'
        
        # Count special patterns that use more tokens
        urls = len(re.findall(url_pattern, text))
        code_blocks = len(re.findall(code_pattern, text))
        
        # Estimate tokens: base chars + overhead for special content
        estimated_tokens = int(char_count / self.chars_per_token)
        estimated_tokens += urls * 10  # URLs tend to use more tokens
        estimated_tokens += code_blocks * 5  # Code blocks have overhead
        
        return max(1, estimated_tokens)  # Minimum 1 token
    
    def count_message_tokens(self, role: str, content: str) -> int:
        """Count tokens for a single message including role and formatting."""
        content_tokens = self.count_tokens(content)
        role_tokens = self.count_tokens(role)
        return content_tokens + role_tokens + self.overhead_per_message
    
    def count_conversation_tokens(self, messages: List[Dict[str, str]]) -> TokenUsage:
        """Count total tokens for a conversation."""
        total_input = 0
        
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            # Handle both string and list content (for tool results)
            if isinstance(content, list):
                # Convert list to string representation for token counting
                content_str = str(content)
            else:
                content_str = str(content)
            
            total_input += self.count_message_tokens(role, content_str)
        
        return TokenUsage(
            input_tokens=total_input,
            total_tokens=total_input,
            estimated=True
        )


@dataclass
class ContextWindowConfig:
    """Configuration for context window management."""
    max_context_tokens: int = 200000  # Claude 3.5 Haiku limit
    max_output_tokens: int = 8192     # Max response tokens
    warning_threshold: float = 0.8    # 80% of context window
    critical_threshold: float = 0.9   # 90% of context window
    buffer_tokens: int = 1000         # Safety buffer
    min_history_tokens: int = 2000    # Minimum tokens to keep in history


class ContextWindowManager:
    """Manages context window usage and implements truncation strategies."""
    
    def __init__(self, config: Optional[ContextWindowConfig] = None):
        self.config = config or ContextWindowConfig()
        self.token_counter = TokenCounter()
        logger.info(f"Context window manager initialized with {self.config.max_context_tokens} token limit")
    
    def calculate_usage(self, messages: List[Dict[str, str]], expected_output_tokens: int = 0) -> Dict[str, Any]:
        """Calculate current token usage and remaining capacity."""
        usage = self.token_counter.count_conversation_tokens(messages)
        
        total_used = usage.input_tokens + expected_output_tokens
        remaining = self.config.max_context_tokens - total_used
        
        usage_percentage = total_used / self.config.max_context_tokens
        
        return {
            "input_tokens": usage.input_tokens,
            "expected_output_tokens": expected_output_tokens,
            "total_used": total_used,
            "remaining": remaining,
            "usage_percentage": usage_percentage,
            "is_warning": usage_percentage >= self.config.warning_threshold,
            "is_critical": usage_percentage >= self.config.critical_threshold,
            "is_overflow": total_used > self.config.max_context_tokens
        }
    
    def should_truncate(self, messages: List[Dict[str, str]], expected_output_tokens: int = 0) -> bool:
        """Determine if conversation needs truncation."""
        usage_info = self.calculate_usage(messages, expected_output_tokens)
        return usage_info["is_warning"] or usage_info["is_overflow"]
    
    def truncate_conversation(
        self, 
        messages: List[Dict[str, str]], 
        expected_output_tokens: int = 0,
        preserve_system: bool = True
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        Truncate conversation to fit within context window.
        
        Returns:
            Tuple of (truncated_messages, truncation_info)
        """
        if not self.should_truncate(messages, expected_output_tokens):
            return messages, {"truncated": False, "messages_removed": 0}
        
        # Separate system messages from conversation
        system_messages = []
        conversation_messages = []
        
        for msg in messages:
            if msg.get("role") == "system" and preserve_system:
                system_messages.append(msg)
            else:
                conversation_messages.append(msg)
        
        # Calculate target tokens for conversation (leave room for output + buffer)
        system_tokens = sum(
            self.token_counter.count_message_tokens(msg.get("role", ""), msg.get("content", ""))
            for msg in system_messages
        )
        
        target_conversation_tokens = (
            self.config.max_context_tokens - 
            expected_output_tokens - 
            self.config.buffer_tokens - 
            system_tokens
        )
        
        # Truncate from the beginning, keeping recent messages
        truncated_conversation = []
        current_tokens = 0
        messages_removed = 0
        
        # Start from the end and work backwards
        for msg in reversed(conversation_messages):
            msg_tokens = self.token_counter.count_message_tokens(
                msg.get("role", ""), 
                msg.get("content", "")
            )
            
            if current_tokens + msg_tokens <= target_conversation_tokens:
                truncated_conversation.insert(0, msg)
                current_tokens += msg_tokens
            else:
                messages_removed += 1
        
        # Combine system messages with truncated conversation
        final_messages = system_messages + truncated_conversation
        
        truncation_info = {
            "truncated": True,
            "messages_removed": messages_removed,
            "original_count": len(messages),
            "final_count": len(final_messages),
            "tokens_saved": len(messages) - len(final_messages),
            "final_tokens": current_tokens + system_tokens
        }
        
        logger.info(f"Truncated conversation: removed {messages_removed} messages, "
                   f"final token count: {truncation_info['final_tokens']}")
        
        return final_messages, truncation_info
    
    def get_optimal_output_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Calculate optimal max_tokens for response given current context usage."""
        usage_info = self.calculate_usage(messages, 0)
        remaining = usage_info["remaining"]
        
        # Reserve some buffer and return reasonable output limit
        available_for_output = remaining - self.config.buffer_tokens
        
        # Cap at the model's maximum output tokens
        optimal_tokens = min(
            max(available_for_output, 100),  # Minimum 100 tokens
            self.config.max_output_tokens
        )
        
        return int(optimal_tokens)
    
    def validate_request(self, messages: List[Dict[str, str]], max_tokens: int) -> Dict[str, Any]:
        """Validate if a request will fit within context window."""
        usage_info = self.calculate_usage(messages, max_tokens)
        
        return {
            "valid": not usage_info["is_overflow"],
            "usage_info": usage_info,
            "recommendations": self._get_recommendations(usage_info)
        }
    
    def _get_recommendations(self, usage_info: Dict[str, Any]) -> List[str]:
        """Get recommendations based on usage patterns."""
        recommendations = []
        
        if usage_info["is_overflow"]:
            recommendations.append("Request exceeds context window - truncation required")
        elif usage_info["is_critical"]:
            recommendations.append("Context window nearly full - consider summarizing history")
        elif usage_info["is_warning"]:
            recommendations.append("Context window usage high - monitor for truncation needs")
        
        if usage_info["usage_percentage"] > 0.5:
            recommendations.append("Consider implementing conversation summarization")
        
        return recommendations


# Global instances
token_counter = TokenCounter()
context_manager = ContextWindowManager()

