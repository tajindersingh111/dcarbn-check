"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { ListResponse, Organisation } from "@/lib/types";

type Provider = "quickbooks" | "xero" | "sage" | "api";
interface Connection {
  id: string;
  organisation_id: string;
  external_customer_id: string;
  provider: Provider;
  external_company_id: string;
  display_name: string;
  status: string;
  mapping_profile_version: string;
  last_synced_at: string | null;
  failure_code: string | null;
  failure_message: string | null;
}
interface SyncJob { id: string; status: string; }

const providers: Array<{ id: Provider | "csv"; name: string; description: string }> = [
  { id: "quickbooks", name: "QuickBooks", description: "Import governed purchase and supplier records." },
  { id: "xero", name: "Xero", description: "Map bills, suppliers and account transactions." },
  { id: "sage", name: "Sage", description: "Connect approved Sage accounting exports." },
  { id: "api", name: "Direct API", description: "Use a secure customer-to-customer data connection." },
  { id: "csv", name: "CSV upload", description: "Upload and validate a governed spreadsheet template." }
];

const requiredTargets = [
  "external_customer_id", "external_transaction_id", "source_system",
  "transaction_date", "supplier_name", "description", "scope_3_category",
  "reported_kg_co2e", "allocation_percentage", "supplier_methodology",
  "supplier_methodology_version", "supplier_reporting_period_start",
  "supplier_reporting_period_end", "supplier_result_calculated_at",
  "boundary_description", "assurance_status", "evidence_reference"
];
const standardMapping = Object.fromEntries(requiredTargets.map((field) => [field, field]));

function providerName(value: string): string {
  return providers.find((provider) => provider.id === value)?.name ?? value;
}

export default function ConnectedSystemsPage() {
  const connections = useApiQuery<Connection[]>("/integrations/data/accounting/connections");
  const organisations = useApiQuery<ListResponse<Organisation>>("/organisations?limit=200");
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [saving, setSaving] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const activeCount = useMemo(
    () => (connections.data ?? []).filter((connection) => connection.status === "active").length,
    [connections.data]
  );

  async function register(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProvider) return;
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await apiRequest<Connection>("/integrations/data/accounting/connections", {
        method: "POST",
        body: JSON.stringify({
          organisation_id: form.get("organisation_id"),
          external_customer_id: form.get("external_customer_id"),
          provider: selectedProvider,
          external_company_id: form.get("external_company_id"),
          display_name: form.get("display_name"),
          mapping_profile_version: "2026.1",
          mapping: standardMapping
        })
      });
      setMessage(
        `${providerName(selectedProvider)} has been registered safely. Provider authorisation can be activated when the production callback and secret vault are available.`
      );
      setSelectedProvider(null);
      await connections.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The connection could not be registered.");
    } finally {
      setSaving(false);
    }
  }

  async function synchronise(connection: Connection) {
    setSyncingId(connection.id);
    setError(null);
    setMessage(null);
    try {
      const job = await apiRequest<SyncJob>(
        `/integrations/data/accounting/connections/${connection.id}/syncs`,
        { method: "POST", body: JSON.stringify({}) }
      );
      setMessage(`Synchronisation job ${job.id} is ${job.status}.`);
      await connections.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Synchronisation could not be started.");
    } finally {
      setSyncingId(null);
    }
  }

  if (connections.loading || organisations.loading) {
    return <LoadingState label="Loading connected systems" />;
  }
  if (connections.error || organisations.error) {
    return (
      <ErrorState
        message={connections.error ?? organisations.error ?? "Connected systems could not be loaded."}
        onRetry={() => {
          void connections.refresh();
          void organisations.refresh();
        }}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Customer data collection"
        title="Connected systems"
        description="Bring accounting and operational data into D-carbN through governed, tenant-scoped connections without exposing passwords or access tokens."
      />

      <div className="connection-summary" aria-label="Connection summary">
        <div><strong>{connections.data?.length ?? 0}</strong><span>Registered systems</span></div>
        <div><strong>{activeCount}</strong><span>Active connections</span></div>
        <div><strong>2026.1</strong><span>Mapping profile</span></div>
      </div>

      <MutationMessage error={error} success={message} />

      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Choose a source</p><h2>Add a connected system</h2></div>
          <span className="record-count">No passwords collected</span>
        </div>
        <div className="provider-grid">
          {providers.map((provider) => (
            <article className="provider-card" key={provider.id}>
              <div className="provider-monogram" aria-hidden="true">
                {provider.name.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <h3>{provider.name}</h3>
                <p>{provider.description}</p>
              </div>
              {provider.id === "csv" ? (
                <Link className="button button-secondary" href="/data-imports">Open CSV import</Link>
              ) : (
                <button
                  className="button button-secondary"
                  onClick={() => setSelectedProvider(provider.id as Provider)}
                  type="button"
                >
                  Set up
                </button>
              )}
            </article>
          ))}
        </div>
      </section>

      {selectedProvider ? (
        <section className="panel connection-setup-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Safe setup</p>
              <h2>Register {providerName(selectedProvider)}</h2>
            </div>
            <button className="text-button" onClick={() => setSelectedProvider(null)} type="button">
              Cancel
            </button>
          </div>
          <p className="connection-note">
            This records the governed connection profile only. OAuth approval and encrypted credentials
            will be enabled when the production hosting callback and secret vault are available.
          </p>
          <form className="connection-form" onSubmit={register}>
            <label>
              Reporting organisation
              <select name="organisation_id" required>
                <option value="">Choose organisation</option>
                {(organisations.data?.items ?? []).map((organisation) => (
                  <option key={organisation.id} value={organisation.id}>{organisation.name}</option>
                ))}
              </select>
            </label>
            <label>
              Connection name
              <input name="display_name" placeholder={`${providerName(selectedProvider)} · UK entity`} required />
            </label>
            <label>
              Customer reference
              <input name="external_customer_id" placeholder="customer-1042" required />
            </label>
            <label>
              External company ID
              <input name="external_company_id" placeholder="Company identifier in source system" required />
            </label>
            <div className="connection-form-actions">
              <span>Standard governed mapping · version 2026.1</span>
              <button className="button button-primary" disabled={saving} type="submit">
                {saving ? "Registering…" : "Register connection"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Connection register</p><h2>Your systems</h2></div>
          <span className="record-count">{connections.data?.length ?? 0} records</span>
        </div>
        {(connections.data ?? []).length === 0 ? (
          <div className="empty-connection-state">
            <h3>No systems registered yet</h3>
            <p>Choose a provider above, or use the governed CSV import journey.</p>
          </div>
        ) : (
          <div className="connection-list">
            {(connections.data ?? []).map((connection) => (
              <article className="connection-row" key={connection.id}>
                <div className="provider-monogram" aria-hidden="true">
                  {providerName(connection.provider).slice(0, 2).toUpperCase()}
                </div>
                <div className="connection-main">
                  <strong>{connection.display_name}</strong>
                  <span>
                    {providerName(connection.provider)} · {connection.external_company_id}
                  </span>
                  {connection.failure_message ? (
                    <small className="field-error">{connection.failure_message}</small>
                  ) : null}
                </div>
                <div className="connection-meta">
                  <StatusBadge status={connection.status} />
                  <span>
                    {connection.last_synced_at
                      ? `Last sync ${new Date(connection.last_synced_at).toLocaleString("en-GB")}`
                      : "Not yet synchronised"}
                  </span>
                </div>
                {connection.status === "active" ? (
                  <button
                    className="button button-secondary"
                    disabled={syncingId === connection.id}
                    onClick={() => void synchronise(connection)}
                    type="button"
                  >
                    {syncingId === connection.id ? "Starting…" : "Sync now"}
                  </button>
                ) : (
                  <span className="connection-awaiting">Awaiting authorisation</span>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="connection-safety">
        <div><strong>Tenant isolated</strong><span>Each connection is restricted to the customer organisation.</span></div>
        <div><strong>Auditable mappings</strong><span>Every source field is tied to a versioned import contract.</span></div>
        <div><strong>Credential safe</strong><span>Passwords and raw access tokens are never stored in this interface.</span></div>
      </section>
    </>
  );
}
