"""Main FastAPI application for the Sustainability Assistant."""

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

from api.routes import router
from api.auth_routes import router as auth_router
from services.llm_service import llm_service
from core.pinecone_memory import PineconeMemoryManager
from database.mongodb import mongodb
from config import settings


# Configure logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
logger.add(
    settings.log_file,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="1 day",
    retention="30 days"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Sustainability Assistant API...")
    
    # Connect to MongoDB
    try:
        await mongodb.connect()
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # In production, you might want to exit here
        # sys.exit(1)
    
    # Initialize LLM service
    if not llm_service.load_model():
        logger.error("Failed to load LLM model")
        # In production, you might want to exit here
        # sys.exit(1)
    
    # Initialize memory manager
    memory_manager = PineconeMemoryManager()
    logger.info("Memory manager initialized")
    
    # Clean up old sessions on startup
    memory_manager.cleanup_old_sessions(hours=24)
    
    logger.info("Sustainability Assistant API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sustainability Assistant API...")
    
    # Disconnect from MongoDB
    await mongodb.disconnect()
    logger.info("Disconnected from MongoDB")


# Create FastAPI application
app = FastAPI(
    title="Sustainability Assistant API",
    description="AI-powered sustainability expert assistant with domain-specific guardrails",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
app.include_router(auth_router)


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "detail": f"Request to {request.url} failed",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Sustainability Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = logger.bind().info("Request started")
    
    response = await call_next(request)
    
    process_time = logger.bind().info("Request completed")
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    
    return response


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
