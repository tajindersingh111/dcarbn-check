"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { Inventory, ListResponse, Organisation, ReportingPeriod } from "@/lib/types";

function tonnes(value: string | null): string {
  if (value === null) return "—";
  return (Number(value) / 1000).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export default function InventoriesPage() {
  const inventories = useApiQuery<ListResponse<Inventory>>("/inventories?limit=200");
  const periods = useApiQuery<ListResponse<ReportingPeriod>>("/reporting-periods");
  const organisations = useApiQuery<ListResponse<Organisation>>("/organisations?limit=200");
  const [inventoryModal, setInventoryModal] = useState(false);
  const [periodModal, setPeriodModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const organisationById = useMemo(
    () => new Map((organisations.data?.items ?? []).map((item) => [item.id, item.name])),
    [organisations.data]
  );

  async function createInventory(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/inventories", {
        method: "POST",
        body: JSON.stringify({
          reporting_period_id: form.get("reporting_period_id"),
          name: form.get("name")
        })
      });
      setInventoryModal(false);
      await inventories.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Inventory could not be created.");
    } finally {
      setSaving(false);
    }
  }

  async function createPeriod(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest("/reporting-periods", {
        method: "POST",
        body: JSON.stringify({
          organisation_id: form.get("organisation_id"),
          name: form.get("name"),
          start_date: form.get("start_date"),
          end_date: form.get("end_date"),
          is_base_year: form.get("is_base_year") === "on"
        })
      });
      setPeriodModal(false);
      await periods.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Reporting period could not be created.");
    } finally {
      setSaving(false);
    }
  }

  if (inventories.loading || periods.loading || organisations.loading) {
    return <LoadingState label="Loading inventories" />;
  }
  if (inventories.error || periods.error || organisations.error) {
    return <ErrorState message={inventories.error ?? periods.error ?? organisations.error ?? "Unknown error"} onRetry={() => {
      void inventories.refresh(); void periods.refresh(); void organisations.refresh();
    }} />;
  }

  return (
    <>
      <PageHeader
        eyebrow="Corporate inventories"
        title="Inventories"
        description="Track reporting periods, calculations, approvals, locks and restatements."
        actions={
          <>
            <button className="button button-secondary" onClick={() => setPeriodModal(true)} type="button">Add reporting period</button>
            <button className="button button-primary" onClick={() => setInventoryModal(true)} type="button"><PlusIcon /> Create inventory</button>
          </>
        }
      />
      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Inventory register</p><h2>Reporting inventories</h2></div>
          <span className="record-count">{inventories.data?.total ?? 0} records</span>
        </div>
        <DataTable caption="Reporting inventories" headers={["Inventory", "Organisation", "Version", "Scope 1", "Scope 2", "Scope 3", "Total", "Status"]}>
          {(inventories.data?.items ?? []).map((inventory) => (
            <tr key={inventory.id}>
              <td><div className="stacked-cell"><strong>{inventory.name}</strong><span>{inventory.reporting_period_name}</span></div></td>
              <td>{inventory.organisation_name}</td>
              <td>v{inventory.version}</td>
              <td>{tonnes(inventory.scope_1_kg_co2e)}</td>
              <td>{tonnes(inventory.scope_2_kg_co2e)}</td>
              <td>{tonnes(inventory.scope_3_kg_co2e)}</td>
              <td><strong>{tonnes(inventory.total_kg_co2e)}</strong></td>
              <td><StatusBadge status={inventory.status} /></td>
            </tr>
          ))}
        </DataTable>
      </section>

      <Modal open={inventoryModal} onClose={() => setInventoryModal(false)} title="Create inventory" description="Create a versioned inventory for an existing reporting period.">
        <form className="modal-form" onSubmit={createInventory}>
          <label>Inventory name<input name="name" required /></label>
          <label>Reporting period<select name="reporting_period_id" required>
            <option value="">Select reporting period</option>
            {(periods.data?.items ?? []).map((period) => (
              <option key={period.id} value={period.id}>{organisationById.get(period.organisation_id) ?? "Organisation"} · {period.name}</option>
            ))}
          </select></label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setInventoryModal(false)} type="button">Cancel</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "Creating…" : "Create inventory"}</button></div>
        </form>
      </Modal>

      <Modal open={periodModal} onClose={() => setPeriodModal(false)} title="Add reporting period" description="Define the dates used by organisational boundaries and inventories.">
        <form className="modal-form" onSubmit={createPeriod}>
          <label>Organisation<select name="organisation_id" required><option value="">Select organisation</option>{(organisations.data?.items ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Period name<input name="name" placeholder="Calendar year 2026" required /></label>
          <label>Start date<input name="start_date" required type="date" /></label>
          <label>End date<input name="end_date" required type="date" /></label>
          <label className="checkbox-field"><input name="is_base_year" type="checkbox" /> Base year</label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setPeriodModal(false)} type="button">Cancel</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "Creating…" : "Create reporting period"}</button></div>
        </form>
      </Modal>
    </>
  );
}
