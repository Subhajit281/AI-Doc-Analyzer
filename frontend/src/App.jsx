import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import LandingView from './components/LandingView';
import DocumentHeader from './components/DocumentHeader';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import PricingModal from './components/PricingModal';
import AuthModal from './components/AuthModal';
import PurchaseHistoryModal from './components/PurchaseHistoryModal';
import {
  uploadDocument,
  askQuestion,
  deleteDocument,
  getCurrentUser,
  getUserDocuments,
} from './services/api';
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

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export default function App() {
  // Document state
  const [documents, setDocuments] = useState([]);
  const [activeDocKey, setActiveDocKey] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // User & Quota state (Strict Authentication: No Guest Mode)
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Modals state
  const [isPricingModalOpen, setIsPricingModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(true);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // Messages scoped per document
  const [messagesByDoc, setMessagesByDoc] = useState({});
  const [conversationIdsByDoc, setConversationIdsByDoc] = useState({});
  const [queryingDocKey, setQueryingDocKey] = useState(null);

  const fileInputRef = useRef(null);

  // Load user session on mount: Strictly pop up login/signup if no session
  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        if (u) {
          setUser(u);
          setIsAuthModalOpen(false);
        } else {
          setUser(null);
          setIsAuthModalOpen(true);
        }
      })
      .catch(() => {
        setUser(null);
        setIsAuthModalOpen(true);
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, []);

  // Fetch active documents stored in user's DB account
  useEffect(() => {
    if (!user) {
      setDocuments([]);
      setActiveDocKey(null);
      return;
    }

    getUserDocuments()
      .then((dbDocs) => {
        if (Array.isArray(dbDocs) && dbDocs.length > 0) {
          const mapped = dbDocs.map((d) => ({
            key: d.document_id,
            document_id: d.document_id,
            filename: d.filename,
            status: 'ready',
            page_count: d.page_count,
            section_count: d.section_count,
            chunk_count: d.chunk_count,
            created_at: d.created_at,
            expires_at: d.expires_at,
            days_remaining: d.days_remaining,
            expiry_label: d.expiry_label || 'Expires in 7d',
            error: null,
          }));
          setDocuments(mapped);
          setActiveDocKey((prev) => (prev ? prev : mapped[0]?.key));
        }
      })
      .catch((err) => console.warn('Could not load user documents from DB:', err));
  }, [user?.id]);

  const activeDocument = useMemo(
    () => documents.find((d) => d.key === activeDocKey) || null,
    [documents, activeDocKey]
  );

  const messages = activeDocKey ? messagesByDoc[activeDocKey] || [] : [];
  const isReady = activeDocument?.status === 'ready';

  // ----------------------------------------------------------
  // Document Upload with 10 MB Limit Check
  // ----------------------------------------------------------
  const handleFilesSelected = useCallback(
    async (fileList) => {
      if (!user) {
        setIsAuthModalOpen(true);
        return;
      }

      const rawFiles = Array.from(fileList || []);
      if (rawFiles.length === 0) return;
      setUploadError('');

      // Enforce 10 MB limit
      const oversized = rawFiles.filter((f) => f.size > MAX_FILE_SIZE_BYTES);
      if (oversized.length > 0) {
        setUploadError(
          `"${oversized[0].name}" exceeds the 10 MB limit. Please select files under 10 MB.`
        );
        return;
      }

      const files = rawFiles;
      const newDocs = files.map((file) => ({
        key: nextDocKey(),
        filename: file.name,
        status: 'uploading',
        document_id: null,
        error: null,
      }));

      setDocuments((prev) => [...prev, ...newDocs]);
      setActiveDocKey(newDocs[0].key);

      await Promise.all(
        newDocs.map(async (doc, i) => {
          try {
            const result = await uploadDocument(files[i]);
            setDocuments((prev) =>
              prev.map((d) =>
                d.key === doc.key
                  ? {
                      ...d,
                      ...result,
                      document_id: result.document_id,
                      status: result.status || 'ready',
                      days_remaining: result.days_remaining ?? 7,
                      expiry_label: result.expiry_label || 'Expires in 7d',
                    }
                  : d
              )
            );
          } catch (err) {
            setDocuments((prev) =>
              prev.map((d) =>
                d.key === doc.key
                  ? { ...d, status: 'error', error: err.message || 'Upload failed.' }
                  : d
              )
            );
            setUploadError(err.message || 'Unable to upload document.');
          }
        })
      );
    },
    [user]
  );

  const handleUploadClick = useCallback(() => {
    if (!user) {
      setIsAuthModalOpen(true);
      return;
    }
    fileInputRef.current?.click();
  }, [user]);

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

  const handleDeleteDocument = useCallback(
    async (docKey) => {
      const docToDelete = documents.find((d) => d.key === docKey);
      try {
        if (docToDelete?.document_id) {
          await deleteDocument(docToDelete.document_id);
        }
      } catch (err) {
        setUploadError(err.message || 'Unable to delete the document.');
        return;
      }

      setDocuments((prev) => prev.filter((d) => d.key !== docKey));
      setMessagesByDoc((prev) => {
        const next = { ...prev };
        delete next[docKey];
        return next;
      });
      setConversationIdsByDoc((prev) => {
        const next = { ...prev };
        delete next[docKey];
        return next;
      });

      if (activeDocKey === docKey) {
        const remaining = documents.filter((d) => d.key !== docKey);
        if (remaining.length > 0) {
          setActiveDocKey(remaining[0].key);
        } else {
          setActiveDocKey(null);
        }
      }
    },
    [documents, activeDocKey]
  );

  const handleClearChat = useCallback(() => {
    if (!activeDocKey) return;
    setMessagesByDoc((prev) => ({
      ...prev,
      [activeDocKey]: [],
    }));
    setConversationIdsByDoc((prev) => ({
      ...prev,
      [activeDocKey]: crypto.randomUUID(),
    }));
  }, [activeDocKey]);

  // ----------------------------------------------------------
  // Send Query with 10-Free-Queries Daily Limit & Paywall Trigger
  // ----------------------------------------------------------
  const handleSend = useCallback(
    async (text) => {
      if (!activeDocument || activeDocument.status !== 'ready' || queryingDocKey) {
        return;
      }

      // Strict Wall: Cannot query without authenticated account
      if (!user) {
        setIsAuthModalOpen(true);
        return;
      }

      // Check daily quota before querying
      const isPro = Boolean(user?.is_pro);
      const usedToday = Number(user?.query_count_today ?? (user?.query_count ?? 0));
      const dailyLimit = Number(user?.daily_limit || 10);

      if (usedToday >= dailyLimit) {
        // Trigger Pricing Modal when reaching or exceeding quota limit
        setIsPricingModalOpen(true);
        return;
      }

      const docKey = activeDocument.key;
      const conversationId = conversationIdsByDoc[docKey] || crypto.randomUUID();
      if (!conversationIdsByDoc[docKey]) {
        setConversationIdsByDoc((prev) => ({ ...prev, [docKey]: conversationId }));
      }

      const userMessage = {
        id: nextId(),
        role: 'user',
        content: text,
      };

      const loadingMessage = {
        id: nextId(),
        role: 'assistant',
        content: '',
        isLoading: true,
      };

      setMessagesByDoc((prev) => ({
        ...prev,
        [docKey]: [...(prev[docKey] || []), userMessage, loadingMessage],
      }));

      setQueryingDocKey(docKey);

      try {
        const result = await askQuestion(
          activeDocument.document_id,
          text,
          conversationId
        );

        // Update quota in state from backend response
        if (result?.user_quota) {
          setUser((prev) => ({
            ...prev,
            ...result.user_quota,
          }));
        } else {
          setUser((prev) =>
            prev
              ? {
                  ...prev,
                  query_count: (prev.query_count || 0) + 1,
                  query_count_today: (prev.query_count_today || 0) + 1,
                  queries_remaining: Math.max(0, (prev.daily_limit || 10) - (prev.query_count_today || 0) - 1),
                }
              : prev
          );
        }

        setMessagesByDoc((prev) => ({
          ...prev,
          [docKey]: (prev[docKey] || []).map((m) =>
            m.id === loadingMessage.id
              ? {
                  ...m,
                  content: result.answer,
                  isLoading: false,
                  model: result.model || (isPro ? 'openai/gpt-oss-120b' : 'llama-3.1-8b-instant'),
                  isPro: result.is_pro ?? isPro,
                }
              : m
          ),
        }));
      } catch (err) {
        if (err.message === 'QUOTA_EXCEEDED' || err.status === 402) {
          // Remove the loading message and open pricing modal
          setMessagesByDoc((prev) => ({
            ...prev,
            [docKey]: (prev[docKey] || []).filter((m) => m.id !== loadingMessage.id),
          }));
          setIsPricingModalOpen(true);
          getCurrentUser().then((u) => u && setUser(u));
        } else if (err.status === 401) {
          localStorage.removeItem('docai_token');
          setUser(null);
          setIsAuthModalOpen(true);
        } else {
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
        }
      } finally {
        setQueryingDocKey(null);
      }
    },
    [activeDocument, queryingDocKey, conversationIdsByDoc, user]
  );

  const handleLogout = () => {
    localStorage.removeItem('docai_token');
    setUser(null);
    setDocuments([]);
    setActiveDocKey(null);
    setMessagesByDoc({});
    setConversationIdsByDoc({});
    setIsAuthModalOpen(true);
  };

  const handlePaymentSuccess = () => {
    getCurrentUser().then((u) => {
      if (u) setUser(u);
    });
  };

  return (
    <div className="app">
      {/* Universal Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.xlsx,.csv,.pptx,.html,.txt,.md"
        multiple
        hidden
        onChange={handleFileInputChange}
      />

      {/* Left Sidebar Panel */}
      <Sidebar
        documents={documents}
        activeDocKey={activeDocKey}
        onSelectDocument={handleSelectDocument}
        onDeleteDocument={handleDeleteDocument}
        onUploadClick={handleUploadClick}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenPricing={() => setIsPricingModalOpen(true)}
        onOpenHistory={() => setIsHistoryModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Workspace Area */}
      <main className="main-content">
        {!activeDocument ? (
          <LandingView
            onUploadClick={handleUploadClick}
            onFilesSelected={handleFilesSelected}
            uploadError={uploadError}
          />
        ) : (
          <div className="chat-container">
            <DocumentHeader
              document={activeDocument}
              onClearChat={handleClearChat}
              onDeleteDocument={handleDeleteDocument}
              hasMessages={messages.length > 0}
            />

            <ChatWindow
              messages={messages}
              isReady={isReady}
              onSelectPrompt={handleSend}
            />

            <ChatInput
              onSend={handleSend}
              onUploadClick={handleUploadClick}
              disabled={false}
              sendDisabled={!isReady || queryingDocKey !== null}
              placeholder={
                activeDocument?.status === 'uploading'
                  ? 'Processing document…'
                  : activeDocument?.status === 'error'
                  ? 'Document processing failed'
                  : `Ask anything about ${activeDocument.filename}...`
              }
            />
          </div>
        )}
      </main>

      {/* Auth Modal (Strict authentication wall: cannot dismiss without logging in) */}
      <AuthModal
        isOpen={authChecked && (isAuthModalOpen || !user)}
        isDismissible={!!user}
        onClose={() => {
          if (user) setIsAuthModalOpen(false);
        }}
        onSuccess={(loggedUser) => {
          setUser(loggedUser);
          setIsAuthModalOpen(false);
        }}
      />

      {/* Pricing Modal (10 Free Queries Paywall with Day, Month, Year in INR & USD + QR) */}
      <PricingModal
        isOpen={isPricingModalOpen}
        onClose={() => setIsPricingModalOpen(false)}
        user={user}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onPaymentSuccess={handlePaymentSuccess}
      />

      {/* Purchase History & Receipts Modal */}
      <PurchaseHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        user={user}
        onUserRefresh={(refreshed) => setUser(refreshed)}
      />
    </div>
  );
}
