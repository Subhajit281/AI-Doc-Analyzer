import { AlertCircle } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import { TypingDots } from './LoadingIndicator';
import './ChatMessage.css';

export default function ChatMessage({ role, content, isLoading, isError }) {
  const isUser = role === 'user';

  return (
    <div className={`chat-message ${isUser ? 'chat-message-user' : 'chat-message-ai'}`}>
      <div
        className={[
          'chat-bubble',
          isUser ? 'chat-bubble-user' : 'chat-bubble-ai',
          isError ? 'chat-bubble-error' : '',
        ].join(' ').trim()}
      >
        {isLoading ? (
          <TypingDots />
        ) : isUser ? (
          <span className="chat-bubble-plain">{content}</span>
        ) : isError ? (
          <span className="chat-bubble-error-text">
            <AlertCircle size={14} strokeWidth={2} />
            {content}
          </span>
        ) : (
          <MarkdownRenderer content={content} />
        )}
      </div>
    </div>
  );
}
