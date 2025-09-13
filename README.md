# 🌱 EarthGPT - AI-Powered Sustainability Assistant

A comprehensive AI assistant focused exclusively on sustainability, environmental topics, and climate action. Built with FastAPI backend and React frontend, featuring advanced guardrails, conversational memory, and progressive summarization.

## ✨ Features

### 🛡️ **Sustainability-Only Guardrails**
- Domain filtering to ensure only sustainability-related queries
- Polite refusal messages for off-topic questions
- Output validation for topical compliance
- Keyword-based and contextual sustainability detection

### 🧠 **Advanced AI Capabilities**
- **Conversational Memory**: Session-based conversation history
- **RAG System**: Retrieval-Augmented Generation with vector embeddings
- **Progressive Summarization**: Two-stage responses for complex questions
- **Context Awareness**: Maintains conversation context and continuity

### 🎨 **Modern Frontend**
- Beautiful, responsive React interface
- Dark/Light mode toggle
- Multiple chat sessions with sidebar navigation
- Real-time messaging with animations
- Mobile-first design

### 📊 **Monitoring & Analytics**
- Comprehensive interaction logging
- Performance metrics and system health
- Guardrail analytics and rejection tracking
- Topic-based usage analytics

## 🚀 Quick Start

### **Option 1: Automated Setup (Recommended)**

1. **Clone and setup:**
```bash
git clone <repository-url>
cd EarthGPT
python setup_earthgpt.py
```

2. **If frontend dependencies fail, run the fix:**
```bash
python fix_frontend_deps.py
```

3. **Start the application:**
```bash
python start_earthgpt.py
```

### **Option 2: Manual Setup**

1. **Backend Setup:**
```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Start backend
python main.py
```

2. **Frontend Setup:**
```bash
# Install Node.js dependencies
cd frontend
npm install --legacy-peer-deps

# Start frontend
npm start
```

## 🌐 Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 📱 Usage Examples

### **Sustainability Queries (✅ Allowed)**
- "How can I reduce my carbon footprint?"
- "What are the benefits of renewable energy?"
- "Explain ESG criteria for sustainable investing"
- "What is the circular economy concept?"
- "How does climate change affect biodiversity?"

### **Non-Sustainability Queries (❌ Blocked)**
- "What's the weather like today?"
- "Tell me about the latest movies"
- "How do I cook pasta?"
- "What are the best sports teams?"

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React         │    │   FastAPI        │    │   ChromaDB      │
│   Frontend      │◄──►│   Backend        │◄──►│   Vector Store  │
│   (Port 3000)   │    │   (Port 8000)    │    │   (Local)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chat UI       │    │   Guardrails     │    │   RAG System    │
│   Sessions      │    │   Memory         │    │   Embeddings    │
│   Dark Mode     │    │   LLM Service    │    │   Knowledge     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Configuration

### **Backend Configuration** (`config.py`)
- Model settings (DeepSeek-R1-Distill-Qwen-14B)
- Guardrail keywords and patterns
- Memory and session limits
- API and logging settings

### **Frontend Configuration** (`frontend/.env`)
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## 📊 API Endpoints

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

## 🧪 Testing

### **Run API Tests:**
```bash
cd backend
python test_api.py
```

### **Test Categories:**
- Health check
- Sustainability queries
- Guardrail system
- Progressive summarization
- Session management
- System statistics

## 🛠️ Development

### **Backend Development:**
```bash
# Start with auto-reload
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **Frontend Development:**
```bash
cd frontend
npm start
```

### **Code Structure:**
```
EarthGPT/
├── backend/               # Python FastAPI backend
│   ├── api/              # FastAPI routes
│   ├── core/             # Core business logic
│   │   ├── guardrails.py # Sustainability guardrails
│   │   ├── memory.py     # Conversation memory & RAG
│   │   ├── complex_questions.py # Progressive summarization
│   │   └── prompt_engineering.py # Prompt templates
│   ├── models/           # Pydantic schemas
│   ├── services/         # External services
│   ├── utils/            # Utilities and monitoring
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   └── requirements.txt # Python dependencies
├── frontend/             # React frontend
│   ├── src/components/   # React components
│   ├── src/hooks/        # Custom hooks
│   ├── src/services/     # API services
│   └── src/types/        # TypeScript types
├── setup_earthgpt.py    # Setup script
├── start_earthgpt.py    # Startup script
└── README.md            # This file
```

## 🚀 Production Deployment

### **Using Docker:**
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Environment Variables:**
```env
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-secure-secret-key
DATABASE_URL=your-database-url
REDIS_URL=your-redis-url
```

## 📈 Monitoring

The system includes comprehensive monitoring:
- **Interaction Logging**: All conversations logged with metadata
- **Performance Metrics**: Response times, throughput, error rates
- **Guardrail Analytics**: Rejection reasons and trends
- **Topic Analytics**: Sustainability topic usage patterns

Access monitoring via:
- `GET /api/v1/admin/stats` - System statistics
- Log files in `./logs/` directory
- Metrics stored in `metrics.json`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API documentation at `/docs` when running the server

## 🌟 Acknowledgments

- Built with FastAPI and React
- Powered by DeepSeek-R1-Distill-Qwen-14B
- Vector storage with ChromaDB
- Styled with Tailwind CSS
- Animated with Framer Motion

---

**EarthGPT** - Making sustainability knowledge accessible through AI 🌱