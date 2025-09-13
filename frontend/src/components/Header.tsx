import React from 'react';
import { Menu, Settings } from 'lucide-react';

interface HeaderProps {
  onToggleSidebar: () => void;
  currentSession: { title: string } | null;
  isOnline: boolean;
}

const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  currentSession,
  isOnline,
}) => {
  return (
    <header className="h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4 lg:px-6">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors lg:hidden"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
        
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg earthgpt-brand text-gray-900 dark:text-white">
              <span className="earth">Earth</span><span className="gpt">GPT</span>
            </h1>
            {currentSession && (
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                {currentSession.title === 'New Chat' ? 'Current Chat' : currentSession.title}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Status indicator */}
        <div className="flex items-center gap-2 text-sm">
          <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 animate-pulse-green' : 'bg-red-500'}`}></div>
          <span className="text-gray-600 dark:text-gray-400">
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* Settings button */}
        <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" aria-label="Settings">
          <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      </div>
    </header>
  );
};

export default Header;
