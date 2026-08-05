"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { AuditReport, AuditReportListItem, Inventory, ListResponse } from "@/lib/types";

export default function AuditReportsPage() {
  const reports = useApiQuery<ListResponse<AuditReportListItem>>("/audit-reports?limit=200");
  const inventories = useApiQuery<ListResponse<Inventory>>("/inventories?limit=200");
  const [generateModal, setGenerateModal] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPath = selectedReportId ? `/audit-reports/${selectedReportId}` : null;
  const selectedReport = useApiQuery<AuditReport>(selectedPath);
  const selectedListItem = useMemo(
    () => reports.data?.items.find((item) => item.id === selectedReportId) ?? null,
    [reports.data, selectedReportId]
  );

  async function generate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const report = await apiRequest<AuditReport>(`/inventories/${form.get("inventory_id")}/audit-reports`, {
        method: "POST",
        body: JSON.stringify({
          finalize: form.get("finalize") === "on",
          scope_2_headline_basis: form.get("scope_2_headline_basis")
        })
      });
      setGenerateModal(false);
      setSelectedReportId(report.id);
      await reports.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Report generation failed.");
    } finally {
      setWorking(false);
    }
  }

  if (reports.loading || inventories.loading) return <LoadingState label="Loading audit reports" />;
  if (reports.error || inventories.error) return <ErrorState message={reports.error ?? inventories.error ?? "Unknown error"} onRetry={() => { void reports.refresh(); void inventories.refresh(); }} />;

  return (
    <>
      <PageHeader eyebrow="Audit-ready output" title="Audit reports" description="Generate immutable, versioned reporting snapshots with canonical SHA-256 hashes." actions={<button className="button button-primary" onClick={() => setGenerateModal(true)} type="button">Generate report</button>} />
      <section className="panel">
        <div className="panel-heading"><div><p className="eyebrow">Report register</p><h2>Generated snapshots</h2></div><span className="record-count">{reports.data?.total ?? 0} reports</span></div>
        <DataTable caption="Audit reports" headers={["Inventory", "Version", "Generated", "Total tCO₂e", "SHA-256", "Status", ""]}>
          {(reports.data?.items ?? []).map((report) => <tr key={report.id}><td><strong>{report.inventory_name}</strong></td><td>v{report.version}</td><td>{new Date(report.generated_at).toLocaleString("en-GB")}</td><td>{Number(report.total_t_co2e).toLocaleString("en-GB", { maximumFractionDigits: 2 })}</td><td><code className="hash">{report.report_sha256.slice(0, 16)}…</code></td><td><StatusBadge status={report.status} /></td><td><button className="text-button" onClick={() => setSelectedReportId(report.id)} type="button">Open</button></td></tr>)}
        </DataTable>
      </section>

      {selectedReportId ? <section className="panel report-preview">
        <div className="panel-heading"><div><p className="eyebrow">Report contents</p><h2>{selectedListItem?.inventory_name ?? "Audit report"}</h2></div></div>
        {selectedReport.loading ? <LoadingState label="Loading report payload" /> : selectedReport.error ? <ErrorState message={selectedReport.error} onRetry={selectedReport.refresh} /> : <pre className="report-json">{JSON.stringify(selectedReport.data?.report_payload ?? {}, null, 2)}</pre>}
      </section> : null}

      <Modal open={generateModal} onClose={() => setGenerateModal(false)} title="Generate audit report" description="Create a deterministic snapshot from an approved inventory.">
        <form className="modal-form" onSubmit={generate}>
          <label>Inventory<select name="inventory_id" required><option value="">Select approved inventory</option>{(inventories.data?.items ?? []).filter((item) => ["approved", "locked", "superseded"].includes(item.status)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>
            Scope 2 headline basis
            <select name="scope_2_headline_basis" required>
              <option value="location_based">Location-based</option>
              <option value="market_based">Market-based (requires verified contractual evidence)</option>
            </select>
          </label>
          <section className="validation-banner">
            <strong>Dual reporting remains in the report</strong>
            <p>Both Scope 2 totals are disclosed. This choice only determines the non-double-counted headline total.</p>
          </section>
          <label className="checkbox-field"><input name="finalize" type="checkbox" /> Finalize report immediately</label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setGenerateModal(false)} type="button">Cancel</button><button className="button button-primary" disabled={working} type="submit">{working ? "Generating…" : "Generate report"}</button></div>
        </form>
      </Modal>
    </>
  );
}
