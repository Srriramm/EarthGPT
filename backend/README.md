# EarthGPT Backend

FastAPI backend for the EarthGPT sustainability AI assistant.

## 🏗️ Architecture

```
backend/
├── api/                    # FastAPI routes and endpoints
│   └── routes.py          # Main API routes
├── core/                   # Core business logic
│   ├── guardrails.py      # Sustainability-only guardrails
│   ├── memory.py          # Conversational memory & RAG
│   ├── complex_questions.py # Progressive summarization
│   └── prompt_engineering.py # Prompt templates
├── models/                 # Pydantic data models
│   └── schemas.py         # API request/response schemas
├── services/              # External service integrations
│   └── llm_service.py     # LLM inference service
├── utils/                 # Utilities and monitoring
│   └── monitoring.py      # Metrics and analytics
├── main.py               # FastAPI application entry point
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── test_api.py          # API test suite
└── run_demo.py          # Demo script
```

## 🚀 Quick Start

### **Installation:**
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

### **Development:**
```bash
# Start with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### **Core Chat**
- `POST /api/v1/chat` - Main conversation endpoint
- `GET /api/v1/health` - Health check

### **Session Management**
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions/{id}` - Get session info
- `GET /api/v1/sessions/{id}/history` - Get conversation history
- `DELETE /api/v1/sessions/{id}` - Delete session

### **System Information**
- `GET /api/v1/model/info` - Get model information
- `GET /api/v1/admin/stats` - Get system statistics
- `POST /api/v1/admin/cleanup` - Clean up old sessions

## 🧪 Testing

```bash
# Run the test suite
python test_api.py

# Run demo
python run_demo.py
```

## 🔧 Configuration

Edit `config.py` to customize:
- Model settings
- Guardrail keywords
- Memory limits
- API settings
- Logging configuration

## 📊 Monitoring

The backend includes comprehensive monitoring:
- Interaction logging
- Performance metrics
- Guardrail analytics
- System health checks

Access monitoring data via:
- `GET /api/v1/admin/stats` - System statistics
- Log files in `../logs/` directory
- Metrics stored in `metrics.json`

## 🌱 Sustainability Features

### **Guardrails System**
- Domain filtering for sustainability topics
- Polite refusal for off-topic queries
- Output validation
- Keyword-based detection

### **Memory & RAG**
- Session-based conversation history
- Vector embeddings with ChromaDB
- Context-aware responses
- Knowledge base integration

### **Progressive Summarization**
- Complex question detection
- Two-stage response system
- User-controlled detailed explanations
- Intelligent complexity scoring

## 🔌 Integration

The backend is designed to work with:
- **Frontend**: React application (port 3000)
- **Vector DB**: ChromaDB (local storage)
- **LLM**: DeepSeek-R1-Distill-Qwen-14B (or mock for development)

## 📝 Environment Variables

Create a `.env` file for custom configuration:
```env
ENVIRONMENT=development
DEBUG=True
MODEL_NAME=deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
API_HOST=0.0.0.0
API_PORT=8000
```

## 🚀 Production Deployment

### **Using Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Environment Setup:**
```bash
export ENVIRONMENT=production
export DEBUG=False
export SECRET_KEY=your-secure-secret-key
```

## 📈 Performance

- **Response Time**: < 2 seconds average
- **Concurrent Users**: 100+ (with proper scaling)
- **Memory Usage**: ~2GB (with full model)
- **Storage**: Local file-based (ChromaDB)

## 🔒 Security

- Input validation with Pydantic
- Guardrail filtering
- Error handling and logging
- CORS configuration
- Rate limiting (configurable)

## 📚 Documentation

- **API Docs**: http://localhost:8000/docs (when running)
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/api/v1/health

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure sustainability focus is maintained
5. Test with the frontend integration

## 📄 License

This project is licensed under the MIT License.



