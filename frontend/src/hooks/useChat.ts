import { useState, useCallback, useEffect, useRef } from 'react';
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
  const sessionsLoadedRef = useRef(false);

  // Load sessions from backend on mount
  useEffect(() => {
    console.log('useChat useEffect triggered:', {
      isAuthenticated,
      sessionsLoadedRef: sessionsLoadedRef.current,
      sessionsLength: sessions.length
    });
    
    const loadSessions = async () => {
      // Prevent multiple loading attempts
      if (sessionsLoadedRef.current) {
        console.log('Sessions already loaded, skipping reload');
        setIsLoadingSessions(false);
        return;
      }
      
      try {
        // Only load sessions for authenticated users
        if (!isAuthenticated) {
          console.log('User not authenticated, skipping session loading');
          sessionsLoadedRef.current = true;
          setIsLoadingSessions(false);
          return;
        }
        
        console.log('Loading authenticated sessions...');
        const authSessions = await authService.getUserSessions();
        console.log('Raw auth sessions from backend:', authSessions);
        const backendSessions: ChatSession[] = authSessions.map((session: any) => ({
          id: session.id,
          title: session.title || 'New Chat',
          messages: [], // Messages will be loaded when session is selected
          createdAt: session.created_at,
          lastActivity: session.last_activity,
          isActive: session.is_active,
          messageCount: session.message_count || 0, // Map backend message_count to frontend messageCount
        }));
        console.log(`Loaded ${backendSessions.length} authenticated sessions:`, backendSessions);
        
        setSessions(backendSessions);
        sessionsLoadedRef.current = true;
        
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
              console.log('Persisted session not found in backend sessions, using most recent:', persistedSessionId);
              // Clear the invalid persisted session ID
              localStorage.removeItem('earthgpt-current-session-id');
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
            console.log('Loading messages for target session:', targetSession.id);
            const response = await authService.getSessionHistory(targetSession.id);
            console.log('Session history response:', response);
            console.log('Response messages:', response.messages);
            
            const sessionWithMessages = {
              ...targetSession,
              messages: response.messages || []
            };
            console.log('Setting current session with messages:', sessionWithMessages);
            setCurrentSession(sessionWithMessages);
            
            // Persist the current session ID
            localStorage.setItem('earthgpt-current-session-id', targetSession.id);
          } catch (error) {
            console.error('Error loading messages for target session:', error);
            setCurrentSession(targetSession);
            localStorage.setItem('earthgpt-current-session-id', targetSession.id);
          }
        } else {
          // No sessions found - don't create one here, let App.tsx handle it
          console.log('No sessions found, will let App.tsx create one if needed');
          setCurrentSession(null);
          localStorage.removeItem('earthgpt-current-session-id');
          sessionsLoadedRef.current = true;
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
        sessionsLoadedRef.current = true;
      } finally {
        setIsLoadingSessions(false);
      }
    };
    
    loadSessions();
  }, [isAuthenticated]);

  // Reset sessions loaded flag when authentication changes
  useEffect(() => {
    console.log('Authentication state changed, resetting sessions loaded flag:', isAuthenticated);
    sessionsLoadedRef.current = false;
    setIsLoadingSessions(true);
    
    // Clear current session when authentication changes
    if (!isAuthenticated) {
      setCurrentSession(null);
      setSessions([]);
      localStorage.removeItem('earthgpt-current-session-id');
    }
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
      // Use authenticated session creation only
      const response = await authService.createSession({ title: 'New Chat' });
      const newSession: ChatSession = {
        id: response.id,
        title: response.title,
        messages: [],
        createdAt: response.created_at,
        lastActivity: response.last_activity,
        isActive: response.is_active,
      };

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
  }, []);

  // Select a session and load its messages
  const selectSession = useCallback(async (session: ChatSession) => {
    try {
      // Load messages for this session from backend (authenticated only)
      const response = await authService.getSessionHistory(session.id);
      
      console.log('Loaded messages for session:', session.id, response.messages);
      console.log('Response from getSessionHistory:', response);
      const sessionWithMessages = {
        ...session,
        messages: response.messages || []
      };
      console.log('Setting current session with messages:', sessionWithMessages);
      setCurrentSession(sessionWithMessages);
      
      // Persist the selected session ID
      localStorage.setItem('earthgpt-current-session-id', session.id);
    } catch (error) {
      console.error('Error loading session messages:', error);
      // Fallback to session without messages
      setCurrentSession(session);
      localStorage.setItem('earthgpt-current-session-id', session.id);
    }
  }, []);

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await authService.deleteSession(sessionId);
      
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
  }, [currentSession, sessions]);

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

      // Send message to API (authenticated only)
      let response: ChatResponse;
      try {
        response = await authService.sendAuthenticatedMessage({
          message: content,
          session_id: currentSession.id,
          request_detailed: requestDetailed,
        });
      } catch (error: any) {
        // If session not found, create a new session and retry
        if (error.response?.status === 404 && error.response?.data?.detail === "Session not found") {
          console.log('Session not found, creating new session and retrying...');
          const newSession = await createNewSession();
          
          // Retry with new session
          response = await authService.sendAuthenticatedMessage({
            message: content,
            session_id: newSession.id,
            request_detailed: requestDetailed,
          });
        } else {
          throw error;
        }
      }

      // Add assistant response
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        memory_used: response.memory_used,
      };

      const finalMessages = [...updatedMessages, assistantMessage];
      const finalSession = {
        ...updatedSession,
        messages: finalMessages,
        lastActivity: new Date().toISOString(),
        messageCount: finalMessages.length, // Update message count
      };

      setCurrentSession(finalSession);
      setSessions(prev => prev.map(session => 
        session.id === currentSession.id ? finalSession : session
      ));

      // Show guardrail warning if triggered
      if (response.guardrail_triggered) {
        toast.error('This topic is outside my sustainability focus. Please ask about environmental topics.');
      }

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
  }, [currentSession, updateSessionTitle, createNewSession]);

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



