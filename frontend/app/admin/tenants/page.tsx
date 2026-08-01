"use client";

import { useState } from "react";

import { MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { apiRequest } from "@/lib/api";

export default function TenantOnboardingPage() {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ tenant_slug: string; invitation_token: string } | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiRequest<{ tenant_slug: string; invitation_token: string }>("/platform/tenants/onboard", {
        method: "POST",
        body: JSON.stringify({
          tenant_name: form.get("tenant_name"),
          tenant_slug: form.get("tenant_slug"),
          owner_email: form.get("owner_email"),
          owner_full_name: form.get("owner_full_name")
        })
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Tenant onboarding failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Platform administration" title="Tenant onboarding" description="Provision a tenant workspace, system roles, owner account, and invitation." />
      <section className="panel onboarding-panel">
        {result ? <div className="token-panel"><h2>Tenant provisioned</h2><p>Workspace: <strong>{result.tenant_slug}</strong></p><p>Owner invitation:</p><code>{`${window.location.origin}/accept-invitation?token=${result.invitation_token}`}</code></div> : <form className="form-grid" onSubmit={submit}><label>Tenant name<input name="tenant_name" required /></label><label>Tenant slug<input name="tenant_slug" pattern="[a-z0-9-]+" required /></label><label>Owner full name<input name="owner_full_name" required /></label><label>Owner email<input name="owner_email" required type="email" /></label><div className="field-span-2"><MutationMessage error={error} /></div><div className="button-row field-span-2"><button className="button button-primary" disabled={working} type="submit">{working ? "Provisioning…" : "Provision tenant"}</button></div></form>}
      </section>
    </>
  );
}
