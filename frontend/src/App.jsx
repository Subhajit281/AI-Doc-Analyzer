import { useState, useRef, useCallback, useMemo } from 'react';
import Header from './components/Header';
import UploadState from './components/UploadState';
import DocumentInfo from './components/DocumentInfo';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import { uploadDocument, askQuestion } from './services/api';
import './App.css';

let messageIdCounter = 0;
const nextId = () => {
  messageIdCounter += 1;
  return messageIdCounter;
};

let docKeyCounter = 0;
const nextDocKey = () => {
  docKeyCounter += 1;
  return `doc-${docKeyCounter}`;
};

export default function App() {
  // documents: [{ key, filename, status: 'uploading' | 'ready' | 'error', document_id, error }]
  const [documents, setDocuments] = useState([]);
  const [activeDocKey, setActiveDocKey] = useState(null);
  const [uploadError, setUploadError] = useState('');

  // messages scoped per document, keyed by document key
  const [messagesByDoc, setMessagesByDoc] = useState({});
  const [queryingDocKey, setQueryingDocKey] = useState(null);

  const fileInputRef = useRef(null);

  const activeDocument = useMemo(
    () => documents.find((d) => d.key === activeDocKey) || null,
    [documents, activeDocKey]
  );

  const messages = activeDocKey ? messagesByDoc[activeDocKey] || [] : [];
  const isReady = activeDocument?.status === 'ready';
  const isQuerying = queryingDocKey !== null && queryingDocKey === activeDocKey;

  const handleFilesSelected = useCallback(async (fileList) => {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;
    setUploadError('');

    const newDocs = files.map((file) => ({
      key: nextDocKey(),
      filename: file.name,
      status: 'uploading',
      document_id: null,
      error: null,
    }));

    setDocuments((prev) => [...prev, ...newDocs]);

    // If nothing is active yet, switch to the first newly-added doc right away.
    setActiveDocKey((prev) => prev ?? newDocs[0].key);

    await Promise.all(
      newDocs.map(async (doc, i) => {
        try {
          const result = await uploadDocument(files[i]);
          setDocuments((prev) =>
            prev.map((d) =>
              d.key === doc.key
                ? { ...d, ...result, status: result.status || 'ready' }
                : d
            )
          );
        } catch (err) {
          setDocuments((prev) =>
            prev.map((d) =>
              d.key === doc.key
                ? { ...d, status: 'error', error: err.message || 'Upload failed. Please try again.' }
                : d
            )
          );
          setUploadError(err.message || 'Unable to upload one or more documents.');
        }
      })
    );
  }, []);

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback(
    (e) => {
      if (e.target.files?.length) {
        handleFilesSelected(e.target.files);
        e.target.value = '';
      }
    },
    [handleFilesSelected]
  );

  const handleSelectDocument = useCallback((key) => {
    setActiveDocKey(key);
  }, []);

  const handleSend = useCallback(
    async (text) => {
      if (!activeDocument || activeDocument.status !== 'ready' || isQuerying) return;

      const docKey = activeDocument.key;
      const userMessage = { id: nextId(), role: 'user', content: text };
      const loadingMessage = { id: nextId(), role: 'assistant', content: '', isLoading: true };

      setMessagesByDoc((prev) => ({
        ...prev,
        [docKey]: [...(prev[docKey] || []), userMessage, loadingMessage],
      }));
      setQueryingDocKey(docKey);

      try {
        const result = await askQuestion(activeDocument.document_id, text);
        setMessagesByDoc((prev) => ({
          ...prev,
          [docKey]: (prev[docKey] || []).map((m) =>
            m.id === loadingMessage.id
              ? { ...m, content: result.answer, isLoading: false }
              : m
          ),
        }));
      } catch (err) {
        setMessagesByDoc((prev) => ({
          ...prev,
          [docKey]: (prev[docKey] || []).map((m) =>
            m.id === loadingMessage.id
              ? {
                  ...m,
                  content: err.message || 'Unable to get a response. Please try again.',
                  isLoading: false,
                  isError: true,
                }
              : m
          ),
        }));
      } finally {
        setQueryingDocKey(null);
      }
    },
    [activeDocument, isQuerying]
  );

  const hasDocs = documents.length > 0;

  return (
    <div className="app">
      <Header hasDocument={hasDocs} />

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt"
        multiple
        hidden
        onChange={handleFileInputChange}
      />

      {!hasDocs ? (
        <UploadState onUploadClick={handleUploadClick} error={uploadError} />
      ) : (
        <>
          <DocumentInfo
            documents={documents}
            activeDocKey={activeDocKey}
            onSelectDocument={handleSelectDocument}
          />
          <ChatWindow messages={messages} />
          <ChatInput
            onSend={handleSend}
            onUploadClick={handleUploadClick}
            disabled={false}
            sendDisabled={!isReady || isQuerying}
            placeholder={
              activeDocument?.status === 'uploading'
                ? 'Processing document…'
                : 'Ask anything about your document...'
            }
          />
        </>
      )}
    </div>
  );
}