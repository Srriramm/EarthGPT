"""Batch request service for handling multiple Claude API requests."""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from models.schemas import Message
from services.llm_service import llm_service
from config import settings


class BatchService:
    """Service for handling batch requests to Claude API."""
    
    def __init__(self):
        """Initialize the batch service."""
        self.max_batch_size = 10  # Maximum number of requests per batch
        self.max_concurrent_requests = 5  # Maximum concurrent requests
        
        logger.info(f"Batch service initialized with max batch size: {self.max_batch_size}")
    
    async def process_batch_requests(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple requests in batch.
        
        Args:
            requests: List of request dictionaries with the following structure:
                {
                    "id": "unique_request_id",
                    "messages": List[Message],
                    "max_tokens": Optional[int],
                    "temperature": Optional[float],
                    "is_detailed": bool,
                    "session_id": Optional[str]
                }
        
        Returns:
            List of response dictionaries with the following structure:
                {
                    "id": "unique_request_id",
                    "response": str,
                    "error": Optional[str],
                    "usage_info": Dict[str, Any],
                    "success": bool
                }
        """
        if not requests:
            return []
        
        # Validate batch size
        if len(requests) > self.max_batch_size:
            logger.warning(f"Batch size {len(requests)} exceeds maximum {self.max_batch_size}")
            requests = requests[:self.max_batch_size]
        
        # Process requests concurrently with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def process_single_request(request: Dict[str, Any]) -> Dict[str, Any]:
            """Process a single request with semaphore control."""
            async with semaphore:
                try:
                    request_id = request.get("id", "unknown")
                    messages = request.get("messages", [])
                    max_tokens = request.get("max_tokens")
                    temperature = request.get("temperature")
                    is_detailed = request.get("is_detailed", False)
                    session_id = request.get("session_id")
                    
                    # Generate response using LLM service
                    result = await llm_service.generate_response(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        is_detailed=is_detailed,
                        session_id=session_id
                    )
                    
                    return {
                        "id": request_id,
                        "response": result.get("response", ""),
                        "error": result.get("error"),
                        "usage_info": result.get("usage_info", {}),
                        "success": result.get("error") is None,
                        "memory_used": result.get("memory_used", False),
                        "tokens_used": result.get("tokens_used", 0)
                    }
                    
                except Exception as e:
                    logger.error(f"Error processing request {request.get('id', 'unknown')}: {e}")
                    return {
                        "id": request.get("id", "unknown"),
                        "response": "",
                        "error": str(e),
                        "usage_info": {},
                        "success": False,
                        "memory_used": False,
                        "tokens_used": 0
                    }
        
        # Process all requests concurrently
        logger.info(f"Processing batch of {len(requests)} requests")
        results = await asyncio.gather(*[process_single_request(req) for req in requests])
        
        # Log batch statistics
        successful_requests = sum(1 for result in results if result["success"])
        total_tokens = sum(result["tokens_used"] for result in results)
        
        logger.info(f"Batch processing completed: {successful_requests}/{len(requests)} successful, {total_tokens} total tokens")
        
        return results
    
    async def process_batch_streaming(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple streaming requests in batch.
        
        Args:
            requests: List of request dictionaries (same structure as process_batch_requests)
        
        Returns:
            List of streaming response generators
        """
        if not requests:
            return []
        
        # Validate batch size
        if len(requests) > self.max_batch_size:
            logger.warning(f"Batch size {len(requests)} exceeds maximum {self.max_batch_size}")
            requests = requests[:self.max_batch_size]
        
        # Process streaming requests concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def process_single_streaming_request(request: Dict[str, Any]):
            """Process a single streaming request with semaphore control."""
            async with semaphore:
                try:
                    request_id = request.get("id", "unknown")
                    messages = request.get("messages", [])
                    max_tokens = request.get("max_tokens")
                    temperature = request.get("temperature")
                    is_detailed = request.get("is_detailed", False)
                    session_id = request.get("session_id")
                    
                    # Generate streaming response using LLM service
                    async for chunk in llm_service.generate_response_streaming(
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        is_detailed=is_detailed,
                        session_id=session_id
                    ):
                        # Add request ID to each chunk
                        chunk["request_id"] = request_id
                        yield chunk
                        
                except Exception as e:
                    logger.error(f"Error processing streaming request {request.get('id', 'unknown')}: {e}")
                    yield {
                        "request_id": request.get("id", "unknown"),
                        "type": "error",
                        "content": f"Error processing request: {str(e)}",
                        "error": str(e)
                    }
        
        # Create streaming generators for all requests
        streaming_generators = [process_single_streaming_request(req) for req in requests]
        
        logger.info(f"Created {len(streaming_generators)} streaming generators for batch processing")
        
        return streaming_generators
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batch service statistics."""
        return {
            "max_batch_size": self.max_batch_size,
            "max_concurrent_requests": self.max_concurrent_requests,
            "service_status": "active"
        }


# Global batch service instance
batch_service = BatchService()

