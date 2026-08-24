import './LoadingIndicator.css';

export function TypingDots() {
  return (
    <div className="typing-dots" aria-label="Thinking">
      <span />
      <span />
      <span />
    </div>
  );
}

export function Spinner({ size = 16 }) {
  return (
    <span
      className="spinner"
      style={{ width: size, height: size }}
      aria-hidden="true"
    />
  );
}
