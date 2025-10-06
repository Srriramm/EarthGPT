import React, { useState } from 'react';
import { 
  Copy, 
  Check, 
  ChevronDown,
  Database
} from 'lucide-react';
import { Message } from '../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: Message;
  isSummary?: boolean;
  canRequestDetailed?: boolean;
  onRequestDetailed?: () => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isSummary = false,
  canRequestDetailed = false,
  onRequestDetailed,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const isUser = message.role === 'user';


  if (isUser) {
    // User message layout (right-aligned, content-based width)
    return (
      <div className="chat-message user mb-6 w-full flex flex-col items-end">
        {/* Message Bubble */}
        <div className="inline-block max-w-2xl p-3 bg-earth-100 dark:bg-earth-900 rounded-lg">

          {/* Message Text */}
          <div className="prose prose-sm max-w-none dark:prose-invert text-gray-900 dark:text-gray-100 text-justify">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({children}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-900 dark:text-gray-100">{children}</h1>,
                h2: ({children}) => <h2 className="text-xl font-bold mb-3 mt-5 text-gray-900 dark:text-gray-100">{children}</h2>,
                h3: ({children}) => <h3 className="text-lg font-bold mb-2 mt-4 text-gray-900 dark:text-gray-100">{children}</h3>,
                h4: ({children}) => <h4 className="text-base font-bold mb-2 mt-3 text-gray-900 dark:text-gray-100">{children}</h4>,
                p: ({children}) => <p className="mb-4 leading-relaxed text-justify">{children}</p>,
                strong: ({children}) => <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>,
                ul: ({children}) => <ul className="list-disc list-outside ml-6 mb-4 space-y-2">{children}</ul>,
                ol: ({children}) => <ol className="list-decimal list-outside ml-6 mb-4 space-y-2">{children}</ol>,
                li: ({children}) => <li className="leading-relaxed mb-1">{children}</li>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
        
        {/* Copy Button - Right below the message box */}
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors mt-1"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              Copy
            </>
          )}
        </button>
      </div>
    );
  }

  // Assistant message layout (left-aligned, content-based width)
  return (
    <div className="chat-message assistant mb-6 w-full flex flex-col items-start">
      {/* Message Bubble */}
      <div className="inline-block max-w-3xl p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {isSummary && (
              <span className="sustainability-badge">
                Summary
              </span>
            )}
            
            
            {/* Memory Indicator */}
            {message.memory_used && (
              <span className="flex items-center gap-1 px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
                <Database className="w-3 h-3" />
                Memory
              </span>
            )}
          </div>

          {/* Message Text */}
          <div className="prose prose-sm max-w-none dark:prose-invert text-gray-900 dark:text-gray-100 text-justify">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({children}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-900 dark:text-gray-100">{children}</h1>,
                h2: ({children}) => <h2 className="text-xl font-bold mb-3 mt-5 text-gray-900 dark:text-gray-100">{children}</h2>,
                h3: ({children}) => <h3 className="text-lg font-bold mb-2 mt-4 text-gray-900 dark:text-gray-100">{children}</h3>,
                h4: ({children}) => <h4 className="text-base font-bold mb-2 mt-3 text-gray-900 dark:text-gray-100">{children}</h4>,
                p: ({children}) => <p className="mb-4 leading-relaxed text-justify">{children}</p>,
                strong: ({children}) => <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>,
                ul: ({children}) => <ul className="list-disc list-outside ml-6 mb-4 space-y-2">{children}</ul>,
                ol: ({children}) => <ol className="list-decimal list-outside ml-6 mb-4 space-y-2">{children}</ol>,
                li: ({children}) => <li className="leading-relaxed mb-1">{children}</li>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
      </div>

      {/* Action Buttons - Below the message box */}
      <div className="flex items-center gap-2 mt-1">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              Copy
            </>
          )}
        </button>

        {isSummary && canRequestDetailed && onRequestDetailed && (
          <button
            onClick={onRequestDetailed}
            className="flex items-center gap-1 px-3 py-1 text-xs bg-earth-100 hover:bg-earth-200 dark:bg-earth-900 dark:hover:bg-earth-800 text-earth-800 dark:text-earth-200 rounded-full transition-colors"
          >
            <ChevronDown className="w-3 h-3" />
            Get Detailed Explanation
          </button>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;