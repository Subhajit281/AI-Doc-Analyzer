import { Upload, FileWarning } from 'lucide-react';
import './UploadState.css';

export default function UploadState({ onUploadClick, error }) {
  return (
    <div className="upload-state">
      <div className="upload-state-card" onClick={onUploadClick} role="button" tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onUploadClick(); }}
      >
        <div className="upload-state-icon">
          <Upload size={28} strokeWidth={1.5} />
        </div>
        <p className="upload-state-title">Upload a document to get started</p>
        <p className="upload-state-sub">PDF, DOCX, or TXT — you can add more later</p>
      </div>

      {error && (
        <div className="upload-state-error">
          <FileWarning size={14} strokeWidth={2} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}