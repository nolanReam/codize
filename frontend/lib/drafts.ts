"use client";

// Local draft persistence (M13E.2, pilot issue 3): text typed but not yet
// saved/submitted survives switching tabs and pages. Drafts live in
// localStorage only — the backend stays the source of truth; pages apply the
// stored backend data first and overlay the draft on top, and a successful
// save/submit clears the draft.
//
// Keys are scoped `codize:draft:<user id>:<surface>` where the surface
// encodes page + phase (e.g. "review_board:2") or gate session + step, so one
// account's drafts never appear under another account on a shared machine and
// phases never cross-pollinate. (Projects are 1:1 with users until the
// multi-project milestone, so user scope covers project scope.)

import { useCallback, useEffect, useRef, useState } from "react";

import { getSupabase } from "./supabase";

const PREFIX = "codize:draft:";
const DEBOUNCE_MS = 400;

// Mirror of the backend's secret-content markers (schemas/workflow.py). If a
// draft contains something that looks like a real key, it is not persisted —
// deliberately the same short marker list, not a scanner.
const SECRET_MARKERS = ["sb_secret_", "sk-or-", "AIza", "-----BEGIN "];

export function containsSecretMarker(text: string): boolean {
  return SECRET_MARKERS.some((m) => text.includes(m));
}

export function draftKey(userId: string, surface: string): string {
  return `${PREFIX}${userId}:${surface}`;
}

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export function readDraft<T>(storage: StorageLike, key: string): T | null {
  try {
    const raw = storage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null; // corrupt/blocked storage — behave as "no draft"
  }
}

export function writeDraft(storage: StorageLike, key: string, value: unknown): boolean {
  try {
    const serialized = JSON.stringify(value);
    if (containsSecretMarker(serialized)) return false;
    storage.setItem(key, serialized);
    return true;
  } catch {
    return false; // quota/blocked storage — drafts are best-effort
  }
}

export function clearDraft(storage: StorageLike, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // best-effort
  }
}

// React hook: resolves the signed-in user's id, restores any existing draft
// for `surface`, and exposes a debounced save. Pass a null surface while the
// page doesn't know its scope yet (e.g. phase still loading).
export function useDraft<T>(surface: string | null) {
  const [key, setKey] = useState<string | null>(null);
  const [restored, setRestored] = useState<T | null>(null);
  const [ready, setReady] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setKey(null);
    setRestored(null);
    setReady(false);
    if (!surface) return;
    let cancelled = false;
    getSupabase()
      .auth.getSession()
      .then(({ data }) => {
        if (cancelled) return;
        const uid = data.session?.user?.id;
        if (!uid) {
          setReady(true); // signed out — no draft scope, but don't block pages
          return;
        }
        const k = draftKey(uid, surface);
        setKey(k);
        setRestored(readDraft<T>(window.localStorage, k));
        setReady(true);
      })
      .catch(() => setReady(true));
    return () => {
      cancelled = true;
    };
  }, [surface]);

  // Debounced. The pending write is deliberately NOT cancelled on unmount —
  // navigating away right after typing is exactly the case drafts exist for.
  const save = useCallback(
    (value: T) => {
      if (!key) return;
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => writeDraft(window.localStorage, key, value), DEBOUNCE_MS);
    },
    [key]
  );

  const clear = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    if (key) clearDraft(window.localStorage, key);
  }, [key]);

  return { restored, ready, save, clear };
}
