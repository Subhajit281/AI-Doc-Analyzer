import { useEffect, useRef } from 'react';
import { MessageSquare } from 'lucide-react';
import ChatMessage from './ChatMessage';
import './ChatWindow.css';

export default function ChatWindow({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-window">
        <div className="chat-empty">
          <MessageSquare size={20} strokeWidth={1.5} />
          <p>Ask a question to start the conversation.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window">
      <div className="chat-window-inner">
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            isLoading={message.isLoading}
            isError={message.isError}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
