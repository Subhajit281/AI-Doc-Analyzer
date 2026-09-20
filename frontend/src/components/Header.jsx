import './Header.css';

export default function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-titles">
          <h1 className="header-title">DocAI Analyzer</h1>
          <p className="header-subtitle">Analyze and chat with your documents</p>
        </div>
        {/* <UploadButton
          onFileSelect={onFileSelect}
          isUploading={isUploading}
          fileInputRef={fileInputRef}
          compact={hasDocument}
        /> */}
      </div>
    </header>
  );
}
