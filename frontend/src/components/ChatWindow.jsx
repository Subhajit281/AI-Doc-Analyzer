import { useEffect, useRef } from 'react';
import { Sparkles, Table, ListTree, HelpCircle } from 'lucide-react';
import ChatMessage from './ChatMessage';
import './ChatWindow.css';

const STARTER_PROMPTS = [
  {
    icon: Sparkles,
    label: 'Summarize Key Findings',
    desc: 'Comprehensive executive summary highlighting main objectives and conclusions.',
    prompt: 'Can you provide a comprehensive summary of this document, highlighting the main objectives, findings, and conclusions?',
  },
  {
    icon: Table,
    label: 'Extract Data & Metrics',
    desc: 'Identify important tables, quantitative metrics, and numerical data points.',
    prompt: 'Extract the key data points, figures, statistics, and table metrics discussed across this document.',
  },
  {
    icon: ListTree,
    label: 'Document Structure',
    desc: 'Map out the core sections, headings hierarchy, and topical organization.',
    prompt: 'What are the main sections, topics, and hierarchical structure of this document?',
  },
  {
    icon: HelpCircle,
    label: 'Actionable Insights',
    desc: 'Extract key takeaways, recommendations, and strategic action points.',
    prompt: 'What are the core conclusions, recommendations, and actionable insights from this document?',
  },
];

export default function ChatWindow({ messages, isReady = true, onSelectPrompt }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="chat-window">
        <div className="chat-empty-container">
          <div className="chat-empty-badge">
            <Sparkles size={13} strokeWidth={2} />
            <span>Document Ready for Analysis</span>
          </div>

          <h2 className="chat-empty-title">
            Ask questions, verify claims, or extract insights
          </h2>

          <p className="chat-empty-desc">
            Select a suggested prompt below or type your custom inquiry in the prompt bar.
          </p>

          <div className="starter-prompts-grid">
            {STARTER_PROMPTS.map((item, idx) => {
              const Icon = item.icon;
              return (
                <button
                  key={idx}
                  type="button"
                  className="starter-prompt-card"
                  onClick={() => onSelectPrompt && onSelectPrompt(item.prompt)}
                  disabled={!isReady}
                  title={isReady ? item.prompt : 'Document is processing…'}
                >
                  <div className="starter-prompt-header">
                    <div className="starter-prompt-icon-box">
                      <Icon size={15} strokeWidth={2} />
                    </div>
                    <span className="starter-prompt-label">{item.label}</span>
                  </div>
                  <p className="starter-prompt-text">{item.desc}</p>
                </button>
              );
            })}
          </div>
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
            model={message.model}
            isPro={message.isPro}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
