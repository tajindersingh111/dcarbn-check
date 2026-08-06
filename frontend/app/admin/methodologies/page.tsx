"use client";

import { useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { DataTable } from "@/components/data-table";
import { PlusIcon } from "@/components/icons";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { useApiQuery } from "@/lib/use-api";
import type { ListResponse } from "@/lib/types";

interface MethodologyVersion {
  id: string;
  method_key: string;
  version: number;
  name: string;
  status: string;
  scope: string;
  scope_3_category: number | null;
  jurisdiction: string;
  reporting_year: number | null;
  effective_from: string;
  effective_to: string | null;
  expression: string;
  output_unit: string;
  input_schema: { inputs: Array<{ name: string }> };
  golden_tests: Array<{ inputs: Record<string, string> }>;
  source_reference: string;
  change_reason: string;
  created_by: string;
  reviewed_by: string | null;
  approved_by: string | null;
  activated_by: string | null;
}

function lifecycleAction(item: MethodologyVersion): string | undefined {
  if (item.status === "draft") return "submit";
  if (item.status === "in_review") return item.reviewed_by ? "approve" : "review";
  if (item.status === "approved") return "activate";
  if (item.status === "active") return "retire";
  return undefined;
}

interface Comparison {
  changed_fields: Record<string, unknown>;
}

interface ImpactPreview {
  baseline_output: string;
  candidate_output: string;
  absolute_change: string;
  percentage_change: string | null;
  output_unit: string;
}

export default function MethodologiesPage() {
  const methods = useApiQuery<ListResponse<MethodologyVersion>>("/methodologies");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actingId, setActingId] = useState<string | null>(null);
  const [scope, setScope] = useState("scope_2");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);

  async function createVersion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const inputName = String(form.get("input_name"));
      const inputUnit = String(form.get("input_unit"));
      const factorName = "factor_value";
      await apiRequest("/methodologies", {
        method: "POST",
        body: JSON.stringify({
          method_key: form.get("method_key"),
          name: form.get("name"),
          scope,
          scope_3_category:
            scope === "scope_3" ? Number(form.get("scope_3_category")) : null,
          jurisdiction: form.get("jurisdiction"),
          reporting_year: Number(form.get("reporting_year")),
          effective_from: form.get("effective_from"),
          effective_to: form.get("effective_to") || null,
          expression: form.get("expression"),
          output_unit: form.get("output_unit"),
          inputs: [
            { name: inputName, unit: inputUnit, required: true, minimum: "0" },
            {
              name: factorName,
              unit: String(form.get("factor_unit")),
              required: true,
              minimum: "0"
            },
            {
              name: "allocation_percentage",
              unit: "percent",
              required: true,
              minimum: "0",
              maximum: "100"
            }
          ],
          validation_rules: [],
          golden_tests: [{
            name: "Administrator release control",
            inputs: {
              [inputName]: String(form.get("golden_activity_value")),
              [factorName]: String(form.get("golden_factor_value")),
              allocation_percentage: "100"
            },
            expected_output: String(form.get("golden_expected_output")),
            tolerance: String(form.get("golden_tolerance") || "0")
          }],
          source_reference: form.get("source_reference"),
          change_reason: form.get("change_reason")
        })
      });
      setOpen(false);
      setMessage("Draft methodology version created. Submit it for independent review when ready.");
      await methods.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Methodology could not be created.");
    } finally {
      setSaving(false);
    }
  }

  async function transition(item: MethodologyVersion, action: string) {
    setActingId(item.id);
    setError(null);
    setMessage(null);
    try {
      await apiRequest(`/methodologies/${item.id}/${action}`, { method: "POST" });
      setMessage(`${item.name} moved through the ${action} control.`);
      await methods.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Lifecycle action failed.");
    } finally {
      setActingId(null);
    }
  }

  async function compareSelected() {
    if (selectedIds.length !== 2) return;
    setComparing(true);
    setError(null);
    try {
      const [baselineId, candidateId] = selectedIds;
      const baseline = methods.data?.items.find((item) => item.id === baselineId);
      if (!baseline) throw new Error("Baseline methodology was not found.");
      const comparison = await apiRequest<Comparison>(
        `/methodologies/${baselineId}/compare/${candidateId}`
      );
      const inputs = baseline.golden_tests[0]?.inputs;
      if (!inputs) throw new Error("A baseline golden test is required for impact preview.");
      const impact = await apiRequest<ImpactPreview>(
        `/methodologies/${baselineId}/impact-preview/${candidateId}`,
        { method: "POST", body: JSON.stringify({ inputs }) }
      );
      setMessage(
        `${Object.keys(comparison.changed_fields).length} controlled fields changed. ` +
        `Impact: ${impact.baseline_output} → ${impact.candidate_output} ${impact.output_unit} ` +
        `(${impact.percentage_change ?? "not applicable"}%). No inventory was changed.`
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Version comparison failed.");
    } finally {
      setComparing(false);
    }
  }

  if (methods.loading) return <LoadingState label="Loading methodology registry" />;
  if (methods.error) return <ErrorState message={methods.error} onRetry={() => void methods.refresh()} />;

  return (
    <>
      <PageHeader
        eyebrow="Platform governance"
        title="Methodology registry"
        description="Create and approve versioned formulas without changing historical customer reports."
        actions={<button className="button button-primary" onClick={() => setOpen(true)} type="button"><PlusIcon /> New version</button>}
      />
      <section className="validation-banner">
        <strong>Controlled change process</strong>
        <p>Published versions are immutable. Every new formula must pass its golden tests and independent review before activation.</p>
      </section>
      <MutationMessage error={error} success={message} />
      <section className="panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Version register</p><h2>Calculation methodologies</h2></div>
          <div className="button-row">
            <span className="record-count">{methods.data?.total ?? 0} versions</span>
            <button className="button button-secondary" disabled={selectedIds.length !== 2 || comparing} onClick={() => void compareSelected()} type="button">
              {comparing ? "Comparing…" : "Compare selected"}
            </button>
          </div>
        </div>
        <DataTable caption="Calculation methodology versions" headers={["Select", "Method", "Version", "Scope", "Effective", "Status", "Control"]}>
          {(methods.data?.items ?? []).map((item) => {
            const action = lifecycleAction(item);
            return (
              <tr key={item.id}>
                <td><input aria-label={`Select ${item.name} v${item.version}`} checked={selectedIds.includes(item.id)} disabled={!selectedIds.includes(item.id) && selectedIds.length >= 2} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} type="checkbox" /></td>
                <td><div className="stacked-cell"><strong>{item.name}</strong><span>{item.method_key}</span></div></td>
                <td>v{item.version}</td>
                <td>{item.scope.replace("_", " ")}{item.scope_3_category ? ` · Cat ${item.scope_3_category}` : ""}</td>
                <td>{item.effective_from}{item.effective_to ? ` – ${item.effective_to}` : ""}</td>
                <td><StatusBadge status={item.status} /></td>
                <td>{action ? <button className="button button-secondary" disabled={actingId === item.id} onClick={() => void transition(item, action)} type="button">{action}</button> : "—"}</td>
              </tr>
            );
          })}
        </DataTable>
      </section>

      <Modal open={open} onClose={() => setOpen(false)} title="Create methodology version" description="Define a draft formula and its release-control example.">
        <form className="modal-form" onSubmit={createVersion}>
          <label>Method key<input name="method_key" placeholder="scope2.location_electricity" required /></label>
          <label>Display name<input name="name" required /></label>
          <label>Scope<select name="scope" onChange={(event) => setScope(event.target.value)} value={scope}><option value="scope_1">Scope 1</option><option value="scope_2">Scope 2</option><option value="scope_3">Scope 3</option></select></label>
          {scope === "scope_3" ? <label>Scope 3 category<input max="15" min="1" name="scope_3_category" required type="number" /></label> : null}
          <div className="form-grid">
            <label>Jurisdiction<input defaultValue="GB" name="jurisdiction" required /></label>
            <label>Reporting year<input defaultValue="2026" name="reporting_year" required type="number" /></label>
            <label>Effective from<input name="effective_from" required type="date" /></label>
            <label>Effective to<input name="effective_to" type="date" /></label>
          </div>
          <label>Formula expression<input defaultValue="activity_value * factor_value * allocation_percentage / 100" name="expression" required /></label>
          <div className="form-grid">
            <label>Activity variable<input defaultValue="activity_value" name="input_name" required /></label>
            <label>Activity unit<input defaultValue="kWh" name="input_unit" required /></label>
            <label>Factor unit<input defaultValue="kg CO2e/kWh" name="factor_unit" required /></label>
            <label>Output unit<input defaultValue="kg CO2e" name="output_unit" required /></label>
          </div>
          <div className="form-grid">
            <label>Golden activity value<input defaultValue="1000" name="golden_activity_value" required /></label>
            <label>Golden factor value<input name="golden_factor_value" required /></label>
            <label>Expected output<input name="golden_expected_output" required /></label>
            <label>Tolerance<input defaultValue="0" name="golden_tolerance" required /></label>
          </div>
          <label>Official source URL<input name="source_reference" required type="url" /></label>
          <label>Reason for change<textarea minLength={20} name="change_reason" required rows={3} /></label>
          <MutationMessage error={error} />
          <div className="button-row modal-actions"><button className="button button-secondary" onClick={() => setOpen(false)} type="button">Cancel</button><button className="button button-primary" disabled={saving} type="submit">{saving ? "Creating…" : "Create draft version"}</button></div>
        </form>
      </Modal>
    </>
  );
}
