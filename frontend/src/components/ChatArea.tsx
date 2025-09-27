import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Message } from '../types';
import ChatMessage from './ChatMessage';
import SummarizationIndicator from './SummarizationIndicator';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  isSummary?: boolean;
  canRequestDetailed?: boolean;
  onRequestDetailed?: () => void;
  guardrailTriggered?: boolean;
  guardrailReason?: string;
  isSummarizing?: boolean;
}

const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  isSummary = false,
  canRequestDetailed = false,
  onRequestDetailed,
  guardrailTriggered = false,
  guardrailReason,
  isSummarizing = false,
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

      {/* Summarization Indicator */}
      <SummarizationIndicator isVisible={isSummarizing} />

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


      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatArea;
