"use client";

import Link from "next/link";
import { useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login, verifyMfa } = useAuth();
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [challengeToken, setChallengeToken] = useState<string | null>(null);

  async function submitCredentials(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const outcome = await login(
        String(form.get("email")),
        String(form.get("password")),
        String(form.get("tenant_slug"))
      );
      setChallengeToken(outcome.challengeToken);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setWorking(false);
    }
  }

  async function submitMfa(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challengeToken) return;
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await verifyMfa(challengeToken, String(form.get("code")));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "MFA verification failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <span>D</span>
          <div><strong>D-carbN</strong><small>Carbon Platform</small></div>
        </div>
        <p className="eyebrow">Secure access</p>
        <h1>{challengeToken ? "Verify your identity" : "Sign in"}</h1>
        {challengeToken ? (
          <form className="auth-form" onSubmit={submitMfa}>
            <p>Enter the six-digit authenticator code or a recovery code.</p>
            <label>MFA or recovery code<input autoComplete="one-time-code" name="code" required /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">
              {working ? "Verifying…" : "Verify and sign in"}
            </button>
          </form>
        ) : (
          <form className="auth-form" onSubmit={submitCredentials}>
            <label>Tenant workspace<input autoComplete="organization" name="tenant_slug" placeholder="northstar-logistics" required /></label>
            <label>Email address<input autoComplete="email" name="email" required type="email" /></label>
            <label>Password<input autoComplete="current-password" minLength={12} name="password" required type="password" /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">
              {working ? "Signing in…" : "Sign in"}
            </button>
            <Link className="text-link" href="/forgot-password">Forgot your password?</Link>
          </form>
        )}
      </section>
    </main>
  );
}
