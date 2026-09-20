import { useEffect, useState } from 'react';
import { X, History, CheckCircle2, AlertCircle, Loader2, Receipt, Crown } from 'lucide-react';
import { getPurchaseHistory, getCurrentUser } from '../services/api';
import './PurchaseHistoryModal.css';

export default function PurchaseHistoryModal({ isOpen, onClose, user, onUserRefresh }) {
  const [payments, setPayments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!isOpen || !user) return;

    let isMounted = true;
    setIsLoading(true);
    setErrorMsg('');

    // Synchronize latest user quota metrics
    getCurrentUser()
      .then((refreshed) => {
        if (refreshed && isMounted && onUserRefresh) {
          onUserRefresh(refreshed);
        }
      })
      .catch((err) => console.warn('Could not sync user profile:', err));

    getPurchaseHistory()
      .then((data) => {
        if (isMounted) {
          setPayments(data.payments || []);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setErrorMsg(err.message || 'Failed to load purchase history.');
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, user?.id]);

  if (!isOpen) return null;

  return (
    <div className="history-modal-overlay" onClick={onClose}>
      <div className="history-modal-container" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="history-modal-close"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={18} strokeWidth={2} />
        </button>

        <div className="history-header">
          <div className="history-icon-box">
            <History size={20} strokeWidth={2} />
          </div>
          <div>
            <h2 className="history-title">Account & Purchase History</h2>
            <p className="history-subtitle">
              Logged in as <strong>{user?.email}</strong>
            </p>
          </div>
        </div>

        {/* Account Plan Summary Card */}
        <div className="account-plan-summary">
          <div className="plan-summary-left">
            <div className="plan-summary-icon">
              <Crown size={18} className={user?.is_pro ? 'active' : ''} />
            </div>
            <div>
              <p className="plan-summary-label">Current Status</p>
              <p className="plan-summary-name">
                {user?.is_pro ? `${user.plan.toUpperCase()} Plan (Active)` : 'Free Tier'}
              </p>
            </div>
          </div>
          <div className="plan-summary-right">
            {user?.is_pro ? (
              <div className="plan-quota-col">
                <span className="plan-active-tag">Active Subscription</span>
                <span className="plan-sub-quota">
                  {user?.query_count_today ?? 0} / {user?.daily_limit || 100} Queries Today
                </span>
                <span className="plan-lifetime-quota">
                  {user?.query_count ?? 0} total lifetime
                </span>
              </div>
            ) : (
              <div className="plan-quota-col">
                <span className="plan-quota-tag">
                  {user?.query_count_today ?? 0} / {user?.daily_limit || 10} Queries Used Today
                </span>
                <span className="plan-lifetime-quota">
                  {user?.query_count ?? 0} total lifetime
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="history-content">
          <h3 className="history-section-title">Transactions & Receipts</h3>

          {isLoading ? (
            <div className="history-loading">
              <Loader2 size={24} className="doc-chip-spin" />
              <p>Loading transactions…</p>
            </div>
          ) : errorMsg ? (
            <div className="history-error">
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          ) : payments.length === 0 ? (
            <div className="history-empty">
              <Receipt size={28} strokeWidth={1.5} className="history-empty-icon" />
              <p className="history-empty-title">No transactions yet</p>
              <p className="history-empty-desc">Your subscription orders and receipts will appear here.</p>
            </div>
          ) : (
            <div className="history-timeline">
              {payments.map((p, idx) => (
                <div key={p.id || idx} className="timeline-item">
                  <div className="timeline-status-icon" title={p.status || 'created'}>
                    {p.status === 'paid' ? <CheckCircle2 size={16} className="timeline-check" /> : <AlertCircle size={16} />}
                  </div>
                  <div className="timeline-details">
                    <div className="timeline-row-top">
                      <span className="timeline-plan-title">
                        {p.plan ? `${p.plan.toUpperCase()} Pass` : 'Pro Subscription'}
                      </span>
                      <span className="timeline-amount">
                        {p.currency === 'USD'
                          ? `$${Number(p.amount_display ?? p.amount / 100).toFixed(2)}`
                          : `₹${Number(p.amount_display ?? p.amount_inr ?? p.amount / 100).toFixed(2)}`}
                      </span>
                    </div>
                    <div className="timeline-row-bottom">
                      <span className="timeline-order-id">{p.status === 'paid' ? 'Paid' : 'Pending'} · Order: {p.order_id}</span>
                      <span className="timeline-date">
                        {p.created_at ? new Date(p.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
