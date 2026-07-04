"use client";

// Shared loading / error / content wrapper so every screen has honest states.
export default function Async({
  loading,
  error,
  onRetry,
  children,
}: {
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  children: React.ReactNode;
}) {
  if (loading) return <div className="loading">loading</div>;
  if (error) {
    return (
      <div className="notice error">
        {error}
        {onRetry && (
          <div style={{ marginTop: 10 }}>
            <button className="btn small" onClick={onRetry}>
              Retry
            </button>
          </div>
        )}
      </div>
    );
  }
  return <>{children}</>;
}
