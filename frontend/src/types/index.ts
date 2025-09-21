export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  lastActivity: string;
  isActive: boolean;
  messageCount?: number; // Add message count from backend
}

export interface ChatResponse {
  response: string;
  session_id: string;
  is_summary: boolean;
  can_request_detailed: boolean;
  guardrail_triggered: boolean;
  guardrail_reason?: string;
  timestamp: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  request_detailed?: boolean;
}

export interface SystemStats {
  active_sessions: number;
  total_documents: number;
  guardrails_enabled: boolean;
  model_loaded: boolean;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  model_loaded: boolean;
  guardrails_enabled: boolean;
  memory_system_active: boolean;
}

export interface SustainabilityTopic {
  name: string;
  icon: string;
  description: string;
  keywords: string[];
}

export interface AppState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isLoading: boolean;
  isDarkMode: boolean;
  sidebarOpen: boolean;
}






