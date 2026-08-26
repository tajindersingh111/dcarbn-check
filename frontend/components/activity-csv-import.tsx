"use client";

import { useEffect, useMemo, useState } from "react";

import {
  governedMethods,
  type GovernedMethodOption
} from "@/components/activity-form";
import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import { parseCsv } from "@/lib/scope3-import";
import type { Inventory, ListResponse, Organisation } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

type ImportStatus = "ready" | "importing" | "imported" | "failed";

interface ActivityImportRow {
  index: number;
  values: Record<string, string>;
  method: GovernedMethodOption | null;
  errors: string[];
  status: ImportStatus;
}

const requiredColumns = [
  "calculation_method_id",
  "activity_date",
  "description",
  "activity_value",
  "activity_unit",
  "source_record_id"
] as const;

const templateCsv = `calculation_method_id,activity_date,description,activity_value,activity_unit,evidence_reference,source_record_id,geography_code
scope1.stationary_diesel.litres.uk_2026.v1,2026-03-31,Backup generator diesel,1250,litres,fuel-invoice-001.pdf,fuel-001,GB
scope2.location_electricity.kwh.uk_2026.v1,2026-03-31,Purchased electricity,50000,kWh,electricity-bill-001.pdf,electricity-001,GB
scope3.category6.domestic_air.with_rf.passenger_km.uk_2026.v1,2026-03-31,Domestic business flights,8500,passenger.km,travel-report-001.pdf,travel-001,GB`;

const hvoTemplateCsv = `calculation_method_id,activity_date,description,activity_value,activity_unit,evidence_reference,source_record_id,geography_code
scope1.mobile_combustion.hvo.litres.uk_2023.v1,2023-12-31,HVO fleet fuel combustion,1000,litres,hvo-fuel-ledger-fy2024.xlsx,hvo-scope1-2023,GB
scope3.category3.hvo_wtt.litres.uk_2023.v1,2023-12-31,HVO fuel well-to-tank,1000,litres,hvo-fuel-ledger-fy2024.xlsx,hvo-wtt-2023,GB
scope1.mobile_combustion.hvo.litres.uk_2024.v1,2024-10-31,HVO fleet fuel combustion,976227,litres,hvo-fuel-ledger-fy2024.xlsx,hvo-scope1-fy2024,GB
scope3.category3.hvo_wtt.litres.uk_2024.v1,2024-10-31,HVO fuel well-to-tank,976227,litres,hvo-fuel-ledger-fy2024.xlsx,hvo-wtt-fy2024,GB
scope1.mobile_combustion.hvo.litres.uk_2025.v1,2025-12-31,HVO fleet fuel combustion,1000,litres,hvo-fuel-ledger-2025.xlsx,hvo-scope1-2025,GB
scope3.category3.hvo_wtt.litres.uk_2025.v1,2025-12-31,HVO fuel well-to-tank,1000,litres,hvo-fuel-ledger-2025.xlsx,hvo-wtt-2025,GB
scope1.mobile_combustion.hvo.litres.uk_2026.v1,2026-12-31,HVO fleet fuel combustion,1000,litres,hvo-fuel-ledger-2026.xlsx,hvo-scope1-2026,GB
scope3.category3.hvo_wtt.litres.uk_2026.v1,2026-12-31,HVO fuel well-to-tank,1000,litres,hvo-fuel-ledger-2026.xlsx,hvo-wtt-2026,GB`;

function normaliseHeader(value: string): string {
  const normalised = value.trim().toLowerCase().replace(/[\s-]+/g, "_");
  return normalised === "calculation_method" ? "calculation_method_id" : normalised;
}

function rowFromCsv(
  headers: string[],
  cells: string[],
  index: number,
  inventory: Inventory | undefined
): ActivityImportRow {
  const values = Object.fromEntries(
    headers.map((header, columnIndex) => [
      normaliseHeader(header),
      cells[columnIndex]?.trim() ?? ""
    ])
  );
  const errors: string[] = [];
  for (const column of requiredColumns) {
    if (!values[column]) errors.push(`${column.replaceAll("_", " ")} is required`);
  }

  const method =
    governedMethods.find((item) => item.id === values.calculation_method_id) ?? null;
  if (values.calculation_method_id && !method) {
    errors.push(
      `Calculation method “${values.calculation_method_id}” is not governed in this release`
    );
  }
  if (method && values.activity_unit !== method.activityUnit) {
    errors.push(`Unit must be ${method.activityUnit} for the selected method`);
  }
  if (method?.specialist && !values.evidence_reference) {
    errors.push("Evidence reference is required for specialist HVO methods");
  }
  if (
    method?.reportingYear &&
    values.activity_date &&
    values.activity_date.slice(0, 4) !== method.reportingYear
  ) {
    errors.push(`Activity date must be in ${method.reportingYear} for the selected HVO method`);
  }

  const amount = Number(values.activity_value);
  if (values.activity_value && (!Number.isFinite(amount) || amount <= 0)) {
    errors.push("Activity value must be a positive number");
  }
  if (
    values.activity_date &&
    (!/^\d{4}-\d{2}-\d{2}$/.test(values.activity_date) ||
      Number.isNaN(Date.parse(values.activity_date)))
  ) {
    errors.push("Activity date must use YYYY-MM-DD");
  }
  if (
    inventory &&
    values.activity_date &&
    (values.activity_date < inventory.reporting_period_start ||
      values.activity_date > inventory.reporting_period_end)
  ) {
    errors.push(
      `Activity date must fall within ${inventory.reporting_period_start} to ${inventory.reporting_period_end}`
    );
  }

  return { index, values, method, errors, status: "ready" };
}

function activityPayload(
  row: ActivityImportRow,
  organisationId: string
): Record<string, unknown> {
  const method = row.method!;
  return {
    organisation_id: organisationId,
    activity_type: method.activityType,
    scope: method.scope,
    scope_2_method: method.scope === "scope_2" ? "location_based" : "not_applicable",
    scope_3_category: method.scope === "scope_3" ? Number(method.scope3Category) : null,
    activity_date: row.values.activity_date,
    description: row.values.description,
    activity_value: row.values.activity_value,
    activity_unit: method.activityUnit,
    geography_code: row.values.geography_code || "GB",
    factor_level_1: method.factorLevel1,
    factor_level_2: method.factorLevel2 || null,
    factor_level_3: method.factorLevel3 || null,
    factor_level_4: method.factorLevel4 || null,
    factor_column_text: method.factorColumnText || null,
    lifecycle_boundary: method.lifecycleBoundary || null,
    allocation_percentage: "100.00",
    data_quality_level: "primary",
    data_quality_score: 90,
    source_system: "csv-upload",
    source_record_id: row.values.source_record_id,
    evidence_reference: row.values.evidence_reference || null,
    metadata_json: { calculation_method_id: method.id }
  };
}

export function ActivityCsvImport({
  onShowSupplierResults
}: {
  onShowSupplierResults: () => void;
}) {
  const organisations = useApiQuery<ListResponse<Organisation>>(
    "/organisations?limit=200"
  );
  const inventories = useApiQuery<ListResponse<Inventory>>(
    "/inventories?limit=200&scope_2_headline_basis=location_based"
  );
  const [organisationId, setOrganisationId] = useState("");
  const [inventoryId, setInventoryId] = useState("");
  const [fileName, setFileName] = useState("");
  const [sourceRows, setSourceRows] = useState<{ headers: string[]; rows: string[][] } | null>(
    null
  );
  const [rows, setRows] = useState<ActivityImportRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const filteredInventories = useMemo(
    () =>
      (inventories.data?.items ?? []).filter(
        (inventory) => !organisationId || inventory.organisation_id === organisationId
      ),
    [inventories.data, organisationId]
  );
  const inventory = filteredInventories.find((item) => item.id === inventoryId);
  const validCount = rows.filter((row) => row.errors.length === 0).length;
  const importedCount = rows.filter((row) => row.status === "imported").length;

  useEffect(() => {
    if (!organisationId && organisations.data?.items[0]) {
      setOrganisationId(organisations.data.items[0].id);
    }
  }, [organisationId, organisations.data]);

  useEffect(() => {
    if (!filteredInventories.some((item) => item.id === inventoryId)) {
      setInventoryId(filteredInventories[0]?.id ?? "");
    }
  }, [filteredInventories, inventoryId]);

  useEffect(() => {
    if (!sourceRows) return;
    setRows(
      sourceRows.rows.map((cells, index) =>
        rowFromCsv(sourceRows.headers, cells, index + 2, inventory)
      )
    );
  }, [inventory, sourceRows]);

  function downloadTemplate() {
    const blob = new Blob([templateCsv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "dcarbn-activity-upload-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadHvoTemplate() {
    const blob = new Blob([hvoTemplateCsv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "dcarbn-uk-2023-2026-hvo-activity-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function readFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setMessage(null);
    try {
      const parsed = parseCsv(await file.text());
      const normalised = parsed.headers.map(normaliseHeader);
      if (new Set(normalised).size !== normalised.length) {
        throw new Error("The CSV contains duplicate column headings after normalisation.");
      }
      const missing = requiredColumns.filter((column) => !normalised.includes(column));
      if (missing.length > 0) {
        throw new Error(`Missing columns: ${missing.join(", ")}.`);
      }
      const sourceIds = parsed.rows.map(
        (cells) => cells[normalised.indexOf("source_record_id")]?.trim() ?? ""
      );
      const duplicate = sourceIds.find(
        (value, index) => value && sourceIds.indexOf(value) !== index
      );
      if (duplicate) throw new Error(`Duplicate source_record_id: ${duplicate}.`);
      setFileName(file.name);
      setSourceRows({ headers: parsed.headers, rows: parsed.rows });
      setMessage(`${parsed.rows.length} rows read. Review the validation result below.`);
    } catch (caught) {
      setFileName("");
      setSourceRows(null);
      setRows([]);
      setError(caught instanceof Error ? caught.message : "The CSV could not be read.");
    }
  }

  async function submitImport() {
    if (!inventoryId || rows.length === 0 || validCount !== rows.length) return;
    setImporting(true);
    setError(null);
    setMessage(null);
    let failures = 0;
    for (const row of rows) {
      setRows((current) =>
        current.map((item) =>
          item.index === row.index ? { ...item, status: "importing" } : item
        )
      );
      try {
        await apiRequest(`/inventories/${inventoryId}/activities`, {
          method: "POST",
          body: JSON.stringify(activityPayload(row, organisationId))
        });
        setRows((current) =>
          current.map((item) =>
            item.index === row.index ? { ...item, status: "imported" } : item
          )
        );
      } catch (caught) {
        failures += 1;
        const detail = caught instanceof Error ? caught.message : "Import failed";
        setRows((current) =>
          current.map((item) =>
            item.index === row.index
              ? { ...item, status: "failed", errors: [...item.errors, detail] }
              : item
          )
        );
      }
    }
    setImporting(false);
    setMessage(
      failures === 0
        ? `All ${rows.length} activity records were imported and audited.`
        : `${rows.length - failures} records imported; ${failures} need attention.`
    );
  }

  if (organisations.loading || inventories.loading) {
    return <LoadingState label="Loading upload workspace" />;
  }
  if (organisations.error || inventories.error) {
    return (
      <ErrorState
        message={organisations.error ?? inventories.error ?? "Unknown error"}
        onRetry={() => {
          void organisations.refresh();
          void inventories.refresh();
        }}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Customer data upload"
        title="Upload Scope 1, 2 and 3 activity data"
        description="Choose the customer and reporting inventory once, upload one simple CSV, and let D-carbN validate every row before it is saved."
        actions={
          <button className="button button-secondary" onClick={onShowSupplierResults} type="button">
            Supplier-calculated Scope 3
          </button>
        }
      />

      <ol className="import-steps" aria-label="Activity import progress">
        {["Choose destination", "Upload CSV", "Check rows", "Import"].map((label, index) => {
          const active =
            index === 0
              ? !inventoryId
              : index === 1
                ? Boolean(inventoryId && !sourceRows)
                : index === 2
                  ? rows.length > 0 && importedCount === 0
                  : importedCount > 0;
          return (
            <li className={active ? "import-step-active" : ""} key={label}>
              <span>{index + 1}</span>
              {label}
            </li>
          );
        })}
      </ol>

      <MutationMessage error={error} success={message} />

      <section className="panel import-source-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Step 1</p>
            <h2>Where should the data go?</h2>
          </div>
          <StatusBadge status={inventoryId ? "complete" : "draft"} />
        </div>
        <div className="form-grid">
          <label>
            Customer organisation
            <select value={organisationId} onChange={(event) => setOrganisationId(event.target.value)}>
              {(organisations.data?.items ?? []).map((organisation) => (
                <option key={organisation.id} value={organisation.id}>{organisation.name}</option>
              ))}
            </select>
          </label>
          <label>
            Reporting inventory
            <select required value={inventoryId} onChange={(event) => setInventoryId(event.target.value)}>
              {filteredInventories.length === 0 ? <option value="">Create an inventory first</option> : null}
              {filteredInventories.map((item) => (
                <option key={item.id} value={item.id}>{item.name} · {item.reporting_period_name}</option>
              ))}
            </select>
          </label>
          <label>
            Reporting dates
            <input
              disabled
              value={inventory ? `${inventory.reporting_period_start} to ${inventory.reporting_period_end}` : "Select an inventory"}
            />
          </label>
        </div>
      </section>

      <section className="panel import-source-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Step 2</p>
            <h2>Choose one activity CSV</h2>
          </div>
          <div className="button-row">
            <button className="button button-secondary" onClick={downloadTemplate} type="button">
              Download standard template
            </button>
            <button className="button button-secondary" onClick={downloadHvoTemplate} type="button">
              Download UK 2023–2026 HVO template
            </button>
          </div>
        </div>
        <div className="upload-zone">
          <label className="button button-primary" htmlFor="activity-csv-file">Choose CSV file</label>
          <input
            accept=".csv,text/csv"
            id="activity-csv-file"
            onChange={(event) => void readFile(event.target.files?.[0])}
            type="file"
          />
          <div>
            <strong>{fileName || "No file selected"}</strong>
            <span>
              {sourceRows ? `${sourceRows.rows.length} activity rows detected` : "Eight clear columns; no manual column mapping."}
            </span>
          </div>
          <span>CSV only</span>
        </div>
      </section>

      {rows.length > 0 ? (
        <section className="panel import-preview-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 3</p>
              <h2>Check before import</h2>
            </div>
            <div className="preview-counts">
              <span className="status-chip status-chip-success">{validCount} ready</span>
              <span className={validCount === rows.length ? "status-chip" : "status-chip status-chip-error"}>
                {rows.length - validCount} need attention
              </span>
            </div>
          </div>
          <div className="table-shell">
            <table>
              <caption>Activity CSV validation preview</caption>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Value</th>
                  <th>Scope / method</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.index}>
                    <td>{row.index}</td>
                    <td>{row.values.activity_date}</td>
                    <td>{row.values.description}</td>
                    <td>{row.values.activity_value} {row.values.activity_unit}</td>
                    <td>{row.method?.label ?? row.values.calculation_method_id}</td>
                    <td>
                      <StatusBadge status={row.status === "imported" ? "complete" : row.errors.length ? "failed" : "draft"} />
                      {row.errors.map((item) => <small className="field-error" key={item}>{item}</small>)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="import-submit-row">
            <p>
              HVO is a specialist method and is never assumed. Its template records the same evidenced litres once for Scope 1 combustion and once for Scope 3 Category 3 well-to-tank; the report discloses biogenic CO₂ outside the scopes.
            </p>
            <button
              className="button button-primary"
              disabled={importing || !inventoryId || validCount !== rows.length || importedCount === rows.length}
              onClick={() => void submitImport()}
              type="button"
            >
              {importing ? "Importing…" : `Import ${validCount} validated rows`}
            </button>
          </div>
        </section>
      ) : null}
    </>
  );
}
