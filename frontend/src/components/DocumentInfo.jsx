import { FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import './DocumentInfo.css';

const STATUS_ICON = {
  uploading: <Loader2 size={12} strokeWidth={2.5} className="doc-chip-spin" />,
  ready: <CheckCircle2 size={12} strokeWidth={2.5} />,
  error: <AlertCircle size={12} strokeWidth={2.5} />,
};

export default function DocumentInfo({ documents, activeDocKey, onSelectDocument }) {
  if (!documents || documents.length === 0) return null;

  return (
    <div className="document-info-bar">
      <div className="document-info-scroll">
        {documents.map((doc) => {
          const isActive = doc.key === activeDocKey;
          return (
            <button
              key={doc.key}
              type="button"
              className={`doc-chip doc-chip-${doc.status}${isActive ? ' doc-chip-active' : ''}`}
              onClick={() => onSelectDocument(doc.key)}
              title={doc.status === 'error' ? doc.error : doc.filename}
            >
              <FileText size={12} strokeWidth={2} className="doc-chip-file-icon" />
              <span className="doc-chip-name">{doc.filename}</span>
              <span className="doc-chip-status">{STATUS_ICON[doc.status]}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}