import { useState, useCallback, useEffect } from 'react';
import { ChatSession, Message, ChatResponse } from '../types';
import { chatAPI } from '../services/api';
import { toast } from 'react-hot-toast';

export const useChat = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // Load sessions from backend on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const response = await chatAPI.getUserSessions();
        const backendSessions = response.sessions.map((session: any) => ({
          id: session.session_id,
          title: session.preview || 'New Chat',
          messages: [], // Messages will be loaded when session is selected
          createdAt: session.created_at,
          lastActivity: session.last_activity,
          isActive: session.is_active,
        }));
        
        setSessions(backendSessions);
        
        // Set the most recent session as current and load its messages
        if (backendSessions.length > 0) {
          const mostRecent = backendSessions.reduce((latest: ChatSession, current: ChatSession) => 
            new Date(current.lastActivity) > new Date(latest.lastActivity) ? current : latest
          );
          
          // Load messages for the most recent session
          try {
            const response = await chatAPI.getConversationHistory(mostRecent.id);
            const sessionWithMessages = {
              ...mostRecent,
              messages: response.messages || []
            };
            setCurrentSession(sessionWithMessages);
          } catch (error) {
            console.error('Error loading messages for most recent session:', error);
            setCurrentSession(mostRecent);
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
  }, []);

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
      const response = await chatAPI.createSession();
      const newSession: ChatSession = {
        id: response.session_id,
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString(),
        lastActivity: new Date().toISOString(),
        isActive: true,
      };

      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
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
      setCurrentSession(newSession);
      return newSession;
    }
  }, []);

  // Select a session and load its messages
  const selectSession = useCallback(async (session: ChatSession) => {
    try {
      // Load messages for this session from backend
      const response = await chatAPI.getConversationHistory(session.id);
      console.log('Loaded messages for session:', session.id, response.messages);
      const sessionWithMessages = {
        ...session,
        messages: response.messages || []
      };
      setCurrentSession(sessionWithMessages);
    } catch (error) {
      console.error('Error loading session messages:', error);
      // Fallback to session without messages
      setCurrentSession(session);
    }
  }, []);

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string) => {
    try {
      await chatAPI.deleteSession(sessionId);
      setSessions(prev => prev.filter(session => session.id !== sessionId));
      
      if (currentSession?.id === sessionId) {
        const remainingSessions = sessions.filter(session => session.id !== sessionId);
        setCurrentSession(remainingSessions.length > 0 ? remainingSessions[0] : null);
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

      // Send message to API
      const response: ChatResponse = await chatAPI.sendMessage({
        message: content,
        session_id: currentSession.id,
        request_detailed: requestDetailed,
      });

      // Add assistant response
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



