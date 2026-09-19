import { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  X,
  Loader2,
  AlertCircle,
  Layers,
  FileSpreadsheet,
  Presentation,
  PanelLeftClose,
  PanelLeftOpen,
  Crown,
  Sparkles,
  User,
  LogOut,
  History,
  LogIn,
  Clock,
  Cpu,
} from 'lucide-react';
import './Sidebar.css';

function getFileIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (ext === 'pdf') {
    return <FileText size={16} className="sidebar-doc-type-icon pdf-icon" strokeWidth={1.75} />;
  }
  if (['xlsx', 'xls', 'csv'].includes(ext)) {
    return <FileSpreadsheet size={16} className="sidebar-doc-type-icon sheet-icon" strokeWidth={1.75} />;
  }
  if (['pptx', 'ppt'].includes(ext)) {
    return <Presentation size={16} className="sidebar-doc-type-icon ppt-icon" strokeWidth={1.75} />;
  }
  return <FileText size={16} className="sidebar-doc-type-icon" strokeWidth={1.75} />;
}

export default function Sidebar({
  documents,
  activeDocKey,
  onSelectDocument,
  onDeleteDocument,
  onUploadClick,
  isCollapsed,
  onToggleCollapse,
  user,
  onOpenAuth,
  onOpenPricing,
  onOpenHistory,
  onLogout,
}) {
  const [hoveredDocKey, setHoveredDocKey] = useState(null);
  const [resetCountdown, setResetCountdown] = useState('');

  const isPro = Boolean(user?.is_pro);
  const plan = user?.plan || 'free';
  const queryCount = user?.query_count || 0; // lifetime count
  const queryCountToday = user?.query_count_today || 0; // resets every 24h
  const dailyLimit = user?.daily_limit || (isPro ? 100 : 10);
  const progressPercent = Math.min(100, Math.round((queryCountToday / dailyLimit) * 100));
  const isDailyLimitReached = queryCountToday >= dailyLimit;

  // Plan title label
  const planLabel = {
    day: 'Day Pass (100/d)',
    month: 'Monthly Pro (100/d)',
    year: 'Annual Pro (200/d)',
    free: 'Free Tier (10/d)',
  }[plan] || 'Free Tier (10/d)';

  // 24-hour reset countdown calculation
  useEffect(() => {
    if (!user?.query_reset_at) {
      setResetCountdown('');
      return;
    }

    const updateTimer = () => {
      const target = new Date(user.query_reset_at).getTime();
      const diff = target - Date.now();
      if (diff <= 0) {
        setResetCountdown('Renewing daily quota…');
      } else {
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        setResetCountdown(hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000);
    return () => clearInterval(interval);
  }, [user?.query_reset_at]);

  return (
    <aside className={`sidebar ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      {/* Top Brand Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo-icon">
            <Layers size={18} strokeWidth={2.2} />
          </div>
          {!isCollapsed && (
            <div className="sidebar-titles">
              <span className="sidebar-brand-name">DocAI Analyzer</span>
              {/* <span className="sidebar-badge">Pro Document Intelligence</span> */}
            </div>
          )}
        </div>

        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>

      {/* Primary New Document Action */}
      <div className="sidebar-action-area">
        <button
          type="button"
          className="sidebar-upload-btn"
          onClick={onUploadClick}
          title="Upload new document (up to 10 MB)"
        >
          <Plus size={16} strokeWidth={2.2} />
          {!isCollapsed && <span>New Document</span>}
        </button>
      </div>

      {/* Documents Section Header */}
      {!isCollapsed && (
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Documents</span>
          {documents.length > 0 && (
            <span className="sidebar-count-pill">{documents.length}</span>
          )}
        </div>
      )}

      {/* Documents Vertical List */}
      <div className="sidebar-list">
        {documents.length === 0 ? (
          !isCollapsed && (
            <div className="sidebar-empty">
              <p className="sidebar-empty-title">No documents yet</p>
              <p className="sidebar-empty-hint">Uploaded files (up to 10 MB) appear here</p>
            </div>
          )
        ) : (
          documents.map((doc) => {
            const isActive = doc.key === activeDocKey;
            const isHovered = hoveredDocKey === doc.key;

            return (
              <div
                key={doc.key}
                className={`sidebar-doc-card ${isActive ? 'active' : ''} ${
                  doc.status === 'error' ? 'has-error' : ''
                }`}
                onClick={() => onSelectDocument(doc.key)}
                onMouseEnter={() => setHoveredDocKey(doc.key)}
                onMouseLeave={() => setHoveredDocKey(null)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectDocument(doc.key);
                  }
                }}
                title={doc.status === 'error' ? doc.error : doc.filename}
              >
                <div className="sidebar-doc-icon-wrapper">
                  {getFileIcon(doc.filename)}
                </div>

                {!isCollapsed && (
                  <div className="sidebar-doc-info">
                    <span className="sidebar-doc-filename">{doc.filename}</span>
                    <div className="sidebar-doc-meta">
                      {doc.status === 'uploading' ? (
                        <span className="sidebar-status-uploading">
                          <Loader2 size={11} className="doc-chip-spin" /> Processing…
                        </span>
                      ) : doc.status === 'error' ? (
                        <span className="sidebar-status-error">
                          <AlertCircle size={11} /> Failed
                        </span>
                      ) : (
                        <span className="sidebar-status-ready">
                          {doc.expiry_label || 'Expires in 7d'}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Cross / Delete Button */}
                {!isCollapsed && (
                  <button
                    type="button"
                    className={`sidebar-doc-delete-btn ${isHovered || isActive ? 'visible' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteDocument(doc.key);
                    }}
                    title="Remove document"
                    aria-label={`Remove ${doc.filename}`}
                  >
                    <X size={14} strokeWidth={2} />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer: User Account, Query Quota & Upgrade Section */}
      {!isCollapsed ? (
        <div className="sidebar-footer">
          {/* Active Model Indicator */}
          <div className="sidebar-model-chip">
            <Cpu size={12} strokeWidth={2} className="model-chip-icon" />
            <span className="sidebar-model-name">
              {isPro ? 'Better Model Analyzer' : 'Standard Analyzer'}
            </span>
            <span className={`sidebar-model-badge ${isPro ? 'pro' : 'free'}`}>
              {isPro ? 'PRO' : 'FREE'}
            </span>
          </div>

          {/* Quota or Pro Status Box */}
          <div className="sidebar-quota-box">
            {isPro ? (
              <div className="sidebar-pro-status">
                <div className="pro-badge-header">
                  <div className="pro-crown-box">
                    <Crown size={14} className="pro-crown-icon" />
                  </div>
                  <div className="pro-titles-col">
                    <p className="pro-title">{planLabel}</p>
                    <p className="pro-subtitle">
                      {queryCountToday} / {dailyLimit} today • {queryCount} total
                    </p>
                  </div>
                </div>
                <div className="quota-progress-bar">
                  <div
                    className="quota-progress-fill pro-fill"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                {resetCountdown && (
                  <div className="sidebar-reset-timer">
                    <Clock size={11} />
                    <span>Daily quota resets in {resetCountdown}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="sidebar-free-quota">
                <div className="quota-text-row">
                  <span className="quota-label">Daily Queries</span>
                  <span className="quota-count">{queryCountToday} / {dailyLimit}</span>
                </div>
                <div className="quota-progress-bar">
                  <div
                    className={`quota-progress-fill ${isDailyLimitReached ? 'limit-reached' : ''}`}
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="quota-subtext-row">
                  <span className="quota-lifetime-count">{queryCount} total lifetime</span>
                  {resetCountdown && (
                    <span className="quota-reset-text" title={user?.query_reset_at}>
                      <Clock size={10} /> {resetCountdown}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  className={`sidebar-upgrade-btn ${isDailyLimitReached ? 'pulse-cta' : ''}`}
                  onClick={onOpenPricing}
                >
                  <Sparkles size={13} strokeWidth={2} />
                  <span>{isDailyLimitReached ? 'Daily Limit Reached • Upgrade' : 'Upgrade to Pro'}</span>
                </button>
              </div>
            )}
          </div>

          {/* User Account Bar */}
          <div className="sidebar-user-row">
            {user ? (
              <>
                <div className="sidebar-user-info" title={user.email}>
                  <div className="user-avatar-circle">
                    {(user.full_name || user.email)[0].toUpperCase()}
                  </div>
                  <span className="sidebar-user-email">{user.email}</span>
                </div>
                <div className="sidebar-user-actions">
                  <button
                    type="button"
                    className="sidebar-icon-action-btn"
                    onClick={onOpenHistory}
                    title="Purchase History & Receipts"
                  >
                    <History size={14} />
                  </button>
                  <button
                    type="button"
                    className="sidebar-icon-action-btn"
                    onClick={onLogout}
                    title="Log Out"
                  >
                    <LogOut size={14} />
                  </button>
                </div>
              </>
            ) : (
              <button
                type="button"
                className="sidebar-login-btn"
                onClick={onOpenAuth}
              >
                <LogIn size={14} strokeWidth={2} />
                <span>Log In or Sign Up</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="sidebar-footer-collapsed">
          <button
            type="button"
            className="sidebar-collapsed-btn"
            onClick={user ? onOpenHistory : onOpenAuth}
            title={user ? user.email : 'Log in / Sign up'}
          >
            <User size={16} />
          </button>
          {!isPro && (
            <button
              type="button"
              className="sidebar-collapsed-btn pro"
              onClick={onOpenPricing}
              title="Upgrade to Pro"
            >
              <Sparkles size={16} />
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
