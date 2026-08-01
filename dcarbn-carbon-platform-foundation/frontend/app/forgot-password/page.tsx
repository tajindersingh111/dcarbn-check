"use client";

import { useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { apiRequest } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          tenant_slug: form.get("tenant_slug")
        })
      });
      setSent(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Account recovery</p>
        <h1>Reset your password</h1>
        {sent ? (
          <p>If the account exists, password reset instructions have been sent.</p>
        ) : (
          <form className="auth-form" onSubmit={submit}>
            <label>Tenant workspace<input name="tenant_slug" required /></label>
            <label>Email address<input name="email" required type="email" /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">
              {working ? "Sending…" : "Send reset instructions"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
