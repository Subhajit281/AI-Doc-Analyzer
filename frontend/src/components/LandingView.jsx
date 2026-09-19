import { useState } from 'react';
import {
  Upload,
  ShieldCheck,
  Search,
  Zap,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import './LandingView.css';

const SUPPORTED_FORMATS = [
  { label: 'PDF', ext: '.pdf' },
  { label: 'Word', ext: '.docx' },
  { label: 'Excel', ext: '.xlsx' },
  { label: 'PowerPoint', ext: '.pptx' },
  { label: 'HTML', ext: '.html' },
  { label: 'Markdown', ext: '.md' },
  { label: 'Text', ext: '.txt' },
];

export default function LandingView({ onUploadClick, onFilesSelected, uploadError }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelected(e.dataTransfer.files);
    }
  };

  return (
    <div className="landing-view">
      <div className="landing-content">
        {/* Hero Section */}
        <div className="landing-hero">
          <div className="landing-pill">
            <Sparkles size={13} strokeWidth={2} />
            <span>Intelligent Document Assistant</span>
          </div>

          <h1 className="landing-title">
            Intelligent Document Analysis & Chat
          </h1>

          <p className="landing-subtitle">
            Upload PDFs, Word documents, spreadsheets, or presentations to extract
            insights, analyze complex tables, and ask questions with precise citations.
          </p>
        </div>

        {/* Big Drag & Drop Zone */}
        <div
          className={`landing-dropzone ${isDragOver ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={onUploadClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onUploadClick();
          }}
        >
          <div className="landing-dropzone-icon">
            <Upload size={26} strokeWidth={1.75} />
          </div>

          <div className="landing-dropzone-text">
            <p className="dropzone-primary">
              Drop documents here, or <span className="dropzone-browse">browse files</span>
            </p>
            <p className="dropzone-secondary">
              Supports files up to 10 MB each (.pdf, .docx, .xlsx, .pptx, .txt, .md)
            </p>
          </div>

          <div className="landing-formats">
            {SUPPORTED_FORMATS.map((fmt) => (
              <span key={fmt.label} className="landing-format-badge">
                {fmt.label}
              </span>
            ))}
          </div>
        </div>

        {/* Error Notification */}
        {uploadError && (
          <div className="landing-error">
            <AlertCircle size={16} strokeWidth={2} />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Feature Cards Grid */}
        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-icon">
              <Search size={18} strokeWidth={2} />
            </div>
            <h3 className="feature-title">Structure-Aware Analysis</h3>
            <p className="feature-desc">
              Accurately extracts document hierarchies, section flows, and complex tables
              for deep contextual answers.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <ShieldCheck size={18} strokeWidth={2} />
            </div>
            <h3 className="feature-title">Verified Evidence Citations</h3>
            <p className="feature-desc">
              Cross-examines information across sections with verified references
              and explicit citations for trustworthy results.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Zap size={18} strokeWidth={2} />
            </div>
            <h3 className="feature-title">High-Speed Processing</h3>
            <p className="feature-desc">
              Optimized for fast responses, private document handling, and seamless
              multi-turn inquiries.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
