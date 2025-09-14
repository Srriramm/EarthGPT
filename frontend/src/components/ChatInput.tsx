import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, AlertTriangle } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string, requestDetailed?: boolean) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
  placeholder = "Ask me about sustainability, climate change, renewable energy, or environmental topics..."
}) => {
  const [message, setMessage] = useState('');
  const [showGuardrailWarning, setShowGuardrailWarning] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [message]);

  // Check for obviously non-sustainability keywords (only the most obvious ones)
  const checkForNonSustainability = (text: string) => {
    const obviousNonSustainabilityKeywords = [
      'poker', 'gambling', 'casino', 'betting', 'cards',
      'dating', 'relationship', 'love', 'marriage',
      'gaming', 'video game', 'playstation', 'xbox',
      'movie', 'film', 'celebrity', 'entertainment'
    ];
    
    const textLower = text.toLowerCase();
    return obviousNonSustainabilityKeywords.some(keyword => textLower.includes(keyword));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() || isLoading || disabled) return;

    // Check for non-sustainability content
    if (checkForNonSustainability(message)) {
      setShowGuardrailWarning(true);
      setTimeout(() => setShowGuardrailWarning(false), 5000);
      return;
    }

    onSendMessage(message.trim());
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };


  return (
    <div className="w-full max-w-4xl mx-auto bg-transparent">
      {/* Guardrail Warning */}
      {showGuardrailWarning && (
        <div className="mb-4 p-3 bg-yellow-50/50 dark:bg-yellow-900/20 border border-yellow-200/50 dark:border-yellow-800/50 rounded-lg backdrop-blur-sm">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                Sustainability Focus
              </p>
              <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
                EarthGPT specializes in sustainability topics. Try asking about climate change, 
                renewable energy, environmental protection, or sustainable practices.
              </p>
            </div>
          </div>
        </div>
      )}


      {/* Input Form */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isLoading}
            className="input-field resize-none min-h-[60px] max-h-[200px] pr-12"
            rows={1}
          />
          
          <button
            type="submit"
            disabled={!message.trim() || isLoading || disabled}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-earth-600 hover:bg-earth-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Character count */}
        <div className="flex justify-between items-center mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>
            {message.length > 0 && `${message.length} characters`}
          </span>
          <span>
            Press Enter to send, Shift+Enter for new line
          </span>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;


