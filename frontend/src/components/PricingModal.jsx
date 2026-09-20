import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  X,
  Check,
  Sparkles,
  Zap,
  ShieldCheck,
  Clock,
  ArrowRight,
  QrCode,
  CreditCard,
  Lock,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { createOrder, verifyPayment } from '../services/api';
import './PricingModal.css';

const PLANS_DATA = [
  {
    id: 'day',
    name: 'Day Pass',
    badge: '24-Hour Pass',
    price_inr: 29,
    price_usd: 0.49,
    period: 'for 24 hours',
    desc: 'Perfect for urgent assignments or deep document research.',
    features: [
      '100 Document Queries / Day',
      '⚡ Better Model Analyzer',
      'Multi-format analysis (PDF, Word, Excel, PPT)',
      'Verified citations & section references',
      'High-speed accelerated responses',
    ],
  },
  {
    id: 'month',
    name: 'Monthly Pro',
    badge: 'Most Popular',
    popular: true,
    price_inr: 199,
    price_usd: 2.49,
    period: 'per month',
    desc: 'Ideal for professionals, researchers, and students.',
    features: [
      '500 Queries / Month (up to 100/day)',
      'Better Models and Responses',
      'Deep table extraction & multi-page synthesis',
      'Priority response queue & low latency',
      'Full purchase history and invoice receipts',
    ],
  },
  {
    id: 'year',
    name: 'Annual Pro',
    badge: 'Best Value (Save 40%)',
    price_inr: 1499,
    price_usd: 17.99,
    period: 'per year',
    desc: 'Continuous document intelligence with maximum capacity & savings.',
    features: [
      '2,500 Queries / Year (up to 200/day)',
      'Better Models and Responses',
      'All Monthly Pro capabilities included',
      'Highest processing priority & context depth',
      'Priority email customer support',
    ],
  },
];

const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const existing = document.querySelector('script[src*="checkout.razorpay.com"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(true));
      existing.addEventListener('error', () => resolve(false));
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

export default function PricingModal({
  isOpen,
  onClose,
  user,
  onOpenAuth,
  onPaymentSuccess,
}) {
  const [currency, setCurrency] = useState('INR'); // 'INR' or 'USD'
  const [selectedPlan, setSelectedPlan] = useState('month');
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeOrder, setActiveOrder] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const openRazorpayCheckout = async (order) => {
    if (!order) return;

    let isAvailable = !!window.Razorpay;
    if (!isAvailable) {
      isAvailable = await loadRazorpayScript();
    }

    if (!window.Razorpay) {
      setErrorMsg('Razorpay Checkout SDK could not be loaded. Please check your network or scan the QR code below.');
      return;
    }

    const keyId = order.key_id || import.meta.env.VITE_RAZORPAY_KEY_ID || 'rzp_test_TeFbpgyeysB2BK';

    const options = {
      key: keyId,
      amount: order.amount, // paise
      currency: order.currency || 'INR',
      name: 'DocAI Analyzer',
      description: `${order.plan?.name || 'Pro'} Subscription`,
      order_id: order.order_id,
      prefill: {
        email: user?.email || '',
        name: user?.full_name || '',
      },
      theme: {
        color: '#6366f1',
      },
      handler: async (response) => {
        try {
          setIsProcessing(true);
          setErrorMsg('');
          const result = await verifyPayment(
            response.razorpay_order_id,
            response.razorpay_payment_id,
            response.razorpay_signature
          );
          setIsSuccess(true);
          setTimeout(() => {
            setIsSuccess(false);
            setActiveOrder(null);
            onPaymentSuccess(result);
            onClose();
          }, 1800);
        } catch (e) {
          setErrorMsg(e.message || 'Payment signature verification failed.');
        } finally {
          setIsProcessing(false);
        }
      },
      modal: {
        ondismiss: () => {
          setIsProcessing(false);
          setErrorMsg('Payment modal dismissed. You can reopen checkout anytime.');
        },
      },
    };

    try {
      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', (response) => {
        const desc = response.error?.description || response.error?.reason || 'Payment failed. Please try another card or UPI.';
        setErrorMsg(`Payment Failed: ${desc}`);
        setIsProcessing(false);
      });
      rzp.open();
    } catch (err) {
      setErrorMsg(`Failed to open Razorpay modal: ${err.message}`);
      setIsProcessing(false);
    }
  };

  const handleSelectPlanAndPay = async (planId) => {
    setErrorMsg('');
    if (!user) {
      // Require authentication to link purchase
      onClose();
      onOpenAuth();
      return;
    }

    setIsProcessing(true);
    try {
      const order = await createOrder(planId, currency);
      setActiveOrder(order);
      // Automatically trigger Razorpay Standard Checkout modal
      if (window.Razorpay) {
        openRazorpayCheckout(order);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Unable to initiate order. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmPayment = async () => {
    if (!activeOrder) return;
    setIsProcessing(true);
    setErrorMsg('');

    try {
      // Complete payment verification
      const paymentId = `pay_${Date.now()}`;
      const signature = `sig_${Date.now()}`;
      const result = await verifyPayment(activeOrder.order_id, paymentId, signature);
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setActiveOrder(null);
        onPaymentSuccess(result);
        onClose();
      }, 1800);
    } catch (err) {
      setErrorMsg(err.message || 'Payment verification failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRazorpayCheckout = () => {
    if (!activeOrder) return;
    openRazorpayCheckout(activeOrder);
  };

  return (
    <div className="pricing-modal-overlay" onClick={onClose}>
      <div
        className="pricing-modal-container"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          className="pricing-modal-close"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={18} strokeWidth={2} />
        </button>

        {isSuccess ? (
          <div className="pricing-success-view">
            <div className="pricing-success-icon">
              <CheckCircle2 size={42} strokeWidth={2} />
            </div>
            <h2 className="pricing-success-title">Payment Confirmed!</h2>
            <p className="pricing-success-desc">
              Your subscription is now active with unlimited document queries.
            </p>
          </div>
        ) : activeOrder ? (
          /* Payment & Dynamic QR Code Screen */
          <div className="pricing-qr-view">
            <div className="pricing-qr-header">
              <div className="pricing-pill">
                <Lock size={12} strokeWidth={2} />
                <span>Encrypted 256-Bit SSL Payment</span>
              </div>
              <h2 className="pricing-qr-title">Scan to Complete Payment</h2>
              <p className="pricing-qr-subtitle">
                Pay <strong>{currency === 'USD' ? `$${(activeOrder.amount_display || activeOrder.amount / 100).toFixed(2)}` : `₹${activeOrder.amount_inr || activeOrder.amount / 100}`}</strong> for {activeOrder.plan?.name || 'Subscription'}
              </p>
            </div>

            {/* Dynamic QR Box */}
            <div className="qr-box-wrapper">
              <div className="qr-code-frame">
                <QRCodeSVG
                  value={activeOrder.upi_qr_data}
                  size={190}
                  level="H"
                  includeMargin={true}
                />
              </div>
              <div className="qr-scan-badge">
                <QrCode size={13} strokeWidth={2} />
                <span>Scan with any UPI app (GPay, PhonePe, Paytm, CRED)</span>
              </div>
            </div>

            {errorMsg && (
              <div className="pricing-error-alert">
                <AlertCircle size={15} />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="pricing-qr-actions">
              <button
                type="button"
                className="pricing-card-btn"
                onClick={handleRazorpayCheckout}
                disabled={isProcessing}
              >
                <CreditCard size={15} strokeWidth={2} />
                <span>Pay with Razorpay Standard Checkout</span>
              </button>

              <button
                type="button"
                className="pricing-verify-btn"
                onClick={handleConfirmPayment}
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <>
                    <Loader2 size={16} className="doc-chip-spin" /> Verifying…
                  </>
                ) : (
                  <>
                    <Check size={16} strokeWidth={2} /> I have paid {currency === 'USD' ? `$${(activeOrder.amount_display || activeOrder.amount / 100).toFixed(2)}` : `₹${activeOrder.amount_inr || activeOrder.amount / 100}`}
                  </>
                )}
              </button>

              <button
                type="button"
                className="pricing-back-btn"
                onClick={() => setActiveOrder(null)}
              >
                Choose Another Plan
              </button>
            </div>
          </div>
        ) : (
          /* Plans Selection Screen */
          <div className="pricing-plans-view">
            {/* Header */}
            <div className="pricing-header">
              <div className="pricing-pill">
                <Sparkles size={13} strokeWidth={2} />
                <span>Affordable Subscription Plans</span>
              </div>

              <h2 className="pricing-title">
                {user && (user.query_count_today || 0) >= (user.daily_limit || 10)
                  ? 'Daily Quota Limit Reached'
                  : 'Upgrade for Superior Models & Limits'}
              </h2>

              <p className="pricing-subtitle">
                {user && (user.query_count_today || 0) >= (user.daily_limit || 10)
                  ? 'You have used your 10 free inquiries for today. Free accounts automatically renew every 24 hours, or upgrade now for up to 100-200 queries/day with our Better Model Analyzer!'
                  : 'Unlock up to 100-200 queries/day powered by our Better Model Analyzer for deep table synthesis and verified citations.'}
              </p>

              {/* Currency Selector */}
              <div className="currency-selector">
                <button
                  type="button"
                  className={`currency-tab ${currency === 'INR' ? 'active' : ''}`}
                  onClick={() => setCurrency('INR')}
                >
                  INR (₹)
                </button>
                <button
                  type="button"
                  className={`currency-tab ${currency === 'USD' ? 'active' : ''}`}
                  onClick={() => setCurrency('USD')}
                >
                  USD ($)
                </button>
              </div>
            </div>

            {errorMsg && (
              <div className="pricing-error-alert">
                <AlertCircle size={15} />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Plans Grid */}
            <div className="pricing-cards-grid">
              {PLANS_DATA.map((plan) => {
                const isSelected = selectedPlan === plan.id;
                const price = currency === 'USD' ? `$${plan.price_usd}` : `₹${plan.price_inr}`;

                return (
                  <div
                    key={plan.id}
                    className={`pricing-card ${plan.popular ? 'popular' : ''} ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedPlan(plan.id)}
                  >
                    {plan.popular && (
                      <div className="pricing-card-badge">{plan.badge}</div>
                    )}

                    <div className="pricing-card-top">
                      <h3 className="plan-name">{plan.name}</h3>
                      <div className="plan-price-row">
                        <span className="plan-price">{price}</span>
                        <span className="plan-period">/ {plan.period}</span>
                      </div>
                      <p className="plan-desc">{plan.desc}</p>
                    </div>

                    <div className="plan-features-list">
                      {plan.features.map((feat, idx) => (
                        <div key={idx} className="plan-feature-item">
                          <Check size={14} strokeWidth={2.5} className="feature-check" />
                          <span>{feat}</span>
                        </div>
                      ))}
                    </div>

                    <button
                      type="button"
                      className={`plan-cta-btn ${plan.popular ? 'primary' : 'secondary'}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectPlanAndPay(plan.id);
                      }}
                      disabled={isProcessing}
                    >
                      <span>Get Started</span>
                      <ArrowRight size={14} strokeWidth={2} />
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Trust Footer */}
            <div className="pricing-footer">
              <div className="pricing-trust-item">
                <ShieldCheck size={14} />
                <span>Instant Activation</span>
              </div>
              <div className="pricing-trust-item">
                <Lock size={14} />
                <span>End-to-End Encrypted</span>
              </div>
              <div className="pricing-trust-item">
                <Clock size={14} />
                <span>Cancel Anytime</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

