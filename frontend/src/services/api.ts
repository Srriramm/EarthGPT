import axios from 'axios';
import { ChatRequest, ChatResponse, SystemStats, HealthResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const chatAPI = {
  // Send a chat message
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post('/chat', request);
    return response.data;
  },

  // Create a new session
  createSession: async (userId: string = "default"): Promise<{ session_id: string; message: string }> => {
    const response = await api.post('/sessions', null, {
      params: { user_id: userId }
    });
    return response.data;
  },

  // Get all user sessions
  getUserSessions: async (userId: string = "default") => {
    const response = await api.get('/sessions', {
      params: { user_id: userId }
    });
    return response.data;
  },

  // Get session info
  getSessionInfo: async (sessionId: string) => {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },

  // Get conversation history
  getConversationHistory: async (sessionId: string) => {
    const response = await api.get(`/sessions/${sessionId}/history`);
    return response.data;
  },

  // Delete a session
  deleteSession: async (sessionId: string) => {
    const response = await api.delete(`/sessions/${sessionId}`);
    return response.data;
  },

  // Get system health
  getHealth: async (): Promise<HealthResponse> => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get system stats
  getStats: async (): Promise<SystemStats> => {
    const response = await api.get('/admin/stats');
    return response.data;
  },

  // Get model info
  getModelInfo: async () => {
    const response = await api.get('/model/info');
    return response.data;
  },

  // Cleanup old sessions
  cleanupSessions: async () => {
    const response = await api.post('/admin/cleanup');
    return response.data;
  },

};

export default api;



