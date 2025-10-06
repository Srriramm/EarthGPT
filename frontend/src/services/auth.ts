import api from './api';
import axios from 'axios';

// Create a separate API instance for auth endpoints (without /api/v1 prefix)
const authApi = axios.create({
  baseURL: process.env.REACT_APP_API_URL?.replace('/api/v1', '') || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  last_activity: string;
  message_count: number;
  is_active: boolean;
}

export interface CreateSessionRequest {
  title: string;
}

class AuthService {
  private token: string | null = null;
  private user: User | null = null;

  constructor() {
    // Load token from localStorage on initialization
    this.token = localStorage.getItem('auth_token');
    this.user = this.getStoredUser();
  }

  // Authentication methods
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    try {
      const response = await authApi.post<TokenResponse>('/auth/login', credentials);
      this.setToken(response.data.access_token);
      await this.fetchCurrentUser();
      return response.data;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }

  async register(userData: RegisterRequest): Promise<User> {
    try {
      const response = await authApi.post<User>('/auth/register', userData);
      return response.data;
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    this.token = null;
    this.user = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
  }

  async fetchCurrentUser(): Promise<User> {
    if (!this.token) {
      throw new Error('No authentication token');
    }

    try {
      const response = await authApi.get<User>('/auth/me');
      this.user = response.data;
      this.storeUser(response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      throw error;
    }
  }

  // Session management methods
  async createSession(sessionData: CreateSessionRequest): Promise<ChatSession> {
    try {
      const response = await authApi.post<ChatSession>('/auth/sessions', sessionData);
      return response.data;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }

  async getUserSessions(): Promise<ChatSession[]> {
    try {
      const response = await authApi.get<ChatSession[]>('/auth/sessions');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
      throw error;
    }
  }

  async getSessionHistory(sessionId: string): Promise<{ session_id: string; messages: any[] }> {
    try {
      const response = await authApi.get(`/auth/sessions/${sessionId}/history`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch session history:', error);
      throw error;
    }
  }

  async deleteSession(sessionId: string): Promise<void> {
    try {
      await authApi.delete(`/auth/sessions/${sessionId}`);
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  }

  // Chat methods for authenticated users
  async sendAuthenticatedMessage(request: { message: string; session_id?: string; request_detailed?: boolean }): Promise<any> {
    try {
      // Use the regular api instance for chat endpoints since they're under /api/v1
      const response = await api.post('/chat', request);
      return response.data;
    } catch (error) {
      console.error('Failed to send authenticated message:', error);
      throw error;
    }
  }

  // Utility methods
  setToken(token: string): void {
    this.token = token;
    localStorage.setItem('auth_token', token);
    // Update API client with new token
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    authApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  getToken(): string | null {
    return this.token;
  }

  getCurrentUser(): User | null {
    return this.user;
  }

  isAuthenticated(): boolean {
    return !!this.token && !!this.user;
  }

  private storeUser(user: User): void {
    localStorage.setItem('user_data', JSON.stringify(user));
  }

  private getStoredUser(): User | null {
    try {
      const stored = localStorage.getItem('user_data');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  // Initialize API client with token if available
  initializeApiClient(): void {
    if (this.token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
      authApi.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
    }
  }
}

export const authService = new AuthService();

// Initialize API client on module load
authService.initializeApiClient();
