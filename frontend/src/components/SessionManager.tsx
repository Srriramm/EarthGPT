import React, { useState } from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ChatSession } from '../services/auth';

interface SessionManagerProps {
  onSessionSelect: (session: ChatSession) => void;
}

const SessionManager: React.FC<SessionManagerProps> = ({ onSessionSelect }) => {
  const { sessions, createSession, deleteSession, currentSession } = useAuth();
  const [isCreating, setIsCreating] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSessionTitle.trim()) return;

    setIsLoading(true);
    try {
      const newSession = await createSession({ title: newSessionTitle.trim() });
      setNewSessionTitle('');
      setIsCreating(false);
      onSessionSelect(newSession);
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this session?')) {
      try {
        await deleteSession(sessionId);
      } catch (error) {
        console.error('Failed to delete session:', error);
      }
    }
  };


  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Chat Sessions
          </h2>
          <button
            onClick={() => setIsCreating(true)}
            className="p-2 text-gray-500 hover:text-earth-600 dark:text-gray-400 dark:hover:text-earth-400 transition-colors"
            title="New Session"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>

        {/* New Session Form */}
        {isCreating && (
          <form onSubmit={handleCreateSession} className="mb-4">
            <div className="flex space-x-2">
              <input
                type="text"
                value={newSessionTitle}
                onChange={(e) => setNewSessionTitle(e.target.value)}
                placeholder="Session title..."
                className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-earth-500 focus:border-earth-500 dark:bg-gray-700 dark:text-white"
                autoFocus
              />
              <button
                type="submit"
                disabled={isLoading || !newSessionTitle.trim()}
                className="px-3 py-2 text-sm bg-earth-600 text-white rounded-lg hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? '...' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setNewSessionTitle('');
                }}
                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No chat sessions yet</p>
            <p className="text-xs mt-1">Create your first session to get started</p>
          </div>
        ) : (
          <div className="p-2">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onSessionSelect(session)}
                className={`group p-3 rounded-lg cursor-pointer transition-colors mb-2 ${
                  currentSession?.id === session.id
                    ? 'bg-earth-100 dark:bg-earth-900/30 border border-earth-200 dark:border-earth-700'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {session.title}
                    </h3>
                    <div className="flex items-center mt-1 text-xs text-gray-500 dark:text-gray-400">
                      <MessageSquare className="h-3 w-3 mr-1" />
                      <span>{session.message_count} messages</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400 transition-all"
                    title="Delete session"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
          {sessions.length} session{sessions.length !== 1 ? 's' : ''}
        </div>
      </div>
    </div>
  );
};

export default SessionManager;

