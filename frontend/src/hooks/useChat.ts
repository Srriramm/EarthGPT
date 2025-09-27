import { useState, useCallback, useEffect } from 'react';
import { ChatSession, Message, ChatResponse } from '../types';
import { chatAPI } from '../services/api';
import { authService } from '../services/auth';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

export const useChat = () => {
  const { isAuthenticated } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // Load sessions from backend on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        let backendSessions: ChatSession[] = [];
        
        if (isAuthenticated) {
          // Use auth service for authenticated users
          const authSessions = await authService.getUserSessions();
          backendSessions = authSessions.map((session: any) => ({
            id: session.id,
            title: session.title || 'New Chat',
            messages: [], // Messages will be loaded when session is selected
            createdAt: session.created_at,
            lastActivity: session.last_activity,
            isActive: session.is_active,
            messageCount: session.message_count || 0, // Map backend message_count to frontend messageCount
          }));
        } else {
          // Use regular API for non-authenticated users
          const response = await chatAPI.getUserSessions();
          backendSessions = response.sessions.map((session: any) => ({
            id: session.session_id,
            title: session.preview || 'New Chat',
            messages: [], // Messages will be loaded when session is selected
            createdAt: session.created_at,
            lastActivity: session.last_activity,
            isActive: session.is_active,
            messageCount: session.message_count || 0, // Map backend message_count to frontend messageCount
          }));
        }
        
        setSessions(backendSessions);
        
        // Check if we have a persisted current session ID
        const persistedSessionId = localStorage.getItem('earthgpt-current-session-id');
        
        // Set the most recent session as current and load its messages
        if (backendSessions.length > 0) {
          let targetSession: ChatSession;
          
          // Try to restore the persisted session first
          if (persistedSessionId) {
            const persistedSession = backendSessions.find(s => s.id === persistedSessionId);
            if (persistedSession) {
              targetSession = persistedSession;
              console.log('Restored persisted session:', persistedSessionId);
            } else {
              // Fallback to most recent if persisted session not found
              targetSession = backendSessions.reduce((latest: ChatSession, current: ChatSession) => 
                new Date(current.lastActivity) > new Date(latest.lastActivity) ? current : latest
              );
            }
          } else {
            // Use most recent session
            targetSession = backendSessions.reduce((latest: ChatSession, current: ChatSession) => 
              new Date(current.lastActivity) > new Date(latest.lastActivity) ? current : latest
            );
          }
          
          // Load messages for the target session
          try {
            let response;
            if (isAuthenticated) {
              response = await authService.getSessionHistory(targetSession.id);
            } else {
              response = await chatAPI.getConversationHistory(targetSession.id);
            }
            
            const sessionWithMessages = {
              ...targetSession,
              messages: response.messages || []
            };
            setCurrentSession(sessionWithMessages);
            
            // Persist the current session ID
            localStorage.setItem('earthgpt-current-session-id', targetSession.id);
          } catch (error) {
            console.error('Error loading messages for target session:', error);
            setCurrentSession(targetSession);
            localStorage.setItem('earthgpt-current-session-id', targetSession.id);
          }
        }
      } catch (error) {
        console.error('Error loading sessions from backend:', error);
        // Fallback to localStorage if backend fails
        const savedSessions = localStorage.getItem('earthgpt-sessions');
        if (savedSessions) {
          try {
            const parsedSessions = JSON.parse(savedSessions);
            setSessions(parsedSessions);
          } catch (parseError) {
            console.error('Error parsing localStorage sessions:', parseError);
          }
        }
      } finally {
        setIsLoadingSessions(false);
      }
    };
    
    loadSessions();
  }, [isAuthenticated]);

  // Save sessions to localStorage as backup whenever sessions change
  useEffect(() => {
    localStorage.setItem('earthgpt-sessions', JSON.stringify(sessions));
  }, [sessions]);

  // Check API health
  const checkHealth = useCallback(async () => {
    try {
      const health = await chatAPI.getHealth();
      setIsOnline(health.status === 'healthy');
      return health.status === 'healthy';
    } catch (error) {
      setIsOnline(false);
      return false;
    }
  }, []);

  // Create a new chat session
  const createNewSession = useCallback(async () => {
    try {
      let newSession: ChatSession;
      
      if (isAuthenticated) {
        // Use authenticated session creation
        const response = await authService.createSession({ title: 'New Chat' });
        newSession = {
          id: response.id,
          title: response.title,
          messages: [],
          createdAt: response.created_at,
          lastActivity: response.last_activity,
          isActive: response.is_active,
        };
      } else {
        // Use non-authenticated session creation
        const response = await chatAPI.createSession();
        newSession = {
          id: response.session_id,
          title: 'New Chat',
          messages: [],
          createdAt: new Date().toISOString(),
          lastActivity: new Date().toISOString(),
          isActive: true,
        };
      }

      setSessions(prev => [newSession, ...prev]);
      // Switch to new session with smooth transition
      setCurrentSession(newSession);
      
      // Persist the new session ID
      localStorage.setItem('earthgpt-current-session-id', newSession.id);
      return newSession;
    } catch (error) {
      console.error('Error creating session:', error);
      // Fallback to local session creation
      const newSession: ChatSession = {
        id: `session-${Date.now()}`,
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString(),
        lastActivity: new Date().toISOString(),
        isActive: true,
      };

      setSessions(prev => [newSession, ...prev]);
      // Switch to new session with smooth transition
      setCurrentSession(newSession);
      
      // Persist the new session ID
      localStorage.setItem('earthgpt-current-session-id', newSession.id);
      return newSession;
    }
  }, [isAuthenticated]);

  // Select a session and load its messages
  const selectSession = useCallback(async (session: ChatSession) => {
    try {
      // Load messages for this session from backend
      let response;
      if (isAuthenticated) {
        response = await authService.getSessionHistory(session.id);
      } else {
        response = await chatAPI.getConversationHistory(session.id);
      }
      
      console.log('Loaded messages for session:', session.id, response.messages);
      const sessionWithMessages = {
        ...session,
        messages: response.messages || []
      };
      setCurrentSession(sessionWithMessages);
      
      // Persist the selected session ID
      localStorage.setItem('earthgpt-current-session-id', session.id);
    } catch (error) {
      console.error('Error loading session messages:', error);
      // Fallback to session without messages
      setCurrentSession(session);
      localStorage.setItem('earthgpt-current-session-id', session.id);
    }
  }, [isAuthenticated]);

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      if (isAuthenticated) {
        await authService.deleteSession(sessionId);
      } else {
        await chatAPI.deleteSession(sessionId);
      }
      
      setSessions(prev => prev.filter(session => session.id !== sessionId));
      
      if (currentSession?.id === sessionId) {
        const remainingSessions = sessions.filter(session => session.id !== sessionId);
        if (remainingSessions.length > 0) {
          setCurrentSession(remainingSessions[0]);
          localStorage.setItem('earthgpt-current-session-id', remainingSessions[0].id);
        } else {
          setCurrentSession(null);
          localStorage.removeItem('earthgpt-current-session-id');
        }
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      toast.error('Failed to delete session');
    }
  }, [currentSession, sessions, isAuthenticated]);

  // Update session title based on first message
  const updateSessionTitle = useCallback((sessionId: string, title: string) => {
    setSessions(prev => prev.map(session => 
      session.id === sessionId 
        ? { ...session, title, lastActivity: new Date().toISOString() }
        : session
    ));
  }, []);

  // Send a message
  const sendMessage = useCallback(async (
    content: string, 
    requestDetailed: boolean = false
  ): Promise<void> => {
    if (!currentSession) {
      toast.error('No active session');
      return;
    }

    setIsLoading(true);

    try {
      // Add user message to current session
      const userMessage: Message = {
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      const updatedMessages = [...currentSession.messages, userMessage];
      const updatedSession = {
        ...currentSession,
        messages: updatedMessages,
        lastActivity: new Date().toISOString(),
      };

      setCurrentSession(updatedSession);
      setSessions(prev => prev.map(session => 
        session.id === currentSession.id ? updatedSession : session
      ));

      // Update session title if this is the first message
      if (currentSession.messages.length === 0) {
        const title = content.length > 50 ? content.substring(0, 50) + '...' : content;
        updateSessionTitle(currentSession.id, title);
      }

      // Send message to API (use authenticated endpoint if user is logged in)
      let response: ChatResponse;
      if (isAuthenticated) {
        response = await authService.sendAuthenticatedMessage({
          message: content,
          session_id: currentSession.id,
          request_detailed: requestDetailed,
        });
      } else {
        response = await chatAPI.sendMessage({
          message: content,
          session_id: currentSession.id,
          request_detailed: requestDetailed,
        });
      }

      // Add assistant response (including rejection messages)
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
      };

      const finalMessages = [...updatedMessages, assistantMessage];

      const finalSession = {
        ...updatedSession,
        messages: finalMessages,
        lastActivity: new Date().toISOString(),
        messageCount: response.message_count || finalMessages.length, // Use backend message count
        isSummarizing: response.summarization_triggered || false,
      };

      setCurrentSession(finalSession);
      setSessions(prev => prev.map(session => 
        session.id === currentSession.id ? finalSession : session
      ));

      // Auto-hide summarization indicator after 3 seconds
      if (response.summarization_triggered) {
        setTimeout(() => {
          setCurrentSession(prev => prev ? { ...prev, isSummarizing: false } : null);
          setSessions(prev => prev.map(session => 
            session.id === currentSession.id 
              ? { ...session, isSummarizing: false }
              : session
          ));
        }, 3000);
      }

      // No toast notification for guardrail triggers - silent blocking

    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message. Please try again.');
      
      // Remove the user message if API call failed
      setCurrentSession(prev => prev ? {
        ...prev,
        messages: prev.messages.slice(0, -1)
      } : null);
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, updateSessionTitle]);

  // Request detailed explanation
  const requestDetailed = useCallback(async () => {
    if (!currentSession || currentSession.messages.length === 0) return;
    
    const lastUserMessage = currentSession.messages
      .filter(msg => msg.role === 'user')
      .pop();
    
    if (lastUserMessage) {
      await sendMessage(lastUserMessage.content, true);
    }
  }, [currentSession, sendMessage]);

  return {
    sessions,
    currentSession,
    isLoading,
    isOnline,
    isLoadingSessions,
    createNewSession,
    selectSession,
    deleteSession,
    sendMessage,
    requestDetailed,
    checkHealth,
  };
};



