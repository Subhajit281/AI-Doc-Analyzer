import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MarkdownRenderer.css';

export default function MarkdownRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ node, ...props }) => (
            <div className="table-fragment-container">
              <table className="fragment-table" {...props} />
            </div>
          ),
          pre: ({ node, ...props }) => (
            <div className="code-fragment-container">
              <pre className="fragment-pre" {...props} />
            </div>
          ),
          blockquote: ({ node, ...props }) => (
            <div className="quote-fragment-container">
              <blockquote {...props} />
            </div>
          ),
          h1: ({ node, ...props }) => <h1 className="fragment-h1" {...props} />,
          h2: ({ node, ...props }) => <h2 className="fragment-h2" {...props} />,
          h3: ({ node, ...props }) => <h3 className="fragment-h3" {...props} />,
          h4: ({ node, ...props }) => <h4 className="fragment-h4" {...props} />,
          ul: ({ node, ...props }) => <ul className="fragment-list fragment-ul" {...props} />,
          ol: ({ node, ...props }) => <ol className="fragment-list fragment-ol" {...props} />,
          li: ({ node, ...props }) => <li className="fragment-li" {...props} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
