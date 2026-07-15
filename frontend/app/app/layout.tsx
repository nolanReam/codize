"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import GuidedProjectNav from "@/components/GuidedProjectNav";
import GuidedProjectNavigationProvider, {
  useGuidedProjectNavigation,
} from "@/components/GuidedProjectNavigationProvider";
import ReconnectionModal from "@/components/ReconnectionModal";
import Tutorial, { TUTORIAL_SEEN_KEY } from "@/components/Tutorial";
import { acknowledgeReconnection, getReconnection } from "@/lib/api";
import { getSupabase } from "@/lib/supabase";
import type { ReconnectionSummary } from "@/lib/types";

// One reconnection check per browser session. The contract (backend M11):
// GET first on every login, THEN acknowledge — immediately when no modal is
// needed, on the "Let's keep building" click when it is. Never acknowledge
// before the GET, or the modal is silently suppressed.
const RECONNECT_FLAG = "codize:reconnection-checked";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
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
      setUserId(data.session.user.id);
      setReady(true);

      // First visit ever on this browser: open the "How Codize works" guide.
      // Dismissing stamps localStorage, so returning users are never blocked;
      // the sidebar button reopens it on demand.
      // M17 makes adaptive entry the first-use task. The broader tutorial
      // remains available from Help without covering that focused decision.

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

  if (!ready || !userId) return <div className="loading" style={{ padding: 40 }}>checking session</div>;

  return (
    <GuidedProjectNavigationProvider userId={userId}>
      <ShellFrame
        email={email}
        pathname={pathname}
        onHelp={() => setShowTutorial(true)}
        onSignOut={() => void signOut()}
      >
        {reconnection && (
          <ReconnectionModal summary={reconnection} busy={ackBusy} onKeepBuilding={keepBuilding} />
        )}
        {/* the reconnection modal always wins; the tutorial waits its turn */}
        {!reconnection && showTutorial && <Tutorial onClose={closeTutorial} />}
        {children}
      </ShellFrame>
    </GuidedProjectNavigationProvider>
  );
}

function ShellFrame({
  children,
  email,
  pathname,
  onHelp,
  onSignOut,
}: {
  children: React.ReactNode;
  email: string | null;
  pathname: string;
  onHelp: () => void;
  onSignOut: () => void;
}) {
  const { navigation, state } = useGuidedProjectNavigation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mobileOpen) return;
    const drawer = drawerRef.current;
    if (!drawer) return;
    const trigger = triggerRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      Array.from(
        drawer.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
        )
      );
    focusable()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
      trigger?.focus();
    };
  }, [mobileOpen]);

  const closeMobile = () => setMobileOpen(false);
  const openHelp = () => {
    closeMobile();
    window.setTimeout(onHelp, 0);
  };

  return (
    <div className="shell">
      <aside className="sidebar desktop-sidebar">
        <div className="brand">
          CODIZE<span>_</span>
        </div>
        <GuidedProjectNav
          pathname={pathname}
          email={email}
          idPrefix="desktop"
          onHelp={onHelp}
          onSignOut={onSignOut}
        />
      </aside>

      <header className="mobile-shell-header">
        <Link href="/app" className="mobile-brand" aria-label="Codize Project Home">
          CODIZE<span>_</span>
        </Link>
        <span className="mobile-current-step">
          {state === "ready" ? navigation.continueAction.label : "Project navigation"}
        </span>
        <button
          ref={triggerRef}
          type="button"
          className="mobile-menu-button"
          aria-expanded={mobileOpen}
          aria-controls="mobile-project-navigation"
          onClick={() => setMobileOpen(true)}
        >
          <span aria-hidden="true">☰</span>
          <span>Menu</span>
        </button>
      </header>

      {mobileOpen && (
        <div className="mobile-drawer-layer">
          <button
            type="button"
            className="mobile-drawer-backdrop"
            aria-label="Close project navigation"
            onClick={closeMobile}
          />
          <div
            ref={drawerRef}
            id="mobile-project-navigation"
            className="mobile-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Project navigation menu"
          >
            <div className="mobile-drawer-heading">
              <div className="brand">
                CODIZE<span>_</span>
              </div>
              <button type="button" className="mobile-drawer-close" onClick={closeMobile}>
                <span aria-hidden="true">×</span>
                <span className="sr-only">Close project navigation</span>
              </button>
            </div>
            <GuidedProjectNav
              pathname={pathname}
              email={email}
              idPrefix="mobile"
              onNavigate={closeMobile}
              onHelp={openHelp}
              onSignOut={onSignOut}
            />
          </div>
        </div>
      )}

      <main className="main">
        <div className="main-inner">{children}</div>
      </main>
    </div>
  );
}
