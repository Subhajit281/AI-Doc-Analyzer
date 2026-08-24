import { Upload } from 'lucide-react';
import { Spinner } from './LoadingIndicator';
import './UploadButton.css';

export default function UploadButton({
  onFileSelect,
  isUploading,
  fileInputRef,
  compact = false,
}) {
  const handleClick = () => {
    if (isUploading) return;
    fileInputRef.current?.click();
  };

  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
    // allow re-selecting the same file later
    e.target.value = '';
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
      <button
        type="button"
        className="upload-button"
        onClick={handleClick}
        disabled={isUploading}
        aria-label="Upload document"
      >
        {isUploading ? <Spinner size={15} /> : <Upload size={15} strokeWidth={2} />}
        <span>{compact ? 'New document' : 'Upload document'}</span>
      </button>
    </>
  );
}
