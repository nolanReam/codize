"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ReconnectionModal from "@/components/ReconnectionModal";
import Tutorial, { TUTORIAL_SEEN_KEY } from "@/components/Tutorial";
import { acknowledgeReconnection, getReconnection } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";
import type { ReconnectionSummary } from "@/lib/types";

const NAV = [
  { href: "/app", label: "Cockpit", exact: true },
  { href: "/app/phase", label: "Phase Workspace", exact: true },
  { href: "/app/phase/prompt", label: "Prompt Builder" },
  { href: "/app/phase/import", label: "Bring Back What Changed" },
  { href: "/app/phase/review", label: "Review Board" },
  { href: "/app/phase/evidence", label: "Evidence Panel" },
  { href: "/app/phase/verify", label: "Verification Lab" },
  { href: "/app/gate", label: "Project Defense" },
  { href: "/app/report", label: "Defense Report" },
];

// One reconnection check per browser session. The contract (backend M11):
// GET first on every login, THEN acknowledge — immediately when no modal is
// needed, on the "Let's keep building" click when it is. Never acknowledge
// before the GET, or the modal is silently suppressed.
const RECONNECT_FLAG = "codize:reconnection-checked";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [reconnection, setReconnection] = useState<ReconnectionSummary | null>(null);
  const [ackBusy, setAckBusy] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const supabase = getSupabase();
      const { data } = await supabase.auth.getSession();
      if (cancelled) return;
      if (!data.session) {
        router.replace("/login");
        return;
      }
      setEmail(data.session.user.email ?? null);
      setReady(true);

      // First visit ever on this browser: open the "How Codize works" guide.
      // Dismissing stamps localStorage, so returning users are never blocked;
      // the sidebar button reopens it on demand.
      if (!localStorage.getItem(TUTORIAL_SEEN_KEY)) setShowTutorial(true);

      if (!sessionStorage.getItem(RECONNECT_FLAG)) {
        try {
          const state = await getReconnection();
          if (cancelled) return;
          if (state.reconnection_needed && state.summary) {
            setReconnection(state.summary);
          } else {
            await acknowledgeReconnection();
          }
          sessionStorage.setItem(RECONNECT_FLAG, "1");
        } catch {
          // Fail open: never block the workspace on the reconnection check.
          // The flag stays unset so the next full load retries.
        }
      }
    })();

    const { data: sub } = getSupabase().auth.onAuthStateChange((_event, session) => {
      if (!session) router.replace("/login");
    });
    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, [router]);

  const closeTutorial = useCallback(() => {
    localStorage.setItem(TUTORIAL_SEEN_KEY, "1");
    setShowTutorial(false);
  }, []);

  const keepBuilding = useCallback(async () => {
    setAckBusy(true);
    try {
      await acknowledgeReconnection();
    } catch {
      // The click is the acknowledgment moment; a failed write shouldn't trap
      // the user in the modal — the next login will re-offer it.
    } finally {
      setReconnection(null);
      setAckBusy(false);
    }
  }, []);

  async function signOut() {
    sessionStorage.removeItem(RECONNECT_FLAG);
    await getSupabase().auth.signOut();
    router.replace("/login");
  }

  if (!ready) return <div className="loading" style={{ padding: 40 }}>checking session</div>;

  return (
    <div className="shell">
      {reconnection && (
        <ReconnectionModal summary={reconnection} busy={ackBusy} onKeepBuilding={keepBuilding} />
      )}
      {/* the reconnection modal always wins; the tutorial waits its turn */}
      {!reconnection && showTutorial && <Tutorial onClose={closeTutorial} />}
      <aside className="sidebar">
        <div className="brand">
          CODIZE<span>_</span>
        </div>
        <div className="nav-section">Workspace</div>
        {NAV.slice(0, 2).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link${
              (item.exact ? pathname === item.href : pathname.startsWith(item.href)) ? " active" : ""
            }`}
          >
            {item.label}
          </Link>
        ))}
        <div className="nav-section">Build Loop</div>
        {NAV.slice(2, 7).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link${pathname.startsWith(item.href) ? " active" : ""}`}
          >
            {item.label}
          </Link>
        ))}
        <div className="nav-section">Defend</div>
        {NAV.slice(7).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-link${pathname.startsWith(item.href) ? " active" : ""}`}
          >
            {item.label}
          </Link>
        ))}
        <div className="nav-section">Help</div>
        <button className="nav-link" onClick={() => setShowTutorial(true)}>
          How Codize works
        </button>
        <div className="sidebar-footer">
          <div style={{ marginBottom: 8 }}>{email}</div>
          <button className="btn small" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <div className="main-inner">{children}</div>
      </main>
    </div>
  );
}
