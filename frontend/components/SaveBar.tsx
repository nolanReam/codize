"use client";

// Shared save row for artifact forms: button + error + last-saved timestamp.
export default function SaveBar({
  saving,
  saveError,
  savedAt,
  onSave,
  label = "Save",
  disabled = false,
}: {
  saving: boolean;
  saveError: string | null;
  savedAt: string | null;
  onSave: () => void;
  label?: string;
  disabled?: boolean;
}) {
  return (
    <div style={{ marginTop: 16 }}>
      {saveError && <div className="notice error" role="alert">{saveError}</div>}
      <div className="row">
        <button className="btn primary" disabled={saving || disabled} onClick={onSave}>
          {saving ? "Saving…" : label}
        </button>
        {savedAt && (
          <span className="muted mono" role="status">
            saved {new Date(savedAt).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}
