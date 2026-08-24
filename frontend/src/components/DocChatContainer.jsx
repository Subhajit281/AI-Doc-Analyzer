import { useState } from 'react';
import ChatWindow from './ChatWindow';
import ChatInput from './ChatInput';
import UploadEmptyState from './UploadEmptyState';
import './DocChatContainer.css';

export default function DocChatContainer() {
  const [docs, setDocs] = useState([]); // { id, name, status }
  const [messages, setMessages] = useState([]);

  const hasDocs = docs.length > 0;
  const hasReadyDoc = docs.some((d) => d.status === 'ready');
  const isProcessing = docs.some((d) => d.status === 'uploading' || d.status === 'processing');

  const handleFilesSelected = (fileList) => {
    const files = Array.from(fileList);
    const newDocs = files.map((f) => ({
      id: crypto.randomUUID(),
      name: f.name,
      status: 'uploading',
    }));
    setDocs((prev) => [...prev, ...newDocs]);
    newDocs.forEach((doc, i) => processDoc(doc, files[i]));
  };

  const updateDocStatus = (id, status) =>
    setDocs((prev) => prev.map((d) => (d.id === id ? { ...d, status } : d)));

  const processDoc = async (doc, file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const uploadRes = await fetch('/api/documents/upload', { method: 'POST', body: formData });
      if (!uploadRes.ok) throw new Error('upload failed');

      updateDocStatus(doc.id, 'processing');
      const { documentId } = await uploadRes.json();
      await waitForProcessing(documentId);
      updateDocStatus(doc.id, 'ready');
    } catch {
      updateDocStatus(doc.id, 'error');
    }
  };

  const waitForProcessing = async (documentId) => {
    for (let i = 0; i < 30; i++) {
      const res = await fetch(`/api/documents/${documentId}/status`);
      const { status } = await res.json();
      if (status === 'ready') return;
      if (status === 'error') throw new Error('processing failed');
      await new Promise((r) => setTimeout(r, 1500));
    }
    throw new Error('processing timeout');
  };

  const handleSend = (text) => {
    if (!hasReadyDoc) return;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }]);
    // TODO: call your chat API, then append the assistant reply
  };

  return (
    <div className="doc-chat-container">
      {!hasDocs ? (
        <UploadEmptyState onFilesSelected={handleFilesSelected} />
      ) : (
        <>
          <ChatWindow messages={messages} />
          <ChatInput
            onSend={handleSend}
            onUpload={handleFilesSelected}
            sendDisabled={!hasReadyDoc}
            placeholder={isProcessing && !hasReadyDoc ? 'Processing document(s)…' : undefined}
          />
        </>
      )}
    </div>
  );
}