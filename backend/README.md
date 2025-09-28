# EarthGPT Backend

A sophisticated sustainability-focused AI assistant backend built with FastAPI, featuring advanced guardrails, hybrid memory management, and intelligent conversation handling.

## Architecture Overview

EarthGPT Backend is designed as a modular, scalable system that combines multiple AI models and advanced memory management to provide intelligent sustainability-focused conversations while maintaining strict content filtering and context awareness.

### Core Components
- **FastAPI Application**: RESTful API with authentication
- **Hybrid Guardrail System**: Multi-layer content filtering using embeddings + LLM
- **Hybrid Memory Management**: MongoDB + Pinecone for persistent semantic search
- **Smart Context Management**: Intelligent conversation history and token optimization
- **Multi-Model LLM Integration**: Claude 3.7 Sonnet (main) + Claude 3.5 Haiku (classification/summarization)

## 📁 Directory Structure

```
backend/
├── api/                    # API endpoints and routing
├── auth/                   # Authentication and authorization
├── core/                   # Core business logic and services
├── guardrails/             # Content filtering and validation
├── services/               # External service integrations
├── models/                 # Database models and schemas
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
- Database connections (MongoDB, Pinecone)
- LLM model configurations (Claude 3.7 Sonnet, Claude 3.5 Haiku)
- API keys and environment variables
- Token limits and optimization parameters

#### `main.py`
**Purpose**: FastAPI application entry point and middleware setup
**Features**:
- CORS configuration
- Request/response logging
- Health check endpoints
- Application lifecycle management

### API Layer (`api/`)

#### `api/routes.py`
**Purpose**: Main API endpoints for chat functionality
**Key Endpoints**:
- `POST /api/v1/chat` - Anonymous chat
- `POST /api/v1/chat/authenticated` - Authenticated chat
- `GET /api/v1/health` - Health check

**Flow**:
1. **Input Validation**: Validates incoming chat requests
2. **Session Management**: Creates or retrieves conversation sessions
3. **Guardrail Check**: Validates sustainability relevance using hybrid classifier
4. **Context Retrieval**: Gets optimized conversation context with semantic search
5. **LLM Generation**: Generates response using Claude 3.7 Sonnet
6. **Output Validation**: Validates response content and relevance
7. **Memory Storage**: Stores conversation in hybrid memory system

### Authentication (`auth/`)

#### `auth/dependencies.py`
**Purpose**: Authentication and authorization dependencies
**Features**:
- JWT token validation
- User session management
- Role-based access control
- Security middleware integration

### Core Business Logic (`core/`)

#### `core/smart_memory.py`
**Purpose**: Intelligent conversation memory and context management
**Key Features**:
- **Session Management**: Tracks conversation sessions and message history
- **Token Optimization**: Manages context window limits and message truncation
- **Semantic Search Integration**: Retrieves relevant old messages using hybrid memory
- **Context Building**: Constructs optimized prompts with recent + relevant historical context

**Flow**:
1. **Message Storage**: Stores user/assistant messages with token tracking
2. **Context Optimization**: Limits recent messages to prevent context pollution
3. **Semantic Search**: Finds relevant old messages using multiple search strategies
4. **Context Assembly**: Combines recent + relevant historical context

#### `core/hybrid_memory.py`
**Purpose**: Persistent memory storage using MongoDB + Pinecone
**Architecture**:
- **MongoDB**: Stores full message content, metadata, and relationships
- **Pinecone**: Stores vector embeddings for semantic search
- **Hybrid Storage**: Combines both for comprehensive memory management

**Key Methods**:
- `store_message()`: Stores messages in both MongoDB and Pinecone
- `search_similar_messages()`: Performs semantic search across conversation history
- `get_conversation_history()`: Retrieves chronological message history

### 🧠 Memory System Architecture

#### **Why Two Memory Systems?**

**Smart Memory** (`core/smart_memory.py`) - **Active Session Manager**
- **Purpose**: Manages current conversation sessions and context optimization
- **Storage**: In-memory (temporary, session-based)
- **Focus**: Fast session operations, context assembly, token optimization
- **Lifecycle**: Data exists only during active session

**Hybrid Memory** (`core/hybrid_memory.py`) - **Persistent Knowledge Base**
- **Purpose**: Provides persistent storage and semantic search across all conversations
- **Storage**: MongoDB + Pinecone (permanent, cross-session)
- **Focus**: Long-term memory, semantic search, cross-session knowledge
- **Lifecycle**: Data persists forever for comprehensive memory

#### **How They Work Together**
```
1. User sends message
   ↓
2. Smart Memory: Adds to current session (fast, temporary)
   ↓
3. Hybrid Memory: Stores permanently (MongoDB + Pinecone)
   ↓
4. Smart Memory: Retrieves context (recent + semantic search)
   ↓
5. Smart Memory: Builds optimized prompt for LLM
   ↓
6. LLM generates response
   ↓
7. Smart Memory: Adds response to session
   ↓
8. Hybrid Memory: Stores response permanently
```

#### **Example: "Do you remember about the rebound effect?"**
```python
# Smart Memory: Gets current session context
current_session = smart_memory.get_session_messages(session_id)

# Hybrid Memory: Searches ALL conversations for "rebound effect"
old_messages = hybrid_memory.search_similar_messages(
    query="rebound effect",
    user_id=user_id,
    session_id=session_id  # Excludes current session
)

# Smart Memory: Combines and optimizes context
optimized_context = smart_memory.build_context(
    recent=current_session,      # Last 6 messages
    relevant=old_messages        # Relevant old messages
)
```

#### `core/prompt_engineering.py`
**Purpose**: Intelligent prompt construction and optimization
**Features**:
- **System Prompt Management**: Maintains EarthGPT's sustainability-focused persona
- **Context Integration**: Incorporates relevant historical context from semantic search
- **Length Control**: Detects user intent for response length ("in short", "detailed")
- **Token Management**: Optimizes prompt length within model limits

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

### Guardrails (`guardrails/`)

#### `guardrails/hybrid_classifier_guardrails.py`
**Purpose**: Advanced multi-layer content filtering system
**Architecture**:
1. **Layer 1 - Embedding Classification**: Fast semantic similarity against sustainability categories
2. **Layer 2 - LLM Classification**: Claude 3.5 Haiku fallback for uncertain cases
3. **Layer 3 - Follow-up Detection**: Two-layer system for conversation continuity
4. **Layer 4 - Output Validation**: Intelligent response validation

**Key Features**:
- **Hybrid Approach**: Combines speed of embeddings with accuracy of LLM
- **Two-Layer Follow-up Detection**: Pattern-based + LLM-based for conversation continuity
- **Intelligent Output Validation**: Semantic similarity + context-aware thresholds
- **Sustainability Categories**: Comprehensive environmental and sustainability topic coverage

#### `guardrails/intelligent_output_validator.py`
**Purpose**: Advanced response validation using semantic similarity
**Features**:
- **Semantic Validation**: Uses sentence transformers for content similarity
- **Adaptive Thresholds**: Adjusts validation strictness based on input confidence
- **Technical Term Recognition**: Recognizes sustainability-specific terminology
- **Graceful Fallbacks**: Falls back to basic validation if semantic validation fails

### 🔌 Services (`services/`)

#### `services/llm_service.py`
**Purpose**: Main LLM service integration with Claude 3.7 Sonnet
**Features**:
- **Response Generation**: Primary chat response generation
- **Token Management**: Handles context window limits and optimization
- **Error Handling**: Robust error handling and fallback mechanisms
- **Performance Monitoring**: Tracks response times and token usage

### Models (`models/`)

#### `models/chat.py`
**Purpose**: Pydantic models for API request/response validation
**Key Models**:
- `ChatRequest`: Input validation for chat messages
- `ChatResponse`: Response formatting and metadata
- `SessionInfo`: Session management and tracking

## System Flow

### Complete Backend Architecture Flow

```mermaid
graph TB
    %% User Input
    User[👤 User Query] --> API[🌐 API Routes<br/>api/routes.py]
    
    %% API Layer
    API --> Auth{🔐 Authenticated?}
    Auth -->|Yes| AuthCheck[🔑 Auth Dependencies<br/>auth/dependencies.py]
    Auth -->|No| SessionMgt[📝 Session Management]
    AuthCheck --> SessionMgt
    
    %% Session Management
    SessionMgt --> SmartMem[🧠 Smart Memory<br/>core/smart_memory.py]
    SmartMem --> AddMsg[➕ Add User Message<br/>to Session]
    
    %% Guardrail System
    AddMsg --> Guardrails[🛡️ Hybrid Guardrails<br/>guardrails/hybrid_classifier_guardrails.py]
    Guardrails --> EmbedClass[📊 Embedding Classification<br/>Layer 1: Fast Semantic Check]
    
    EmbedClass --> Certain{✅ Certain?}
    Certain -->|Yes| FollowUp[🔄 Follow-up Detection<br/>Two-Layer System]
    Certain -->|No| LLMClass[🤖 LLM Classification<br/>Layer 2: Claude 3.5 Haiku]
    
    LLMClass --> FollowUp
    FollowUp --> Decision{🎯 Allow Query?}
    Decision -->|No| Reject[❌ Reject Response]
    Decision -->|Yes| ContextRetrieval[📚 Context Retrieval]
    
    %% Context Management
    ContextRetrieval --> RecentCtx[📋 Recent Context<br/>Last 6 Messages]
    ContextRetrieval --> HybridMem[💾 Hybrid Memory<br/>core/hybrid_memory.py]
    
    HybridMem --> SemanticSearch[🔍 Semantic Search<br/>MongoDB + Pinecone]
    SemanticSearch --> RelevantMsgs[📄 Relevant Old Messages<br/>Cross-Session Memory]
    
    RecentCtx --> ContextAssembly[🔧 Context Assembly<br/>Smart Memory]
    RelevantMsgs --> ContextAssembly
    
    %% Prompt Engineering
    ContextAssembly --> PromptEng[📝 Prompt Engineering<br/>core/prompt_engineering.py]
    PromptEng --> SystemPrompt[🎭 System Prompt<br/>EarthGPT Persona]
    PromptEng --> ContextPrompt[📖 Context Integration<br/>Recent + Historical]
    PromptEng --> LengthControl[📏 Length Control<br/>"in short" vs "detailed"]
    
    %% LLM Generation
    SystemPrompt --> LLMService[🤖 LLM Service<br/>services/llm_service.py]
    ContextPrompt --> LLMService
    LengthControl --> LLMService
    
    LLMService --> Claude37[🧠 Claude 3.7 Sonnet<br/>Main Response Generation]
    Claude37 --> Response[💬 Generated Response]
    
    %% Output Validation
    Response --> OutputVal[✅ Output Validation<br/>guardrails/intelligent_output_validator.py]
    OutputVal --> SemanticVal[🔍 Semantic Validation<br/>Sentence Transformers]
    SemanticVal --> Valid{✅ Valid Response?}
    
    Valid -->|No| Reject
    Valid -->|Yes| FormatResponse[📤 Format Response]
    
    %% Memory Storage
    FormatResponse --> StoreUser[💾 Store User Message<br/>Hybrid Memory]
    FormatResponse --> StoreAssistant[💾 Store Assistant Response<br/>Hybrid Memory]
    
    StoreUser --> MongoDB[(🗄️ MongoDB<br/>Full Message Storage)]
    StoreUser --> Pinecone[(🔍 Pinecone<br/>Vector Embeddings)]
    
    StoreAssistant --> MongoDB
    StoreAssistant --> Pinecone
    
    %% Response to User
    FormatResponse --> UserResponse[👤 Response to User]
    
    %% Styling
    classDef userClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef apiClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef coreClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef guardrailClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef memoryClass fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px
    classDef llmClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef dbClass fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    
    class User,UserResponse userClass
    class API,AuthCheck,SessionMgt apiClass
    class SmartMem,PromptEng,ContextAssembly coreClass
    class Guardrails,EmbedClass,LLMClass,FollowUp,OutputVal,SemanticVal guardrailClass
    class HybridMem,SemanticSearch,RelevantMsgs,RecentCtx memoryClass
    class LLMService,Claude37 llmClass
    class MongoDB,Pinecone dbClass
```

### Detailed Flow Breakdown

#### 1. **Request Processing Flow**
```
User Query → API Route → Authentication Check → Session Management → Smart Memory
```

#### 2. **Content Filtering Flow**
```
Query → Embedding Classification → LLM Classification (if uncertain) → Follow-up Detection → Decision
```

#### 3. **Context Management Flow**
```
Query → Recent Context Retrieval → Semantic Search → Context Assembly → Prompt Building
```

#### 4. **Response Generation Flow**
```
Optimized Context → LLM Generation → Output Validation → Response Formatting → Memory Storage
```

#### 5. **Memory Storage Flow**
```
Message → MongoDB Storage → Embedding Generation → Pinecone Storage → Hybrid Memory Complete
```

## Key Integrations

### LLM Models
- **Claude 3.7 Sonnet**: Primary chat responses (high-quality, comprehensive)
- **Claude 3.5 Haiku**: Classification and summarization (fast, cost-effective)

### Database Systems
- **MongoDB**: Document storage for messages, sessions, and metadata
- **Pinecone**: Vector database for semantic search and similarity matching

### External Services
- **Anthropic API**: LLM model access and management
- **Sentence Transformers**: Local embedding generation for semantic similarity

## 🔧 Configuration Requirements

### Environment Variables
```bash
# Database
MONGODB_URL=mongodb://localhost:27017
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_pinecone_env

# LLM Services
ANTHROPIC_API_KEY=your_anthropic_key

# Application
SECRET_KEY=your_secret_key
DEBUG=False
```

### Dependencies
- **FastAPI**: Web framework
- **Pydantic**: Data validation and settings
- **Motor**: Async MongoDB driver
- **Pinecone**: Vector database client
- **Anthropic**: Claude API client
- **Sentence Transformers**: Embedding models
- **NumPy**: Numerical computations

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
# Ensure Pinecone index is created
```

### 4. Run Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

This backend system represents a sophisticated approach to AI-powered sustainability assistance, combining advanced guardrails, intelligent memory management, and multi-model LLM integration to provide accurate, contextual, and reliable responses while maintaining strict content filtering and conversation continuity.
