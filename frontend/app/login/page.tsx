"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getSupabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();

  // Arriving from far down the landing page must not leave the login screen
  // scrolled — the screen also fits one viewport, so there is nothing to
  // scroll into, but reset explicitly as well.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const supabase = getSupabase();
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        if (!data.session) {
          // Email confirmations are on for this Supabase project.
          setNotice("Check your email to confirm your account, then sign in.");
          setMode("signin");
          return;
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
      // Spec: signup goes straight into the app — the cockpit forwards new
      // users to intake question 1.
      router.replace("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <div className="glass auth-card">
        <div className="brand mono" style={{ letterSpacing: "0.12em", fontWeight: 600 }}>
          CODIZE<span style={{ color: "var(--accent)" }}>_</span>
        </div>
        <h1 style={{ fontSize: 20, margin: "18px 0 4px" }}>
          {mode === "signin" ? "Sign in" : "Create your account"}
        </h1>
        <p className="muted" style={{ marginBottom: 18 }}>
          {mode === "signin"
            ? "Back to the workspace."
            : "You'll go straight into project intake — no dashboard detours."}
        </p>

        {error && <div className="notice error">{error}</div>}
        {notice && <div className="notice ok">{notice}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn primary" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Working…" : mode === "signin" ? "Sign in" : "Sign up"}
          </button>
        </form>

        <p className="muted" style={{ marginTop: 16 }}>
          {mode === "signin" ? (
            <>
              New here?{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  setMode("signup");
                  setError(null);
                }}
              >
                Create an account
              </a>
            </>
          ) : (
            <>
              Already building?{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  setMode("signin");
                  setError(null);
                }}
              >
                Sign in
              </a>
            </>
          )}
        </p>
        <p className="muted" style={{ marginTop: 8 }}>
          <Link href="/">← Back to codize.dev</Link>
        </p>
      </div>
    </main>
  );
}
