import React from 'react';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Moon, 
  Sun,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatSession } from '../types';

interface SidebarProps {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  isDarkMode: boolean;
  sidebarOpen: boolean;
  onNewChat: () => void;
  onSelectSession: (session: ChatSession) => void;
  onDeleteSession: (sessionId: string) => void;
  onToggleDarkMode: () => void;
  onToggleSidebar: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSession,
  isDarkMode,
  sidebarOpen,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onToggleDarkMode,
  onToggleSidebar,
}) => {
  const truncateTitle = (title: string, maxLength: number = 30) => {
    return title.length > maxLength ? title.substring(0, maxLength) + '...' : title;
  };

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onToggleSidebar}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-50 w-80 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        flex flex-col
      `}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white earthgpt-brand">
                <span className="earth">Earth</span><span className="gpt">GPT</span>
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onToggleDarkMode}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="Toggle dark mode"
              >
                {isDarkMode ? (
                  <Sun className="w-5 h-5 text-yellow-500" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                )}
              </button>
              <button
                onClick={onToggleSidebar}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors lg:hidden"
                aria-label="Close sidebar"
              >
                <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </button>
            </div>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <motion.button
            onClick={onNewChat}
            className="w-full flex items-center gap-3 px-4 py-3 bg-earth-600 hover:bg-earth-700 text-white rounded-lg font-medium transition-colors"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Plus className="w-5 h-5" />
            New Chat
          </motion.button>
        </div>

        {/* Chat Sessions */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          <div className="space-y-2">
            {sessions.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  No conversations yet
                </p>
                <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                  Start a new chat to begin
                </p>
                <button
                  onClick={() => {
                    localStorage.setItem('earthgpt-no-auto-session', 'true');
                    window.location.reload();
                  }}
                  className="mt-3 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 underline"
                >
                  Start with no sessions
                </button>
              </div>
            ) : (
              <AnimatePresence>
                {sessions.map((session, index) => (
                  <motion.div
                    key={session.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2, delay: index * 0.05 }}
                    className={`
                      group relative flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all duration-200
                      ${currentSession?.id === session.id 
                        ? 'bg-earth-100 dark:bg-earth-900 text-earth-800 dark:text-earth-200 shadow-sm' 
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 hover:shadow-sm'
                      }
                    `}
                    onClick={() => onSelectSession(session)}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <MessageSquare className="w-4 h-4 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {truncateTitle(session.title)}
                      </p>
                      {/* Session info */}
                      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {session.messageCount || session.messages?.length || 0} messages
                      </div>
                    </div>
                    <motion.button
                      initial={{ opacity: 0 }}
                      whileHover={{ opacity: 1 }}
                      onClick={(e) => {
                        e.stopPropagation();
                        console.log('Delete button clicked for session:', session.id);
                        onDeleteSession(session.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-all"
                      aria-label="Delete session"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </motion.button>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse-green"></div>
            <span><span className="earthgpt-brand"><span className="earth">Earth</span><span className="gpt">GPT</span></span> Online</span>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
