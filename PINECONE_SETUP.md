# Pinecone Setup for EarthGPT

This document explains how to set up Pinecone storage for persistent conversation history in EarthGPT.

## Overview

EarthGPT now uses Pinecone for storing conversation history, which means:
- ✅ Conversations persist across browser refreshes
- ✅ Conversations are stored in the cloud
- ✅ Semantic search through conversation history
- ✅ Scalable storage for multiple users

## Setup Instructions

### 1. Create a Pinecone Account

1. Go to [Pinecone](https://www.pinecone.io/)
2. Sign up for a free account
3. Create a new project

### 2. Get Your API Credentials

1. In your Pinecone dashboard, go to "API Keys"
2. Copy your API key
3. Note your environment (e.g., "us-east-1-aws")

### 3. Configure Environment Variables

Create a `.env` file in the `backend` directory with:

```env
# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
```

### 4. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 5. Start the Backend

```bash
cd backend
python main.py
```

## How It Works

### Conversation Storage
- Each message is stored as a vector in Pinecone
- Messages are embedded using the `all-MiniLM-L6-v2` model
- Metadata includes session ID, message type, timestamp, and user ID

### Session Management
- Sessions are created with unique UUIDs
- Session metadata is stored in memory (can be moved to database)
- Messages are retrieved by session ID

### Features
- **Persistent Storage**: Conversations survive browser refreshes
- **Semantic Search**: Search through conversation history
- **User Isolation**: Each user's conversations are separate
- **Scalable**: Pinecone handles large volumes of data

## API Endpoints

### New Endpoints
- `GET /api/v1/sessions` - Get all user sessions
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions/{session_id}/history` - Get conversation history
- `DELETE /api/v1/sessions/{session_id}` - Delete session

### Updated Endpoints
- `POST /api/v1/chat` - Now uses Pinecone for context retrieval

## Frontend Changes

The frontend has been updated to:
- Load sessions from the backend on startup
- Create sessions via API calls
- Load conversation history when selecting sessions
- Delete sessions via API calls

## Fallback Behavior

If Pinecone is unavailable:
- The system falls back to localStorage
- Sessions are created locally
- No conversation history is lost

## Troubleshooting

### Common Issues

1. **"Pinecone API key not found"**
   - Ensure your `.env` file is in the `backend` directory
   - Check that `PINECONE_API_KEY` is set correctly

2. **"Pinecone environment not found"**
   - Verify your `PINECONE_ENVIRONMENT` setting
   - Check your Pinecone dashboard for the correct environment

3. **"Index not found"**
   - The system will automatically create the index on first run
   - Ensure your Pinecone account has sufficient quota

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

## Migration from LocalStorage

Existing localStorage sessions will be:
1. Loaded as fallback if backend is unavailable
2. Gradually replaced with Pinecone sessions as new conversations are created
3. Preserved as backup in localStorage

## Cost Considerations

- Pinecone free tier: 100,000 vectors
- Each message = 1 vector
- Monitor usage in Pinecone dashboard
- Consider cleanup policies for old conversations

## Security Notes

- API keys should be kept secure
- Consider implementing user authentication
- Session data is isolated by user ID
- Messages are stored with timestamps for audit trails
