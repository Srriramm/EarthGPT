import React, { useState } from 'react';
import { 
  Copy, 
  Check, 
  ChevronDown
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
  const isAssistant = message.role === 'assistant';

  const markdownComponents = {
    h1: ({node, children, ...props}: any) => <h1 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white" {...props}>{children}</h1>,
    h2: ({node, children, ...props}: any) => <h2 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white" {...props}>{children}</h2>,
    h3: ({node, children, ...props}: any) => <h3 className="text-base font-semibold mb-2 text-gray-900 dark:text-white" {...props}>{children}</h3>,
    h4: ({node, children, ...props}: any) => <h4 className="text-sm font-semibold mb-1 text-gray-900 dark:text-white" {...props}>{children}</h4>,
    p: ({node, children, ...props}: any) => <p className="mb-3 leading-relaxed text-justify" {...props}>{children}</p>,
    ul: ({node, children, ...props}: any) => <ul className="list-disc list-outside mb-3 space-y-2 ml-4" {...props}>{children}</ul>,
    ol: ({node, children, ...props}: any) => <ol className="list-decimal list-outside mb-3 space-y-2 ml-4" {...props}>{children}</ol>,
    li: ({node, children, ...props}: any) => <li className="leading-relaxed" {...props}>{children}</li>,
    strong: ({node, children, ...props}: any) => <strong className="font-semibold text-gray-900 dark:text-white" {...props}>{children}</strong>,
    em: ({node, children, ...props}: any) => <em className="italic" {...props}>{children}</em>,
    code: ({node, inline, className, children, ...props}: any) => 
      inline ? 
        <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm font-mono" {...props}>{children}</code> :
        <code className="block bg-gray-100 dark:bg-gray-800 p-3 rounded-lg text-sm font-mono overflow-x-auto" {...props}>{children}</code>,
    blockquote: ({node, children, ...props}: any) => <blockquote className="border-l-4 border-earth-500 pl-4 italic my-3" {...props}>{children}</blockquote>,
    a: ({node, children, ...props}: any) => <a className="text-earth-600 dark:text-earth-400 hover:underline" {...props}>{children}</a>,
    table: ({node, children, ...props}: any) => <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-700 my-3" {...props}>{children}</table>,
    th: ({node, children, ...props}: any) => <th className="border border-gray-300 dark:border-gray-700 px-3 py-2 bg-gray-50 dark:bg-gray-800 font-semibold" {...props}>{children}</th>,
    td: ({node, children, ...props}: any) => <td className="border border-gray-300 dark:border-gray-700 px-3 py-2" {...props}>{children}</td>,
  };

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
              components={markdownComponents}
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
          {isSummary && (
            <div className="flex items-center gap-2 mb-2">
              <span className="sustainability-badge">
                Summary
              </span>
            </div>
          )}

          {/* Message Text */}
          <div className="prose prose-sm max-w-none dark:prose-invert text-gray-900 dark:text-gray-100 text-justify">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
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