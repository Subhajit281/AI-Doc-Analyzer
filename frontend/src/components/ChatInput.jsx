import { useState, useRef, useEffect } from 'react';
import { ArrowUp, Plus } from 'lucide-react';
import './ChatInput.css';

export default function ChatInput({ onSend, onUploadClick, disabled, sendDisabled, placeholder }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !sendDisabled;

  const handleSend = () => {
    if (!canSend) return;
    onSend(value.trim());
    setValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-bar">
      <div className="chat-input-inner">
        <div className="chat-input-box">
          <button
            type="button"
            className="chat-input-plus"
            onClick={onUploadClick}
            aria-label="Add document"
          >
            <Plus size={16} strokeWidth={2.25} />
          </button>
          <textarea
            ref={textareaRef}
            className="chat-input-textarea"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || 'Ask anything about your document...'}
            disabled={disabled}
            rows={1}
          />
          <button
            type="button"
            className="chat-input-send"
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send message"
          >
            <ArrowUp size={16} strokeWidth={2.25} />
          </button>
        </div>
      </div>
    </div>
  );
}