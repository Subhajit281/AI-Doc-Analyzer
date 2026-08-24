import { useRef } from 'react';
import { Upload } from 'lucide-react';
import './UploadEmptyState.css';

export default function UploadEmptyState({ onFilesSelected }) {
  const inputRef = useRef(null);

  const handleChange = (e) => {
    if (e.target.files?.length) {
      onFilesSelected(e.target.files);
      e.target.value = '';
    }
  };

  return (
    <div className="upload-empty-state">
      <div className="upload-empty-card" onClick={() => inputRef.current?.click()}>
        <Upload size={28} strokeWidth={1.5} />
        <p className="upload-empty-title">Upload a document to get started</p>
        <p className="upload-empty-sub">PDF, DOCX, or TXT — you can add more later</p>
      </div>
      <input ref={inputRef} type="file" accept=".pdf,.doc,.docx,.txt" multiple hidden onChange={handleChange} />
    </div>
  );
}