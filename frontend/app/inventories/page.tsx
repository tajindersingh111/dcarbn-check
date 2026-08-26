"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { PlusIcon } from "@/components/icons";
import { InventoryCalculationRunner } from "@/components/inventory-calculation-runner";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { Inventory, ListResponse, Organisation, ReportingPeriod } from "@/lib/types";

type GovernedReportingPeriod = ReportingPeriod & {
  base_year_reason: string | null;
  recalculation_policy: string | null;
  recalculation_significance_threshold_percent: string;
  comparative_reporting_period_id: string | null;
};

function tonnes(value: string | null): string {
  if (value === null) return "—";
  return (Number(value) / 1000).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

export default function InventoriesPage() {
  const [scope2HeadlineBasis, setScope2HeadlineBasis] = useState<"location_based" | "market_based">("location_based");
  const inventories = useApiQuery<ListResponse<Inventory>>(
    `/inventories?limit=200&scope_2_headline_basis=${scope2HeadlineBasis}`
  );
  const periods = useApiQuery<ListResponse<GovernedReportingPeriod>>("/reporting-periods");
  const organisations = useApiQuery<ListResponse<Organisation>>("/organisations?limit=200");
  const [inventoryModal, setInventoryModal] = useState(false);
  const [periodModal, setPeriodModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [periodOrganisationId, setPeriodOrganisationId] = useState("");
  const [baseYear, setBaseYear] = useState(false);
  const [calculationInventory, setCalculationInventory] = useState<Inventory | null>(null);

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
          is_base_year: baseYear,
          base_year_reason: baseYear ? form.get("base_year_reason") : null,
          recalculation_policy: baseYear ? form.get("recalculation_policy") : null,
          recalculation_significance_threshold_percent: form.get("recalculation_significance_threshold_percent"),
          comparative_reporting_period_id: baseYear || !form.get("comparative_reporting_period_id")
            ? null
            : form.get("comparative_reporting_period_id")
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
            <label>Headline Scope 2 basis<select aria-label="Headline Scope 2 basis" onChange={(event) => setScope2HeadlineBasis(event.target.value as "location_based" | "market_based")} value={scope2HeadlineBasis}><option value="location_based">Location-based</option><option value="market_based">Market-based</option></select></label>
            <button className="button button-secondary" onClick={() => setPeriodModal(true)} type="button">Add reporting period</button>
            <button className="button button-primary" onClick={() => setInventoryModal(true)} type="button"><PlusIcon /> Create inventory</button>
          </>
        }
      />
      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Reporting governance</p><h2>Base year and comparative register</h2></div>
          <span className="record-count">{periods.data?.total ?? 0} periods</span>
        </div>
        <DataTable caption="Base year and comparative reporting-period register" headers={["Period", "Organisation", "Role", "Comparative", "Threshold", "Policy status"]}>
          {(periods.data?.items ?? []).map((period) => {
            const comparative = (periods.data?.items ?? []).find((item) => item.id === period.comparative_reporting_period_id);
            return (
              <tr key={period.id}>
                <td><div className="stacked-cell"><strong>{period.name}</strong><span>{period.start_date} to {period.end_date}</span></div></td>
                <td>{organisationById.get(period.organisation_id) ?? "Organisation"}</td>
                <td>{period.is_base_year ? <StatusBadge status="base year" /> : "Reporting year"}</td>
                <td>{comparative?.name ?? "—"}</td>
                <td>{Number(period.recalculation_significance_threshold_percent).toLocaleString("en-GB", { maximumFractionDigits: 4 })}%</td>
                <td>{period.is_base_year && period.recalculation_policy ? "Recorded" : period.is_base_year ? "Required" : "Inherited from base year"}</td>
              </tr>
            );
          })}
        </DataTable>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Inventory register</p><h2>Reporting inventories</h2></div>
          <span className="record-count">{inventories.data?.total ?? 0} records</span>
        </div>
        <DataTable caption="Reporting inventories with separate Scope 2 methods" headers={["Inventory", "Organisation", "Version", "Scope 1", "Scope 2 location-based", "Scope 2 market-based", "Scope 3", `Headline total (${scope2HeadlineBasis === "location_based" ? "location-based" : "market-based"})`, "Status", ""]}>
          {(inventories.data?.items ?? []).map((inventory) => (
            <tr key={inventory.id}>
              <td><div className="stacked-cell"><strong>{inventory.name}</strong><span>{inventory.reporting_period_name}</span></div></td>
              <td>{inventory.organisation_name}</td>
              <td>v{inventory.version}</td>
              <td>{tonnes(inventory.scope_1_kg_co2e)}</td>
              <td>{tonnes(inventory.scope_2_location_based_kg_co2e)}</td>
              <td>{tonnes(inventory.scope_2_market_based_kg_co2e)}</td>
              <td>{tonnes(inventory.scope_3_kg_co2e)}</td>
              <td><strong>{tonnes(inventory.total_kg_co2e)}</strong></td>
              <td><StatusBadge status={inventory.status} /></td>
              <td>
                <button
                  className="text-button"
                  onClick={() => setCalculationInventory(inventory)}
                  type="button"
                >
                  Calculate
                </button>
              </td>
            </tr>
          ))}
        </DataTable>
      </section>

      <Modal
        open={Boolean(calculationInventory)}
        onClose={() => setCalculationInventory(null)}
        title="Calculate inventory"
        description="Run governed calculations and review the non-double-counted Scope 1, 2 and 3 headline."
      >
        {calculationInventory ? (
          <InventoryCalculationRunner
            inventoryId={calculationInventory.id}
            inventoryName={calculationInventory.name}
            onCompleted={inventories.refresh}
          />
        ) : null}
      </Modal>

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
          <label>Organisation<select name="organisation_id" onChange={(event) => setPeriodOrganisationId(event.target.value)} required value={periodOrganisationId}><option value="">Select organisation</option>{(organisations.data?.items ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Period name<input name="name" placeholder="Calendar year 2026" required /></label>
          <label>Start date<input name="start_date" required type="date" /></label>
          <label>End date<input name="end_date" required type="date" /></label>
          <label className="checkbox-field"><input checked={baseYear} name="is_base_year" onChange={(event) => setBaseYear(event.target.checked)} type="checkbox" /> Base year</label>
          {baseYear ? (
            <>
              <label>Reason for selecting this base year<textarea name="base_year_reason" placeholder="Explain why this is a representative and complete base year." required /></label>
              <label>Base-year recalculation policy<textarea name="recalculation_policy" placeholder="Describe structural-change, methodology-change and material-error triggers." required /></label>
            </>
          ) : (
            <label>Comparative period<select name="comparative_reporting_period_id"><option value="">No comparative selected yet</option>{(periods.data?.items ?? []).filter((period) => period.organisation_id === periodOrganisationId).map((period) => <option key={period.id} value={period.id}>{period.name}</option>)}</select></label>
          )}
          <label>Significance threshold (%)<input defaultValue="5" max="100" min="0.0001" name="recalculation_significance_threshold_percent" required step="0.0001" type="number" /></label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setPeriodModal(false)} type="button">Cancel</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "Creating…" : "Create reporting period"}</button></div>
        </form>
      </Modal>
    </>
  );
}
