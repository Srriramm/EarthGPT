import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Sparkles } from 'lucide-react';

interface SummarizationIndicatorProps {
  isVisible: boolean;
  type?: 'summarization' | 'semantic_search';
}

const SummarizationIndicator: React.FC<SummarizationIndicatorProps> = ({ isVisible, type = 'summarization' }) => {
  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="w-full mb-4"
        >
          <div className={`flex items-center justify-center p-4 border rounded-lg shadow-sm ${
            type === 'semantic_search' 
              ? 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800'
              : 'bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800'
          }`}>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Brain className={`w-5 h-5 ${type === 'semantic_search' ? 'text-green-600 dark:text-green-400' : 'text-blue-600 dark:text-blue-400'}`} />
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="absolute -top-1 -right-1"
                >
                  <Sparkles className={`w-3 h-3 ${type === 'semantic_search' ? 'text-green-500' : 'text-blue-500'}`} />
                </motion.div>
              </div>
              <div className="text-center">
                <h3 className={`text-sm font-medium mb-1 ${type === 'semantic_search' ? 'text-green-800 dark:text-green-200' : 'text-blue-800 dark:text-blue-200'}`}>
                  {type === 'semantic_search' ? 'Searching Context' : 'Summarizing Context'}
                </h3>
                <p className={`text-xs ${type === 'semantic_search' ? 'text-green-600 dark:text-green-300' : 'text-blue-600 dark:text-blue-300'}`}>
                  {type === 'semantic_search' ? 'Finding relevant messages from this conversation' : 'Optimizing conversation history for better performance'}
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default SummarizationIndicator;
