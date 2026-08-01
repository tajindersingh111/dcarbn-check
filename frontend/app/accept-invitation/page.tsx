"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { apiRequest } from "@/lib/api";

function AcceptInvitationForm() {
  const searchParams = useSearchParams();
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/auth/invitations/accept", {
        method: "POST",
        body: JSON.stringify({
          token: searchParams.get("token") ?? "",
          password: form.get("password"),
          password_confirmation: form.get("password_confirmation")
        })
      });
      setSuccess(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invitation could not be accepted.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Tenant invitation</p>
        <h1>Create your account</h1>
        {success ? (
          <><p>Your account is active.</p><a className="button button-primary" href="/login">Continue to sign in</a></>
        ) : (
          <form className="auth-form" onSubmit={submit}>
            <label>Password<input minLength={12} name="password" required type="password" /></label>
            <label>Confirm password<input minLength={12} name="password_confirmation" required type="password" /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">{working ? "Activating…" : "Activate account"}</button>
          </form>
        )}
      </section>
    </main>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<main className="auth-page" aria-busy="true" />}>
      <AcceptInvitationForm />
    </Suspense>
  );
}
