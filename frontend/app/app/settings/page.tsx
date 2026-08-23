"use client";

import { useEffect, useState } from "react";

import { V2Card, V2Notice, V2Skeleton } from "@/components/v2/V2Primitives";
import { ApiError } from "@/lib/api";
import { getPreferences, updateDialogueSound } from "@/lib/v2-api";
import type { UserPreferencesView } from "@/lib/v2-types";

export default function AppSettingsPage() {
  const [preferences, setPreferences] = useState<UserPreferencesView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getPreferences().then(setPreferences).catch((reason) =>
      setError(reason instanceof ApiError ? reason.message : "Couldn't load settings."));
  }, []);

  const toggleSound = async () => {
    if (!preferences) return;
    setBusy(true); setError(null);
    try { setPreferences(await updateDialogueSound(preferences.version, !preferences.dialogue_sound_enabled)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Couldn't save that setting."); }
    finally { setBusy(false); }
  };

  return (
    <div className="v2-page v2-page-narrow">
      <header className="v2-page-header"><p className="v2-eyebrow">Settings</p><h1>Settings</h1><p>Account and presentation preferences belong here.</p></header>
      {error && <V2Notice tone="error">{error}</V2Notice>}
      {!preferences ? <V2Card><V2Skeleton lines={3} /></V2Card> : <V2Card><h2>Presentation</h2>
        <div className="v2-setting-row"><div><strong>Dialogue sounds</strong><p>Play Codybara’s quiet text blips while dialogue appears.</p></div>
          <button type="button" className="v2-button v2-button-secondary" role="switch"
            aria-checked={preferences.dialogue_sound_enabled} onClick={() => void toggleSound()} disabled={busy}>
            {preferences.dialogue_sound_enabled ? "On" : "Off"}</button></div>
        <p className="v2-muted">Reduced motion follows your system setting and reveals dialogue immediately.</p>
      </V2Card>}
    </div>
  );
}
