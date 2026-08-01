"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { apiRequest } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({
          token: searchParams.get("token") ?? "",
          password: form.get("password"),
          password_confirmation: form.get("password_confirmation")
        })
      });
      setComplete(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Password reset failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <p className="eyebrow">Account recovery</p>
        <h1>Choose a new password</h1>
        {complete ? (
          <>
            <p>Your password has been reset and existing sessions were revoked.</p>
            <Link className="button button-primary" href="/login">Continue to sign in</Link>
          </>
        ) : (
          <form className="auth-form" onSubmit={submit}>
            <label>New password<input minLength={12} name="password" required type="password" /></label>
            <label>Confirm new password<input minLength={12} name="password_confirmation" required type="password" /></label>
            <MutationMessage error={error} />
            <button className="button button-primary" disabled={working} type="submit">
              {working ? "Resetting…" : "Reset password"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="auth-page" aria-busy="true" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
