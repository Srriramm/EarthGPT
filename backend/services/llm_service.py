"""LLM service for handling Claude API integration with token management and memory tool."""

import os
import time
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from pathlib import Path
from anthropic import Anthropic
from loguru import logger
from models.schemas import Message, MessageRole
from config import settings
from core.token_manager import ContextWindowManager, TokenCounter
from core.claude_memory_tool import claude_memory_tool_handler
from core.mongodb_memory import mongodb_session_manager
from core.cache_manager import cache_manager
from core.error_handler import error_handler

# Constants
MIN_REQUEST_INTERVAL = 2  # Minimum 2 seconds between requests
DETAILED_RESPONSE_MULTIPLIER = 2  # Multiply tokens for detailed responses
BRIEF_RESPONSE_LIMIT = 1000  # Token limit for brief responses
CONTINUATION_TOKEN_MINIMUM = 2000  # Minimum tokens for continuation calls
FINAL_CALL_TOKEN_LIMIT = 3000  # Token limit for final API calls


class LLMService:
    """Service for handling LLM inference with Claude API."""
    
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or settings.claude_api_key
        self.model_name = settings.claude_model
        self.client = None
        self.is_loaded = False
        
        # Initialize token management
        self.context_manager = ContextWindowManager()
        self.token_counter = TokenCounter()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = MIN_REQUEST_INTERVAL
        
        logger.info(f"LLM Service initialized with Claude model: {self.model_name}")
    
    def _rate_limit(self):
        """Simple rate limiting to prevent API rate limit errors."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_beta_headers(self):
        """Get beta headers for enabled tools."""
        extra_headers = {}
        beta_features = []
        
        if settings.enable_claude_memory_tool:
            beta_features.append("context-management-2025-06-27")
        
        if settings.enable_web_fetch_tool:
            beta_features.append("web-fetch-2025-09-10")
        
        if beta_features:
            extra_headers["anthropic-beta"] = ",".join(beta_features)
        
        return extra_headers
    
    def _extract_usage_info(self, response) -> Dict[str, Any]:
        """
        Extract comprehensive usage information from Claude API response.
        Based on Claude API documentation: https://docs.anthropic.com/en/api/messages
        """
        usage_info = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0
        }
        
        if hasattr(response, 'usage') and response.usage:
            # Extract standard usage metrics
            usage_info["input_tokens"] = getattr(response.usage, 'input_tokens', 0)
            usage_info["output_tokens"] = getattr(response.usage, 'output_tokens', 0)
            usage_info["cache_creation_input_tokens"] = getattr(response.usage, 'cache_creation_input_tokens', 0)
            usage_info["cache_read_input_tokens"] = getattr(response.usage, 'cache_read_input_tokens', 0)
            
            # Calculate total tokens (input + output + cache creation, but not cache read)
            usage_info["total_tokens"] = (
                usage_info["input_tokens"] + 
                usage_info["output_tokens"] + 
                usage_info["cache_creation_input_tokens"]
            )
            
            # Estimate cost based on Claude Sonnet 4 pricing (as of 2025)
            # Input: $3.00 per 1M tokens, Output: $15.00 per 1M tokens
            input_cost = (usage_info["input_tokens"] / 1_000_000) * 3.00
            output_cost = (usage_info["output_tokens"] / 1_000_000) * 15.00
            usage_info["estimated_cost_usd"] = input_cost + output_cost
            
            logger.info(f"Token Usage - Input: {usage_info['input_tokens']}, Output: {usage_info['output_tokens']}, "
                       f"Cache Creation: {usage_info['cache_creation_input_tokens']}, Cache Read: {usage_info['cache_read_input_tokens']}, "
                       f"Total: {usage_info['total_tokens']}, Estimated Cost: ${usage_info['estimated_cost_usd']:.6f}")
        else:
            logger.warning("No usage information available in Claude API response")
            
        return usage_info
    
    def load_model(self) -> bool:
        """Initialize the Claude API client."""
        try:
            if not self.api_key:
                logger.error("Claude API key not found. Please set ANTHROPIC_API_KEY in your .env file.")
                return False
            
            logger.info(f"Initializing Claude API client with model: {self.model_name}")
            
            # Initialize Claude client
            self.client = Anthropic(api_key=self.api_key)
            
            self.is_loaded = True
            logger.info("Claude API client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client: {e}")
            return False
    
    async def generate_response(
        self, 
        messages: List[Message], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        is_detailed: bool = False,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from Claude API with token management and memory tool support.
        
        Args:
            messages: List of conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            is_detailed: Whether to generate a detailed response
            session_id: Session ID for memory tool context
            
        Returns:
            Dictionary with response text and metadata
        """
        if not self.is_loaded:
            logger.error("Claude API client not initialized, attempting to initialize...")
            if not self.load_model():
                logger.error("Failed to initialize Claude API client")
                return {
                    "response": "I'm sorry, the Claude API is not currently available. Please check your API key and try again later.",
                    "error": "api_not_available",
                    "usage_info": {}
                }
        
        try:
            # Format messages for Claude API
            formatted_messages, system_prompt = self._format_messages_for_claude(messages)
            
            # Check cache first if caching is enabled
            if settings.enable_prompt_caching:
                cache_manager.increment_cache_request()
                cached_response = cache_manager.get_cached_response(
                    formatted_messages, 
                    self.model_name, 
                    max_tokens or settings.max_tokens, 
                    temperature or settings.temperature
                )
                
                if cached_response:
                    cache_manager.increment_cache_hit()
                    logger.info("Returning cached response")
                    return cached_response
            
            # Calculate token usage and validate request
            expected_output_tokens = max_tokens or settings.max_tokens
            
            # Check if user is asking for detailed response based on their message
            user_message = ""
            if formatted_messages:
                for msg in reversed(formatted_messages):
                    if msg.get("role") == "user" or (hasattr(msg, 'role') and msg.role == MessageRole.USER):
                        user_message = msg.get("content", "") if isinstance(msg, dict) else (msg.content if hasattr(msg, 'content') else str(msg))
                        break
            
            # Detect elaboration requests
            elaboration_indicators = [
                "detailed", "comprehensive", "thorough", "in depth", "elaborate", 
                "explain in detail", "tell me more", "more information", "full explanation",
                "step by step", "how exactly", "what are the", "list all", "give me all",
                "break down", "walk me through", "explain how", "show me how", "describe in detail",
                "give me details", "more details", "all the details", "complete explanation",
                "everything about", "all about", "comprehensive guide", "detailed guide"
            ]
            
            user_wants_detail = any(indicator in user_message.lower() for indicator in elaboration_indicators)
            
            if is_detailed or user_wants_detail:
                expected_output_tokens = min(expected_output_tokens * DETAILED_RESPONSE_MULTIPLIER, 4096)
                logger.info(f"User requested detailed response, increasing max_tokens to {expected_output_tokens}")
            else:
                # For brief responses, limit tokens to encourage conciseness
                expected_output_tokens = min(expected_output_tokens, BRIEF_RESPONSE_LIMIT)
                logger.info(f"Brief response requested, limiting max_tokens to {expected_output_tokens}")
            
            # Validate context window
            validation = self.context_manager.validate_request(formatted_messages, expected_output_tokens)
            
            if not validation["valid"]:
                logger.warning(f"Request exceeds context window: {validation['usage_info']}")
                return {
                    "response": "I'm sorry, this conversation has become too long for me to process effectively. Please start a new conversation or ask a more focused question.",
                    "error": "context_window_exceeded",
                    "usage_info": validation["usage_info"],
                    "recommendations": validation["recommendations"]
                }
            
            # Truncate if needed
            if self.context_manager.should_truncate(formatted_messages, expected_output_tokens):
                logger.info("Truncating conversation to fit context window")
                formatted_messages, truncation_info = self.context_manager.truncate_conversation(
                    formatted_messages, expected_output_tokens
                )
                logger.info(f"Truncation info: {truncation_info}")
            
            # Get optimal output tokens
            optimal_tokens = self.context_manager.get_optimal_output_tokens(formatted_messages)
            response_tokens = min(expected_output_tokens, optimal_tokens)
            
            # Generate response
            logger.debug(f"Generating response with {len(formatted_messages)} messages, max_tokens: {response_tokens}")
            
            # Debug: Log token usage breakdown
            if formatted_messages:
                first_msg = formatted_messages[0]
                logger.info(f"LLM Service: First message role: {first_msg.get('role', 'unknown')}")
                if system_prompt:
                    logger.info(f"LLM Service: System prompt present, length: {len(system_prompt)} characters (~{len(system_prompt.split())} tokens)")
                else:
                    logger.warning(f"LLM Service: No system prompt found!")
                
                # Log message count and approximate token usage
                total_chars = sum(len(msg.get('content', '')) for msg in formatted_messages)
                logger.info(f"LLM Service: {len(formatted_messages)} messages, ~{total_chars} characters total (~{total_chars//4} tokens)")
            
            # Prepare API parameters
            api_params = {
                "model": self.model_name,
                "max_tokens": response_tokens,
                "temperature": temperature or settings.temperature,
                "messages": formatted_messages
            }
            
            # Note: cache_control parameter is not supported in the current API version
            # Caching is handled client-side through our cache manager
            
            # Add system prompt if available
            if system_prompt:
                api_params["system"] = system_prompt
            
            # Add tools if enabled
            tools = []
            
            # Add web fetch tool if enabled
            if settings.enable_web_fetch_tool:
                web_fetch_tool = {
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": settings.web_fetch_max_uses
                }
                tools.append(web_fetch_tool)
            
            # Add web search tool if enabled
            if settings.enable_web_search_tool:
                web_search_tool = {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": settings.web_search_max_uses
                }
                tools.append(web_search_tool)
            
            # Add text editor tool if enabled (for Claude 4 models)
            if settings.enable_text_editor_tool:
                text_editor_tool = {
                    "type": "text_editor_20250728",
                    "name": "str_replace_based_edit_tool",
                    "max_characters": settings.text_editor_max_characters
                }
                tools.append(text_editor_tool)
            
            # Add custom memory tool if enabled
            if settings.enable_claude_memory_tool:
                # Define custom memory tool
                memory_tool = {
                    "name": "memory",
                    "description": "Manage persistent memory storage for user information and context",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "enum": ["view", "create", "str_replace", "insert", "delete", "rename"],
                                "description": "The memory operation to perform"
                            },
                            "path": {
                                "type": "string",
                                "description": "File or directory path in memory storage"
                            },
                            "file_text": {
                                "type": "string",
                                "description": "Text content for create operations"
                            },
                            "old_str": {
                                "type": "string",
                                "description": "Text to replace in str_replace operations"
                            },
                            "new_str": {
                                "type": "string",
                                "description": "New text for str_replace operations"
                            },
                            "insert_line": {
                                "type": "integer",
                                "description": "Line number for insert operations"
                            },
                            "insert_text": {
                                "type": "string",
                                "description": "Text to insert"
                            },
                            "old_path": {
                                "type": "string",
                                "description": "Original path for rename operations"
                            },
                            "new_path": {
                                "type": "string",
                                "description": "New path for rename operations"
                            }
                        },
                        "required": ["command", "path"]
                    }
                }
                tools.append(memory_tool)
            
            
            # Set tools if any are enabled
            if tools:
                api_params["tools"] = tools
            
            # Apply rate limiting
            self._rate_limit()
            
            # Use standard API with beta headers
            response = self.client.messages.create(**api_params, extra_headers=self._get_beta_headers())
            
            # Log initial API call usage
            initial_usage = self._extract_usage_info(response)
            logger.info(f"Initial API call completed - {initial_usage['total_tokens']} total tokens used")
            
            # Check for tool calls and handle them properly
            if settings.enable_claude_memory_tool and response.content:
                # Check if Claude made any tool calls
                tool_calls = []
                memory_used = False
                
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type in ['tool_use', 'server_tool_use']:
                        tool_calls.append(content_block)
                        # Track which tools were used
                        if hasattr(content_block, 'name'):
                            if content_block.name == 'memory':
                                memory_used = True
                
                if tool_calls:
                    # Process tool calls and continue conversation
                    result = await self._handle_tool_calls_and_continue(response, tool_calls, session_id, api_params)
                    # Add tool usage information to the result
                    result['memory_used'] = memory_used
                    return result
            
            # Extract text from response (no tool calls) - collect all text blocks
            if response.content and len(response.content) > 0:
                # Collect all text content from all blocks
                text_blocks = []
                for content_block in response.content:
                    if hasattr(content_block, 'text') and content_block.text:
                        text_blocks.append(content_block.text.strip())
                    elif hasattr(content_block, 'type') and content_block.type == 'text' and hasattr(content_block, 'text') and content_block.text:
                        text_blocks.append(content_block.text.strip())
                
                if text_blocks:
                    # Concatenate all text blocks for complete response
                    response_text = "\n\n".join(text_blocks)
                else:
                    response_text = "I apologize, but I couldn't generate a response. Please try again."
            else:
                logger.warning("No content in Claude response")
                response_text = "I apologize, but I couldn't generate a response. Please try again."
            
            # Extract comprehensive usage information from Claude API response
            final_usage = self._extract_usage_info(response)
            
            # Prepare response data
            response_data = {
                "response": response_text,
                "error": None,
                "memory_used": False,
                "usage_info": final_usage,
                "tokens_used": response_tokens
            }
            
            # Cache the response if caching is enabled
            if settings.enable_prompt_caching:
                cache_manager.cache_response(
                    formatted_messages,
                    self.model_name,
                    max_tokens or settings.max_tokens,
                    temperature or settings.temperature,
                    response_data
                )
            
            logger.debug(f"Generated response length: {len(response_text)}")
            return response_data
            
        except Exception as e:
            # Use enhanced error handler
            error_info = error_handler.handle_claude_api_error(e)
            
            return {
                "response": error_info["message"],
                "error": error_info["error"],
                "usage_info": {},
                "tokens_used": 0,
                "retry_recommended": error_info["retry_recommended"],
                "retry_after_seconds": error_info["retry_after_seconds"]
            }
    
    async def _handle_tool_calls_and_continue(self, response, tool_calls, session_id: Optional[str], api_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tool calls and continue the conversation with Claude.
        
        This follows the documentation pattern:
        1. Claude makes tool calls
        2. We execute them locally
        3. We return tool results to Claude
        4. Claude continues with the tool results
        
        Args:
            response: Claude API response object
            tool_calls: List of tool calls from Claude
            session_id: Session ID for context
            api_params: Original API parameters
            
        Returns:
            Dictionary with final response text and metadata
        """
        try:
            # Prepare messages for continuation
            messages = api_params["messages"].copy()
            
            # Add Claude's response (including tool calls) to messages
            claude_message = {
                "role": "assistant",
                "content": []
            }
            
            for content_block in response.content:
                if hasattr(content_block, 'type'):
                    if content_block.type == 'text':
                        claude_message["content"].append({
                            "type": "text",
                            "text": content_block.text
                        })
                    elif content_block.type == 'tool_use' and content_block.name == 'memory':
                        # Only add client tools to conversation - server tools are handled internally
                        claude_message["content"].append({
                            "type": "tool_use",
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": content_block.input
                        })
            
            messages.append(claude_message)
            
            # Execute tool calls and prepare tool results
            tool_results = []
            memory_used = False
            
            for tool_call in tool_calls:
                if tool_call.name == 'memory':
                    memory_used = True
                    # Execute memory tool call
                    tool_result = await self._handle_memory_tool_call(tool_call.input, session_id)
                    
                    # Create a more informative tool result
                    if tool_result.get("success"):
                        content = tool_result.get("content", "")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": f"Memory operation completed: {content}"
                        })
                    else:
                        error_msg = tool_result.get('error', 'Unknown error')
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": f"Memory operation failed: {error_msg}. Please continue with your response despite this memory operation issue."
                        })
            
            # Add tool results to messages
            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
            
            # Continue conversation with Claude using the tool results
            logger.info("Continuing conversation with Claude after tool calls")
            
            # Update API parameters with new messages
            continue_params = api_params.copy()
            continue_params["messages"] = messages
            
            # Ensure continuation calls have enough tokens for comprehensive responses
            if continue_params.get("max_tokens", 0) < CONTINUATION_TOKEN_MINIMUM:
                continue_params["max_tokens"] = CONTINUATION_TOKEN_MINIMUM
            
            # Make another API call to get Claude's final response
            logger.info(f"Making continuation API call with {len(messages)} messages")
            self._rate_limit()
            
            final_response = self.client.messages.create(**continue_params, extra_headers=self._get_beta_headers())
            
            # Log continuation API call usage
            continuation_usage = self._extract_usage_info(final_response)
            logger.info(f"Continuation API call completed - {continuation_usage['total_tokens']} total tokens used")
            logger.info(f"Continuation response received: {type(final_response)} with {len(final_response.content) if final_response.content else 0} content blocks")
            
            # Check if the response contains more tool calls - limit to prevent infinite loops
            if final_response.stop_reason == "tool_use":
                logger.info("Final response contains more tool calls, processing them...")
                # Extract tool calls from the final response
                additional_tool_calls = []
                for content_block in final_response.content:
                    if hasattr(content_block, 'type') and content_block.type in ['tool_use', 'server_tool_use']:
                        additional_tool_calls.append(content_block)
                
                # Limit to prevent infinite loops - only process one round of additional tools
                if len(additional_tool_calls) > 0 and len(additional_tool_calls) <= 2:  # Reasonable limit
                    # First, add the assistant's tool use to the conversation (only for client tools)
                    assistant_tool_use_content = []
                    for tool_call in additional_tool_calls:
                        if tool_call.name == 'memory':  # Only add client tools
                            assistant_tool_use_content.append({
                                "type": "tool_use",
                                "id": tool_call.id,
                                "name": tool_call.name,
                                "input": tool_call.input
                            })
                    
                    if assistant_tool_use_content:
                        messages.append({
                            "role": "assistant",
                            "content": assistant_tool_use_content
                        })
                    
                    # Then execute tools and add results
                    additional_tool_results = []
                    for tool_call in additional_tool_calls:
                        if tool_call.name == 'memory':
                            # Execute the tool
                            tool_result = await self._handle_memory_tool_call(tool_call.input, session_id)
                            
                            # Create a more informative tool result
                            if tool_result.get("success"):
                                content = tool_result.get("content", "")
                                additional_tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_call.id,
                                    "content": f"Memory operation completed: {content}"
                                })
                            else:
                                error_msg = tool_result.get('error', 'Unknown error')
                                additional_tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_call.id,
                                    "content": f"Memory operation failed: {error_msg}. Please continue with your response despite this memory operation issue."
                                })
                    
                    # Add tool results to messages
                    if additional_tool_results:
                        messages.append({
                            "role": "user",
                            "content": additional_tool_results
                        })
                    
                    # Make final API call without tools to force text response
                    final_params = continue_params.copy()
                    final_params["messages"] = messages
                    final_params.pop("tools", None)  # Remove tools to force text response
                    final_params.pop("tool_choice", None)  # Remove tool choice
                    final_params["max_tokens"] = CONTINUATION_TOKEN_MINIMUM
                    
                    logger.info(f"Making final API call without tools to get text response")
                    self._rate_limit()
                    
                    final_response = self.client.messages.create(**final_params, extra_headers=self._get_beta_headers())
                    
                    # Log final API call usage
                    final_api_usage = self._extract_usage_info(final_response)
                    logger.info(f"Final API call completed - {final_api_usage['total_tokens']} total tokens used")
                    logger.info(f"Final response received: {type(final_response)} with {len(final_response.content) if final_response.content else 0} content blocks")
                else:
                    logger.warning(f"Too many additional tool calls ({len(additional_tool_calls)}), skipping to prevent infinite loops")
            
            # Extract final response text - collect all text blocks for complete response
            if final_response.content and len(final_response.content) > 0:
                logger.info(f"Processing {len(final_response.content)} content blocks")
                
                # Collect all text content from all blocks
                text_blocks = []
                for i, content_block in enumerate(final_response.content):
                    logger.info(f"Content block {i}: type={type(content_block)}, has text={hasattr(content_block, 'text')}, has type attr={hasattr(content_block, 'type')}")
                    
                    if hasattr(content_block, 'text') and content_block.text:
                        text_blocks.append(content_block.text.strip())
                        logger.info(f"Found text in block {i}: {len(content_block.text)} characters")
                    elif hasattr(content_block, 'type') and content_block.type == 'text' and hasattr(content_block, 'text') and content_block.text:
                        text_blocks.append(content_block.text.strip())
                        logger.info(f"Found text in block {i} (type=text): {len(content_block.text)} characters")
                
                if text_blocks:
                    # Concatenate all text blocks for complete response
                    response_text = "\n\n".join(text_blocks)
                    logger.info(f"Combined response from {len(text_blocks)} text blocks: {len(response_text)} characters")
                else:
                    # No text blocks found - this happens when only tool results are returned
                    # Make another API call to get the actual response
                    logger.warning("No text blocks found in response, making another API call to get response")
                    
                    # Add a more specific user message to prompt for the response
                    messages.append(Message(role=MessageRole.USER, content="Please provide a response to the original question."))
                    
                    # Make another API call without tools to force text response
                    final_params = continue_params.copy()
                    final_params["messages"] = messages
                    final_params.pop("tools", None)  # Remove tools to force text response
                    final_params.pop("tool_choice", None)  # Remove tool choice
                    
                    # Ensure we have enough tokens for a comprehensive response
                    final_params["max_tokens"] = FINAL_CALL_TOKEN_LIMIT
                    
                    logger.info(f"Making final API call without tools to get text response")
                    self._rate_limit()
                    
                    text_response = self.client.messages.create(**final_params, extra_headers=self._get_beta_headers())
                    
                    # Log text response API call usage
                    text_usage = self._extract_usage_info(text_response)
                    logger.info(f"Text response API call completed - {text_usage['total_tokens']} total tokens used")
                    
                    # Extract text from this response
                    if text_response.content and len(text_response.content) > 0:
                        text_blocks = []
                        for content_block in text_response.content:
                            if hasattr(content_block, 'text') and content_block.text:
                                text_blocks.append(content_block.text.strip())
                        
                        if text_blocks:
                            response_text = "\n\n".join(text_blocks)
                            logger.info(f"Got text response from final call: {len(response_text)} characters")
                        else:
                            response_text = "I apologize, but I couldn't generate a response after processing the search results."
                            logger.warning("Still no text blocks found in final response")
                    else:
                        response_text = "I apologize, but I couldn't generate a response after processing the search results."
                        logger.warning("No content in final response")
            else:
                logger.warning("No content in final response")
                response_text = "I apologize, but I encountered a technical issue generating a response. Please try asking your question again, and I'll do my best to provide a helpful answer."
            
            # Extract comprehensive usage information from Claude API response
            final_usage = self._extract_usage_info(final_response)
            
            return {
                "response": response_text,
                "error": None,
                "memory_used": memory_used,
                "usage_info": final_usage,
                "tokens_used": api_params.get("max_tokens", 4096),
                "tool_calls_processed": len(tool_calls)
            }
            
        except Exception as e:
            # Use enhanced error handler
            error_info = error_handler.handle_claude_api_error(e)
            
            return {
                "response": error_info["message"],
                "error": error_info["error"],
                "usage_info": {},
                "tokens_used": 0,
                "tool_calls_processed": 0,
                "retry_recommended": error_info["retry_recommended"],
                "retry_after_seconds": error_info["retry_after_seconds"]
            }
    
    async def _handle_memory_tool_call(self, tool_input: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle a memory tool call from Claude.
        
        Args:
            tool_input: The input parameters for the memory tool
            session_id: Session ID for context
            
        Returns:
            Dictionary with the result of the memory operation
        """
        try:
            logger.info(f"Handling memory tool call: {tool_input} for session: {session_id}")
            
            # Process the memory command with session scoping
            result = await claude_memory_tool_handler.handle_memory_command(tool_input, session_id)
            
            logger.info(f"Memory tool result: {result}")
            return result
            
        except Exception as e:
            # Use enhanced error handler for tool errors
            error_info = error_handler.handle_tool_error("memory", e)
            return {
                "success": False,
                "error": error_info["error"],
                "content": error_info["message"]
            }
    
    def _format_messages_for_claude(self, messages: List[Message]) -> Tuple[List[Dict[str, str]], str]:
        """Format messages for Claude messages API with sustainability focus."""
        formatted_messages = []
        system_prompt = None
        
        # Extract system prompt from messages
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                system_prompt = message.content
                break
        
        # Add default system prompt if none found (simplified to avoid conflicts)
        if not system_prompt:
            system_prompt = "You are EarthGPT, a sustainability expert. Respond naturally and conversationally."
        
        # Convert messages to Claude format, properly handling system messages
        for message in messages:
            if message.role == MessageRole.USER:
                formatted_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif message.role == MessageRole.ASSISTANT:
                formatted_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
            # Skip system messages as they're handled separately
        
        return formatted_messages, system_prompt
    
    def generate_response_simple(
        self, 
        messages: List[Message], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        is_detailed: bool = False,
        session_id: Optional[str] = None
    ) -> str:
        """
        Generate a response from Claude API (backward-compatible method).
        
        Returns just the response text for existing code compatibility.
        """
        result = self.generate_response(messages, max_tokens, temperature, is_detailed, session_id)
        return result.get("response", "I'm sorry, I couldn't generate a response.")
    
    async def generate_response_streaming(
        self, 
        messages: List[Message], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        is_detailed: bool = False,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a streaming response from Claude API.
        
        Args:
            messages: List of conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            is_detailed: Whether to generate a detailed response
            session_id: Session ID for memory tool context
            
        Yields:
            Dictionary with streaming response chunks
        """
        if not self.is_loaded:
            logger.error("Claude API client not initialized, attempting to initialize...")
            if not self.load_model():
                logger.error("Failed to initialize Claude API client")
                yield {
                    "type": "error",
                    "content": "I'm sorry, the Claude API is not currently available. Please check your API key and try again later.",
                    "error": "api_not_available"
                }
                return
        
        try:
            # Format messages for Claude API
            formatted_messages, system_prompt = self._format_messages_for_claude(messages)
            
            # Calculate token usage and validate request
            expected_output_tokens = max_tokens or settings.max_tokens
            if is_detailed:
                expected_output_tokens = min(expected_output_tokens * DETAILED_RESPONSE_MULTIPLIER, 4096)
            
            # Validate context window
            validation = self.context_manager.validate_request(formatted_messages, expected_output_tokens)
            
            if not validation["valid"]:
                logger.warning(f"Request exceeds context window: {validation['usage_info']}")
                yield {
                    "type": "error",
                    "content": "I'm sorry, this conversation has become too long for me to process effectively. Please start a new conversation or ask a more focused question.",
                    "error": "context_window_exceeded",
                    "usage_info": validation["usage_info"],
                    "recommendations": validation["recommendations"]
                }
                return
            
            # Truncate if needed
            if self.context_manager.should_truncate(formatted_messages, expected_output_tokens):
                logger.info("Truncating conversation to fit context window")
                formatted_messages, truncation_info = self.context_manager.truncate_conversation(
                    formatted_messages, expected_output_tokens
                )
                logger.info(f"Truncation info: {truncation_info}")
            
            # Get optimal output tokens
            optimal_tokens = self.context_manager.get_optimal_output_tokens(formatted_messages)
            response_tokens = min(expected_output_tokens, optimal_tokens)
            
            # Prepare API parameters
            api_params = {
                "model": self.model_name,
                "max_tokens": response_tokens,
                "temperature": temperature or settings.temperature,
                "messages": formatted_messages,
                "stream": True  # Enable streaming
            }
            
            # Add system prompt if available
            if system_prompt:
                api_params["system"] = system_prompt
            
            # Add tools if enabled
            tools = []
            
            # Add web fetch tool if enabled
            if settings.enable_web_fetch_tool:
                web_fetch_tool = {
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": settings.web_fetch_max_uses
                }
                tools.append(web_fetch_tool)
            
            # Add web search tool if enabled
            if settings.enable_web_search_tool:
                web_search_tool = {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": settings.web_search_max_uses
                }
                tools.append(web_search_tool)
            
            # Add text editor tool if enabled (for Claude 4 models)
            if settings.enable_text_editor_tool:
                text_editor_tool = {
                    "type": "text_editor_20250728",
                    "name": "str_replace_based_edit_tool",
                    "max_characters": settings.text_editor_max_characters
                }
                tools.append(text_editor_tool)
            
            # Add custom memory tool if enabled
            if settings.enable_claude_memory_tool:
                # Define custom memory tool
                memory_tool = {
                    "name": "memory",
                    "description": "Manage persistent memory storage for user information and context",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "enum": ["view", "create", "str_replace", "insert", "delete", "rename"],
                                "description": "The memory operation to perform"
                            },
                            "path": {
                                "type": "string",
                                "description": "File or directory path in memory storage"
                            },
                            "file_text": {
                                "type": "string",
                                "description": "Text content for create operations"
                            },
                            "old_str": {
                                "type": "string",
                                "description": "Text to replace in str_replace operations"
                            },
                            "new_str": {
                                "type": "string",
                                "description": "New text for str_replace operations"
                            },
                            "insert_line": {
                                "type": "integer",
                                "description": "Line number for insert operations"
                            },
                            "insert_text": {
                                "type": "string",
                                "description": "Text to insert"
                            },
                            "old_path": {
                                "type": "string",
                                "description": "Original path for rename operations"
                            },
                            "new_path": {
                                "type": "string",
                                "description": "New path for rename operations"
                            }
                        },
                        "required": ["command", "path"]
                    }
                }
                tools.append(memory_tool)
            
            # Set tools if any are enabled
            if tools:
                api_params["tools"] = tools
            
            # Apply rate limiting
            self._rate_limit()
            
            # Stream the response
            async with self.client.messages.stream(**api_params, extra_headers=self._get_beta_headers()) as stream:
                async for chunk in stream:
                    if chunk.type == "content_block_delta":
                        yield {
                            "type": "content",
                            "content": chunk.delta.text,
                            "chunk_id": getattr(chunk, 'index', 0)
                        }
                    elif chunk.type == "message_start":
                        yield {
                            "type": "message_start",
                            "message_id": chunk.message.id,
                            "model": chunk.message.model
                        }
                    elif chunk.type == "message_delta":
                        if hasattr(chunk, 'usage') and chunk.usage:
                            yield {
                                "type": "usage",
                                "usage": {
                                    "input_tokens": getattr(chunk.usage, 'input_tokens', 0),
                                    "output_tokens": getattr(chunk.usage, 'output_tokens', 0),
                                    "total_tokens": getattr(chunk.usage, 'input_tokens', 0) + getattr(chunk.usage, 'output_tokens', 0)
                                }
                            }
                    elif chunk.type == "message_stop":
                        yield {
                            "type": "message_stop",
                            "stop_reason": getattr(chunk, 'stop_reason', 'end_turn')
                        }
                    elif chunk.type == "error":
                        yield {
                            "type": "error",
                            "content": f"Streaming error: {chunk.error}",
                            "error": chunk.error
                        }
                        
        except Exception as e:
            # Use enhanced error handler
            error_info = error_handler.handle_claude_api_error(e)
            yield {
                "type": "error",
                "content": error_info["message"],
                "error": error_info["error"],
                "retry_recommended": error_info["retry_recommended"],
                "retry_after_seconds": error_info["retry_after_seconds"]
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the Claude API configuration."""
        return {
            "model_name": self.model_name,
            "api_provider": "Anthropic Claude",
            "is_loaded": self.is_loaded,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "has_api_key": bool(self.api_key),
            "context_window": self.context_manager.config.max_context_tokens,
            "max_output_tokens": self.context_manager.config.max_output_tokens,
            "streaming_enabled": settings.enable_streaming
        }


# Global LLM service instance
llm_service = LLMService()
logger.info("Using Claude API LLM service")