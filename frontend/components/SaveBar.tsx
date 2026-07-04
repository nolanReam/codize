"use client";

// Shared save row for artifact forms: button + error + last-saved timestamp.
export default function SaveBar({
  saving,
  saveError,
  savedAt,
  onSave,
  label = "Save",
}: {
  saving: boolean;
  saveError: string | null;
  savedAt: string | null;
  onSave: () => void;
  label?: string;
}) {
  return (
    <div style={{ marginTop: 16 }}>
      {saveError && <div className="notice error">{saveError}</div>}
      <div className="row">
        <button className="btn primary" disabled={saving} onClick={onSave}>
          {saving ? "Saving…" : label}
        </button>
        {savedAt && (
          <span className="muted mono">
            saved {new Date(savedAt).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}
