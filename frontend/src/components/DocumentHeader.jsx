import {
  FileText,
  FileSpreadsheet,
  Presentation,
  RotateCcw,
  Trash2,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import './DocumentHeader.css';

function getFileIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (ext === 'pdf') {
    return <FileText size={16} strokeWidth={2} className="doc-header-icon pdf" />;
  }
  if (['xlsx', 'xls', 'csv'].includes(ext)) {
    return <FileSpreadsheet size={16} strokeWidth={2} className="doc-header-icon sheet" />;
  }
  if (['pptx', 'ppt'].includes(ext)) {
    return <Presentation size={16} strokeWidth={2} className="doc-header-icon ppt" />;
  }
  return <FileText size={16} strokeWidth={2} className="doc-header-icon" />;
}

export default function DocumentHeader({
  document,
  onClearChat,
  onDeleteDocument,
  hasMessages,
}) {
  if (!document) return null;

  return (
    <div className="document-header">
      <div className="document-header-left">
        <div className="document-header-icon-box">
          {getFileIcon(document.filename)}
        </div>

        <div className="document-header-title-group">
          <div className="document-header-title-row">
            <span className="document-header-name" title={document.filename}>
              {document.filename}
            </span>
            {document.status === 'ready' ? (
              <span className="doc-status-badge ready">
                <span className="status-indicator-dot" /> Ready
              </span>
            ) : document.status === 'uploading' ? (
              <span className="doc-status-badge uploading">
                <Loader2 size={11} className="doc-chip-spin" /> Processing…
              </span>
            ) : (
              <span className="doc-status-badge error">
                <AlertCircle size={11} /> Error
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="document-header-actions">
        {hasMessages && (
          <button
            type="button"
            className="doc-header-action-btn"
            onClick={onClearChat}
            title="Reset conversation for this document"
          >
            <RotateCcw size={14} strokeWidth={2} />
            <span>Clear Chat</span>
          </button>
        )}

        <button
          type="button"
          className="doc-header-action-btn delete-btn"
          onClick={() => onDeleteDocument(document.key)}
          title="Delete document"
        >
          <Trash2 size={14} strokeWidth={2} />
          <span>Remove</span>
        </button>
      </div>
    </div>
  );
}
