"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { ApprovalQueueItem, Inventory, ListResponse } from "@/lib/types";

export default function ApprovalsPage() {
  const approvals = useApiQuery<ListResponse<ApprovalQueueItem>>("/inventory-approvals?limit=200");
  const inventories = useApiQuery<ListResponse<Inventory>>(
    "/inventories?limit=200&scope_2_headline_basis=location_based"
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [requestModal, setRequestModal] = useState(false);
  const [requestInventoryId, setRequestInventoryId] = useState("");
  const [reason, setReason] = useState("All evidence, boundaries, factor lineage and calculations have been reviewed.");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selected = useMemo(
    () => approvals.data?.items.find((item) => item.id === selectedId) ?? approvals.data?.items[0] ?? null,
    [approvals.data, selectedId]
  );

  async function requestApproval(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      await apiRequest(`/inventories/${form.get("inventory_id")}/approval-requests`, {
        method: "POST",
        body: JSON.stringify({ calculation_run_id: form.get("calculation_run_id") })
      });
      setRequestModal(false);
      await approvals.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval request failed.");
    } finally {
      setWorking(false);
    }
  }

  async function action(type: "start" | "approve" | "reject" | "lock") {
    if (!selected) return;
    setWorking(true);
    setError(null);
    setMessage(null);
    try {
      if (type === "start") {
        await apiRequest(`/inventory-approvals/${selected.id}/start-review`, { method: "POST" });
      } else if (type === "lock") {
        await apiRequest(`/inventories/${selected.inventory_id}/lock`, {
          method: "POST",
          body: JSON.stringify({ lock_reason: reason })
        });
      } else {
        await apiRequest(`/inventory-approvals/${selected.id}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision: type === "approve" ? "approved" : "rejected", decision_reason: reason })
        });
      }
      setMessage("Approval workflow updated.");
      await approvals.refresh();
      await inventories.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Approval action failed.");
    } finally {
      setWorking(false);
    }
  }

  if (approvals.loading || inventories.loading) return <LoadingState label="Loading approval workflow" />;
  if (approvals.error || inventories.error) return <ErrorState message={approvals.error ?? inventories.error ?? "Unknown error"} onRetry={() => { void approvals.refresh(); void inventories.refresh(); }} />;

  return (
    <>
      <PageHeader eyebrow="Inventory governance" title="Approval workflow" description="Independently review evidence, boundaries, factor lineage and completed calculations." actions={<button className="button button-primary" onClick={() => setRequestModal(true)} type="button">Request approval</button>} />
      <section className="split-layout">
        <article className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Approval queue</p><h2>Inventory submissions</h2></div></div>
          <DataTable caption="Inventory approval requests" headers={["Inventory", "Requested by", "Controls", "Status"]}>
            {(approvals.data?.items ?? []).map((item) => {
              const controls = [item.evidence_complete, item.boundary_complete, item.factor_lineage_complete, item.calculation_complete].filter(Boolean).length;
              return <tr className={item.id === selected?.id ? "selected-row" : ""} key={item.id} onClick={() => setSelectedId(item.id)}><td><div className="stacked-cell"><strong>{item.inventory_name}</strong><span>Version {item.version}</span></div></td><td>{item.requested_by}</td><td>{controls}/4</td><td><StatusBadge status={item.status} /></td></tr>;
            })}
          </DataTable>
        </article>
        <aside className="panel detail-panel">
          {selected ? <>
            <div className="panel-heading"><div><p className="eyebrow">Decision</p><h2>{selected.inventory_name}</h2></div><StatusBadge status={selected.status} /></div>
            <div className="control-list">
              {[
                ["Evidence complete", selected.evidence_complete],
                ["Organisational boundary approved", selected.boundary_complete],
                ["Factor lineage complete", selected.factor_lineage_complete],
                ["Calculation results complete", selected.calculation_complete]
              ].map(([label, complete]) => <div className="control-item" key={String(label)}><span className={complete ? "control-check" : "control-check control-missing"}>{complete ? "✓" : "!"}</span><span>{label}</span></div>)}
            </div>
            <label className="full-width-field">Decision reason<textarea rows={4} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <MutationMessage error={error} success={message} />
            <div className="button-row">
              {selected.status === "pending" ? <button className="button button-primary" disabled={working} onClick={() => void action("start")} type="button">Start review</button> : null}
              {selected.status === "in_review" ? <><button className="button button-danger" disabled={working} onClick={() => void action("reject")} type="button">Reject</button><button className="button button-primary" disabled={working} onClick={() => void action("approve")} type="button">Approve inventory</button></> : null}
              {selected.status === "approved" ? <button className="button button-primary" disabled={working} onClick={() => void action("lock")} type="button">Lock inventory</button> : null}
            </div>
          </> : <p>No approval requests exist.</p>}
        </aside>
      </section>

      <Modal open={requestModal} onClose={() => setRequestModal(false)} title="Request inventory approval" description="Submit one completed calculation run for independent review.">
        <form className="modal-form" onSubmit={requestApproval}>
          <label>Inventory<select name="inventory_id" required value={requestInventoryId} onChange={(event) => setRequestInventoryId(event.target.value)}><option value="">Select inventory</option>{(inventories.data?.items ?? []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <CalculationRunSelect inventoryId={requestInventoryId} />
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setRequestModal(false)} type="button">Cancel</button><button className="button button-primary" disabled={working || !requestInventoryId} type="submit">{working ? "Submitting…" : "Submit approval request"}</button></div>
        </form>
      </Modal>
    </>
  );
}

function CalculationRunSelect({ inventoryId }: { inventoryId: string }) {
  const query = useApiQuery<ListResponse<{ id: string; version: number; status: string; result_count: number }>>(inventoryId ? `/inventories/${inventoryId}/calculation-runs` : null);
  return <label>Calculation run<select name="calculation_run_id" required disabled={!inventoryId || query.loading}><option value="">Select completed run</option>{(query.data?.items ?? []).filter((item) => item.status === "completed").map((item) => <option key={item.id} value={item.id}>Version {item.version} · {item.result_count} results</option>)}</select>{query.error ? <small className="field-error">{query.error}</small> : null}</label>;
}
