"use client";

import { useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { apiRequest } from "@/lib/api";

export default function SecuritySettingsPage() {
  const [secret, setSecret] = useState<string | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function startEnrollment() {
    setWorking(true);
    setError(null);
    try {
      const response = await apiRequest<{ secret: string; provisioning_uri: string }>(
        "/auth/mfa/enroll",
        { method: "POST" }
      );
      setSecret(response.secret);
      setUri(response.provisioning_uri);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "MFA enrollment failed.");
    } finally {
      setWorking(false);
    }
  }

  async function confirm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiRequest<{ recovery_codes: string[] }>(
        "/auth/mfa/confirm",
        {
          method: "POST",
          body: JSON.stringify({ code: form.get("code") })
        }
      );
      setCodes(response.recovery_codes);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "MFA confirmation failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account security"
        title="Multi-factor authentication"
        description="Protect your account with a time-based authenticator and single-use recovery codes."
      />
      <section className="panel onboarding-panel">
        {!secret ? (
          <button className="button button-primary" disabled={working} onClick={() => void startEnrollment()} type="button">
            Begin MFA enrollment
          </button>
        ) : codes.length === 0 ? (
          <form className="auth-form" onSubmit={confirm}>
            <div className="token-panel">
              <strong>Authenticator secret</strong>
              <code>{secret}</code>
              <p>Provisioning URI:</p>
              <code>{uri}</code>
            </div>
            <label>Six-digit verification code<input name="code" required /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">
              {working ? "Confirming…" : "Enable MFA"}
            </button>
          </form>
        ) : (
          <div className="token-panel">
            <h2>Save your recovery codes</h2>
            <p>Each code can be used once. Store them in an approved password manager.</p>
            <div className="recovery-code-grid">
              {codes.map((code) => <code key={code}>{code}</code>)}
            </div>
          </div>
        )}
      </section>
    </>
  );
}
