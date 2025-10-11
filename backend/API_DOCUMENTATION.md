# EarthGPT Backend API Documentation

This document provides comprehensive API documentation for the EarthGPT backend, including all endpoints, request/response formats, authentication, and error handling.

## Base URL
```
http://localhost:8000
```

## Authentication
All protected endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

## API Endpoints

### 1. Authentication Endpoints

#### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "password": "password123"
}
```

**Response (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "is_active": true,
    "created_at": "2025-01-07T10:30:00Z"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "User already exists",
  "detail": "Email already registered"
}
```

#### POST `/api/v1/auth/login`
Authenticate user and get access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Invalid credentials",
  "detail": "Email or password incorrect"
}
```

### 2. Chat Endpoints

#### POST `/api/v1/chat`
Send a chat message and get AI response (authenticated users only).

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "What are the benefits of solar energy?",
  "session_id": "optional_session_id",
  "request_detailed": false
}
```

**Response (200 OK):**
```json
{
  "response": "Solar energy offers numerous benefits for both the environment and economy. It's a clean, renewable source of power that reduces greenhouse gas emissions...",
  "session_id": "session_123",
  "user_id": "user_456",
  "is_sustainability_related": true,
  "confidence_score": 0.95,
  "is_summary": false,
  "can_request_detailed": false,
  "guardrail_triggered": false,
  "guardrail_reason": null,
  "memory_used": true,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "error": null,
  "user": {
    "id": "user_456",
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "is_active": true,
    "created_at": "2025-01-07T10:30:00Z"
  },
  "timestamp": "2025-01-07T10:30:00Z"
}
```

**Non-Sustainability Query Response (200 OK):**
```json
{
  "response": "I'm specialized in sustainability topics. Please ask me about environmental issues, climate change, renewable energy, sustainable practices, or related topics.",
  "session_id": "session_123",
  "user_id": "user_456",
  "is_sustainability_related": false,
  "confidence_score": 0.9,
  "is_summary": false,
  "can_request_detailed": false,
  "guardrail_triggered": true,
  "guardrail_reason": "Query appears to be about non-sustainability topics",
  "memory_used": false,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "error": null,
  "user": {
    "id": "user_456",
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "is_active": true,
    "created_at": "2025-01-07T10:30:00Z"
  },
  "timestamp": "2025-01-07T10:30:00Z"
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Not authenticated",
  "detail": "Authentication required"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "response": "I'm sorry, I encountered an unexpected error. Please try again.",
  "session_id": "session_123",
  "user_id": "user_456",
  "is_sustainability_related": true,
  "confidence_score": 0.0,
  "memory_used": false,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "error": "Database connection failed",
  "user": {
    "id": "user_456",
    "email": "user@example.com",
    "username": "username",
    "full_name": "Full Name",
    "is_active": true,
    "created_at": "2025-01-07T10:30:00Z"
  },
  "timestamp": "2025-01-07T10:30:00Z"
}
```

### 3. Session Management Endpoints

#### GET `/api/v1/sessions`
Get all chat sessions for the authenticated user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
[
  {
    "session_id": "session_123",
    "created_at": "2025-01-07T10:30:00Z",
    "last_activity": "2025-01-07T11:45:00Z",
    "message_count": 8,
    "is_active": true,
    "title": "Solar Energy Discussion"
  },
  {
    "session_id": "session_124",
    "created_at": "2025-01-06T14:20:00Z",
    "last_activity": "2025-01-06T15:30:00Z",
    "message_count": 4,
    "is_active": true,
    "title": "Climate Change Questions"
  }
]
```

**Error Response (401 Unauthorized):**
```json
{
  "error": "Not authenticated",
  "detail": "Authentication required"
}
```

#### GET `/api/v1/sessions/{session_id}/history`
Get conversation history for a specific session.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Path Parameters:**
- `session_id` (string): The session ID to retrieve history for

**Response (200 OK):**
```json
{
  "session_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "What are the benefits of solar energy?",
      "timestamp": "2025-01-07T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Solar energy offers numerous benefits for both the environment and economy...",
      "timestamp": "2025-01-07T10:30:15Z"
    },
    {
      "role": "user",
      "content": "Can you tell me more about the environmental benefits?",
      "timestamp": "2025-01-07T10:32:00Z"
    },
    {
      "role": "assistant",
      "content": "The environmental benefits of solar energy are significant...",
      "timestamp": "2025-01-07T10:32:20Z"
    }
  ]
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Session not found",
  "detail": "Session with ID session_123 not found"
}
```

**Error Response (403 Forbidden):**
```json
{
  "error": "Access denied",
  "detail": "You don't have permission to access this session"
}
```

#### DELETE `/api/v1/sessions/{session_id}`
Delete a specific chat session.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Path Parameters:**
- `session_id` (string): The session ID to delete

**Response (200 OK):**
```json
{
  "message": "Session deleted successfully"
}
```

**Error Response (404 Not Found):**
```json
{
  "error": "Session not found",
  "detail": "Session with ID session_123 not found"
}
```

**Error Response (403 Forbidden):**
```json
{
  "error": "Access denied",
  "detail": "You don't have permission to delete this session"
}
```

### 4. Health Check Endpoints

#### GET `/api/v1/health`
Get system health status and configuration information.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-07T10:30:00Z",
  "version": "1.0.0",
  "model_loaded": true,
  "guardrails_enabled": true,
  "memory_system_active": true,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "web_fetch_enabled": false,
  "memory_stats": {
    "total_sessions": 45,
    "total_memories": 234,
    "total_metadata_entries": 45,
    "storage_type": "MongoDB"
  }
}
```

#### GET `/`
Get basic API information.

**Response (200 OK):**
```json
{
  "message": "Sustainability Assistant API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

## Data Models

### User Model
```typescript
interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}
```

### Message Model
```typescript
interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}
```

### Session Model
```typescript
interface SessionInfo {
  session_id: string;
  created_at: string;
  last_activity: string;
  message_count: number;
  is_active: boolean;
  title: string;
}
```

### Chat Response Model
```typescript
interface ChatResponse {
  response: string;
  session_id: string;
  user_id: string;
  is_sustainability_related: boolean;
  confidence_score: number;
  is_summary: boolean;
  can_request_detailed: boolean;
  guardrail_triggered: boolean;
  guardrail_reason?: string;
  memory_used: boolean;
  claude_memory_enabled: boolean;
  web_search_enabled: boolean;
  error?: string;
  user?: User;
  timestamp: string;
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "timestamp": "2025-01-07T10:30:00Z"
}
```

### Common HTTP Status Codes

#### 200 OK
- Successful request
- Used for all successful operations

#### 201 Created
- Resource created successfully
- Used for user registration

#### 400 Bad Request
- Invalid request data
- Missing required fields
- Validation errors

#### 401 Unauthorized
- Missing or invalid authentication token
- Expired token

#### 403 Forbidden
- Valid token but insufficient permissions
- Access to resource denied

#### 404 Not Found
- Resource not found
- Session doesn't exist

#### 500 Internal Server Error
- Server-side error
- Database connection issues
- LLM service errors

## Request/Response Examples

### Example 1: Complete Chat Flow

**1. Register User:**
```bash
POST /api/v1/auth/register
{
  "email": "john@example.com",
  "username": "john_doe",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

**2. Login:**
```bash
POST /api/v1/auth/login
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**3. Start Chat Session:**
```bash
POST /api/v1/chat
Authorization: Bearer <token>
{
  "message": "What are the environmental benefits of renewable energy?",
  "request_detailed": false
}
```

**4. Follow-up Question:**
```bash
POST /api/v1/chat
Authorization: Bearer <token>
{
  "message": "Can you elaborate on solar energy specifically?",
  "session_id": "session_123",
  "request_detailed": true
}
```

**5. Get Session History:**
```bash
GET /api/v1/sessions/session_123/history
Authorization: Bearer <token>
```

### Example 2: Non-Sustainability Query

```bash
POST /api/v1/chat
Authorization: Bearer <token>
{
  "message": "How do I cook pasta?",
  "session_id": "session_123"
}
```

**Response:**
```json
{
  "response": "I'm specialized in sustainability topics. Please ask me about environmental issues, climate change, renewable energy, sustainable practices, or related topics.",
  "session_id": "session_123",
  "user_id": "user_456",
  "is_sustainability_related": false,
  "confidence_score": 0.9,
  "guardrail_triggered": true,
  "guardrail_reason": "Query appears to be about non-sustainability topics",
  "memory_used": false,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "error": null,
  "user": { ... },
  "timestamp": "2025-01-07T10:30:00Z"
}
```

### Example 3: Memory-Based Query

```bash
POST /api/v1/chat
Authorization: Bearer <token>
{
  "message": "Do you remember what we discussed about carbon emissions?",
  "session_id": "session_123"
}
```

**Response:**
```json
{
  "response": "Yes, I remember our discussion about carbon emissions. We talked about how reducing carbon emissions is crucial for combating climate change...",
  "session_id": "session_123",
  "user_id": "user_456",
  "is_sustainability_related": true,
  "confidence_score": 0.95,
  "guardrail_triggered": false,
  "memory_used": true,
  "claude_memory_enabled": true,
  "web_search_enabled": false,
  "error": null,
  "user": { ... },
  "timestamp": "2025-01-07T10:30:00Z"
}
```

## Frontend Integration Guidelines

### 1. Authentication Flow
1. Implement login/register forms
2. Store JWT token in localStorage or secure storage
3. Include token in Authorization header for protected requests
4. Handle token expiration and refresh

### 2. Chat Interface
1. Implement real-time chat interface
2. Handle streaming responses (if implemented)
3. Display guardrail messages for non-sustainability queries
4. Show loading states during API calls

### 3. Session Management
1. Display list of user sessions
2. Allow session deletion
3. Show session history
4. Handle session switching

### 4. Error Handling
1. Display user-friendly error messages
2. Handle network errors gracefully
3. Show loading states
4. Implement retry mechanisms

### 5. State Management
1. Manage user authentication state
2. Store current session information
3. Cache conversation history
4. Handle real-time updates

## Rate Limiting
- No explicit rate limiting implemented
- Backend includes internal rate limiting for Claude API calls
- Consider implementing client-side rate limiting for better UX

## CORS Configuration
- CORS enabled for development origins
- Production origins configurable via `ALLOWED_ORIGINS` environment variable
- Supports credentials (cookies, authorization headers)


This documentation provides all the information needed for frontend development. The API is designed to be RESTful and follows standard HTTP conventions for easy integration.
