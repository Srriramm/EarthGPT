import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Message } from '../types';
import ChatMessage from './ChatMessage';
import { AlertTriangle } from 'lucide-react';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  isSummary?: boolean;
  canRequestDetailed?: boolean;
  onRequestDetailed?: () => void;
  guardrailTriggered?: boolean;
  guardrailReason?: string;
}

const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  isSummary = false,
  canRequestDetailed = false,
  onRequestDetailed,
  guardrailTriggered = false,
  guardrailReason,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="h-full overflow-y-auto py-6 space-y-4 w-full px-2">
      {/* Welcome Message */}
      {messages.length === 0 && !isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-12"
        >
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
            Welcome to <span className="earthgpt-brand"><span className="earth">Earth</span><span className="gpt">GPT</span></span>
          </h2>
        </motion.div>
      )}

      {/* Messages */}
      <AnimatePresence>
        {messages.map((message, index) => (
          <motion.div
            key={`${message.timestamp}-${index}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="w-full"
          >
            <ChatMessage
              message={message}
              isSummary={isSummary && message.role === 'assistant' && index === messages.length - 1}
              canRequestDetailed={canRequestDetailed && message.role === 'assistant' && index === messages.length - 1}
              onRequestDetailed={onRequestDetailed}
            />
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Loading Indicator */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-3 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg w-full"
        >
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm earthgpt-brand"><span className="earth">Earth</span><span className="gpt">GPT</span></span>
              <span className="text-xs text-gray-500 dark:text-gray-400">is thinking...</span>
            </div>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </motion.div>
      )}

      {/* Guardrail Warning */}
      {guardrailTriggered && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                Topic Outside Sustainability Focus
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-2">
                {guardrailReason || "I'm a sustainability expert assistant focused on environmental topics, climate action, and sustainable practices."}
              </p>
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                I'd be happy to help with questions about renewable energy, carbon reduction, ESG, 
                or other sustainability-related topics!
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatArea;
