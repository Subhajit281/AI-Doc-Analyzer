import { AlertCircle, Cpu, Zap } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import { TypingDots } from './LoadingIndicator';
import './ChatMessage.css';

export default function ChatMessage({
  role,
  content,
  isLoading,
  isError,
  model,
  isPro,
}) {
  const isUser = role === 'user';

  const isProModel = Boolean(isPro || (model && (model.includes('qwen') || model.includes('compound'))));
  const modelLabel = isProModel
    ? 'Better Model Analyzer'
    : 'DocAI Assistant';

  return (
    <div className={`chat-message ${isUser ? 'chat-message-user' : 'chat-message-ai'}`}>
      <div
        className={[
          'chat-bubble',
          isUser ? 'chat-bubble-user' : 'chat-bubble-ai',
          isError ? 'chat-bubble-error' : '',
        ].join(' ').trim()}
      >
        {!isUser && !isLoading && !isError && (
          <div className="chat-bubble-header-bar">
            <div className={`ai-model-pill ${isProModel ? 'pro-pill' : 'free-pill'}`}>
              {isProModel ? <Zap size={11} strokeWidth={2.5} /> : <Cpu size={11} strokeWidth={2} />}
              <span>{modelLabel}</span>
              <span className="ai-model-tag">{isProModel ? 'PRO' : 'FREE'}</span>
            </div>
          </div>
        )}

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
          <div className="chat-bubble-markdown-wrapper">
            <MarkdownRenderer content={content} />
          </div>
        )}
      </div>
    </div>
  );
}
