import type { ReactNode } from "react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="api-state" role="status">
      <span className="spinner" />
      <p>{label}…</p>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="api-state api-error" role="alert">
      <strong>Unable to load this workflow</strong>
      <p>{message}</p>
      <button className="button button-secondary" onClick={onRetry} type="button">
        Retry
      </button>
    </div>
  );
}

export function MutationMessage({
  error,
  success
}: {
  error?: string | null;
  success?: ReactNode;
}) {
  if (error) {
    return <p className="inline-message inline-message-error">{error}</p>;
  }
  if (success) {
    return <p className="inline-message inline-message-success">{success}</p>;
  }
  return null;
}
