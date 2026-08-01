"use client";

import { useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { OrganisationIcon, PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { ListResponse, Organisation } from "@/lib/types";

export default function OrganisationsPage() {
  const query = useApiQuery<ListResponse<Organisation>>(
    "/organisations?limit=200"
  );
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest<Organisation>("/organisations", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"),
          legal_name: form.get("legal_name") || null,
          registration_number: form.get("registration_number") || null,
          country_code: form.get("country_code")
        })
      });
      setOpen(false);
      await query.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Organisation could not be created.");
    } finally {
      setSaving(false);
    }
  }

  if (query.loading) return <LoadingState label="Loading organisations" />;
  if (query.error) return <ErrorState message={query.error} onRetry={query.refresh} />;

  return (
    <>
      <PageHeader
        eyebrow="Reporting structure"
        title="Organisations"
        description="Manage reporting organisations and their corporate identity."
        actions={
          <button className="button button-primary" onClick={() => setOpen(true)} type="button">
            <PlusIcon /> Add organisation
          </button>
        }
      />
      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Tenant structure</p><h2>Reporting organisations</h2></div>
          <span className="record-count">{query.data?.total ?? 0} records</span>
        </div>
        <DataTable caption="Reporting organisations" headers={["Organisation", "Country", "Registration", "Status"]}>
          {(query.data?.items ?? []).map((organisation) => (
            <tr key={organisation.id}>
              <td>
                <div className="entity-cell">
                  <span className="table-icon"><OrganisationIcon /></span>
                  <div><strong>{organisation.name}</strong><span>{organisation.legal_name ?? "Corporate reporting organisation"}</span></div>
                </div>
              </td>
              <td>{organisation.country_code}</td>
              <td>{organisation.registration_number ?? "—"}</td>
              <td><StatusBadge status={organisation.is_active ? "active" : "inactive"} /></td>
            </tr>
          ))}
        </DataTable>
      </section>

      <Modal
        description="Create a tenant-scoped reporting organisation."
        onClose={() => setOpen(false)}
        open={open}
        title="Add organisation"
      >
        <form className="modal-form" onSubmit={create}>
          <label>Name<input name="name" required /></label>
          <label>Legal name<input name="legal_name" /></label>
          <label>Registration number<input name="registration_number" /></label>
          <label>Country code<input defaultValue="GB" maxLength={2} name="country_code" required /></label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions">
            <button className="button button-secondary" onClick={() => setOpen(false)} type="button">Cancel</button>
            <button className="button button-primary" disabled={saving} type="submit">{saving ? "Creating…" : "Create organisation"}</button>
          </div>
        </form>
      </Modal>
    </>
  );
}
