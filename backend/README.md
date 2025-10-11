# EarthGPT Backend

A sustainability-focused AI assistant backend built with FastAPI, featuring advanced guardrails, MongoDB-based memory management, and intelligent conversation handling.

## Architecture Overview

EarthGPT Backend is designed as a modular, scalable system that combines MongoDB-based memory management with advanced guardrails to provide intelligent sustainability-focused conversations while maintaining strict content filtering and context awareness.

### Core Components
- **FastAPI Application**: RESTful API with JWT authentication
- **Hybrid Guardrail System**: Multi-layer content filtering using embeddings + LLM classification
- **MongoDB Memory Management**: Session-based memory and conversation storage
- **Smart Context Management**: Intelligent conversation history and token optimization
- **Multi-Model LLM Integration**: Claude Sonnet 4.5 (main) + Claude 3.5 Haiku (classification/summarization)

## Directory Structure

```
backend/
├── api/                    # API endpoints and routing
│   ├── routes.py          # Main chat endpoints
│   └── auth_routes.py     # Authentication endpoints
├── auth/                   # Authentication and authorization
│   └── dependencies.py    # Auth dependencies and middleware
├── core/                   # Core business logic and services
│   ├── mongodb_memory.py  # MongoDB-based session and memory management
│   ├── claude_memory_tool.py # Claude Memory Tool implementation
│   ├── prompt_engineering.py # Prompt construction and optimization
│   ├── classification_llm.py # LLM service for classification (Claude 3.5 Haiku)
│   ├── summarization_llm.py # LLM service for summarization (Claude 3.5 Haiku)
│   ├── title_generator.py # Conversation title generation
│   ├── token_manager.py   # Token counting and context window management
│   ├── cache_manager.py   # Prompt caching system
│   └── error_handler.py   # Enhanced error handling
├── database/               # Database connections and configuration
│   └── mongodb.py         # MongoDB connection manager
├── guardrails/             # Content filtering and validation
│   ├── __init__.py        # Guardrails module exports
│   ├── base.py            # Base guardrails class
│   ├── models.py          # Guardrail data models
│   ├── hybrid_classifier_guardrails.py # Main guardrail system
│   └── intelligent_output_validator.py # Response validation
├── models/                 # Data models and schemas
│   ├── schemas.py         # Pydantic models for API
│   └── user.py            # User and session models
├── services/               # External service integrations
│   ├── llm_service.py     # Main LLM service (Claude Sonnet 4)
│   └── batch_service.py   # Batch request processing
├── logs/                   # Application logs
├── config.py              # Application configuration
├── main.py                # FastAPI application entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Core Files Explained

### Configuration & Entry Point

#### `config.py`
**Purpose**: Central configuration management using Pydantic BaseSettings
**Key Settings**:
- Database connections (MongoDB)
- LLM model configurations (Claude Sonnet 4, Claude 3.5 Haiku)
- API keys and environment variables
- Token limits and optimization parameters
- Security settings and CORS configuration

#### `main.py`
**Purpose**: FastAPI application entry point and middleware setup
**Features**:
- CORS configuration with environment-specific origins
- Request/response logging
- Health check endpoints
- Application lifecycle management
- Error handling middleware

### API Layer (`api/`)

#### `api/routes.py`
**Purpose**: Main API endpoints for authenticated chat functionality
**Key Endpoints**:
- `POST /api/v1/chat` - Authenticated chat
- `GET /api/v1/sessions` - Get user sessions
- `GET /api/v1/sessions/{session_id}/history` - Get session history
- `DELETE /api/v1/sessions/{session_id}` - Delete session
- `GET /api/v1/health` - Health check

**Flow**:
1. **Authentication**: Validates JWT token and user access
2. **Session Management**: Creates or retrieves conversation sessions via MongoDB
3. **Guardrail Check**: Validates sustainability relevance using hybrid classifier
4. **Context Retrieval**: Gets optimized conversation context from MongoDB
5. **LLM Generation**: Generates response using Claude Sonnet 4.5 with Claude Memory Tool
6. **Memory Storage**: Stores conversation in MongoDB session manager
7. **Title Generation**: Generates conversation titles for long sessions

#### `api/auth_routes.py`
**Purpose**: Authentication and user management endpoints
**Features**:
- User registration and login
- JWT token management
- User session handling

### Authentication (`auth/`)

#### `auth/dependencies.py`
**Purpose**: Authentication and authorization dependencies
**Features**:
- JWT token validation
- User session management
- Role-based access control
- Security middleware integration

### Core Business Logic (`core/`)

#### `core/mongodb_memory.py`
**Purpose**: MongoDB-based session and memory management
**Key Features**:
- **Session Management**: Creates and manages conversation sessions
- **Message Storage**: Stores user and assistant messages in MongoDB
- **Context Building**: Retrieves recent messages and relevant memories
- **Memory Search**: Simple text-based memory search within sessions
- **Session Metadata**: Tracks session information and activity

**Key Methods**:
- `create_session()`: Creates new conversation sessions
- `add_message_to_session()`: Stores messages in sessions
- `build_context()`: Builds optimized context for responses
- `get_session_messages()`: Retrieves message history
- `search_memories()`: Searches memories within sessions

#### `core/claude_memory_tool.py`
**Purpose**: Implementation of Claude's native Memory Tool
**Features**:
- **Memory Commands**: Implements view, create, str_replace, insert, delete, rename
- **MongoDB Integration**: Stores memory operations in MongoDB
- **Session Scoping**: Memory operations are scoped to sessions
- **Security**: Path validation and safe memory operations

#### `core/prompt_engineering.py`
**Purpose**: Intelligent prompt construction and optimization
**Features**:
- **System Prompt Management**: Maintains EarthGPT's sustainability-focused persona
- **Context Integration**: Incorporates relevant historical context
- **Length Control**: Detects user intent for response length
- **Token Management**: Optimizes prompt length within model limits
- **Conversation History**: Limits history to prevent context pollution

#### `core/classification_llm.py`
**Purpose**: Dedicated LLM service for sustainability classification using Claude 3.5 Haiku
**Features**:
- **Fast Classification**: Optimized for quick YES/NO sustainability relevance decisions
- **Cost-Effective**: Uses Haiku model for classification tasks
- **Deterministic**: Low temperature (0.0) for consistent results

#### `core/summarization_llm.py`
**Purpose**: LLM service for conversation summarization using Claude 3.5 Haiku
**Features**:
- **Conversation Summarization**: Creates concise summaries of long conversations
- **Context Compression**: Reduces token usage while preserving key information
- **Incremental Updates**: Updates summaries as conversations progress

#### `core/title_generator.py`
**Purpose**: Generates conversation titles for long chat sessions
**Features**:
- **Automatic Title Generation**: Creates descriptive titles after 3+ messages
- **Context-Aware**: Uses conversation content to generate relevant titles
- **User-Friendly**: Helps users identify and manage conversations

#### `core/token_manager.py`
**Purpose**: Token counting and context window management
**Features**:
- **Token Counting**: Accurate token estimation for different models
- **Context Window Management**: Optimizes context within model limits
- **Message Truncation**: Intelligently truncates messages when needed

#### `core/cache_manager.py`
**Purpose**: Prompt caching system for Claude API responses
**Features**:
- **Response Caching**: Caches API responses to reduce costs and latency
- **TTL Management**: Configurable cache expiration
- **Memory Management**: Automatic cleanup of old cache entries
- **Statistics**: Cache hit/miss tracking

#### `core/error_handler.py`
**Purpose**: Enhanced error handling for Claude API and tools
**Features**:
- **Error Classification**: Categorizes different types of errors
- **User-Friendly Messages**: Converts technical errors to user-friendly responses
- **Retry Logic**: Determines when errors should be retried
- **Rate Limiting**: Handles API rate limit errors

### Guardrails (`guardrails/`)

#### `guardrails/hybrid_classifier_guardrails.py`
**Purpose**: Advanced multi-layer content filtering system
**Architecture**:
1. **Layer 1 - Embedding Classification**: Fast semantic similarity against sustainability categories using SentenceTransformer
2. **Layer 2 - LLM Classification**: Claude 3.5 Haiku fallback for uncertain cases
3. **Layer 3 - Follow-up Detection**: Two-layer system (pattern-based + LLM-based) for conversation continuity
4. **Layer 4 - Output Validation**: Intelligent response validation using semantic similarity

**Key Features**:
- **Hybrid Approach**: Combines speed of embeddings with accuracy of LLM
- **Two-Layer Follow-up Detection**: Pattern-based + LLM-based for conversation continuity
- **Intelligent Output Validation**: Semantic similarity + context-aware thresholds
- **Sustainability Categories**: Comprehensive environmental and sustainability topic coverage
- **Memory Query Detection**: Allows memory-related questions through guardrails

#### `guardrails/intelligent_output_validator.py`
**Purpose**: Advanced response validation using semantic similarity
**Features**:
- **Semantic Validation**: Uses sentence transformers for content similarity
- **Adaptive Thresholds**: Adjusts validation strictness based on input confidence
- **Technical Term Recognition**: Recognizes sustainability-specific terminology
- **Graceful Fallbacks**: Falls back to basic validation if semantic validation fails

#### `guardrails/base.py`
**Purpose**: Base class for all guardrail implementations
**Features**:
- **Abstract Interface**: Defines common guardrail methods
- **Consistent API**: Standardized interface for all guardrail types

#### `guardrails/models.py`
**Purpose**: Data models for guardrail system
**Features**:
- **GuardrailCheck**: Result model for guardrail decisions
- **Type Safety**: Pydantic models for validation

### Services (`services/`)

#### `services/llm_service.py`
**Purpose**: Main LLM service integration with Claude Sonnet 4
**Features**:
- **Response Generation**: Primary chat response generation
- **Token Management**: Handles context window limits and optimization
- **Error Handling**: Robust error handling and fallback mechanisms
- **Memory Tool Integration**: Uses Claude's native Memory Tool
- **Streaming Support**: Supports streaming responses
- **Rate Limiting**: Prevents API rate limit errors

#### `services/batch_service.py`
**Purpose**: Batch request processing for multiple Claude API requests
**Features**:
- **Concurrent Processing**: Processes multiple requests in parallel
- **Semaphore Control**: Limits concurrent requests to prevent rate limiting
- **Error Handling**: Individual request error handling
- **Statistics**: Batch processing metrics and monitoring

### Database (`database/`)

#### `database/mongodb.py`
**Purpose**: MongoDB connection and database management
**Features**:
- **Async Connection**: Motor-based async MongoDB client
- **Connection Management**: Handles connection lifecycle
- **Index Creation**: Automatic index creation for performance
- **Error Handling**: Robust error handling and logging

### Models (`models/`)

#### `models/schemas.py`
**Purpose**: Pydantic models for API request/response validation
**Key Models**:
- `ConversationRequest`: Input validation for chat messages
- `ConversationResponse`: Response formatting and metadata
- `SessionInfo`: Session management and tracking
- `Message`: Individual message structure
- `User`: User authentication and profile data
- `MemoryContext`: Context retrieval from memory system

#### `models/user.py`
**Purpose**: User and session data models
**Features**:
- **User Management**: User registration and authentication
- **Session Models**: Chat session tracking and management
- **Database Integration**: MongoDB collection definitions

## Complete Backend Flow

### 1. Sustainability-Based Question Flow
**Example: "What are the benefits of solar energy?"**

1. **API Entry Point**
   - User sends request to `/api/v1/chat`
   - Authentication check via JWT token
   - Session management (create new or retrieve existing)

2. **Guardrail Processing**
   - Fast path check for obvious non-sustainability terms
   - Hybrid classification system:
     - Embedding-based classification using SentenceTransformer
     - LLM classification using Claude 3.5 Haiku for uncertain cases
   - Query passes sustainability check

3. **Context Building**
   - System prompt added ("You are EarthGPT, a sustainability expert...")
   - Context summary from previous conversations retrieved
   - Recent message history (last 6 messages) added
   - Current user message appended

4. **Response Generation**
   - Claude Sonnet 4.5 generates response
   - Claude Memory Tool may be used for persistent knowledge storage
   - Token management ensures context window limits

5. **Memory Storage**
   - User message stored in MongoDB session
   - Assistant response stored in MongoDB session
   - Claude Memory Tool stores persistent knowledge if used

6. **Response Return**
   - Complete response with metadata returned
   - Session activity updated
   - Title generated if first exchange

### 2. Non-Sustainability Question Flow
**Example: "How do I cook pasta?"**

1. **Initial Processing**
   - API route receives request
   - Authentication and session management

2. **Fast Guardrail Check**
   - Detects obvious non-sustainability terms (cooking, recipes, etc.)
   - Checks for sustainability indicators in query
   - No sustainability context found

3. **Block Decision**
   - Query blocked immediately
   - No further processing occurs

4. **Refusal Response**
   - Polite message returned: "I'm specialized in sustainability topics..."
   - User directed to ask about environmental issues, climate change, etc.

### 3. Follow-up Question Flow
**Example: "Can you elaborate on that?"**

1. **Follow-up Detection**
   - Layer 1: Pattern-based detection (explain more, elaborate, tell me more, etc.)
   - Layer 2: LLM-based detection for ambiguous cases using Claude 3.5 Haiku

2. **Context Analysis**
   - Retrieves previous conversation context
   - Calculates sustainability score of context (≥0.3 threshold)

3. **Decision Logic**
   - High context sustainability score → Allow with high confidence (0.95)
   - Low context sustainability score → Allow with lower confidence (0.8)

4. **Processing**
   - Continues with normal response generation flow
   - Uses conversation context to generate relevant response

### 4. Memory-Based Question Flow
**Example: "Do you remember what we discussed about carbon emissions?"**

1. **Memory Detection**
   - Identifies memory-related phrases ("remember", "discussed", "you said", etc.)
   - Memory query allowed through guardrails

2. **Context Retrieval**
   - Searches MongoDB session memories
   - Accesses Claude Memory Tool for persistent knowledge
   - Retrieves relevant historical context

3. **Memory Integration**
   - Combines recent session context with persistent memory
   - Builds comprehensive context for response generation

4. **Response Generation**
   - Claude generates response using retrieved memory context
   - Response includes information from previous conversations

5. **Memory Update**
   - New information may be stored in Claude Memory Tool
   - Response stored in MongoDB session

### 5. Other Scenarios

#### A. Streaming Response Flow
1. **Streaming Request**
   - User requests streaming response
   - LLM Service generates response stream

2. **Real-time Processing**
   - Response generated in chunks
   - Content deltas sent to client in real-time
   - Client receives updates as they're generated

#### B. Batch Request Flow
1. **Batch Processing**
   - Multiple requests processed concurrently
   - Semaphore controls concurrency (max 5 concurrent)
   - Each request processed individually

2. **Result Collection**
   - Results collected and returned as batch
   - Error handling for individual failed requests

#### C. Error Handling Flow
1. **Error Classification**
   - Rate limit errors → Retry with delay
   - Authentication errors → Return auth error
   - Context window errors → Suggest new conversation
   - Generic errors → Return user-friendly message

2. **Error Response**
   - Appropriate error message returned
   - Retry recommendations provided
   - Logging for debugging

## Key Integrations

### LLM Models
- **Claude Sonnet 4.5**: Primary chat responses (high-quality, comprehensive)
- **Claude 3.5 Haiku**: Classification and summarization (fast, cost-effective)

### Database Systems
- **MongoDB**: Document storage for messages, sessions, and metadata

### External Services
- **Anthropic API**: LLM model access and management
- **Sentence Transformers**: Local embedding generation for semantic similarity

## Configuration Requirements

### Environment Variables
```bash
# Database
MONGODB_URL=mongodb://localhost:27017

# LLM Services
ANTHROPIC_API_KEY=your_anthropic_key

# Application
SECRET_KEY=your_secret_key
DEBUG=False
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Dependencies
- **FastAPI**: Web framework and API routing
- **Pydantic**: Data validation and settings management
- **Motor**: Async MongoDB driver
- **Anthropic**: Claude API client for LLM integration
- **Sentence Transformers**: Local embedding generation
- **NumPy**: Numerical computations for similarity calculations
- **Loguru**: Advanced logging system
- **Uvicorn**: ASGI server for FastAPI

## Getting Started

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup
```bash
# Ensure MongoDB is running
```

### 4. Run Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

This backend system provides a sophisticated approach to AI-powered sustainability assistance, combining advanced guardrails, intelligent memory management, and multi-model LLM integration to provide accurate, contextual, and reliable responses while maintaining strict content filtering and conversation continuity.