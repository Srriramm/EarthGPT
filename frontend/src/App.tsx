import React, { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import { useChat } from './hooks/useChat';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './contexts/AuthContext';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import AuthPage from './components/AuthPage';

const App: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isDarkMode, toggleTheme } = useTheme();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const {
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
  } = useChat();

  // Check health on mount and periodically
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, [checkHealth]);

  // Create initial session if none exist (only after loading is complete)
  useEffect(() => {
    if (!isLoadingSessions && sessions.length === 0) {
      createNewSession();
    }
  }, [isLoadingSessions, sessions.length, createNewSession]);

  const handleNewChat = async () => {
    await createNewSession();
    setSidebarOpen(false);
  };

  const handleSelectSession = async (session: any) => {
    await selectSession(session);
    setSidebarOpen(false);
  };

  const handleDeleteSession = async (sessionId: string) => {
    await deleteSession(sessionId);
  };

  const handleSendMessage = async (message: string, requestDetailed?: boolean) => {
    await sendMessage(message, requestDetailed);
  };

  const handleRequestDetailed = async () => {
    await requestDetailed();
  };

  const handleToggleSidebar = () => {
    setSidebarOpen(prev => !prev);
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors ${isDarkMode ? 'dark' : ''}`}>
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-earth-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show authentication page if not authenticated
  if (!isAuthenticated) {
    return (
      <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors ${isDarkMode ? 'dark' : ''}`}>
        <AuthPage />
      </div>
    );
  }

  return (
    <div className={`h-screen bg-gray-50 dark:bg-gray-900 transition-colors ${isDarkMode ? 'dark' : ''}`}>
      <div className="flex h-full">
        {/* Sidebar */}
        <Sidebar
          sessions={sessions}
          currentSession={currentSession}
          isDarkMode={isDarkMode}
          sidebarOpen={sidebarOpen}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onToggleDarkMode={toggleTheme}
          onToggleSidebar={handleToggleSidebar}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col w-full h-full overflow-hidden">
          {/* Header */}
          <Header
            onToggleSidebar={handleToggleSidebar}
            currentSession={currentSession}
            isOnline={isOnline}
          />

          {/* Loading State */}
          {isLoadingSessions ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-earth-600 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">Loading conversations...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Chat Area */}
              <div className="flex-1 relative overflow-hidden">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentSession?.id || 'no-session'}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.4, ease: "easeInOut" }}
                    className="h-full"
                  >
                    <ChatArea
                      messages={currentSession?.messages || []}
                      isLoading={isLoading}
                      onRequestDetailed={handleRequestDetailed}
                    />
                  </motion.div>
                </AnimatePresence>
              </div>

              {/* Chat Input */}
              <div className="p-6 bg-transparent">
                <ChatInput
                  onSendMessage={handleSendMessage}
                  isLoading={isLoading}
                  disabled={!isOnline}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: isDarkMode ? '#374151' : '#ffffff',
            color: isDarkMode ? '#f9fafb' : '#111827',
            border: `1px solid ${isDarkMode ? '#4b5563' : '#e5e7eb'}`,
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#ffffff',
            },
          },
        }}
      />
    </div>
  );
};

export default App;
