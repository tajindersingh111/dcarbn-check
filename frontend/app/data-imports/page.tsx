"use client";

import { useMemo, useState } from "react";

import { ErrorState, LoadingState, MutationMessage } from "@/components/api-state";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { apiRequest } from "@/lib/api";
import {
  initialColumnMapping,
  mapCsvRows,
  parseCsv,
  toApiRecord,
  validateImportRow
} from "@/lib/scope3-import";
import type {
  AccountingSourceSystem,
  AccountingTemplate,
  ImportRow,
  ValidatedImportRow
} from "@/lib/scope3-import";
import { useApiQuery } from "@/lib/use-api";

interface ImportBatch {
  id: string;
  status: string;
  records_received: number;
  records_imported: number;
  records_rejected: number;
  source_payload_sha256: string;
  failure_message: string | null;
}

const exampleCsv = `external_customer_id,external_transaction_id,source_system,source_account_code,source_account_name,transaction_date,supplier_name,description,currency_code,net_amount,scope_3_category,reported_kg_co2e,allocation_percentage,supplier_methodology,supplier_methodology_version,supplier_reporting_period_start,supplier_reporting_period_end,supplier_result_calculated_at,boundary_description,assurance_status,evidence_reference,source_document_reference,source_record_version
customer-1042,txn-1-001,xero,5000,Purchased materials,2026-03-31,Example Supplier Ltd,Supplier-specific attributable lifecycle result,GBP,12500.00,1,1000,75,GHG Protocol supplier-specific method,2026.1,2026-01-01,2026-12-31,2026-07-01T00:00:00Z,Cradle-to-gate attributable emissions,third_party_verified,supplier-assurance-2026.pdf,bill-1001,4`;

const friendlyNames: Record<string, string> = {
  external_customer_id: "Customer ID",
  external_transaction_id: "Transaction ID",
  source_system: "Source system",
  transaction_date: "Transaction date",
  supplier_name: "Supplier or investee",
  description: "Description",
  scope_3_category: "Scope 3 category",
  reported_kg_co2e: "Reported kgCO₂e",
  allocation_percentage: "Allocation %",
  supplier_methodology: "Methodology",
  supplier_methodology_version: "Methodology version",
  supplier_reporting_period_start: "Reporting period start",
  supplier_reporting_period_end: "Reporting period end",
  supplier_result_calculated_at: "Result calculated at",
  boundary_description: "Lifecycle boundary",
  assurance_status: "Assurance status",
  evidence_reference: "Evidence reference"
};

function fieldLabel(column: string): string {
  return (
    friendlyNames[column] ??
    column
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

export default function DataImportsPage() {
  const template = useApiQuery<AccountingTemplate>(
    "/integrations/data/accounting/scope-3/template"
  );
  const [source, setSource] = useState<AccountingSourceSystem>("csv");
  const [fileName, setFileName] = useState("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawRows, setRawRows] = useState<string[][]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [rows, setRows] = useState<ValidatedImportRow[]>([]);
  const [selectedRow, setSelectedRow] = useState<number | null>(null);
  const [batch, setBatch] = useState<ImportBatch | null>(null);
  const [parsingError, setParsingError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  const columns = useMemo(
    () => [
      ...(template.data?.required_columns ?? []),
      ...(template.data?.optional_columns ?? [])
    ],
    [template.data]
  );
  const validCount = rows.filter((row) => row.valid).length;
  const invalidCount = rows.length - validCount;
  const selected = rows.find((row) => row.index === selectedRow) ?? null;

  function loadCsv(content: string, name: string) {
    try {
      const parsed = parseCsv(content);
      setFileName(name);
      setHeaders(parsed.headers);
      setRawRows(parsed.rows);
      setMapping(initialColumnMapping(parsed.headers, columns));
      setRows([]);
      setBatch(null);
      setSelectedRow(null);
      setParsingError(null);
      setMessage(
        `${parsed.rows.length} row${parsed.rows.length === 1 ? "" : "s"} detected. Confirm the column mapping.`
      );
    } catch (caught) {
      setParsingError(
        caught instanceof Error ? caught.message : "The CSV could not be read."
      );
    }
  }

  async function readFile(file: File | undefined) {
    if (!file) return;
    loadCsv(await file.text(), file.name);
  }

  function preview() {
    const templateData = template.data;
    if (!templateData) return;
    const missing = templateData.required_columns.filter(
      (column) => !mapping[column]
    );
    if (missing.length > 0) {
      setParsingError(
        `Map every required column before continuing: ${missing
          .map(fieldLabel)
          .join(", ")}.`
      );
      return;
    }
    const mapped = mapCsvRows(headers, rawRows, mapping).map((values) => ({
      ...values,
      source_system: values.source_system || source
    }));
    const validated = mapped.map((values, index) =>
      validateImportRow(values, templateData.required_columns, index + 1)
    );
    setRows(validated);
    setSelectedRow(validated.find((row) => !row.valid)?.index ?? null);
    setParsingError(null);
    setMessage(
      validated.every((row) => row.valid)
        ? "Every row passed the governed pre-import checks."
        : "Correct the highlighted rows before importing."
    );
  }

  function updateRow(index: number, column: string, value: string) {
    const templateData = template.data;
    if (!templateData) return;
    setRows((current) =>
      current.map((row) =>
        row.index === index
          ? validateImportRow(
              { ...row.values, [column]: value },
              templateData.required_columns,
              index
            )
          : row
      )
    );
    setBatch(null);
  }

  async function submitImport() {
    if (rows.length === 0 || invalidCount > 0) return;
    setImporting(true);
    setParsingError(null);
    setMessage(null);
    try {
      const response = await apiRequest<ImportBatch>(
        "/integrations/data/accounting/scope-3/batch",
        {
          method: "POST",
          body: JSON.stringify({
            schema_version: template.data?.schema_version ?? "1.0",
            idempotency_key: `customer-accounting-${source}-${Date.now()}`,
            records: rows.map((row) => toApiRecord(row.values))
          })
        }
      );
      setBatch(response);
      setMessage(
        "The accepted records entered the governed emissions review queue."
      );
    } catch (caught) {
      setParsingError(
        caught instanceof Error ? caught.message : "The import could not be submitted."
      );
    } finally {
      setImporting(false);
    }
  }

  if (template.loading) return <LoadingState label="Loading import contract" />;
  if (template.error) {
    return (
      <ErrorState
        message={template.error}
        onRetry={() => void template.refresh()}
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Customer data collection"
        title="Accounting and CSV import"
        description="Map, validate and reconcile supplier-specific Scope 3 results before they enter your emissions review queue."
      />

      <ol className="import-steps" aria-label="Import progress">
        {["Source and file", "Column mapping", "Validation preview", "Reconciliation"].map(
          (label, index) => {
            const active =
              index === 0
                ? headers.length === 0
                : index === 1
                  ? headers.length > 0 && rows.length === 0
                  : index === 2
                    ? rows.length > 0 && !batch
                    : Boolean(batch);
            return (
              <li className={active ? "import-step-active" : ""} key={label}>
                <span>{index + 1}</span>
                {label}
              </li>
            );
          }
        )}
      </ol>

      <MutationMessage error={parsingError} success={message} />

      <section className="panel import-source-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Step 1</p>
            <h2>Choose the source and file</h2>
          </div>
          <StatusBadge status={headers.length > 0 ? "complete" : "draft"} />
        </div>
        <div className="source-options">
          {(template.data?.supported_source_systems ?? []).map((item) => (
            <button
              aria-pressed={source === item}
              className={source === item ? "source-option source-option-active" : "source-option"}
              key={item}
              onClick={() => setSource(item)}
              type="button"
            >
              <strong>{item === "csv" ? "CSV upload" : item}</strong>
              <small>
                {item === "api"
                  ? "Direct customer system connection"
                  : `Import a ${item} export using the governed template`}
              </small>
            </button>
          ))}
        </div>
        <div className="upload-zone">
          <label className="button button-primary" htmlFor="accounting-file">
            Choose CSV file
          </label>
          <input
            accept=".csv,text/csv"
            id="accounting-file"
            onChange={(event) => void readFile(event.target.files?.[0])}
            type="file"
          />
          <div>
            <strong>{fileName || "No file selected"}</strong>
            <span>
              {rawRows.length > 0
                ? `${rawRows.length} data rows · ${headers.length} columns`
                : "Use the supplied template or load the safe example."}
            </span>
          </div>
          <button
            className="button button-secondary"
            onClick={() => loadCsv(exampleCsv, "scope3-accounting-example.csv")}
            type="button"
          >
            Load example
          </button>
        </div>
      </section>

      {headers.length > 0 ? (
        <section className="panel import-mapping-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 2</p>
              <h2>Confirm column mapping</h2>
            </div>
            <span className="record-count">
              {Object.values(mapping).filter(Boolean).length}/{columns.length} mapped
            </span>
          </div>
          <div className="mapping-grid">
            {columns.map((column) => (
              <label key={column}>
                {fieldLabel(column)}
                {template.data?.required_columns.includes(column) ? " *" : ""}
                <select
                  aria-label={`Map ${fieldLabel(column)}`}
                  value={mapping[column] ?? ""}
                  onChange={(event) =>
                    setMapping((current) => ({
                      ...current,
                      [column]: event.target.value
                    }))
                  }
                >
                  <option value="">Do not import</option>
                  {headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <div className="button-row">
            <button className="button button-primary" onClick={preview} type="button">
              Build validation preview
            </button>
          </div>
        </section>
      ) : null}

      {rows.length > 0 ? (
        <section className="panel import-preview-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 3</p>
              <h2>Review and correct the data</h2>
            </div>
            <div className="preview-counts">
              <span className="status-chip status-chip-success">{validCount} valid</span>
              <span className={invalidCount ? "status-chip status-chip-error" : "status-chip"}>
                {invalidCount} need attention
              </span>
            </div>
          </div>
          <div className="table-shell">
            <table>
              <caption>Scope 3 import validation preview</caption>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Supplier</th>
                  <th>Category</th>
                  <th>Reported kgCO₂e</th>
                  <th>Evidence</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.index}>
                    <td>{row.index}</td>
                    <td>{row.values.supplier_name}</td>
                    <td>{row.values.scope_3_category}</td>
                    <td>{row.values.reported_kg_co2e}</td>
                    <td>{row.values.evidence_reference}</td>
                    <td>
                      <StatusBadge status={row.valid ? "complete" : "failed"} />
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => setSelectedRow(row.index)}
                        type="button"
                      >
                        {row.valid ? "Review" : "Correct"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selected ? (
            <div className="correction-panel" aria-label={`Correct row ${selected.index}`}>
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Row {selected.index}</p>
                  <h2>Correction form</h2>
                </div>
                <button
                  className="text-button"
                  onClick={() => setSelectedRow(null)}
                  type="button"
                >
                  Close
                </button>
              </div>
              <div className="mapping-grid">
                {(template.data?.required_columns ?? []).map((column) => (
                  <label key={column}>
                    {fieldLabel(column)}
                    <input
                      aria-invalid={Boolean(selected.errors[column])}
                      aria-label={`Row ${selected.index} ${fieldLabel(column)}`}
                      value={selected.values[column] ?? ""}
                      onChange={(event) =>
                        updateRow(selected.index, column, event.target.value)
                      }
                    />
                    {selected.errors[column] ? (
                      <small className="field-error">{selected.errors[column]}</small>
                    ) : null}
                  </label>
                ))}
              </div>
            </div>
          ) : null}

          <div className="import-submit-row">
            <p>
              Imported categories remain suggestions until a customer reviewer confirms
              the inventory classification and evidence.
            </p>
            <button
              className="button button-primary"
              disabled={importing || invalidCount > 0}
              onClick={() => void submitImport()}
              type="button"
            >
              {importing ? "Importing…" : `Import ${validCount} validated rows`}
            </button>
          </div>
        </section>
      ) : null}

      {batch ? (
        <section className="panel reconciliation-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Step 4</p>
              <h2>Import reconciliation</h2>
            </div>
            <StatusBadge status={batch.records_rejected ? "review_required" : "complete"} />
          </div>
          <div className="reconciliation-grid">
            <div><span>Received</span><strong>{batch.records_received}</strong></div>
            <div><span>Imported</span><strong>{batch.records_imported}</strong></div>
            <div><span>Rejected</span><strong>{batch.records_rejected}</strong></div>
            <div><span>Batch status</span><strong>{batch.status}</strong></div>
          </div>
          <p className="hash-line">
            Audit fingerprint: <code>{batch.source_payload_sha256}</code>
          </p>
          {batch.failure_message ? (
            <p className="field-error">{batch.failure_message}</p>
          ) : null}
        </section>
      ) : null}
    </>
  );
}
