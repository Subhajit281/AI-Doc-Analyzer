import { useState, useEffect } from 'react';
import {
  X,
  Lock,
  Mail,
  User,
  AlertCircle,
  Loader2,
  LogIn,
  UserPlus,
  ShieldCheck,
  KeyRound,
  ArrowRight,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react';
import { loginUser, signupUser, sendOtp, verifyOtp } from '../services/api';
import './AuthModal.css';

export default function AuthModal({
  isOpen,
  onClose,
  onSuccess,
  isDismissible = true,
}) {
  const [tab, setTab] = useState('login'); // 'login' or 'signup'
  const [authMethod, setAuthMethod] = useState('otp'); // 'otp' or 'password'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [otpCode, setOtpCode] = useState('');

  const [otpSent, setOtpSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  if (!isOpen) return null;

  const handleSendOtp = async (e) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!email || !email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await sendOtp(email, tab);
      setOtpSent(true);
      setCountdown(60);
      setSuccessMsg(res.message || 'Verification code sent to your email.');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to send verification code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    if (!otpCode || otpCode.trim().length !== 6) {
      setErrorMsg('Please enter the complete 6-digit code.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await verifyOtp(email, otpCode.trim(), tab, password, fullName);
      localStorage.setItem('docai_token', data.token);
      onSuccess(data.user, data.token);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Invalid or expired code. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setIsSubmitting(true);

    try {
      let data;
      if (tab === 'login') {
        data = await loginUser(email, password);
      } else {
        data = await signupUser(email, password, fullName);
      }

      localStorage.setItem('docai_token', data.token);
      onSuccess(data.user, data.token);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setErrorMsg('');
    setSuccessMsg('');
    setOtpSent(false);
    setOtpCode('');
  };

  return (
    <div
      className="auth-modal-overlay"
      onClick={isDismissible ? onClose : undefined}
    >
      <div className="auth-modal-container" onClick={(e) => e.stopPropagation()}>
        {!isDismissible && (
          <div className="auth-required-banner">
            <ShieldCheck size={14} />
            <span>Authentication Required • Please log in to start analyzing documents</span>
          </div>
        )}

        {isDismissible && (
          <button
            type="button"
            className="auth-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} strokeWidth={2} />
          </button>
        )}

        {/* Tabs: Log In vs Create Account */}
        <div className="auth-tabs-row">
          <button
            type="button"
            className={`auth-tab-btn ${tab === 'login' ? 'active' : ''}`}
            onClick={() => {
              setTab('login');
              resetForm();
            }}
          >
            <LogIn size={15} />
            <span>Log In</span>
          </button>
          <button
            type="button"
            className={`auth-tab-btn ${tab === 'signup' ? 'active' : ''}`}
            onClick={() => {
              setTab('signup');
              resetForm();
            }}
          >
            <UserPlus size={15} />
            <span>Create Account</span>
          </button>
        </div>

        <div className="auth-body">
          {/* Method Switcher: OTP Code vs Password */}
          <div className="auth-method-toggle">
            <button
              type="button"
              className={`method-toggle-btn ${authMethod === 'otp' ? 'active' : ''}`}
              onClick={() => {
                setAuthMethod('otp');
                resetForm();
              }}
            >
              <ShieldCheck size={14} />
              <span>Secure OTP Code</span>
            </button>
            <button
              type="button"
              className={`method-toggle-btn ${authMethod === 'password' ? 'active' : ''}`}
              onClick={() => {
                setAuthMethod('password');
                resetForm();
              }}
            >
              <Lock size={14} />
              <span>Password</span>
            </button>
          </div>

          <h2 className="auth-title">
            {tab === 'login' ? 'Welcome Back' : 'Create Account'}
          </h2>
          <p className="auth-desc">
            {authMethod === 'otp'
              ? 'A 6-digit verification code valid for 10 minutes will be sent to your email.'
              : 'Sign in with your email and password.'}
          </p>

          {errorMsg && (
            <div className="auth-error-banner">
              <AlertCircle size={15} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="auth-success-banner">
              <CheckCircle2 size={15} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* OTP Flow */}
          {authMethod === 'otp' ? (
            !otpSent ? (
              <form className="auth-form" onSubmit={handleSendOtp}>
                {tab === 'signup' && (
                  <div className="auth-input-group">
                    <label className="auth-label">Full Name</label>
                    <div className="auth-input-wrapper">
                      <User size={15} className="auth-input-icon" />
                      <input
                        type="text"
                        className="auth-input"
                        placeholder="Your name"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                      />
                    </div>
                  </div>
                )}

                <div className="auth-input-group">
                  <label className="auth-label">Email Address</label>
                  <div className="auth-input-wrapper">
                    <Mail size={15} className="auth-input-icon" />
                    <input
                      type="email"
                      className="auth-input"
                      placeholder="name@example.com"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="doc-chip-spin" /> Sending Code…
                    </>
                  ) : (
                    <>
                      <span>Send 6-Digit Code</span>
                      <ArrowRight size={15} />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <form className="auth-form" onSubmit={handleVerifyOtp}>
                <div className="auth-otp-notice">
                  <span>Enter the 6-digit code sent to:</span>
                  <strong>{email}</strong>
                </div>

                <div className="auth-input-group">
                  <label className="auth-label">Verification Code</label>
                  <div className="auth-input-wrapper otp-input-wrapper">
                    <KeyRound size={16} className="auth-input-icon" />
                    <input
                      type="text"
                      className="auth-input otp-digit-input"
                      placeholder="123456"
                      maxLength={6}
                      autoFocus
                      required
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="auth-submit-btn"
                  disabled={isSubmitting || otpCode.length !== 6}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="doc-chip-spin" /> Verifying…
                    </>
                  ) : (
                    'Verify & Log In'
                  )}
                </button>

                <div className="auth-otp-footer">
                  {countdown > 0 ? (
                    <span className="otp-countdown">Resend code in {countdown}s</span>
                  ) : (
                    <button
                      type="button"
                      className="otp-resend-btn"
                      onClick={() => handleSendOtp(null)}
                      disabled={isSubmitting}
                    >
                      <RotateCcw size={13} />
                      <span>Resend Code</span>
                    </button>
                  )}
                  <button
                    type="button"
                    className="otp-change-email-btn"
                    onClick={() => {
                      setOtpSent(false);
                      setOtpCode('');
                    }}
                  >
                    Change Email
                  </button>
                </div>
              </form>
            )
          ) : (
            /* Traditional Password Flow */
            <form className="auth-form" onSubmit={handlePasswordSubmit}>
              {tab === 'signup' && (
                <div className="auth-input-group">
                  <label className="auth-label">Full Name</label>
                  <div className="auth-input-wrapper">
                    <User size={15} className="auth-input-icon" />
                    <input
                      type="text"
                      className="auth-input"
                      placeholder="Your name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="auth-input-group">
                <label className="auth-label">Email Address</label>
                <div className="auth-input-wrapper">
                  <Mail size={15} className="auth-input-icon" />
                  <input
                    type="email"
                    className="auth-input"
                    placeholder="name@example.com"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label className="auth-label">Password</label>
                <div className="auth-input-wrapper">
                  <Lock size={15} className="auth-input-icon" />
                  <input
                    type="password"
                    className="auth-input"
                    placeholder="••••••••"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="doc-chip-spin" /> Authenticating…
                  </>
                ) : tab === 'login' ? (
                  'Log In'
                ) : (
                  'Create Account'
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
